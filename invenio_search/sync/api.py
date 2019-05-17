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

    def __init__(self, rollover_threshold, source_indexes=[], dest_indexes=[]):
        """Initialize the job configuration."""
        self.rollover_threshold = rollover_threshold
        self.source_indexes = source_indexes
        self.dest_indexes = dest_indexes

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
            from invenio_pidstore.models import PersistenIdentifier, PIDStatus
            from invenio_records.models import RecordMetadata

            records_ids = RecordMetadata.query.with_entities(RecordMetadata.id).filter(RecordMetadata.updated >= update_time).all()
            pids = PersistenIdentifier.query.filter(PersistenIdentifier.update >= update_time).all()

            deleted_records = [str(pid.object_uuid) for pid in pids if pid.status = PIDStatus.deleted]
            updated_records = [str(recid) for recid in records_ids if recid not in deleted_records]

            return (updated_records, deleted_records)

        # determine bounds
        s = RecordsSearch()
        s = s.sort('-updated')[0]
        hits = s.execute()
        total = hits.total if lt_es7 : hits.total.value

        start_time = None if total < 1 else hits.hits[0]['_source']['_updated']
        end_time = datetime.now()

        if not start_time:
            # use of reindex api
            payload = {
                "source": {
                    "index": self.source_indexes[0]
                },
                "dest": {
                    "index": self.dest_indexes[0]
                }
            }
            # reindex using ES reindex api
            current_search_client.reindex(body=payload)
        else:
            # Fetch data from start_time until end_time from db
            (updated_redords, deleted_records) = _get_remaining_records()
            indexer = RecordIndexer()
            indexer.bulk_index(updated_redords)
            indexer.bulk.delete(deleted_records)

            total_actions = len(updated_redords + deleted_records)
            if total_actions <= self.rollover_threshold:
                self.rollover()
            else:
                # configure or compute time to rerun
                run_sync_job.apply_async(self, eta=timedelta(minutes=10))
