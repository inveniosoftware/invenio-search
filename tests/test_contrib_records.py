# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
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


"""Test record indexing."""

from __future__ import absolute_import, print_function

from time import sleep

from click.testing import CliRunner
from flask_cli import ScriptInfo
from invenio_db import db

from invenio_search.cli import index as cmd
from invenio_search.proxies import current_search, current_search_client


def test_record_indexing(records_app):
    """Run record autoindexer."""
    app = records_app
    search = app.extensions['invenio-search']
    search.register_mappings('records', 'data')

    with app.app_context():

        current_search_client.indices.delete_alias('_all', '_all',
                                                   ignore=[400, 404])
        current_search_client.indices.delete('*')
        aliases = current_search_client.indices.get_aliases()
        assert 0 == len(aliases)

    runner = CliRunner()
    script_info = ScriptInfo(create_app=lambda info: app)

    with runner.isolated_filesystem():
        result = runner.invoke(cmd, ['destroy', '--yes-i-know'],
                               obj=script_info)
        result = runner.invoke(cmd, ['init'],
                               obj=script_info)
        assert 0 == result.exit_code

    with app.app_context():
        from invenio_records.models import RecordMetadata
        with db.session.begin_nested():
            record1 = RecordMetadata(json={
                '$schema': ('http://example.com/schemas/'  # external site
                            'records/default-v1.0.0.json'),
                'title': 'Test1',
            })
            db.session.add(record1)
            record2 = RecordMetadata(json={
                '$schema': {
                    '$ref': ('http://example.com/schemas/'  # external site
                             'records/default-v1.0.0.json')
                },
                'title': 'Test2',
            })
            db.session.add(record2)
        db.session.commit()

        response = current_search_client.get(
            index='records-default-v1.0.0',
            id=record1.id,
        )
        assert str(record1.id) == response['_id']

        response = current_search_client.get(
            index='records-default-v1.0.0',
            id=record2.id,
        )
        assert str(record2.id) == response['_id']

        db.session.delete(record1)
        db.session.commit()

        response = current_search_client.get(
            index='records-default-v1.0.0',
            id=record1.id,
            ignore=404,
        )
        assert not response['found']

    # Clean-up:
    with app.app_context():
        result = runner.invoke(cmd, ['destroy', '--yes-i-know'],
                               obj=script_info)
        assert 0 == result.exit_code
