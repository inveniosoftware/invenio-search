# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Index syncing tasks."""

from __future__ import absolute_import, print_function

from celery import shared_task

from .proxies import current_index_sync


@shared_task(ignore_result=True)
def run_sync_job(job_id):
    """Run an index sync job by its ID."""
    job = current_index_sync.jobs[job_id]
    job.run()
