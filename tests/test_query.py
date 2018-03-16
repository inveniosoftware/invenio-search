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

from elasticsearch_dsl import Q, Search
from flask import request

from invenio_search.api import DefaultFilter, RecordsSearch


def test_empty_query(app):
    """Test building an empty query."""
    with app.app_context():
        q = RecordsSearch()
        assert q.to_dict()['query'] == {'match_all': {}}

        q = RecordsSearch.faceted_search('')
        assert q._s.to_dict()['query'] == {'match_all': {}}

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
    """Test building an empty query."""
    from flask import g

    class TestSearch(RecordsSearch):
        class Meta:
            default_filter = DefaultFilter(
                lambda: Q('terms', public=g.public)
            )

    with app.app_context():
        g.public = 1
        q = TestSearch()
        assert q.to_dict()['query'] == {
            'bool': {'minimum_should_match': "0<1",
                     'filter': [{'terms': {'public': 1}}]}
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


def test_es_preference_param_no_request():
    """Test that the preference param is not added when not in a request."""
    RecordsSearch.__bases__ = (SpySearch,)

    rs = RecordsSearch()
    new_rs = rs.with_preference_param()
    assert new_rs.exposed_params == {}


def test_es_preference_param(app):
    """Test the preference param is correctly added in a request."""
    RecordsSearch.__bases__ = (SpySearch,)

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
