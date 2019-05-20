# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Indexer class for syncing."""

from __future__ import absolute_import, print_function

from datetime import datetime
from invenio_indexer.api import RecordIndexer
from invenio_indexer.utils import es_bulk_param_compatibility
from invenio_records.api import Record
from invenio_records.models import RecordMetadata
from kombu import Exchange, Queue

SYNC_INDEXER_MQ_EXCHANGE = Exchange('sync_indexer', type='direct')
"""Default exchange for message queue."""

SYNC_INDEXER_MQ_QUEUE = Queue(
    'indexer', exchange=SYNC_INDEXER_MQ_EXCHANGE, routing_key='sync-indexer')

SYNC_INDEXER_MQ_ROUTING_KEY = 'sync-indexer'
"""Default routing key for message queue."""

class SyncIndexer(RecordIndexer):
    """Indexer class for ES syncing module."""

    def __init__(self, **kwargs):
        self._queue = SYNC_INDEXER_MQ_QUEUE
        self._routing_key = SYNC_INDEXER_MQ_ROUTING_KEY
        self._exchange = SYNC_INDEXER_MQ_EXCHANGE
        super(SyncIndexer, self).__init__(**kwargs)

    #
    # Low-level implementation
    #
    def _bulk_op(self, record_id_iterator, op_type, index=None, doc_type=None):
        """Index record in Elasticsearch asynchronously.

        :param record_id_iterator: Iterator that yields record UUIDs.
        :param op_type: Indexing operation (one of ``index``, ``create``,
            ``delete`` or ``update``).
        :param index: The Elasticsearch index. (Default: ``None``)
        :param doc_type: The Elasticsearch doc_type. (Default: ``None``)
        """
        with self.create_producer() as producer:
            for (rec, updated_timespamp) in record_id_iterator:
                producer.publish(dict(
                    id=str(rec),
                    op=op_type,
                    index=index,
                    doc_type=doc_type,
                    record_updated_time=str(datetime.timestamp(updated_timespamp)),
                ))

    def _get_record(self, payload):
        """Return record to sync."""
        id_ = payload['id']
        updated_ = datetime.fromtimestamp(float(payload['record_updated_time']))
        model = RecordMetadata.query.filter_by(id=id_, updated=updated_).one()
        return Record(data=model.json, model=model)

    def _delete_action(self, payload):
        """Bulk delete action.

        :param payload: Decoded message body.
        :returns: Dictionary defining an Elasticsearch bulk 'delete' action.
        """
        index, doc_type = payload.get('index'), payload.get('doc_type')
        import ipdb; ipdb.set_trace()
        if not (index and doc_type):
            record = self._get_record(payload)
            index, doc_type = self.record_to_index(record)

        return {
            '_op_type': 'delete',
            '_index': index,
            '_type': doc_type,
            '_id': payload['id'],
        }

    @es_bulk_param_compatibility
    def _index_action(self, payload):
        """Bulk index action.

        :param payload: Decoded message body.
        :returns: Dictionary defining an Elasticsearch bulk 'index' action.
        """
        record = self._get_record(payload)
        index, doc_type = self.record_to_index(record)

        arguments = {}
        body = self._prepare_record(record, index, doc_type, arguments)

        action = {
            '_op_type': 'index',
            '_index': index,
            '_type': doc_type,
            '_id': str(record.id),
            '_version': record.revision_id,
            '_version_type': self._version_type,
            '_source': body
        }
        action.update(arguments)

        return action
