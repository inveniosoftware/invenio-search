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

import pypeg2
from werkzeug.utils import cached_property

from .utils import parser, query_enhancers, query_walkers, search_walkers


class Query(object):
    """Query wrapper."""

    def __init__(self, query=None, **kwargs):
        """Initialize with search query."""
        self._parser = parser()
        self._query = query or ''
        self.body = {}
        self.build(**kwargs)

    @cached_property
    def query(self):
        """Parse query string using given grammar."""
        # Skip pypeg2 parsing if parser is undefined.
        if self._parser is None:
            return self._query

        tree = pypeg2.parse(self._query, parser(), whitespace="")
        for walker in query_walkers():
            tree = tree.accept(walker)
        return tree

    def build(self, **kwargs):
        """Build query body."""
        # Enhance query first
        for enhancer in query_enhancers():
            enhancer(self, **kwargs)

        query = self.query

        if self._parser is not None:
            for walker in search_walkers():
                query = query.accept(walker)

        self.body['query'] = query

    def __getitem__(self, sliced_key):
        """Set pagination."""
        if isinstance(sliced_key, slice):
            assert sliced_key.step in (None, 1)
            self.body.update({
                'size': sliced_key.stop - sliced_key.start,
                'from': sliced_key.start,
            })
        else:
            self.body.update({
                'size': 1,
                'from': int(sliced_key),
            })
        return self

    def sort(self, *fields):
        """Specify sorting options.

        Call with no arguments with reset the sorting.
        """
        # Reset sorting options.
        if not fields:
            if 'sort' in self.body:
                del self.body['sort']
            return self

        def _parse_field(field_data):
            """Parse field data and checks for ``-`` before field name."""
            if isinstance(field_data, dict):
                return field_data
            order = 'asc' if not field_data.startswith('-') else 'desc'
            # TODO add field name mapping
            return {field_data.lstrip('-'): {'order': order}}

        self.body.setdefault('sort', [])
        for field in fields:
            self.body['sort'].append(_parse_field(field))
        return self

    def highlight(self, field=None, **kwargs):
        """Enable hightlighs for given field."""
        self.body.setdefault('highlight', {'fields': {}})

        if field is None:
            del self.body['highlight']
            return self

        self.body['highlight']['fields'][field] = kwargs
        return self

    # TODO aggregation, parent_child, etc.
