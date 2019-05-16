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


@index_cmd.group()
def sync():
    """Manage index syncing."""
    pass


@sync.command('init')
def init_sync():
    """Initialize index syncing."""
    pass


@sync.command('run')
@click.argument('jobs', nargs=-1)
@with_appcontext
def run_sync(jobs):
    """Run current index syncing."""
    for job in jobs:
        print('Running sync job: {}'.format(job))
        sync_config = current_app.config['SEARCH_SYNC_JOBS'][job]
        CurrentSyncJob = obj_or_import_string(sync_config['cls'])
        sync_job = CurrentSyncJob(**sync_config['params'])
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
