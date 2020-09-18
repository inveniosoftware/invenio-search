# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.


"""Module tests."""

from __future__ import absolute_import, print_function

import hashlib
from functools import partial

import pytest
from elasticsearch import VERSION as ES_VERSION
from elasticsearch_dsl import Q, Search
from flask import request

from invenio_search.api import BaseRecordsSearch, BaseRecordsSearchV2, \
    DefaultFilter, RecordsSearch, RecordsSearchV2


def test_empty_query(app):
    """Test building an empty query."""
    def _assert_base_search(q):
        """Assert base search queries."""
        if ES_VERSION[0] >= 7:
            q.to_dict() == {}
        else:
            q.to_dict() == {'query': {'match_all': {}}}

    def _assert_base_faceted_search(q):
        """Assert base faceted search queries."""
        if ES_VERSION[0] >= 7:
            q._s.to_dict() == {'highlight': {'fields': {'*': {}}}}
        else:
            q._s.to_dict() == {'query': {'match_all': {}}}

    def _assert_pagination_sorting(q):
        """Assert pagination and sorting cases."""
        assert q.to_dict()['from'] == 10
        assert q.to_dict()['size'] == 1

        q = q[10:20]
        assert q.to_dict()['from'] == 10
        assert q.to_dict()['size'] == 10

        q = q.sort({'field1': {'order': 'asc'}})
        assert q.to_dict()['sort'][0] == {'field1': {'order': 'asc'}}

        q = q.sort()
        assert 'sort' not in q.to_dict()

        q = q.sort('-field1')
        assert q.to_dict()['sort'][0] == {'field1': {'order': 'desc'}}

        q = q.sort('field2', {'field3': {'order': 'asc'}})
        assert q.to_dict()['sort'][0] == 'field2'
        assert q.to_dict()['sort'][1] == {'field3': {'order': 'asc'}}
        q.sort()

    def _assert_highlighting(q):
        """Assert query highlighting."""
        q = q.highlight('field1', index_options='offsets')
        assert len(q.to_dict()['highlight']['fields']) == 1
        assert q.to_dict()['highlight']['fields']['field1'] == {
            'index_options': 'offsets'
        }

        q = q.highlight('field2')
        assert len(q.to_dict()['highlight']['fields']) == 2
        assert q.to_dict()['highlight']['fields']['field1'] == {
            'index_options': 'offsets'
        }
        assert q.to_dict()['highlight']['fields']['field2'] == {}

        q = q.highlight()
        assert 'highligth' not in q.to_dict()

    # V1
    q = RecordsSearch()
    _assert_base_search(q)

    q = RecordsSearch.faceted_search('')
    _assert_base_faceted_search(q)

    q = RecordsSearch()[10]
    _assert_pagination_sorting(q)

    q = RecordsSearch()
    _assert_highlighting(q)

    # V2 (Faceted search removed)
    q = RecordsSearchV2()
    _assert_base_search(q)

    q = RecordsSearchV2()[10]
    _assert_pagination_sorting(q)

    q = RecordsSearchV2()
    _assert_highlighting(q)


def test_elasticsearch_query(app):
    """Test building a real query."""
    from flask import g

    def filter_():
        return Q('terms', public=g.public)

    class TestSearch(RecordsSearch):
        class Meta:
            default_filter = DefaultFilter(filter_)

    g.public = 1
    q = TestSearch()
    assert q.to_dict()['query'] == {
        'bool': {
            'minimum_should_match': "0<1",
            'filter': [{'terms': {'public': 1}}]
        }
    }
    g.public = 0
    q = TestSearch()
    q = q.query(Q('match', title='Higgs'))
    assert q.to_dict()['query']['bool']['filter'] == [
        {'terms': {'public': 0}}
    ]
    assert q.to_dict()['query']['bool']['must'] == [
        {'match': {'title': 'Higgs'}}
    ]

    # NOTE: Why duplicated code? To check changes.
    # The V2 does not access any global, therefore the reset
    # makes no sense. It is tested anyway.

    g.public = 1
    q = RecordsSearchV2(default_filter=filter_())
    assert q.to_dict()['query'] == {
        'bool': {
            'minimum_should_match': "0<1",
            'filter': [{'terms': {'public': 1}}]
        }
    }
    g.public = 0
    q = RecordsSearchV2(default_filter=filter_())
    q = q.query(Q('match', title='Higgs'))
    assert q.to_dict()['query']['bool']['filter'] == [
        {'terms': {'public': 0}}
    ]
    assert q.to_dict()['query']['bool']['must'] == [
        {'match': {'title': 'Higgs'}}
    ]


class SpySearch(Search):
    exposed_params = {}

    def params(self, **kwargs):
        self.exposed_params.update(kwargs)
        return super(SpySearch, self).params(**kwargs)


def test_es_preference_param_no_request(app):
    """Test that the preference param is not added when not in a request."""
    BaseRecordsSearch.__bases__ = (SpySearch,)

    rs = RecordsSearch()
    new_rs = rs.with_preference_param()
    assert new_rs.exposed_params == {}

    # NOTE: for RecordsSearchV2 no preference requires no call


def test_es_preference_param(app):
    """Test the preference param is correctly added in a request."""
    BaseRecordsSearch.__bases__ = (SpySearch,)

    with app.test_request_context('/', headers={'User-Agent': 'Chrome'},
                                  environ_base={'REMOTE_ADDR': '212.54.1.8'}):
        rs = RecordsSearch()
        new_rs = rs.with_preference_param()

        alg = hashlib.md5()
        encoded_user_agent = 'Chrome'.encode('utf8')
        encoded_user_string = '{ip}-{ua}'.format(ip=request.remote_addr,
                                                 ua=encoded_user_agent)
        alg.update(encoded_user_string.encode('utf8'))
        digest = alg.hexdigest()

        assert new_rs.exposed_params == dict(preference=digest)

    # Note: V2 does not require a request context
    BaseRecordsSearchV2.__bases__ = (SpySearch,)

    rs = RecordsSearchV2()
    new_rs = rs.with_preference_param(preference=1234)
    assert new_rs.exposed_params == {'preference': 1234}


@pytest.mark.parametrize("search_cls", [RecordsSearch, RecordsSearchV2])
def test_elasticsearch_query_min_score(app, search_cls):
    """Test building a query with min_score."""
    app.config.update(SEARCH_RESULTS_MIN_SCORE=0.1)

    q = search_cls()
    q = q.query(Q('match', title='Higgs'))

    search_dict = q.to_dict()
    assert 'min_score' in search_dict
    assert search_dict['min_score'] == app.config['SEARCH_RESULTS_MIN_SCORE']


def _test_original_index_is_stored_when_prefixing(q, prefixed_index,
                                                  original_index):
    """Test original index is stored."""
    q = q.query(Q('match', title='Higgs'))
    q = q.sort()
    search_dict = q.to_dict()
    assert 'query' in search_dict
    assert q._index == prefixed_index
    assert q._original_index == original_index


def test_prefix_index_from_meta(app):
    """Test that index is prefixed when you use `Meta.index` field."""
    class TestSearch(RecordsSearch):
        class Meta:
            index = 'myindex'
    prefix_value = 'myprefix-'
    index_value = TestSearch.Meta.index
    app.config['SEARCH_INDEX_PREFIX'] = prefix_value

    prefixed_index = ['{}{}'.format(prefix_value, index_value)]
    q = TestSearch()
    _test_original_index_is_stored_when_prefixing(q, prefixed_index,
                                                  [index_value])


@pytest.mark.parametrize("search_cls", [RecordsSearch, RecordsSearchV2])
def test_prefix_index_from_kwargs(app, search_cls):
    """Test that index is prefixed when pass it through kwargs."""
    prefix_value = 'myprefix-'
    index_value = 'myindex'
    app.config['SEARCH_INDEX_PREFIX'] = prefix_value

    prefixed_index = ['{}{}'.format(prefix_value, index_value)]
    q = search_cls(index=index_value)
    _test_original_index_is_stored_when_prefixing(q, prefixed_index,
                                                  [index_value])


@pytest.mark.parametrize("search_cls", [RecordsSearch, RecordsSearchV2])
def test_prefix_index_list(app, search_cls):
    """Test that index is prefixed when pass it through kwargs."""
    prefix_value = 'myprefix-'
    index_value = ['myindex', 'myanotherindex']
    app.config['SEARCH_INDEX_PREFIX'] = prefix_value

    prefixed_index = ['{}{}'.format(prefix_value, _index)
                      for _index in index_value]

    q = search_cls(index=index_value)
    _test_original_index_is_stored_when_prefixing(q, prefixed_index,
                                                  index_value)


@pytest.mark.parametrize("search_cls", [RecordsSearch, RecordsSearchV2])
def test_prefix_multi_index_string(app, search_cls):
    """Test that index is prefixed when pass it through kwargs."""
    prefix_value = 'myprefix-'
    index_value = 'myindex,myanotherindex'
    app.config['SEARCH_INDEX_PREFIX'] = prefix_value

    prefixed_index = [','.join(['{}{}'.format(prefix_value, _index)
                                for _index in index_value.split(',')])]
    q = search_cls(index=index_value)
    _test_original_index_is_stored_when_prefixing(q, prefixed_index,
                                                  [index_value])
