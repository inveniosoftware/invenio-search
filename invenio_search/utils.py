# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2022 CERN.
# Copyright (C)      2022 TU Wien.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Utility functions for search engine."""

import time
from collections.abc import Container
from fnmatch import fnmatch

from flask import current_app

from .proxies import current_search


class DynamicPathMatchSet(Container):
    """Set allowing wildcard matches for dynamic tempalte key paths."""

    def __init__(self, dynamic_templates=None):
        """Initialize the set from a mapping's dynamic templates."""
        self.include = set()
        self.exclude = set()
        if dynamic_templates:
            for dynamic_template in dynamic_templates:
                self.add(dynamic_template)

    def add(self, dynamic_template):
        """Add dynamic template to set."""
        for cfg in dynamic_template.values():
            path_match = cfg.get("path_match", [])
            if isinstance(path_match, str):
                path_match = [path_match]
            self.include.update(path_match)

            path_unmatch = cfg.get("path_unmatch", [])
            if isinstance(path_unmatch, str):
                path_unmatch = [path_unmatch]
            self.exclude.update(path_unmatch)

    def __contains__(self, key):
        """Use ``fnmatch`` to check included and excluded keys."""
        is_included = any(fnmatch(key, pattern) for pattern in self.include)
        is_excluded = any(fnmatch(key, pattern) for pattern in self.exclude)
        return is_included and not is_excluded


def timestamp_suffix():
    """Generate a suffix based on the current time."""
    return "-" + str(int(time.time()))


def prefix_index(index, prefix=None, app=None):
    """Prefixes the given index if needed.

    :param index: Name of the index to prefix.
    :param prefix: Force a prefix.
    :param app: Flask app to get the prefix config from.
    :returns: A string with the new index name prefixed if needed.
    """
    app = app or current_app
    index_prefix = (
        prefix if prefix is not None else (app.config.get("SEARCH_INDEX_PREFIX")) or ""
    )
    return index_prefix + index


def suffix_index(index, suffix=None, app=None):
    """Suffixes the given index.

    :param index: Name of the index to prefix.
    :param suffix: The suffix to append to the index name.
    :param app: Flask app to get the "invenio-search" extension from.
    :returns: A string with the new index name suffixed.
    """
    search_ext = app.extensions["invenio-search"] if app else current_search
    suffix = suffix if suffix is not None else search_ext.current_suffix
    return index + suffix


def build_index_from_parts(*parts):
    """Build an index name from parts.

    :param parts: String values that will be joined by dashes ("-").
    """
    return "-".join([part for part in parts if part])


def build_alias_name(index, prefix=None, app=None):
    """Build an alias name.

    :param index: Name of the index.
    :param prefix: The prefix to prepend to the index name.
    """
    return build_index_name(index, prefix=prefix, suffix="", app=app)


def build_index_name(index, prefix=None, suffix=None, app=None):
    """Build an index name.

    :param index: Name of the index.
    :param prefix: The prefix to prepend to the index name.
    :param suffix: The suffix to append to the index name.
    :param app: Flask app passed to ``prefix_index`` and ``suffix_index``.
    """
    if not isinstance(index, str):
        index = build_index_from_parts(*index)
    index = prefix_index(index, prefix=prefix, app=app)
    index = suffix_index(index, suffix=suffix, app=app)
    return index
