# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2003, 2004, 2005, 2006, 2007, 2008, 2010, 2011, 2012, 2013,
#               2015, 2016 CERN.
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

# SEARCH_ALLOWED_KEYWORDS -- a list of allowed keywords for the query parser.
SEARCH_ALLOWED_KEYWORDS = []


#
# ELASTIC configuration
#

# SEARCH_ELASTIC_HOSTS -- list of hosts for Elasticsearch client.
# http://elasticsearch-py.readthedocs.io/en/master/api.html#elasticsearch.Elasticsearch
SEARCH_ELASTIC_HOSTS = None  # default localhost

# SEARCH_ELASTIC_KEYWORD_MAPPING -- this variable holds a dictionary to map
# invenio keywords to elasticsearch fields
SEARCH_ELASTIC_KEYWORD_MAPPING = {
    None: ["_all"],
    "author": {
        'a': ["main_entry_personal_name.personal_name",
              "added_entry_personal_name.personal_name"],
        'p': ["main_entry_personal_name.personal_name",
              "added_entry_personal_name.personal_name"],
        'e': ['authors.raw'],
    },
    "collection": ["_collections"],
    "title": ["title_statement.title"],
    "980": [
        "collections.primary",
        "collections.secondary",
        "collections.deleted",
    ],
    "980__a": ["collections.primary"],
    "980__b": ["collections.secondary"],
    "542__l": ["information_relating_to_copyright_status.copyright_status"],
}
