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


"""Module tests."""

from __future__ import absolute_import, print_function

import pytest
from elasticsearch import VERSION as ES_VERSION
from flask import Flask
from mock import patch

from invenio_search import InvenioSearch, current_search_client
from invenio_search.utils import schema_to_index


def test_version():
    """Test version import."""
    from invenio_search import __version__
    assert __version__


def test_init():
    """Test extension initialization."""
    app = Flask('testapp')
    ext = InvenioSearch(app)
    assert 'invenio-search' in app.extensions

    app = Flask('testapp')
    ext = InvenioSearch()
    assert 'invenio-search' not in app.extensions
    ext.init_app(app)
    assert 'invenio-search' in app.extensions


def test_flush_and_refresh(app):
    """Test flush and refresh."""
    search = app.extensions['invenio-search']
    search.flush_and_refresh('_all')


def test_client_reference():
    """Test client reference."""
    client1 = {'name': 'client1'}
    client2 = {'name': 'client2'}

    app1 = Flask('testapp1')
    app2 = Flask('testapp2')

    ext = InvenioSearch()
    assert 'invenio-search' not in app1.extensions
    assert 'invenio-search' not in app2.extensions

    ext.init_app(app1, client=client1)
    assert 'invenio-search' in app1.extensions

    ext.init_app(app2, client=client2)
    assert 'invenio-search' in app2.extensions

    with app1.app_context():
        assert current_search_client == client1

    with app2.app_context():
        assert current_search_client == client2


def test_default_client(app):
    """Test default client."""
    with app.app_context():
        current_search_client.cluster.health(
            wait_for_status='yellow', request_timeout=1
        )


@pytest.mark.parametrize(('schema_url', 'result'), [
    ('invalidfileextension',
     (None, None)),
    ('records/record-v1.0.0.json',
     ('records-record-v1.0.0', 'record-v1.0.0')),
    ('/records/record-v1.0.0.json',
     ('records-record-v1.0.0', 'record-v1.0.0')),
])
def test_schema_to_index(schema_url, result):
    """Test conversion of schema to index name and document type."""
    assert result == schema_to_index(schema_url)


def test_load_entry_point_group(template_entrypoints):
    """Test entry point loading."""
    app = Flask('testapp')
    ext = InvenioSearch(app)
    ep_group = 'test'

    def mock_entry_points_mappings(group=None):
        assert group == ep_group

        class ep(object):

            name = 'records'
            module_name = 'mock_module.mappings'

        yield ep

    assert len(ext.mappings) == 0
    with patch('invenio_search.ext.iter_entry_points',
               mock_entry_points_mappings):
        ext.load_entry_point_group_mappings(
            entry_point_group_mappings=ep_group)
    assert len(ext.mappings) == 3
    # Check that mappings are loaded from the correct folder depending on the
    # ES version.
    if ES_VERSION[0] > 2:
        mappings_dir = 'mock_module/mappings/v{}/records'.format(ES_VERSION[0])
        assert all(mappings_dir in path for path in ext.mappings.values())

    with patch('invenio_search.ext.iter_entry_points',
               return_value=template_entrypoints('invenio_search.templates')):
        if ES_VERSION[0] == 2:
            assert len(ext.templates.keys()) == 2
        elif ES_VERSION[0] == 5:
            assert len(ext.templates.keys()) == 1
