# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2014, 2015 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""Search engine API."""

from functools import partial

from elasticsearch_dsl import FacetedSearch, Search
from elasticsearch_dsl.faceted_search import FacetedResponse
from elasticsearch_dsl.query import Bool, Ids

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


class RecordsSearch(Search):
    """Example subclass to searching records using Elastic DSL."""

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

        # Record class?
        # Record(result['_source'], model=None, id_=result['_id'])

    def __init__(self, **kwargs):
        """Use Meta to set kwargs defaults."""
        kwargs.setdefault('index', getattr(self.Meta, 'index', None))
        kwargs.setdefault('doc_type', getattr(self.Meta, 'doc_types', None))
        kwargs.setdefault('using', current_search_client)

        super(RecordsSearch, self).__init__(**kwargs)

        default_filter = getattr(self.Meta, 'default_filter', None)
        if default_filter:
            self.query = Bool(filter=default_filter)

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
                return search_.response_class(partial(FacetedResponse, self))

        return RecordsFacetedSearch(query=query, filters=filters or {})
