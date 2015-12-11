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

import flask

from flask_sqlalchemy import models_committed, before_models_committed
from invenio_db import db
from invenio_records.models import RecordMetadata
from invenio_access.models import ActionUsers
from invenio_records.permissions import records_read_all

from invenio_search import current_search_client


warnings.warn(
    'Automatic RecordMetadata indexing is enabled.',
    category=ImportWarning,
)


def _index_search_record(record):
    """Index the given record."""
    user_permissions = db.session.query(ActionUsers).filter(
        ActionUsers.argument == str(record.id)).filter(
        ActionUsers.action == records_read_all.value).all()
    record_json = {
        '_access': {
            'include_users': [perm.user_id for perm in user_permissions
                              if not perm.exclude],
            'exclude_users': [perm.user_id for perm in user_permissions
                              if perm.exclude],
            'public': 1 if len(user_permissions) == 0 else 0
        },
        '_created': record.created,
        '_updated': record.updated,
        '_revision': record.version_id - 1,
    }
    record_json.update(record.json)
    current_search_client.index(
        index='records',
        doc_type='record',
        id=str(record.id),
        body=record_json,
    )


@before_models_committed.connect
def register_record_modification(sender, changes):
    """Example handler for indexing access restricted record metadata."""
    processed = flask.g.get('invenio_search_processed_records', set())
    for obj, change in changes:
        if isinstance(obj, RecordMetadata):
            if change in ('insert', 'update'):
                # check that we didn't already register this record
                if str(obj.id) not in processed:
                    _index_search_record(obj)
            elif change in ('delete'):
                # check that we didn't already delete this record
                if str(obj.id) not in processed:
                    current_search_client.delete(
                        index='records',
                        doc_type='record',
                        id=str(obj.id),
                    )
        elif (isinstance(obj, ActionUsers) and
              obj.action == records_read_all.value):
            # check that we didn't already register this record
            if obj.argument not in processed:
                record = db.session.query(RecordMetadata).filter(
                    RecordMetadata.id == obj.argument).one_or_none()
                if record is not None:
                    _index_search_record(record)
                    processed.add(str(record.id))

    flask.g.invenio_search_processed_records = processed


@models_committed.connect
def index_record_modification(sender, changes):
    """Reset the set of processed records for the next session."""
    flask.g.invenio_search_processed_records = set()


def filter_record_access_query_enhancer(query, **kwargs):
    """Enhance query with user authentication rules."""
    from invenio_query_parser.ast import AndOp, DoubleQuotedValue, Keyword, \
        KeywordOp, NotOp
    from flask_security import current_user
    query.body['_source'] = {'exclude': ['_access']}
    if not current_user.is_authenticated:
        query.query = AndOp(
            KeywordOp(Keyword('_access.public'), DoubleQuotedValue(1)),
            query.query
        )
    else:
        query.query = AndOp(
            AndOp(
                KeywordOp(Keyword('_access.include_users'),
                          DoubleQuotedValue(current_user.id)),
                NotOp(KeywordOp(Keyword('_access.exclude_users'),
                                DoubleQuotedValue(current_user.id)))
            ),
            query.query
        )
