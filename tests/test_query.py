# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.


"""Module tests."""

from __future__ import absolute_import, print_function

from elasticsearch_dsl import Q

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
            'bool': {'filter': [{'terms': {'public': 1}}]}
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
