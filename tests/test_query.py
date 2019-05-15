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

from elasticsearch import VERSION as ES_VERSION
from elasticsearch_dsl import Q, Search
from flask import request

from invenio_search.api import BaseRecordsSearch, DefaultFilter, RecordsSearch


def test_empty_query(app):
    """Test building an empty query."""
    q = RecordsSearch()
    if ES_VERSION[0] >= 7:
        q.to_dict() == {}
    else:
        q.to_dict() == {'query': {'match_all': {}}}

    q = RecordsSearch.faceted_search('')
    if ES_VERSION[0] >= 7:
        q._s.to_dict() == {'highlight': {'fields': {'*': {}}}}
    else:
        q._s.to_dict() == {'query': {'match_all': {}}}

    q = RecordsSearch()[10]
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

    q = RecordsSearch()
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


def test_elasticsearch_query(app):
    """Test building a real query."""
    from flask import g

    class TestSearch(RecordsSearch):
        class Meta:
            default_filter = DefaultFilter(
                lambda: Q('terms', public=g.public)
            )

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


def test_elasticsearch_query_min_score(app):
    """Test building a query with min_score."""
    app.config.update(SEARCH_RESULTS_MIN_SCORE=0.1)

    q = RecordsSearch()
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


def test_prefix_index_from_kwargs(app):
    """Test that index is prefixed when pass it through kwargs."""
    prefix_value = 'myprefix-'
    index_value = 'myindex'
    app.config['SEARCH_INDEX_PREFIX'] = prefix_value

    prefixed_index = ['{}{}'.format(prefix_value, index_value)]
    q = RecordsSearch(index=index_value)
    _test_original_index_is_stored_when_prefixing(q, prefixed_index,
                                                  [index_value])


def test_prefix_index_list(app):
    """Test that index is prefixed when pass it through kwargs."""
    prefix_value = 'myprefix-'
    index_value = ['myindex', 'myanotherindex']
    app.config['SEARCH_INDEX_PREFIX'] = prefix_value

    prefixed_index = ['{}{}'.format(prefix_value, _index)
                      for _index in index_value]

    q = RecordsSearch(index=index_value)
    _test_original_index_is_stored_when_prefixing(q, prefixed_index,
                                                  index_value)


def test_prefix_multi_index_string(app):
    """Test that index is prefixed when pass it through kwargs."""
    prefix_value = 'myprefix-'
    index_value = 'myindex,myanotherindex'
    app.config['SEARCH_INDEX_PREFIX'] = prefix_value

    prefixed_index = [','.join(['{}{}'.format(prefix_value, _index)
                                for _index in index_value.split(',')])]
    q = RecordsSearch(index=index_value)
    _test_original_index_is_stored_when_prefixing(q, prefixed_index,
                                                  [index_value])
