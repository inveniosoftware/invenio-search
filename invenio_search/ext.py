# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Invenio module for information retrieval."""

from __future__ import absolute_import, print_function

import json
import os

from pkg_resources import iter_entry_points, resource_filename, \
    resource_isdir, resource_listdir
from werkzeug.utils import cached_property

from . import config
from .cli import index as index_cmd
from .proxies import current_search_client
from .utils import build_index_name


class _SearchState(object):
    """Store connection to elastic client and registered indices."""

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

    def register_templates(self, directory, package_name):
        """Register templates from the provided directory.

        :param directory: The templates directory.
        :param package_name: The package name.
        """
        result = {}

        def _walk_dir(*parts):
            resource_name = os.path.join(*parts)

            for filename in resource_listdir(package_name, resource_name):
                template_name = build_index_name(*(parts[1:] + (filename, )))
                file_path = os.path.join(resource_name, filename)

                if resource_isdir(package_name, file_path):
                    _walk_dir(*(parts + (filename, )))
                    continue

                ext = os.path.splitext(filename)[1]
                if ext not in {'.json', }:
                    continue

                result[template_name] = resource_filename(
                    package_name, os.path.join(resource_name, filename))

        # Start the recursion here:
        _walk_dir(directory)
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
                    result.append(
                        self.register_templates(template_dir, ep.name))
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
                    index=list(tree_or_filename.keys()),
                    name=alias,
                    ignore=ignore,
                )

        for result in _create(self.aliases):
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
                    index=list(tree_or_filename.keys()),
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

        for result in _delete(self.aliases):
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
