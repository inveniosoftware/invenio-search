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

from collections import defaultdict
import pkg_resources

from flask import current_app
from werkzeug.utils import import_string

from . import config
from .cli import index as index_cmd


class _SearchState(object):
    """Store connection to elastic client and regiter indexes."""

    def __init__(self, app, entry_point_group=None, **kwargs):
        """Initialize state."""
        self.app = app
        self.aliases = defaultdict(list)
        self.mappings = {}
        self._client = kwargs.get('client')

        if entry_point_group:
            self.load_entry_point_group(entry_point_group)

    def register_index(self, alias, package_name, resource_name='.',
                       recursive=True):
        """Register mappings from a package under given alias."""
        # TODO build index name from resource_name and filename

        for filename in pkg_resources.resource_listdir(package_name,
                                                       resource_name):
            if recursive and pkg_resources.resource_isdir(package_name,
                                                          filename):
                self.aliases[alias].append(filename)
                self.register_index(
                    filename, package_name,
                    resource_name=os.path.join(resource_name, filename)
                )
                continue

            self.aliases[alias].append(filename)
            self.mapping[filename] = pkg_resouces.resouce_filename(
                package_name, filename
            )

    def load_entry_point_group(self, entry_point_group):
        """Load actions from an entry point group."""
        for ep in pkg_resources.iter_entry_points(group=entry_point_group):
            self.register_mapping(ep.name, ep.module_name)

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
