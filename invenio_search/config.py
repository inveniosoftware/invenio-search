# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2003, 2004, 2005, 2006, 2007, 2008, 2010, 2011, 2012, 2013,
#               2015, 2016, 2017 CERN.
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

"""Invenio Search Engine config parameters."""

#
# ELASTIC configuration
#

SEARCH_ELASTIC_HOSTS = None  # default localhost
"""List of hosts for Elasticsearch client.

Elasticsearch
    <https://elasticsearch-py.readthedocs.io/en/master/api.html#elasticsearch.Elasticsearch>
"""

SEARCH_MAPPINGS = None  # loads all mappings and creates aliases for them
"""List of aliases for which, their search mappings should be created.

If `None` all aliases (and their search mappings) defined through entry_points
in setup.py will be created.

Provide an empty list if no aliases (or their search mappings)
should be created.

For example if you don't want to create aliases
and their mappings for `authors`:

.. code-block::python

    # in your `setup.py` you would specify:
    entry_points={
        ...,
        'invenio_search.mappings': [
            'records = invenio_foo_bar.mappings',
            'authors = invenio_foo_bar.mappings',
            'books = invenio_baz.mappings',
        ],
        ...
    }

    # and in your config.py
    SEARCH_MAPPINGS = ['records']

"""
