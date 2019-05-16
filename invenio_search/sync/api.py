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
from invenio_indexer.api import RecordIndexer
from invenio_search.api import RecordsSearch
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

            records_ids = RecordMetadata.query.with_entities(RecordMetadata.id).filter(RecordMetadata.updated > update_time).all()
            pids = PersistentIdentifier.query.filter(PersistentIdentifier.updated >= update_time).all()

            deleted_records = [pid.object_uuid for pid in pids if pid.status == PIDStatus.DELETED]
            updated_records = [recid[0] for recid in records_ids if recid[0] not in deleted_records]

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
            indexer = RecordIndexer()
            indexer.bulk_index(updated_records)
            indexer.bulk_delete(deleted_records)
            indexer.process_bulk_queue()

            total_actions = len(updated_records + deleted_records)
            print('[*] indexed {} record(s)'.format(total_actions))
            if total_actions <= self.rollover_threshold:
                self.rollover()
            else:
                pass
