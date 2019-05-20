# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Index syncing API."""

from __future__ import absolute_import, print_function

from elasticsearch import VERSION as ES_VERSION
from invenio_search.api import RecordsSearch
from invenio_search.sync.indexer import SyncIndexer
from invenio_search.sync.tasks import run_sync_job
from invenio_search.proxies import current_search_client

lt_es7 = ES_VERSION[0] < 7

class SyncJob:
    """Index synchronization job base class."""

    def __init__(self, rollover_threshold, source_indexes=[], dest_indexes=[],
                 old_es_client={}, new_es_client={}):
        """Initialize the job configuration."""
        self.rollover_threshold = rollover_threshold
        self.source_indexes = source_indexes
        self.dest_indexes = dest_indexes
        self.old_es_client = old_es_client
        self.new_es_client = new_es_client

    def iter_docs(self, from_dt=None, until_dt=None):
        """Iterate over documents that need to be reindexed."""
        raise NotImplementedError()

    def index_docs(self, docs):
        """Bulk index documents."""
        raise NotImplementedError()

    def rollover(self):
        """Perform a rollover action."""
        raise NotImplementedError()

    def run(self):
        """Run the index sync job."""

        def _get_remaining_records(update_time):
            """Return all remaining records after `update_time`."""
            from invenio_pidstore.models import PersistentIdentifier, PIDStatus
            from invenio_records.models import RecordMetadata

            records = [(_rec.id, _rec.updated) for _rec in
                RecordMetadata.query.filter(RecordMetadata.updated > update_time).all()]
            deleted_pids = [_pid.object_uuid for _pid in
                PersistentIdentifier.query.filter_by(status=PIDStatus.DELETED)
                    .filter(PersistentIdentifier.updated >= update_time).all()]

            updated_records = []
            deleted_records = []

            for _rec in records:
                id_ = _rec[0]
                if id_ in deleted_pids:
                    deleted_records.append(_rec)
                else:
                    updated_records.append(_rec)

            return (updated_records, deleted_records)

        # determine bounds
        search = RecordsSearch(index=self.dest_indexes[0])
        search = search.sort('-_updated')
        hits = search.execute()
        total = len(hits) if lt_es7 else len(hits)

        start_time = None if total < 1 else hits[0]['_updated']

        if not start_time:
            # use of reindex api
            print('[*] running reindex')
            old_es_host = '{host}:{port}'.format(**self.old_es_client)
            payload = {
                "source": {
                    "remote": {
                        "host": old_es_host
                    },
                    "index": self.source_indexes[0]
                },
                "dest": {
                    "index": self.dest_indexes[0]
                }
            }
            # reindex using ES reindex api
            current_search_client.reindex(body=payload)
            print('[*] reindex done')
        else:
            # Fetch data from start_time until end_time from db
            (updated_records, deleted_records) = _get_remaining_records(start_time)
            indexer = SyncIndexer()
            indexer.bulk_index(updated_records)
            indexer.bulk_delete(deleted_records)
            indexer.process_bulk_queue()

            total_actions = len(updated_records) + len(deleted_records)
            print('[*] indexed {} record(s)'.format(total_actions))
            if total_actions <= self.rollover_threshold:
                self.rollover()
            else:
                pass


class SyncJobState:
    """Synchronization job state.

    The state is stored in ElasticSearch and can be accessed similarly to a
    python dictionary.
    """

    INIT_STATE = {
        'run_count': 0,
        'last_updated': None,
    }

    def __init__(self, index, document_id, force=False):
        """Synchronization job state in ElasticSearch."""
        self.index = index
        self.document_id = document_id
        if not current_search_client.indices.exists(index) or force:
            self._create()

    @property
    def state(self):
        """Get the full state."""
        return current_search_client.get(
            index=self.index,
            id=self.document_id
        )['_source']

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

    def _create(self):
        """Create state index and the document."""
        if current_search_client.indices.exists(self.index):
            current_search_client.indices.delete(self.index)
        current_search_client.indices.create(self.index)
        self._save(self.INIT_STATE)

    def _save(self, state):
        """Save the state to ElasticSearch."""
        current_search_client.index(
            index=self.index,
            id=self.document_id,
            body=state
        )
