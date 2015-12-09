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

"""Utility functions for search engine."""

import functools

import six
from flask import current_app, g
from werkzeug.utils import import_string


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
