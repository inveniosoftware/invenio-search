# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2024 CERN.
# Copyright (C)      2022 TU Wien.
# Copyright (C) 2025 Graz University of Technology.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Invenio module for information retrieval."""

import json
import os
import warnings
from importlib.resources import files

import dictdiffer
from invenio_base.utils import entry_points
from werkzeug.utils import cached_property

from . import config
from .cli import index as index_cmd
from .engine import ES, OS, SEARCH_DISTRIBUTION, SearchEngine, dsl, search
from .errors import IndexAlreadyExistsError, NotAllowedMappingUpdate
from .utils import (
    build_alias_name,
    build_index_from_parts,
    build_index_name,
    timestamp_suffix,
)


class _SearchState(object):
    """Store connection to elastic client and registered indexes."""

    def __init__(
        self,
        app,
        entry_point_group_mappings=None,
        entry_point_group_templates=None,
        entry_point_group_component_templates=None,
        entry_point_group_index_templates=None,
        **kwargs,
    ):
        """Initialize state.

        :param app: An instance of :class:`~flask.app.Flask`.
        :param entry_point_group_mappings:
            The entrypoint group name to load mappings.
        :param entry_point_group_templates:
            The entrypoint group name to load templates.
        """
        self.app = app
        self.mappings = {}
        self.aliases = {}
        self._client = kwargs.get("client")
        self.entry_point_group_templates = entry_point_group_templates
        self.entry_point_group_component_templates = (
            entry_point_group_component_templates
        )
        self.entry_point_group_index_templates = entry_point_group_index_templates
        self._current_suffix = None

        if entry_point_group_mappings:
            self.load_entry_point_group_mappings(entry_point_group_mappings)

    @property
    def current_suffix(self):
        """Return the current suffix."""
        if self._current_suffix is None:
            self._current_suffix = timestamp_suffix()
        return self._current_suffix

    def _collect_templates(self, entrypoint_group):
        """Load actions from an entry point group."""
        result = []
        for ep in entry_points(group=entrypoint_group):
            loaded_ep = ep.load()

            if callable(loaded_ep):
                for template_dir in loaded_ep():
                    result.append(self.register_templates(template_dir))
            else:
                result.append(self.register_templates(ep.module))

        templates = {}
        for template in result:
            for name, path in template.items():
                templates[name] = path
        return templates

    @cached_property
    def templates(self):
        """Generate a dictionary with template names and file paths."""
        return self._collect_templates(self.entry_point_group_templates)

    @cached_property
    def component_templates(self):
        """Generate a dictionary with component template names and file paths."""
        return self._collect_templates(self.entry_point_group_component_templates)

    @cached_property
    def index_templates(self):
        """Generate a dictionary with index template names and file paths."""
        return self._collect_templates(self.entry_point_group_index_templates)

    @staticmethod
    def _get_mappings_module(module):
        """Resolves the module where to find search mappings/templates.

        Finds the module that contains the search mappings/templates based
        on the current installed search distribution.

        :param module: the module/package name.
        """
        search_major_version = search.VERSION[0]
        if SEARCH_DISTRIBUTION == ES:
            subfolder = "v{}".format(search_major_version)
        elif SEARCH_DISTRIBUTION == OS:
            subfolder = "os-v{}".format(search_major_version)

            # Make sure that the OpenSearch mappings are in the folder.
            # The fallback can be removed after transition to OpenSearch.
            if not (files(module) / subfolder).is_dir():
                # fallback to ES folder with a warning if `os-vx` is not found
                subfolder = "v7"
                warnings.warn(
                    "OpenSearch v{version} mappings files not found, falling back to Elasticsearch v7 mappings for module {module}. Please add the missing OpenSearch os-v{version} mappings.".format(
                        module=module,
                        version=search_major_version,
                    )
                )
        else:
            # should never happen
            raise RuntimeError(
                "Unknown search distribution {}".format(SEARCH_DISTRIBUTION)
            )

        return "{}.{}".format(module, subfolder)

    def register_mappings(self, alias, package_name):
        """Register mappings from a package under given alias.

        :param alias: The alias.
        :param package_name: The package name.
        """
        package_name = self._get_mappings_module(package_name)

        def _walk_dir(aliases, *parts):
            root_name = build_index_from_parts(*parts)
            resource_name = os.path.join(*parts)

            data = aliases.get(root_name, {})

            for filename in os.listdir(files(package_name) / resource_name):
                file_path = os.path.join(resource_name, filename)

                if (files(package_name) / file_path).is_dir():
                    _walk_dir(data, *(parts + (filename,)))
                    continue

                filename_root, ext = os.path.splitext(filename)
                if ext not in {
                    ".json",
                }:
                    continue

                index_name = build_index_from_parts(*(parts + (filename_root,)))
                assert index_name not in data, "Duplicate index"

                filename = os.path.join(files(package_name), resource_name, filename)
                data[index_name] = filename
                self.mappings[index_name] = filename

            aliases[root_name] = data

        # Start the recursion here:
        _walk_dir(self.aliases, alias)

    def register_templates(self, module):
        """Register templates from the provided module.

        :param module: The templates module.
        """
        module = self._get_mappings_module(module)
        result = {}

        def _walk_dir(*parts):
            parts = parts or tuple()
            resource_name = os.path.join(*parts) if parts else ""
            for filename in os.listdir(files(module) / resource_name):
                file_path = os.path.join(resource_name, filename)

                if (files(module) / file_path).is_dir():
                    _walk_dir(*(parts + (filename,)))
                    continue

                filename_root, ext = os.path.splitext(filename)
                if ext not in {
                    ".json",
                }:
                    continue

                template_name = build_index_from_parts(*(parts + (filename_root,)))
                filename = os.path.join(files(module), resource_name, filename)
                result[template_name] = filename

        # Start the recursion here:
        _walk_dir()
        return result

    def load_entry_point_group_mappings(self, entry_point_group_mappings):
        """Load actions from an entry point group."""
        for ep in entry_points(group=entry_point_group_mappings):
            self.register_mappings(ep.name, ep.module)

    def _client_builder(self):
        """Build search engine (ES/OS) client."""
        client_config = self.app.config.get("SEARCH_CLIENT_CONFIG") or {}

        hosts = self.app.config.get("SEARCH_HOSTS")
        elastic_hosts = self.app.config.get("SEARCH_ELASTIC_HOSTS")
        if hosts is None and elastic_hosts is not None:
            warnings.warn(
                "The variable SEARCH_ELASTIC_HOSTS will be replaced by SEARCH_HOSTS",
                DeprecationWarning,
            )

        client_config.setdefault("hosts", hosts or elastic_hosts)
        return SearchEngine(**client_config)

    @property
    def client(self):
        """Return client for current application."""
        if self._client is None:
            self._client = self._client_builder()
        return self._client

    def flush_and_refresh(self, index):
        """Flush and refresh one or more indices.

        .. warning::

           Do not call this method unless you know what you are doing. This
           method is only intended to be called during tests.
        """
        prefixed_index = build_alias_name(index, app=self.app)
        self.client.indices.flush(wait_if_ongoing=True, index=prefixed_index)
        self.client.indices.refresh(index=prefixed_index)
        self.client.cluster.health(wait_for_status="yellow", request_timeout=30)
        return True

    @property
    def cluster_version(self):
        """Get version of Elasticsearch running on the cluster."""
        versionstr = self.client.info()["version"]["number"]
        return [int(x) for x in versionstr.split(".")]

    @property
    def cluster_distribution(self):
        """Get the distribution entry (opensearch or elasticsearch) on the cluster."""
        # OpenSearch provides a "distribution" field containing "opensearch"
        # Elasticsearch doesn't seem to do that
        # (checked versions: 7.10.2, 7.11.2, 7.17.5, 8.3.1)
        return self.client.info()["version"].get("distribution", "elasticsearch")

    @property
    def active_aliases(self):
        """Get a filtered list of aliases based on configuration.

        Returns aliases and their mappings that are defined in the
        `SEARCH_MAPPINGS` config variable. If the `SEARCH_MAPPINGS` is set to
        `None` (the default), all aliases are included.
        """
        whitelisted_aliases = self.app.config.get("SEARCH_MAPPINGS")
        if whitelisted_aliases is None:
            return self.aliases
        else:
            return {k: v for k, v in self.aliases.items() if k in whitelisted_aliases}

    def _get_indices(self, tree_or_filename):
        for name, value in tree_or_filename.items():
            if isinstance(value, dict):
                for result in self._get_indices(value):
                    yield result
            else:
                yield name

    def create_index(
        self,
        index,
        mapping_path=None,
        prefix=None,
        suffix=None,
        create_write_alias=True,
        ignore=None,
        dry_run=False,
    ):
        """Create index with a write alias."""
        mapping_path = mapping_path or self.mappings[index]

        final_alias = None
        alias_result = None
        # To prevent index init --force from creating a suffixed
        # index if the current instance is running without suffixes
        # make sure there is no index with the same name as the
        # alias name (i.e. the index name without the suffix).
        with open(mapping_path, "r") as body:
            final_index = build_index_name(
                index, prefix=prefix, suffix=suffix, app=self.app
            )
            if create_write_alias:
                final_alias = build_alias_name(index, prefix=prefix, app=self.app)
            index_result = (
                self.client.indices.create(
                    index=final_index,
                    body=json.load(body),
                    ignore=ignore,
                )
                if not dry_run
                else None
            )
            if create_write_alias:
                alias_result = (
                    self.client.indices.put_alias(
                        index=final_index,
                        name=final_alias,
                        ignore=ignore,
                    )
                    if not dry_run
                    else None
                )
        return (final_index, index_result), (final_alias, alias_result)

    def create(self, ignore=None, ignore_existing=False, index_list=None):
        """Yield tuple with created index name and responses from a client."""
        ignore = ignore or []
        new_indices = {}
        actions = []
        if ignore_existing and not ignore:
            ignore = [400]
        elif ignore_existing and 400 not in ignore:
            ignore.append(400)

        def ensure_not_exists(name):
            if not ignore_existing and self.client.indices.exists(name):
                raise IndexAlreadyExistsError(
                    'index/alias with name "{}" already exists'.format(name)
                )

        def _build(tree_or_filename, alias=None):
            """Build a list of index/alias actions to perform."""
            for name, value in tree_or_filename.items():
                if isinstance(value, dict):
                    _build(value, alias=name)
                else:
                    if index_list and name not in index_list:
                        continue
                    index_result, alias_result = self.create_index(
                        name, ignore=ignore, dry_run=True
                    )
                    ensure_not_exists(index_result[0])
                    new_indices[name] = index_result[0]
                    if alias_result[0]:
                        ensure_not_exists(alias_result[0])
                        actions.append(
                            dict(
                                type="create_index", index=name, create_write_alias=True
                            )
                        )
                    else:
                        actions.append(
                            dict(
                                type="create_index",
                                index=name,
                                create_write_alias=False,
                            )
                        )
            if alias:
                alias_indices = self._get_indices(tree_or_filename)
                alias_indices = [
                    new_indices[i] for i in alias_indices if i in new_indices
                ]
                if alias_indices:
                    alias_name = build_alias_name(alias, app=self.app)
                    ensure_not_exists(alias_name)
                    actions.append(
                        dict(type="create_alias", index=alias_indices, alias=alias_name)
                    )

        _build(self.active_aliases)

        for action in actions:
            if action["type"] == "create_index":
                index_result, alias_result = self.create_index(
                    action["index"],
                    create_write_alias=action.get("create_write_alias", True),
                    ignore=ignore,
                )
                yield index_result
                if alias_result[0]:
                    yield alias_result
            elif action["type"] == "create_alias":
                yield (
                    action["alias"],
                    self.client.indices.put_alias(
                        index=action["index"],
                        name=action["alias"],
                        ignore=ignore,
                    ),
                )

    def update_mapping(self, index, check=True):
        """Update mapping of the existing index."""
        mapping_path = self.mappings[index]
        index_alias_name = build_alias_name(index)

        # get api returns only dicts
        index_dict = self.client.indices.get(index_alias_name)
        index_keys = list(index_dict.keys())

        # make sure only one index exists
        assert len(index_keys) == 1

        full_index_name = index_keys[0]

        old_mapping = index_dict[full_index_name]["mappings"]

        # need to initialise Index class to use the .put_mapping API wrapper method
        index_ = dsl.Index(full_index_name, using=self.client)

        with open(mapping_path, "r") as body:
            mapping = json.load(body)["mappings"]
            changes = list(dictdiffer.diff(old_mapping, mapping))

            # allow only additions to mappings (backwards compatibility is kept)
            if not check or all([change[0] == "add" for change in changes]):
                # raises 400 if the mapping cannot be updated
                # (f.e. type changes or index needs to be closed)
                index_.put_mapping(using=self.client, body=mapping)
            else:
                non_add_changes = [change for change in changes if change[0] != "add"]
                raise NotAllowedMappingUpdate(
                    "Only additions are allowed when updating mappings to keep backwards compatibility. "
                    f"This mapping has {len(non_add_changes)} non addition changes.\n\n"
                    f"Full list of changes: {changes}"
                )

    def _replace_prefix(self, template_path, body, enforce_prefix):
        """Replace index prefix in template request body."""
        pattern = "__SEARCH_INDEX_PREFIX__"

        prefix = self.app.config["SEARCH_INDEX_PREFIX"] or ""
        if prefix:
            message = f"You are using the prefix `{prefix}`, but the template `{template_path}` does not contain the pattern `{pattern}`."
            if enforce_prefix:
                assert pattern in body, message
            else:
                warnings.warn(message)

        return body.replace(pattern, prefix)

    def _put_template(
        self, template_name, template_file, put_function, ignore, enforce_prefix=True
    ):
        """Put template in search client.

        If enforce_prefix is set to True, and the setting INVENIO_SEARCH_PREFIX_INDEX exists, then the function will
        fail if the template does not use the prefix
        """
        ignore = ignore or []
        with open(template_file, "r") as fp:
            body = fp.read()
            replaced_body = self._replace_prefix(template_file, body, enforce_prefix)
            template_name = build_alias_name(template_name, app=self.app)
            return template_file, put_function(
                name=template_name,
                body=json.loads(replaced_body),
                ignore=ignore,
            )

    def put_templates(self, ignore=None):
        """Yield tuple with registered template and response from client."""
        for template in self.templates:
            yield self._put_template(
                template,
                self.templates[template],
                self.client.indices.put_template,
                ignore,
            )

    def put_component_templates(self, ignore=None):
        for template in self.component_templates:
            yield self._put_template(
                template,
                self.component_templates[template],
                self.client.cluster.put_component_template,
                ignore,
                enforce_prefix=False,
            )

    def put_index_templates(self, ignore=None):
        for template in self.index_templates:
            yield self._put_template(
                template,
                self.index_templates[template],
                self.client.indices.put_index_template,
                ignore,
            )

    def delete(self, ignore=None, index_list=None):
        """Yield tuple with deleted index name and responses from a client."""
        ignore = ignore or []

        def _delete(tree_or_filename, alias=None):
            """Delete indexes and aliases by walking DFS."""
            # Iterate over aliases:
            for name, value in tree_or_filename.items():
                if isinstance(value, dict):
                    for result in _delete(value, alias=name):
                        yield result
                else:
                    if index_list and name not in index_list:
                        continue
                    # Resolve values to suffixed (or not) indices
                    prefixed_index = build_alias_name(name, app=self.app)
                    lookup_response = self.client.indices.get_alias(
                        index=prefixed_index, ignore=[404]
                    )
                    if "error" in lookup_response:
                        indices_to_delete = []
                    else:
                        indices_to_delete = list(lookup_response.keys())
                    if len(indices_to_delete) == 0:
                        pass
                    elif len(indices_to_delete) == 1:
                        yield (
                            name,
                            self.client.indices.delete(
                                index=indices_to_delete[0],
                                ignore=ignore,
                            ),
                        )
                    else:
                        warnings.warn(
                            (
                                "Multiple indices found during deletion of "
                                "{name}: {indices}. Deletion was skipped for them."
                            ).format(name=name, indices=indices_to_delete)
                        )

        for result in _delete(self.active_aliases):
            yield result


class InvenioSearch(object):
    """Invenio-Search extension."""

    def __init__(self, app=None, **kwargs):
        """Extension initialization.

        :param app: An instance of :class:`~flask.app.Flask`.
        """
        self._clients = {}

        if app:
            self.init_app(app, **kwargs)

    def init_app(
        self,
        app,
        entry_point_group_mappings="invenio_search.mappings",
        entry_point_group_templates="invenio_search.templates",
        entry_point_group_component_templates="invenio_search.component_templates",
        entry_point_group_index_templates="invenio_search.index_templates",
        **kwargs,
    ):
        """Flask application initialization.

        :param app: An instance of :class:`~flask.app.Flask`.
        """
        self.init_config(app)

        app.cli.add_command(index_cmd)

        state = _SearchState(
            app,
            entry_point_group_mappings=entry_point_group_mappings,
            entry_point_group_templates=entry_point_group_templates,
            entry_point_group_component_templates=entry_point_group_component_templates,
            entry_point_group_index_templates=entry_point_group_index_templates,
            **kwargs,
        )
        self._state = app.extensions["invenio-search"] = state

    @staticmethod
    def init_config(app):
        """Initialize configuration.

        :param app: An instance of :class:`~flask.app.Flask`.
        """
        for k in dir(config):
            if k.startswith("SEARCH_"):
                app.config.setdefault(k, getattr(config, k))

    def __getattr__(self, name):
        """Proxy to state object."""
        return getattr(self._state, name, None)
