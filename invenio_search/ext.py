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

from flask import current_app
from werkzeug.utils import import_string

from . import config
from .cli import index as index_cmd


class InvenioSearch(object):
    """Invenio-Search extension."""

    def __init__(self, app=None, **kwargs):
        """Extension initialization."""
        self._clients = {}

        if app:
            self.init_app(app, **kwargs)

    def init_app(self, app, elasticsearch=None):
        """Flask application initialization."""
        self.init_config(app)
        # Configure elasticsearch client.
        self._clients[app] = elasticsearch

        for autoindex in app.config.get('SEARCH_AUTOINDEX', []):
            import_string(autoindex)

        app.cli.add_command(index_cmd)
        app.extensions['invenio-search'] = self

    @staticmethod
    def init_config(app):
        """Initialize configuration."""
        for k in dir(config):
            if k.startswith('SEARCH_'):
                app.config.setdefault(k, getattr(config, k))

    @classmethod
    def _client_builder(cls, app):
        """Default Elasticsearch client builder."""
        from elasticsearch import Elasticsearch
        from elasticsearch.connection import RequestsHttpConnection

        return Elasticsearch(
            hosts=app.config.get('SEARCH_ELASTIC_HOSTS'),
            connection_class=RequestsHttpConnection,
        )

    @property
    def client(self):
        """Return client for current application."""
        app = current_app._get_current_object()
        client = self._clients.get(app)
        if client is None:
            client = self._clients[app] = self.__class__._client_builder(app)
        return client
