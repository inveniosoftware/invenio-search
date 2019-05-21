# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Index syncing API."""

from __future__ import absolute_import, print_function

from datetime import datetime

from elasticsearch import VERSION as ES_VERSION
from invenio_search.api import RecordsSearch
from invenio_search.sync.indexer import SyncIndexer
from invenio_search.sync.tasks import run_sync_job
from invenio_search.proxies import current_search_client

lt_es7 = ES_VERSION[0] < 7
INDEX_SYNC_INDEX = '.invenio-index-sync'

def get_es_client(es_config):
    """Get ES client."""
    if es_config['version'] == 2:
        from elasticsearch2 import Elasticsearch
        return Elasticsearch(host='localhost', port=9200)
    else:
        raise Exception('unsupported ES version: {}'.format(es_config['version']))



class SyncJob:
    """Index synchronization job base class."""

    def __init__(self, rollover_threshold,
                 pid_mappings, src_es_client):
        """Initialize the job configuration."""
        self.rollover_threshold = rollover_threshold
        self.pid_mappings = pid_mappings
        self.src_es_client = src_es_client
        self.src_es_client['client'] = get_es_client(src_es_client)
        # self._state_client = SyncJobState(
        #     index=INDEX_SYNC_INDEX,
        #     client=new_es_client,
        #     initial_state={
        #         'index_mapping': {},
        #         'index_suffix': None,
        #         'last_record_update': None,
        #         'reindex_api_task_id': None,
        #         'threshold_reached': False,
        #         'rollover_ready': False,
        #         'rollover_finished': False,
        #         'stats': {},
        #     },
        # )

    def init(self):
        # Check if there's an index sync already happening (and bail)
        if current_search_client.indices.exists(INDEX_SYNC_INDEX):
            raise Exception('The index {} already exists, a job is already running.'.format(INDEX_SYNC_INDEX))

        state = SyncJobState(
            index=INDEX_SYNC_INDEX
        )

        # Get old indices
        index_mapping = {}
        for pid_type, name in self.pid_mappings.items():
            if self.src_es_client['client'].indices.exists(name):
                pass
            elif self.src_es_client['client'].indices.exists_alias(name):
                pass
            else:
                raise Exception("alias or index doesn't exist: {}".format(name))

        # Create new indices

        # Store index mapping in state
        # state.create({
        #     'index_mapping': {},
        #     'index_suffix': None,
        #     'last_record_update': None,
        #     'reindex_api_task_id': None,
        #     'threshold_reached': False,
        #     'rollover_ready': False,
        #     'rollover_finished': False,
        #     'stats': {},
        # })

    def iter_indexer_ops(self, start_date=None, end_date=None):
        """Iterate over documents that need to be reindexed."""
        from datetime import datetime, timedelta
        from invenio_db import db
        from invenio_pidstore.models import PersistentIdentifier, PIDStatus
        from invenio_records.models import RecordMetadata
        import sqlalchemy as sa

        q = db.session.query(
            RecordMetadata.id.distinct(),
            PersistentIdentifier.status
        ).join(
            PersistentIdentifier,
            RecordMetadata.id == PersistentIdentifier.object_uuid
        ).filter(
            PersistentIdentifier.object_type == 'rec',
            RecordMetadata.updated >= start_date
        ).yield_per(500)  # TODO: parameterize

        for record_id, pid_status in q:
            if pid_status == PIDStatus.DELETED:
                yield {'op': 'delete', 'id': record_id}
            else:
                yield {'op': 'create', 'id': record_id}

    def rollover(self):
        """Perform a rollover action."""
        raise NotImplementedError()

    @property
    def state(self):
        return self._state_client

    def run(self):
        """Run the index sync job."""
        # determine bounds
        start_time = self.state['last_record_update']

        # if not start_time:
        #     # use reindex api
        #     print('[*] running reindex')
        #     old_es_host = '{host}:{port}'.format(**self.src_es_client['params'])
        #     payload = {
        #         "source": {
        #             "remote": {"host": old_es_host},
        #             "index": self.source_indexes[0]
        #         },
        #         "dest": {"index": self.dest_indexes[0]}
        #     }
        #     # Reindex using ES Reindex API synchronously
        #     # Keep track of the time we issued the reindex command
        #     start_date = datetime.utcnow()
        #     current_search_client.reindex(body=payload)
        #     self.state['last_record_update'] = \
        #         str(datetime.timestamp(start_date))
        #     print('[*] reindex done')
        # else:
        #     # Fetch data from start_time from db
        #     indexer = SyncIndexer()

        #     # Send indexer actions to special reindex queue
        #     start_date = datetime.utcnow()
        #     indexer._bulk_op(self.iter_indexer_ops(start_time), None)
        #     self.state['last_record_update'] = \
        #             str(datetime.timestamp(start_date))
        #     # Run synchornous bulk index processing
        #     # TODO: make this asynchronous by default
        #     succeeded, failed = indexer.process_bulk_queue()
        #     total_actions = succeeded + failed
        #     print('[*] indexed {} record(s)'.format(total_actions))
        #     if total_actions <= self.rollover_threshold:
        #         self.rollover()


class SyncJobState:
    """Synchronization job state.

    The state is stored in ElasticSearch and can be accessed similarly to a
    python dictionary.
    """

    def __init__(self, index, document_id=None, client=None, force=False,
                 initial_state=None):
        """Synchronization job state in ElasticSearch."""
        self.index = index
        self.doc_type = 'doc' if lt_es7 else '_doc'
        self.document_id = document_id or 'state'
        self.force = force
        self.client = client or current_search_client

    @property
    def state(self):
        """Get the full state."""
        _state = self.client.get(
            index=self.index,
            doc_type=self.doc_type,
            id=self.document_id,
            ignore=[404],
        )
        return _state['_source ']


    def __getitem__(self, key):
        """Get key in state."""
        return self.state[key]

    def __setitem__(self, key, value):
        """Set key in state."""
        state = self.state
        state[key] = value
        self._save(state)

    def __delitem__(self, key):
        """Delete key in state."""
        state = self.state
        del state[key]
        self._save(state)

    def update(self, **changes):
        """Update multiple keys in the state."""
        state = self.state
        for key, value in changes.items():
            state[key] = value
        self._save(state)

    def create(self, initial_state, force=False):
        """Create state index and the document."""
        if (self.force or force) and self.client.indices.exists(self.index):
            self.client.indices.delete(self.index)
        self.client.indices.create(self.index)
        return self._save(initial_state)

    def _save(self, state):
        """Save the state to ElasticSearch."""
        # TODO: User optimistic concurrency control via "version_type=external_gte"
        self.client.index(
            index=self.index,
            id=self.document_id,
            doc_type=self.doc_type,
            body=state
        )
        return self.client.get(
            index=self.index,
            id=self.document_id,
            doc_type=self.doc_type,
        )
