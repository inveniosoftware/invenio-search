# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.


"""Pytest configuration."""

from __future__ import absolute_import, print_function

import os
import shutil
import sys
import tempfile

import pytest
from flask import Flask
from invenio_db import InvenioDB
from sqlalchemy_utils.functions import create_database, database_exists, \
    drop_database

from invenio_search import InvenioSearch

sys.path.append(
    os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                 'tests/mock_module'))


@pytest.fixture()
def app():
    """Flask application fixture."""
    # Set temporary instance path for sqlite
    instance_path = tempfile.mkdtemp()
    app = Flask('testapp', instance_path=instance_path)
    app.config.update(
        TESTING=True
    )
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
