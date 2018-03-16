# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Search engine API."""

import hashlib
from functools import partial

from elasticsearch import VERSION as ES_VERSION
from elasticsearch_dsl import FacetedSearch, Search
from elasticsearch_dsl.faceted_search import FacetedResponse
from elasticsearch_dsl.query import Bool, Ids
from flask import request

from .proxies import current_search_client


class DefaultFilter(object):
    """Shortcut for defining default filters with query parser."""

    def __init__(self, query=None, query_parser=None):
        """Build filter property with query parser."""
        self._query = query
        self.query_parser = query_parser or (lambda x: x)

    @property
    def query(self):
        """Build lazy query if needed."""
        return self._query() if callable(self._query) else self._query

    def __get__(self, obj, objtype):
        """Return parsed query."""
        return self.query_parser(self.query)


class MinShouldMatch(str):
    """Work-around for Elasticsearch DSL problem.

    The ElasticSearch DSL Bool query tries to inspect the
    ``minimum_should_match`` parameter, but understands only integers and not
    queries like "0<1". This class circumvents the specific problematic clause
    in Elasticsearch DSL.
    """

    def __lt__(self, other):
        """Circumvent problematic Elasticsearch DSL clause."""
        return False

    def __le__(self, other):
        """Circumvent problematic Elasticsearch DSL clause."""
        return False

    def __gt__(self, other):
        """Circumvent problematic Elasticsearch DSL clause."""
        return False

    def __ge__(self, other):
        """Circumvent problematic Elasticsearch DSL clause."""
        return False


class RecordsSearch(Search):
    """Example subclass for searching records using Elastic DSL."""

    class Meta:
        """Configuration for ``Search`` and ``FacetedSearch`` classes."""

        index = '_all'
        doc_types = None
        fields = ('*', )
        facets = {}

        default_filter = None
        """Default filter added to search body.

        Example: ``default_filter = DefaultFilter('_access.owner:"1"')``.
        """

    def __init__(self, **kwargs):
        """Use Meta to set kwargs defaults."""
        kwargs.setdefault('index', getattr(self.Meta, 'index', None))
        kwargs.setdefault('doc_type', getattr(self.Meta, 'doc_types', None))
        kwargs.setdefault('using', current_search_client)

        super(RecordsSearch, self).__init__(**kwargs)

        default_filter = getattr(self.Meta, 'default_filter', None)
        if default_filter:
            # NOTE: https://github.com/elastic/elasticsearch/issues/21844
            self.query = Bool(minimum_should_match=MinShouldMatch("0<1"),
                              filter=default_filter)

    def get_record(self, id_):
        """Return a record by its identifier.

        :param id_: The record identifier.
        :returns: The record.
        """
        return self.query(Ids(values=[str(id_)]))

    def get_records(self, ids):
        """Return records by their identifiers.

        :param ids: A list of record identifier.
        :returns: A list of records.
        """
        return self.query(Ids(values=[str(id_) for id_ in ids]))

    @classmethod
    def faceted_search(cls, query=None, filters=None, search=None):
        """Return faceted search instance with defaults set.

        :param query: Elastic DSL query object (``Q``).
        :param filters: Dictionary with selected facet values.
        :param search: An instance of ``Search`` class. (default: ``cls()``).
        """
        search_ = search or cls()

        class RecordsFacetedSearch(FacetedSearch):
            """Pass defaults from ``cls.Meta`` object."""

            index = search_._index[0]
            doc_types = getattr(search_.Meta, 'doc_types', ['_all'])
            fields = getattr(search_.Meta, 'fields', ('*', ))
            facets = getattr(search_.Meta, 'facets', {})

            def search(self):
                """Use ``search`` or ``cls()`` instead of default Search."""
                # Later versions of `elasticsearch-dsl` (>=5.1.0) changed the
                # Elasticsearch FacetedResponse class constructor signature.

                if ES_VERSION[0] > 2:
                    return search_.response_class(FacetedResponse)
                return search_.response_class(partial(FacetedResponse, self))

        return RecordsFacetedSearch(query=query, filters=filters or {})

    def with_preference_param(self):
        """Add the preference param to the ES request and return a new Search.

        The preference param avoids the bouncing effect with multiple
        replicas, documented on ES documentation.
        See: https://www.elastic.co/guide/en/elasticsearch/guide/current
        /_search_options.html#_preference for more information.
        """
        user_hash = self._get_user_hash()
        if user_hash:
            return self.params(preference=user_hash)
        return self

    def _get_user_agent(self):
        """Retrieve the request's User-Agent, if available.

        Taken from Flask Login utils.py.
        """
        user_agent = request.headers.get('User-Agent')
        if user_agent:
            user_agent = user_agent.encode('utf-8')
        return user_agent or ''

    def _get_user_hash(self):
        """Calculate a digest based on request's User-Agent and IP address."""
        if request:
            user_hash = '{ip}-{ua}'.format(ip=request.remote_addr,
                                           ua=self._get_user_agent())
            alg = hashlib.md5()
            alg.update(user_hash.encode('utf8'))
            return alg.hexdigest()
        return None
