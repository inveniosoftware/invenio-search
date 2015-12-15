# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
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
from werkzeug.utils import import_string

from . import config
from .cli import index as index_cmd


class _SearchState(object):
    """Store connection to elastic client and regiter indexes."""

    def __init__(self, app, entry_point_group=None, **kwargs):
        """Initialize state."""
        self.app = app
        self.mappings = {}
        self.aliases = {}
        self.number_of_indexes = 0
        self._client = kwargs.get('client')

        if entry_point_group:
            self.load_entry_point_group(entry_point_group)

    def register_mappings(self, alias, package_name):
        """Register mappings from a package under given alias."""
        def _index_name(*parts):
            """Build index name."""
            return os.path.splitext('-'.join(parts))[0]

        def _walk_dir(aliases, *parts):
            root_name = _index_name(*parts)
            resource_name = os.path.join(*parts)

            if root_name not in aliases:
                self.number_of_indexes += 1

            data = aliases.get(root_name, {})

            for filename in resource_listdir(package_name, resource_name):
                index_name = _index_name(*(parts + (filename, )))
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
                        package_name, os.path.join(resource_name, filename)
                    )
                self.number_of_indexes += 1

            aliases[root_name] = data

        # Start the recursion here:
        _walk_dir(self.aliases, alias)

    def load_entry_point_group(self, entry_point_group):
        """Load actions from an entry point group."""
        for ep in iter_entry_points(group=entry_point_group):
            self.register_mappings(ep.name, ep.module_name)

    def _client_builder(self):
        """Default Elasticsearch client builder."""
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

    def create(self, ignore=None):
        """Yield tuple with name and responses from a client."""
        ignore = ignore or []

        def _create(tree_or_filename, alias=None):
            """Create indexes and aliases by walking DFS."""
            # Iterate over aliases:
            for name, value in tree_or_filename.items():
                if not isinstance(value, dict):
                    with open(value, 'r') as body:
                        yield name, self.client.indices.create(
                            index=name,
                            body=json.load(body),
                            ignore=ignore,
                        )
                else:
                    for result in _create(value, alias=name):
                        yield result

            if alias is not None:
                yield alias, self.client.indices.put_alias(
                    index=list(tree_or_filename.keys()),
                    name=alias,
                    ignore=ignore,
                )

        for result in _create(self.aliases):
            yield result


class InvenioSearch(object):
    """Invenio-Search extension."""

    def __init__(self, app=None, **kwargs):
        """Extension initialization."""
        self._clients = {}

        if app:
            self.init_app(app, **kwargs)

    def init_app(self, app, entry_point_group='invenio_search.mappings',
                 **kwargs):
        """Flask application initialization."""
        self.init_config(app)

        for autoindex in app.config.get('SEARCH_AUTOINDEX', []):
            import_string(autoindex)

        app.cli.add_command(index_cmd)

        state = _SearchState(
            app, entry_point_group=entry_point_group, **kwargs
        )
        self._state = app.extensions['invenio-search'] = state

    @staticmethod
    def init_config(app):
        """Initialize configuration."""
        for k in dir(config):
            if k.startswith('SEARCH_'):
                app.config.setdefault(k, getattr(config, k))

    def __getattr__(self, name):
        """Proxy to state object."""
        return getattr(self._state, name, None)
