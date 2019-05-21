# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Index syncing CLI commands."""

import click

from flask import current_app
from flask.cli import with_appcontext
from invenio_search.cli import index as index_cmd
from invenio_search.utils import obj_or_import_string
from .proxies import current_index_sync


@index_cmd.group()
def sync():
    """Manage index syncing."""
    pass


@sync.command('init')
@with_appcontext
@click.argument('job_id')
def init_sync(job_id):
    """Initialize index syncing."""
    job = current_index_sync.jobs[job_id]
    sync_job = job['cls'](**job['params'])
    sync_job.init()


@sync.command('run')
@with_appcontext
@click.argument('job_id')
def run_sync(job_id):
    """Run current index syncing."""
    job = current_index_sync.jobs[job_id]
    sync_job = job['cls'](**job['params'])
    sync_job.run()


@sync.command('rollover')
def rollover_sync():
    """Perform the index syncing rollover action."""
    pass


@sync.command('status')
def status_sync():
    """Get current index syncing status."""
    pass


@sync.command('cancel')
def cancel_sync():
    """Cancel the current index syncing."""
    pass
