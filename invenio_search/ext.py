# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Invenio module for information retrieval."""

from __future__ import absolute_import, print_function

import errno
import json
import os
import warnings

from elasticsearch import VERSION as ES_VERSION
from pkg_resources import iter_entry_points, resource_filename, \
    resource_isdir, resource_listdir
from werkzeug.utils import cached_property

from . import config
from .cli import index as index_cmd
from .proxies import current_search_client
from .utils import build_index_name


def _get_indices(tree_or_filename):
    for name, value in tree_or_filename.items():
        if isinstance(value, dict):
            for result in _get_indices(value):
                yield result
        else:
            yield name


class _SearchState(object):
    """Store connection to elastic client and registered indexes."""

    def __init__(self, app,
                 entry_point_group_mappings=None,
                 entry_point_group_templates=None,
                 **kwargs):
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
        self.number_of_indexes = 0
        self._client = kwargs.get('client')
        self.entry_point_group_templates = entry_point_group_templates

        if entry_point_group_mappings:
            self.load_entry_point_group_mappings(entry_point_group_mappings)

    @cached_property
    def templates(self):
        result = None
        if self.entry_point_group_templates:
            result = self.load_entry_point_group_templates(
                self.entry_point_group_templates)
        return {k: v for d in result for k, v in d.items()} \
            if result is not None else {}

    def register_mappings(self, alias, package_name):
        """Register mappings from a package under given alias.

        :param alias: The alias.
        :param package_name: The package name.
        """
        # For backwards compatibility, we also allow for ES2 mappings to be
        # placed at the root level of the specified package path, and not in
        # the `<package-path>/v2` directory.
        if ES_VERSION[0] == 2:
            try:
                resource_listdir(package_name, 'v2')
                package_name += '.v2'
            except (OSError, IOError) as ex:
                if getattr(ex, 'errno', 0) != errno.ENOENT:
                    raise
                warnings.warn(
                    "Having mappings in a path which doesn't specify the "
                    "Elasticsearch version is deprecated. Please move your "
                    "mappings to a subfolder named according to the "
                    "Elasticsearch version which your mappings are intended "
                    "for. (e.g. '{}/v2/{}')".format(
                        package_name, alias),
                    PendingDeprecationWarning)
        else:
            package_name = '{}.v{}'.format(package_name, ES_VERSION[0])

        def _walk_dir(aliases, *parts):
            root_name = build_index_name(*parts)
            resource_name = os.path.join(*parts)

            if root_name not in aliases:
                self.number_of_indexes += 1

            data = aliases.get(root_name, {})

            for filename in resource_listdir(package_name, resource_name):
                index_name = build_index_name(*(parts + (filename, )))
                file_path = os.path.join(resource_name, filename)

                if resource_isdir(package_name, file_path):
                    _walk_dir(data, *(parts + (filename, )))
                    continue

                ext = os.path.splitext(filename)[1]
                if ext not in {'.json', }:
                    continue

                assert index_name not in data, 'Duplicate index'
                data[index_name] = self.mappings[index_name] = \
                    resource_filename(
                        package_name, os.path.join(resource_name, filename))
                self.number_of_indexes += 1

            aliases[root_name] = data

        # Start the recursion here:
        _walk_dir(self.aliases, alias)

    def register_templates(self, directory):
        """Register templates from the provided directory.

        :param directory: The templates directory.
        """
        try:
            resource_listdir(directory, 'v{}'.format(ES_VERSION[0]))
            directory = '{}/v{}'.format(directory, ES_VERSION[0])
        except (OSError, IOError) as ex:
            if getattr(ex, 'errno', 0) == errno.ENOENT:
                raise OSError(
                    "Please move your templates to a subfolder named "
                    "according to the Elasticsearch version "
                    "which your templates are intended "
                    "for. (e.g. '{}.v{}')".format(directory,
                                                  ES_VERSION[0]))
        result = {}
        module_name, parts = directory.split('.')[0], directory.split('.')[1:]
        parts = tuple(parts)

        def _walk_dir(parts):
            resource_name = os.path.join(*parts)

            for filename in resource_listdir(module_name, resource_name):
                template_name = build_index_name(*(parts[1:] + (filename, )))
                file_path = os.path.join(resource_name, filename)

                if resource_isdir(module_name, file_path):
                    _walk_dir((parts + (filename, )))
                    continue

                ext = os.path.splitext(filename)[1]
                if ext not in {'.json', }:
                    continue

                result[template_name] = resource_filename(
                    module_name, os.path.join(resource_name, filename))

        # Start the recursion here:
        _walk_dir(parts)
        return result

    def load_entry_point_group_mappings(self, entry_point_group_mappings):
        """Load actions from an entry point group."""
        for ep in iter_entry_points(group=entry_point_group_mappings):
            self.register_mappings(ep.name, ep.module_name)

    def load_entry_point_group_templates(self, entry_point_group_templates):
        """Load actions from an entry point group."""
        result = []
        for ep in iter_entry_points(group=entry_point_group_templates):
            with self.app.app_context():
                for template_dir in ep.load()():
                    result.append(self.register_templates(template_dir))
        return result

    def _client_builder(self):
        """Build Elasticsearch client."""
        from elasticsearch import Elasticsearch
        from elasticsearch.connection import RequestsHttpConnection

        return Elasticsearch(
            hosts=self.app.config.get('SEARCH_ELASTIC_HOSTS'),
            connection_class=RequestsHttpConnection,
        )

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
        self.client.indices.flush(wait_if_ongoing=True, index=index)
        self.client.indices.refresh(index=index)
        self.client.cluster.health(
            wait_for_status='yellow', request_timeout=30)
        return True

    @property
    def cluster_version(self):
        """Get version of Elasticsearch running on the cluster."""
        versionstr = self.client.info()['version']['number']
        return [int(x) for x in versionstr.split('.')]

    @property
    def active_aliases(self):
        """Get a filtered list of aliases based on configuration.

        Returns aliases and their mappings that are defined in the
        `SEARCH_MAPPINGS` config variable. If the `SEARCH_MAPPINGS` is set to
        `None` (the default), all aliases are included.
        """
        whitelisted_aliases = self.app.config.get('SEARCH_MAPPINGS')
        if whitelisted_aliases is None:
            return self.aliases
        else:
            return {k: v for k, v in self.aliases.items()
                    if k in whitelisted_aliases}

    def create(self, ignore=None):
        """Yield tuple with created index name and responses from a client."""
        ignore = ignore or []

        def _create(tree_or_filename, alias=None):
            """Create indices and aliases by walking DFS."""
            # Iterate over aliases:
            for name, value in tree_or_filename.items():
                if isinstance(value, dict):
                    for result in _create(value, alias=name):
                        yield result
                else:
                    with open(value, 'r') as body:
                        yield name, self.client.indices.create(
                            index=name,
                            body=json.load(body),
                            ignore=ignore,
                        )

            if alias:
                yield alias, self.client.indices.put_alias(
                    index=list(_get_indices(tree_or_filename)),
                    name=alias,
                    ignore=ignore,
                )

        for result in _create(self.active_aliases):
            yield result

    def put_templates(self, ignore=None):
        """Yield tuple with registered template and response from client."""
        ignore = ignore or []

        def _put_template(template):
            """Put template in search client."""
            with open(self.templates[template], 'r') as body:
                return self.templates[template],\
                    current_search_client.indices.put_template(
                        name=template,
                        body=json.load(body),
                        ignore=ignore,
                )

        for template in self.templates:
            yield _put_template(template)

    def delete(self, ignore=None):
        """Yield tuple with deleted index name and responses from a client."""
        ignore = ignore or []

        def _delete(tree_or_filename, alias=None):
            """Delete indexes and aliases by walking DFS."""
            if alias:
                yield alias, self.client.indices.delete_alias(
                    index=list(_get_indices(tree_or_filename)),
                    name=alias,
                    ignore=ignore,
                )

            # Iterate over aliases:
            for name, value in tree_or_filename.items():
                if isinstance(value, dict):
                    for result in _delete(value, alias=name):
                        yield result
                else:
                    yield name, self.client.indices.delete(
                        index=name,
                        ignore=ignore,
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

    def init_app(self, app,
                 entry_point_group_mappings='invenio_search.mappings',
                 entry_point_group_templates='invenio_search.templates',
                 **kwargs):
        """Flask application initialization.

        :param app: An instance of :class:`~flask.app.Flask`.
        """
        self.init_config(app)

        app.cli.add_command(index_cmd)

        state = _SearchState(
            app,
            entry_point_group_mappings=entry_point_group_mappings,
            entry_point_group_templates=entry_point_group_templates,
            **kwargs
        )
        self._state = app.extensions['invenio-search'] = state

    @staticmethod
    def init_config(app):
        """Initialize configuration.

        :param app: An instance of :class:`~flask.app.Flask`.
        """
        for k in dir(config):
            if k.startswith('SEARCH_'):
                app.config.setdefault(k, getattr(config, k))

    def __getattr__(self, name):
        """Proxy to state object."""
        return getattr(self._state, name, None)
