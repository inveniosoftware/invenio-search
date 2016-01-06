# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2014, 2015, 2016 CERN.
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

"""Utility functions for search engine."""

import functools
import os

import six
from flask import current_app, g
from werkzeug.utils import import_string


def build_index_name(*parts):
    """Build an index name from parts."""
    return os.path.splitext('-'.join([
        part for part in parts if part
    ]))[0]


def schema_to_index(schema, index_names=None):
    """Get index/doc_type given a schema URL.

    >>> schema_to_index('records/record-v1.0.0.json')
    ('records-record-v1.0.0', 'record-v1.0.0')
    >>> schema_to_index('default-v1.0.0.json')
    ('default-v1.0.0', 'default-v1.0.0')
    >>> schema_to_index('default-v1.0.0.json', index_names=[])
    (None, None)
    >>> schema_to_index('invalidextension')
    (None, None)
    """
    parts = schema.split('/')
    doc_type = os.path.splitext(parts[-1])

    if doc_type[1] not in {'.json', }:
        return (None, None)

    if index_names is None:
        return (build_index_name(*parts), doc_type[0])

    for start in range(len(parts)):
        index_name = build_index_name(*parts[start:])
        if index_name in index_names:
            return (index_name, doc_type[0])

    return (None, None)


def g_memoise(method=None, key=None):
    """Memoise method results on application context."""
    if method is None:
        return functools.partial(g_memoise, key=key)

    key = key or method.__name__

    @functools.wraps(method)
    def decorator(*args, **kwargs):
        results = getattr(g, key, None)
        if results is None:
            results = method(*args, **kwargs)
            setattr(g, key, results)
        return results
    return decorator


@g_memoise
def query_enhancers():
    """Return list of query enhancers."""
    functions = []
    for enhancer in current_app.config['SEARCH_QUERY_ENHANCERS']:
        if isinstance(enhancer, six.string_types):
            enhancer = import_string(enhancer)
        functions.append(enhancer)
    return functions


@g_memoise
def parser():
    """Return search query parser."""
    query_parser = current_app.config['SEARCH_QUERY_PARSER']
    if isinstance(query_parser, six.string_types):
        query_parser = import_string(query_parser)
    return query_parser


@g_memoise
def query_walkers():
    """Return query walker instances."""
    return [
        import_string(walker)() if isinstance(walker, six.string_types)
        else walker() for walker in current_app.config['SEARCH_QUERY_WALKERS']
    ]


@g_memoise
def search_walkers():
    """Return in search walker instances."""
    return [
        import_string(walker)() if isinstance(walker, six.string_types)
        else walker() for walker in current_app.config['SEARCH_WALKERS']
    ]
