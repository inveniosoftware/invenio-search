# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2021 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Compatibility layer for abstracting away Elasticsearch and OpenSearch."""

import pkg_resources

try:
    pkg_resources.get_distribution('opensearch-py')
    # OpenSearch imports
    from opensearch_dsl import FacetedSearch, Search, Q
    from opensearch_dsl.faceted_search import FacetedResponse
    from opensearch_dsl.query import Bool, Ids
    from opensearchpy import VERSION
    from opensearchpy import OpenSearch as Elasticsearch
    from opensearchpy.exceptions import NotFoundError
except pkg_resources.DistributionNotFound:
    # Elasticsearch imports
    from elasticsearch import VERSION, Elasticsearch
    from elasticsearch.exceptions import NotFoundError
    from elasticsearch_dsl import FacetedSearch, Search, Q
    from elasticsearch_dsl.faceted_search import FacetedResponse
    from elasticsearch_dsl.query import Bool, Ids


__all__ = (
    'Bool',
    'Elasticsearch',
    'FacetedResponse',
    'FacetedSearch',
    'Ids',
    'NotFoundError',
    'Search',
    'VERSION',
    'Q',
)
