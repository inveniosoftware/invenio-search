# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Index syncing CLI commands."""

import click

from invenio_search.cli import index as index_cmd


@index_cmd.group()
def sync():
    """Manage index syncing."""
    pass


@sync.command('init')
def init_sync():
    """Initialize index syncing."""
    pass


@sync.command('run')
def run_sync():
    """Run current index syncing."""
    pass


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
