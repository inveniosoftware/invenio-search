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


"""Module tests."""

from __future__ import absolute_import, print_function

from flask import Flask
from flask_cli import FlaskCLI

from invenio_search import InvenioSearch, current_search_client


def test_version():
    """Test version import."""
    from invenio_search import __version__
    assert __version__


def test_init():
    """Test extension initialization."""
    app = Flask('testapp')
    FlaskCLI(app)
    ext = InvenioSearch(app)
    assert 'invenio-search' in app.extensions

    app = Flask('testapp')
    FlaskCLI(app)
    ext = InvenioSearch()
    assert 'invenio-search' not in app.extensions
    ext.init_app(app)
    assert 'invenio-search' in app.extensions


def test_client_reference():
    """Test client reference."""
    client1 = {'name': 'client1'}
    client2 = {'name': 'client2'}

    app1 = Flask('testapp1')
    FlaskCLI(app1)
    app2 = Flask('testapp2')
    FlaskCLI(app2)

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
