# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2022 CERN.
# Copyright (C)      2022 TU Wien.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Search engine API."""

import hashlib

from flask import current_app, request

from .engine import dsl
from .proxies import current_search_client
from .utils import build_alias_name


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


class BaseRecordsSearch(dsl.Search):
    """Example subclass for searching records using Elastic DSL."""

    class Meta:
        """Configuration for ``Search`` and ``FacetedSearch`` classes."""

        index = "*"
        fields = ("*",)
        facets = {}

        default_filter = None
        """Default filter added to search body.

        Example: ``default_filter = DefaultFilter('_access.owner:"1"')``.
        """

    def __init__(self, **kwargs):
        """Use Meta to set kwargs defaults."""
        kwargs.setdefault("index", getattr(self.Meta, "index", None))
        kwargs.setdefault("using", current_search_client)
        kwargs.setdefault("extra", {})

        min_score = current_app.config.get("SEARCH_RESULTS_MIN_SCORE")
        if min_score:
            kwargs["extra"].update(min_score=min_score)

        super(BaseRecordsSearch, self).__init__(**kwargs)

        default_filter = getattr(self.Meta, "default_filter", None)
        if default_filter:
            # NOTE: https://github.com/elastic/elasticsearch/issues/21844
            self.query = dsl.query.Bool(
                minimum_should_match=MinShouldMatch("0<1"), filter=default_filter
            )

    def get_record(self, id_):
        """Return a record by its identifier.

        :param id_: The record identifier.
        :returns: The record.
        """
        return self.query(dsl.query.Ids(values=[str(id_)]))

    def get_records(self, ids):
        """Return records by their identifiers.

        :param ids: A list of record identifier.
        :returns: A list of records.
        """
        return self.query(dsl.query.Ids(values=[str(id_) for id_ in ids]))

    @classmethod
    def faceted_search(cls, query=None, filters=None, search=None):
        """Return faceted search instance with defaults set.

        :param query: Elastic DSL query object (``Q``).
        :param filters: Dictionary with selected facet values.
        :param search: An instance of ``Search`` class. (default: ``cls()``).
        """
        search_ = search or cls()

        class RecordsFacetedSearch(dsl.FacetedSearch):
            """Pass defaults from ``cls.Meta`` object."""

            index = build_alias_name(search_._index[0])
            fields = getattr(search_.Meta, "fields", ("*",))
            facets = getattr(search_.Meta, "facets", {})

            def search(self):
                """Use ``search`` or ``cls()`` instead of default Search."""
                return search_.response_class(dsl.FacetedResponse)

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
        user_agent = request.headers.get("User-Agent")
        if user_agent:
            user_agent = user_agent.encode("utf-8")
        return user_agent or ""

    def _get_user_hash(self):
        """Calculate a digest based on request's User-Agent and IP address."""
        if request:
            user_hash = "{ip}-{ua}".format(
                ip=request.remote_addr, ua=self._get_user_agent()
            )
            alg = hashlib.md5()
            alg.update(user_hash.encode("utf8"))
            return alg.hexdigest()
        return None


class PrefixedIndexList(list):
    """Custom list type for avoiding double prefixing."""

    pass


class PrefixedSearchMixin:
    """Mixing to use index prefixing."""

    def prefix_index(self, index):
        """Using PrefixedIndexList type to avoid double prefixing."""
        # at object instantiation, kwargs['index'] is not defined.
        # Elasticsearch-dsl-py re-instantiated the object at each search
        # by cloning it and passing as kwargs the list of indices
        # kwargs['index'] = ['index-name1', 'index-name2']
        _index_param = index
        if not isinstance(index, PrefixedIndexList):
            if isinstance(index, (tuple, list)):
                _prefixed_index_list = [build_alias_name(_index) for _index in index]
                index = _prefixed_index_list
            elif isinstance(index, str):
                _splitted_index = index.strip().split(",")
                if len(_splitted_index) > 1:
                    _prefix_index_list = [
                        build_alias_name(_index) for _index in _splitted_index
                    ]
                    index = ",".join(_prefix_index_list)
                else:
                    index = build_alias_name(index)
                _index_param = [_index_param]
            self._original_index = _index_param

        return index

    def _clone(self):
        """Clone `_original_index` attribute.

        During re-instantiation Elasticsearch-dsl-py calls `self._clone`
        to copy over the search object. We override the method so we can
        copy the `_original_index` attribute.
        """
        s = super(PrefixedSearchMixin, self)._clone()
        s._original_index = self._original_index
        return s


class BaseRecordsSearchV2(dsl.Search):
    """Base records search V2.

    Apply configuration via kwargs instead of Meta class as in BaseRecordsSearch.
    """

    def __init__(self, fields=("*",), default_filter=None, **kwargs):
        """Sets the needed args in kwargs for the search."""
        kwargs.setdefault("index", "*")
        kwargs.setdefault("using", current_search_client)
        kwargs.setdefault("extra", {})

        min_score = current_app.config.get("SEARCH_RESULTS_MIN_SCORE")
        if min_score:
            kwargs["extra"].update(min_score=min_score)

        super(BaseRecordsSearchV2, self).__init__(**kwargs)

        if default_filter:
            # NOTE: https://github.com/elastic/elasticsearch/issues/21844
            self.query = dsl.query.Bool(
                minimum_should_match=MinShouldMatch("0<1"), filter=default_filter
            )

    def get_record(self, id_):
        """Return a record by its identifier.

        :param id_: The record identifier.
        :returns: The record.
        """
        return self.query(dsl.query.Ids(values=[str(id_)]))

    def get_records(self, ids):
        """Return records by their identifiers.

        :param ids: A list of record identifier.
        :returns: A list of records.
        """
        return self.query(dsl.query.Ids(values=[str(id_) for id_ in ids]))

    def with_preference_param(self, preference=None):
        """Add the preference param to the ES request and return a new Search.

        The preference param avoids the bouncing effect with multiple
        replicas, documented on ES documentation.
        See: https://www.elastic.co/guide/en/elasticsearch/guide/current
        /_search_options.html#_preference for more information.

        :param str preference: A preference value.
        """
        if preference:
            return self.params(preference=preference)
        return self


class RecordsSearch(PrefixedSearchMixin, BaseRecordsSearch):
    """Prefixed record search class."""

    def __init__(self, **kwargs):
        """Constructor."""
        _index = self.prefix_index(
            index=kwargs.get("index", getattr(self.Meta, "index", None))
        )
        kwargs.update({"index": _index})

        super(RecordsSearch, self).__init__(**kwargs)
        if self._index:
            self._index = PrefixedIndexList(self._index)


class RecordsSearchV2(PrefixedSearchMixin, BaseRecordsSearchV2):
    """Prefixed record search class.

    Enhanced version of RecordsSearch class to be able to inject configuration
    via kwargs, instead of using a Meta class.
    """

    def __init__(self, **kwargs):
        """Constructor."""
        _index = self.prefix_index(index=kwargs.get("index", "*"))
        kwargs.update({"index": _index})

        super(RecordsSearchV2, self).__init__(**kwargs)
        if self._index:
            self._index = PrefixedIndexList(self._index)


UnPrefixedRecordsSearch = BaseRecordsSearch
UnPrefixedRecordsSearchV2 = BaseRecordsSearchV2
