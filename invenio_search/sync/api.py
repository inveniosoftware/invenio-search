# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Index syncing API."""

from __future__ import absolute_import, print_function

import json

from datetime import datetime

from elasticsearch import VERSION as ES_VERSION
from flask import current_app
from invenio_search.api import RecordsSearch
from invenio_search.sync.indexer import SyncIndexer
from invenio_search.sync.tasks import run_sync_job
from invenio_search.proxies import current_search, current_search_client
from invenio_search.utils import prefix_index

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
        self._state = SyncJobState(index=INDEX_SYNC_INDEX)

    def _build_index_mapping(self):
        """Build index mapping."""
        old_client = self.src_es_client['client']

        def get_src(name, prefix):
            index_name = None
            if old_client.indices.exists(name):
                index_name = name
            elif old_client.indices.exists_alias(name):
                indexes = list(old_client.indices.get_alias(name=name).keys())
                if not indexes:
                    raise Exception('no index found for alias: {}'.format(name))
                index_name = indexes[0]
            else:
                raise Exception("alias or index doesn't exist: {}".format(name))
            return dict(
                index=index_name,
                prefix=prefix
            )

        def get_dst(aliases, prefixed_name):
            if isinstance(aliases, str):
                raise Exception('failed to find index with name: {}'.format(prefixed_name))
            for key, values in aliases.items():
                if key == prefixed_name:
                    index, mapping = list(values.items())[0]
                    return dict(
                        index=index,
                        mapping=mapping
                    )
                else:
                    return get_dst(values, prefixed_name)

        index_mapping = {}
        for pid_type, name in self.pid_mappings.items():
            mapping = dict(
                src=get_src(name, self.src_es_client['prefix'] or ''),
                dst=get_dst(current_search.aliases, prefix_index(current_app, name))
            )

            index_mapping[pid_type] = mapping
        return index_mapping

    def init(self):
        # Check if there's an index sync already happening (and bail)
        if current_search_client.indices.exists(INDEX_SYNC_INDEX):
            raise Exception('The index {} already exists, a job is already active.'.format(INDEX_SYNC_INDEX))

        # Get old indices
        index_mapping = self._build_index_mapping()

        # Create new indices
        for indexes in index_mapping.values():
            dst = indexes['dst']
            with open(dst['mapping'], 'r') as mapping_file:
                mapping = json.loads(mapping_file.read())
            current_search_client.indices.create(
                index=dst['index'],
                body=mapping
            )
            print('[*] created index: {index} with mappings {mapping}'.format(**dst))

        # Store index mapping in state
        initial_state = {
            'index_mapping': index_mapping,
            'index_suffix': current_search.current_suffix,
            'last_record_update': None,
            'reindex_api_task_id': None,
            'threshold_reached': False,
            'rollover_ready': False,
            'rollover_finished': False,
            'stats': {},
        }
        self.state.create(initial_state)

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
        return self._state

    def run(self):
        """Run the index sync job."""
        # determine bounds
        start_time = self.state['last_record_update']
        index_mapping = self.state['index_mapping']

        if not start_time:
            # use reindex api
            for doc_type, indexes in index_mapping.items():
                print('[*] running reindex for doc type: {}'.format(doc_type))
                old_es_host = '{host}:{port}'.format(**self.src_es_client['params'])
                payload = {
                    "source": {
                        "remote": {"host": old_es_host},
                        "index": indexes['src']['index']
                    },
                    "dest": {"index": indexes['dst']['index']}
                }
                # Reindex using ES Reindex API synchronously
                # Keep track of the time we issued the reindex command
                start_date = datetime.utcnow()
                current_search_client.reindex(body=payload)
                self.state['last_record_update'] = \
                    str(datetime.timestamp(start_date))
            print('[*] reindex done')
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
        return _state['_source']


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
