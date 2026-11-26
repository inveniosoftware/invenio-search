# SPDX-FileCopyrightText: 2015-2024 CERN.
# SPDX-FileCopyrightText: 2025 Graz University of Technology.
# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT


"""Pytest configuration."""

import os
import sys

import pytest
from flask import Flask
from invenio_app.factory import create_app as _create_app

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
        "invenio_search.templates": [
            "records = mock_module.templates",
        ],
    }


@pytest.fixture(scope="module")
def create_app(instance_path, entry_points):
    """Application factory fixture."""
    return _create_app


@pytest.fixture()
def cleanup_search(base_app):
    """Re-initialize invenio-search after the test.

    ``base_app`` is module-scoped, so the invenio-search extension state
    (registered mappings and aliases, current suffix, cached templates)
    is shared between tests. Use this fixture in tests that modify it.

    Similar to ``search_clear``, but resets the in-memory extension state
    instead of the indices in the cluster. To change app config in a test,
    use pytest-invenio's ``set_app_config_fn_scoped``.
    """
    yield
    InvenioSearch(base_app)
