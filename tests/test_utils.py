# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

import pytest
from mock import patch

from invenio_search.utils import schema_to_index


@pytest.mark.parametrize(
    ('schema, expected, index_names'),
    (
        (
            'records/record-v1.0.0.json',
            ('records-record-v1.0.0', 'record-v1.0.0'),
            None,
        ),
        (
            '/records/record-v1.0.0.json',
            ('records-record-v1.0.0', 'record-v1.0.0'),
            None,
        ),
        (
            'default-v1.0.0.json',
            ('default-v1.0.0', 'default-v1.0.0'),
            None,
        ),
        (
            'default-v1.0.0.json',
            (None, None),
            [],
        ),
        (
            'invalidextension',
            (None, None),
            None,
        ),
    ),
)
def test_schema_to_index(schema, expected, index_names, app):
    """Test the expected value of schema to index."""
    result = schema_to_index(schema, index_names=index_names)
    assert result == expected


def test_schema_to_index_prefixes_indices(app):
    """Test that prefix is added to the index when creating it."""
    new_conf = {'SEARCH_INDEX_PREFIX': 'prefix-'}
    with patch.dict(app.config, new_conf):
        result = schema_to_index('default-v1.0.0.json')

        assert result == ('prefix-default-v1.0.0', 'default-v1.0.0')
