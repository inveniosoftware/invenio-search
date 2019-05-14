# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Utility functions for search engine."""

import os
import time

from flask import current_app


def timestamp_suffix():
    """Generate a suffix based on the current time."""
    return '-' + str(int(time.time()))


def prefix_index(app, index):
    """Prefixes the given index if needed.

    :param app: Flask app to get the config from.
    :param index: Name of the index to prefix.
    :returns: A string with the new index name prefixed if needed.
    """
    index_prefix = app.config['SEARCH_INDEX_PREFIX'] or ''
    return index_prefix + index


def suffix_index(app, index, suffix):
    """Suffixes the given index.

    :param app: Flask app to get the config from.
    :param index: Name of the index to prefix.
    :param suffix: The suffix to append to the index name.
    :returns: A string with the new index name suffixed.
    """
    return index + suffix


def build_index_name(app, *parts):
    """Build an index name from parts.

    :param parts: Parts that should be combined to make an index name.
    """
    base_index = os.path.splitext(
        '-'.join([part for part in parts if part])
    )[0]
    return prefix_index(app=app, index=base_index)


def build_suffix_index_name(app, suffix, *parts):
    """Build an index name from parts with a suffix.

    :param parts: Parts that should be combined to make an index name.
    """
    index_name = build_index_name(app, *parts)

    return suffix_index(app=app, index=index_name, suffix=suffix)


def schema_to_index(schema, index_names=None):
    """Get index/doc_type given a schema URL.

    :param schema: The schema name
    :param index_names: A list of index name.
    :returns: A tuple containing (index, doc_type).
    """
    parts = schema.split('/')
    doc_type = os.path.splitext(parts[-1])

    if doc_type[1] not in {'.json', }:
        return (None, None)

    if index_names is None:
        return (build_index_name(current_app, *parts), doc_type[0])

    for start in range(len(parts)):
        index_name = build_index_name(current_app, *parts[start:])
        if index_name in index_names:
            return (index_name, doc_type[0])

    return (None, None)
