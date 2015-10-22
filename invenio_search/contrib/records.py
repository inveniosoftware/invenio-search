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

"""Auto-index records metadata."""

import warnings

from flask_sqlalchemy import models_committed
from invenio_records.models import RecordMetadata

from invenio_search import current_search_client

warnings.warn(
    'Automatic RecordMetadata indexing is enabled.',
    category=ImportWarning,
)


@models_committed.connect
def index_record_modification(sender, changes):
    """Example handler for indexing record metadata."""
    for obj, change in changes:
        if isinstance(obj, RecordMetadata):
            if change in ('insert', 'update'):
                current_search_client.index(
                    index='records',
                    doc_type='record',
                    id=obj.id,
                    body=obj.json,
                )
            elif change in ('delete'):
                current_search_client.delete(
                    index='records',
                    doc_type='record',
                    id=obj.id,
                )
