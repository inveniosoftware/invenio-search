# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.


"""Pytest configuration."""

import os
import shutil
import sys
import tempfile

import pytest
import urllib3
from flask import Flask

from invenio_search import InvenioSearch

sys.path.append(
    os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                 'tests/mock_module'))


@pytest.fixture()
def app_config():
    if 'OPENSEARCH_CLIENT_URI' not in os.environ:
        return {}

    params = {}
    if 'OPENSEARCH_INSECURE' in os.environ:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        params.update(dict(
            port=9200,
            use_ssl=True,
            http_auth=('admin', 'admin'),
            verify_certs=False,
            ssl_show_warn=False,
        ))

    return {
        'SEARCH_CLIENT_CONFIG': {
            'hosts': [
                'https://admin:admin@localhost:9200',
            ],
            'use_ssl': True,
            'verify_certs': False,
            'ssl_show_warn': False,
        }
    }

@pytest.fixture()
def app(app_config):
    """Flask application fixture."""
    # Set temporary instance path for sqlite
    instance_path = tempfile.mkdtemp()
    app = Flask('testapp', instance_path=instance_path)
    app.config.update(
        TESTING=True

    )
    app.config.update(app_config)
    InvenioSearch(app)

    with app.app_context():
        yield app

    # Teardown instance path.
    shutil.rmtree(instance_path)


def mock_iter_entry_points_factory(data, mocked_group):
    """Create a mock iter_entry_points function."""
    from pkg_resources import iter_entry_points

    def entrypoints(group, name=None):
        if group == mocked_group:
            for entrypoint in data:
                yield entrypoint
        else:
            for x in iter_entry_points(group=group, name=name):
                yield x
    return entrypoints


@pytest.fixture()
def template_entrypoints():
    """Declare some events by mocking the invenio_stats.events entrypoint.

    It yields a list like [{event_type: <event_type_name>}, ...].
    """
    eps = []
    for idx in range(5):
        event_type_name = 'mock_module'
        from pkg_resources import EntryPoint
        entrypoint = EntryPoint(event_type_name, event_type_name)
        entrypoint.load = lambda: lambda: ['mock_module.templates']
        eps.append(entrypoint)

    entrypoints = mock_iter_entry_points_factory(
        eps, 'invenio_search.templates')
    return entrypoints
