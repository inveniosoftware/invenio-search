# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Click command-line interface for managing search indexes."""

from __future__ import absolute_import, print_function

import json
import sys
from functools import wraps

import click
from elasticsearch import VERSION as ES_VERSION
from flask.cli import with_appcontext

from .proxies import current_search, current_search_client


def abort_if_false(ctx, param, value):
    """Abort command if value is False."""
    if not value:
        ctx.abort()


def es_version_check(f):
    """Decorator to check Elasticsearch version."""
    @wraps(f)
    def inner(*args, **kwargs):
        cluster_ver = current_search.cluster_version[0]
        client_ver = ES_VERSION[0]
        if cluster_ver != client_ver:
            raise click.ClickException(
                'Elasticsearch version mismatch. Invenio was installed with '
                'Elasticsearch v{client_ver}.x support, but the cluster runs '
                'Elasticsearch v{cluster_ver}.x.'.format(
                    client_ver=client_ver,
                    cluster_ver=cluster_ver,
                ))
        return f(*args, **kwargs)
    return inner


#
# Index management commands
#
@click.group()
def index():
    """Manage search indices."""


@index.command()
@with_appcontext
@es_version_check
def check():
    """Check Elasticsearch version."""
    click.secho('Checks passed', fg='green')


@index.command()
@click.option('--force', is_flag=True, default=False)
@with_appcontext
@es_version_check
def init(force):
    """Initialize registered aliases and mappings."""
    click.secho('Creating indexes...', fg='green', bold=True, file=sys.stderr)
    with click.progressbar(
            current_search.create(ignore=[400] if force else None),
            length=len(current_search.mappings)) as bar:
        for name, response in bar:
            bar.label = name
    click.secho('Putting templates...', fg='green', bold=True, file=sys.stderr)
    with click.progressbar(
            current_search.put_templates(ignore=[400] if force else None),
            length=len(current_search.templates)) as bar:
        for response in bar:
            bar.label = response


@index.command()
@click.option('--yes-i-know', is_flag=True, callback=abort_if_false,
              expose_value=False,
              prompt='Do you know that you are going to destroy all indexes?')
@click.option('--force', is_flag=True, default=False)
@with_appcontext
@es_version_check
def destroy(force):
    """Destroy all indexes."""
    click.secho('Destroying indexes...', fg='red', bold=True, file=sys.stderr)
    with click.progressbar(
            current_search.delete(ignore=[400, 404] if force else None),
            length=len(current_search.mappings)) as bar:
        for name, response in bar:
            bar.label = name


@index.command()
@click.argument('index_name')
@click.option('-b', '--body', type=click.File('r'), default=sys.stdin)
@click.option('--force', is_flag=True, default=False)
@click.option('--verbose', is_flag=True, default=False)
@with_appcontext
@es_version_check
def create(index_name, body, force, verbose):
    """Create a new index."""
    result = current_search_client.indices.create(
        index=index_name,
        body=json.load(body),
        ignore=[400] if force else None,
    )
    if verbose:
        click.echo(json.dumps(result))


@index.command('list')
@click.option('-a', '--only-active', is_flag=True, default=False)
@click.option('--only-aliases', is_flag=True, default=False)
@click.option('--verbose', is_flag=True, default=False)
@with_appcontext
def list_cmd(only_active, only_aliases, verbose):
    """List indices."""
    def _tree_print(d, rec_list=None, verbose=False, indent=2):
        # Note that on every recursion rec_list is copied,
        # which might not be very effective for very deep dictionaries.
        rec_list = rec_list or []
        for idx, key in enumerate(sorted(d)):
            line = (['│' + ' ' * indent
                     if i == 1 else ' ' * (indent+1) for i in rec_list])
            line.append('└──' if len(d)-1 == idx else '├──')
            click.echo(''.join(line), nl=False)
            if isinstance(d[key], dict):
                click.echo(key)
                new_rec_list = rec_list + [0 if len(d)-1 == idx else 1]
                _tree_print(d[key], new_rec_list, verbose)
            else:
                leaf_txt = '{} -> {}'.format(key, d[key]) if verbose else key
                click.echo(leaf_txt)

    aliases = (current_search.active_aliases
               if only_active else current_search.aliases)
    active_aliases = current_search.active_aliases

    if only_aliases:
        click.echo(json.dumps(list((aliases.keys())), indent=4))
    else:
        # Mark active indices for printout
        aliases = {(k + (' *' if k in active_aliases else '')): v
                   for k, v in aliases.items()}
        click.echo(_tree_print(aliases, verbose=verbose))


@index.command()
@click.argument('index_name')
@click.option('--force', is_flag=True, default=False)
@click.option('--verbose', is_flag=True, default=False)
@click.option('--yes-i-know', is_flag=True, callback=abort_if_false,
              expose_value=False,
              prompt='Do you know that you are going to delete the index?')
@with_appcontext
@es_version_check
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
@es_version_check
def put(index_name, doc_type, identifier, body, force, verbose):
    """Index input data."""
    result = current_search_client.index(
        index=index_name,
        doc_type=doc_type or index_name,
        id=identifier,
        body=json.load(body),
        op_type='index' if force or identifier is None else 'create',
    )
    if verbose:
        click.echo(json.dumps(result))
