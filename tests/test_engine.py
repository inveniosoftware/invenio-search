# SPDX-FileCopyrightText: 2026 RERO.
# SPDX-License-Identifier: MIT

"""Engine tests."""

from invenio_search.engine import dsl


def test_dsl_namespace():
    """Test the DSL namespace used by Invenio modules."""
    assert dsl.Q("ids", values=["1"]) == dsl.query.Ids(values=["1"])
    assert isinstance(dsl.Search().query(dsl.query.Bool()), dsl.search.Search)
    assert issubclass(dsl.FacetedResponse, dsl.response.Response)
    assert dsl.A("terms", field="type") == dsl.aggs.Terms(field="type")
    assert dsl.connections.get_connection
