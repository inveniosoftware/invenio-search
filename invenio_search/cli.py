# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015, 2016 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Click command-line interface for managing search indexes."""

from __future__ import absolute_import, print_function

import json
import sys

import click
from flask.cli import with_appcontext

from .proxies import current_search, current_search_client


def abort_if_false(ctx, param, value):
    """Abort command is value is False."""
    if not value:
        ctx.abort()


#
# Index management commands
#
@click.group()
def index():
    """Management command for search indicies."""


@index.command()
@click.option('--force', is_flag=True, default=False)
@with_appcontext
def init(force):
    """Initialize registered aliases and mappings."""
    click.secho('Creating indexes...', fg='green', bold=True, file=sys.stderr)
    with click.progressbar(
            current_search.create(ignore=[400] if force else None),
            length=current_search.number_of_indexes) as bar:
        for name, response in bar:
            bar.label = name


@index.command()
@click.option('--yes-i-know', is_flag=True, callback=abort_if_false,
              expose_value=False,
              prompt='Do you know that you are going to destroy all indexes?')
@click.option('--force', is_flag=True, default=False)
@with_appcontext
def destroy(force):
    """Destroy all indexes."""
    click.secho('Destroying indexes...', fg='red', bold=True, file=sys.stderr)
    with click.progressbar(
            current_search.delete(ignore=[400, 404] if force else None),
            length=current_search.number_of_indexes) as bar:
        for name, response in bar:
            bar.label = name


@index.command()
@click.argument('index_name')
@click.option('-b', '--body', type=click.File('r'), default=sys.stdin)
@click.option('--force', is_flag=True, default=False)
@click.option('--verbose', is_flag=True, default=False)
@with_appcontext
def create(index_name, body, force, verbose):
    """Create new index."""
    result = current_search_client.indices.create(
        index=index_name,
        body=json.load(body),
        ignore=[400] if force else None,
    )
    if verbose:
        click.echo(json.dumps(result))


@index.command()
@click.argument('index_name')
@click.option('--force', is_flag=True, default=False)
@click.option('--verbose', is_flag=True, default=False)
@click.option('--yes-i-know', is_flag=True, callback=abort_if_false,
              expose_value=False,
              prompt='Do you know that you are going to delete the index?')
@with_appcontext
def delete(index_name, force, verbose):
    """Delete index by its name."""
    result = current_search_client.indices.delete(
        index=index_name,
        ignore=[400, 404] if force else None,
    )
    if verbose:
        click.echo(json.dumps(result))


@index.command()
@click.argument('index_name')
@click.argument('doc_type')
@click.option('-i', '--identifier', default=None)
@click.option('-b', '--body', type=click.File('r'), default=sys.stdin)
@click.option('--force', is_flag=True, default=False)
@click.option('--verbose', is_flag=True, default=False)
@with_appcontext
def put(index_name, doc_type, identifier, body, force, verbose):
    """Index input data."""
    result = current_search_client.index(
        index=index_name,
        doc_type=doc_type or index_name,
        id=identifier,
        body=json.load(body),
        op_type='index' if force else 'create',
    )
    if verbose:
        click.echo(json.dumps(result))
