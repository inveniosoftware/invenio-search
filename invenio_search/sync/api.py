# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Index syncing API."""

from __future__ import absolute_import, print_function


class SyncJob:
    """Index synchronization job base class."""

    def __init__(self, rollover_threshold):
        """Initialize the job configuration."""
        self.rollover_threshold = rollover_threshold

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
        docs = self.iter_docs(form_dt, until_dt)
        indexed_count = self.index_docs(docs)
        if indexed_count <= self.rollover_threshold:
            self.rollover()
