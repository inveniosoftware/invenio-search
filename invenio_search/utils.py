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

import os


def build_index_name(*parts):
    """Build an index name from parts."""
    return os.path.splitext('-'.join([
        part for part in parts if part
    ]))[0]


def schema_to_index(schema, index_names=None):
    """Get index/doc_type given a schema URL.

    >>> from invenio_search.utils import schema_to_index
    >>> schema_to_index('records/record-v1.0.0.json')
    ('records-record-v1.0.0', 'record-v1.0.0')
    >>> schema_to_index('default-v1.0.0.json')
    ('default-v1.0.0', 'default-v1.0.0')
    >>> schema_to_index('default-v1.0.0.json', index_names=[])
    (None, None)
    >>> schema_to_index('invalidextension')
    (None, None)

    :param schema: The schema name
    :param index_names: A list of index name.
    :returns: A tuple containing (index, doc_type).
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
