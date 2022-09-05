# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2018 CERN.
# Copyright (C)      2022 University Münster.
# Copyright (C)      2022 TU Wien.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Transparency module for importing the chosen search engine.

This module imports the ``elasticsearch``/``opensearchpy`` and
``elasticsearch_dsl``/``opensearch_dsl`` packages based on availability,
and provides them as ``search`` and ``dsl`` respectively.
The aim of this is to make the choice of the search engine (Elasticsearch
vs. OpenSearch) more transparent.
"""

ES = "Elasticsearch"
OS = "OpenSearch"

try:
    # fail if both ES and OS packages are installed
    import elasticsearch
    import elasticsearch_dsl
    import opensearch_dsl
    import opensearchpy
except ModuleNotFoundError:
    # only one or zero are installed

    try:
        import elasticsearch as search
        import elasticsearch_dsl as dsl

        SearchEngine = search.Elasticsearch
        SEARCH_DISTRIBUTION = ES

    except ModuleNotFoundError:
        import opensearch_dsl as dsl
        import opensearchpy as search

        SearchEngine = search.OpenSearch
        SEARCH_DISTRIBUTION = OS

else:
    # no exception raised, both are installed. Fail.
    raise ImportError(
        "Elasticsearch and OpenSearch libraries cannot be installed both at the same time. Please uninstall the one that you are not using."
    )


def check_search_version(distribution, version):
    """Check if the search in use matches the given distribution and version.

    The ``version`` argument can either be a number or a function accepting one
    argument.
    In the first case, the specified number will be compared for equality with
    the major part of the search version (e.g. 7 for ES 7.x).
    For the second variant, the specified function will be called with the major
    version as argument. This allows for more elaborate and custom comparisons.
    The function is expected to return a boolean value.
    An example would be: ``lambda v: v >= 7``
    """
    if SEARCH_DISTRIBUTION.lower() != distribution.lower():
        return False

    if not callable(version):
        return search.VERSION[0] == version
    else:
        return version(search.VERSION[0])


def check_es_version(version):
    """Convenience alias for ``check_search_version(ES, version)``."""
    return check_search_version(ES, version)


def check_os_version(version):
    """Convenience alias for ``check_search_version(OS, version)``."""
    return check_search_version(OS, version)


def uses_es7():
    """Check if ES7+ (or OS1) is in use."""
    is_es7 = check_search_version(ES, version=lambda v: v >= 7)
    return is_es7 or check_search_version(OS, 1)


__all__ = (
    "ES",
    "OS",
    "SEARCH_DISTRIBUTION",
    "SearchEngine",
    "check_es_version",
    "check_os_version",
    "check_search_version",
    "dsl",
    "search",
    "uses_es7",
)
