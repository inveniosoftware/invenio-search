# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015, 2016 CERN.
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

"""Auto-index records metadata."""

import warnings

from flask import current_app
from flask_sqlalchemy import models_committed
from invenio_records.models import RecordMetadata

from invenio_search import current_search, current_search_client
from invenio_search.utils import schema_to_index

warnings.warn(
    'Automatic RecordMetadata indexing is enabled.',
    category=ImportWarning,
)


@models_committed.connect
def index_record_modification(sender, changes):
    """Example handler for indexing record metadata."""
    index_default = current_app.config['SEARCH_INDEX_DEFAULT']
    doc_type_default = current_app.config['SEARCH_DOC_TYPE_DEFAULT']
    index_names = current_search.mappings.keys()

    for obj, change in changes:
        if isinstance(obj, RecordMetadata):
            index, doc_type = index_default, doc_type_default
            schema = obj.json.get('$schema')
            if isinstance(schema, dict):
                schema = schema.get('$ref')
            if schema:
                index, doc_type = schema_to_index(
                    schema, index_names=index_names
                )

            if change in ('insert', 'update'):
                body = {
                    '_created': obj.created,
                    '_updated': obj.updated,
                }
                body.update(obj.json)
                # FIXME hack so we don't have object and string in $schema
                body['$schema'] = schema
                current_search_client.index(
                    index=index,
                    doc_type=doc_type,
                    id=obj.id,
                    body=body,
                    version=obj.version_id,
                    version_type='external',
                )
            elif change in ('delete'):
                current_search_client.delete(
                    index=index,
                    doc_type=doc_type,
                    id=obj.id,
                )
