# SPDX-FileCopyrightText: 2015-2024 CERN.
# SPDX-FileCopyrightText: 2025 Graz University of Technology.
# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT


"""Pytest configuration."""

import os
import sys
from unittest.mock import Mock

import pytest
from flask import Flask
from invenio_base.utils import entry_points

from invenio_search import InvenioSearch

sys.path.append(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
        "tests/mock_module",
    )
)


@pytest.fixture(scope="module")
def extra_entry_points():
    """Define the extra points for the configuration of the component_templates."""
    return {
        "invenio_search.component_templates": [
            "records = mock_module.component_templates",
        ],
        "invenio_search.index_templates": [
            "records = mock_module.index_templates",
        ],
    }


@pytest.fixture(scope="module")
def create_app(instance_path, entry_points):
    """Application factory fixture.

    Needed for compatibility with pytest-invenio.
    """

    def factory(**config):
        app = Flask("testapp", instance_path=instance_path)
        app.config.update(config)
        InvenioSearch(app)
        return app

    return factory


@pytest.fixture()
def app(create_app, app_config):
    """Flask application fixture.

    Function-scoped (unlike the pytest-invenio one), as tests modify the config.
    """
    app = create_app(**app_config)

    with app.app_context():
        yield app


def mock_iter_entry_points_factory(data, mocked_group):
    """Create a mock iter_entry_points function."""

    def entrypoints(group, name=None):
        if group == mocked_group:
            for entrypoint in data:
                yield entrypoint
        else:
            eps = [eps for eps in entry_points(group=group) if eps.name == name]
            for x in eps:
                yield x

    return entrypoints


@pytest.fixture()
def template_entrypoints():
    """Declare some events by mocking the invenio_stats.events entrypoint.

    It yields a list like [{event_type: <event_type_name>}, ...].
    """
    eps = []
    for idx in range(5):
        entrypoint = Mock(
            name="mock_module",
            value="mock_module",
            group="invenio_search.templates",
        )
        entrypoint.load = lambda: lambda: ["mock_module.templates"]
        eps.append(entrypoint)

    entrypoints = mock_iter_entry_points_factory(eps, "invenio_search.templates")
    return entrypoints
