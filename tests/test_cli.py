# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015, 2016, 2017 CERN.
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


"""Test CLI."""

from __future__ import absolute_import, print_function

from click.testing import CliRunner
from elasticsearch import VERSION as ES_VERSION
from flask.cli import ScriptInfo
from mock import patch

from invenio_search.cli import index as cmd
from invenio_search.proxies import current_search_client


def test_init(app, template_entrypoints):
    """Run client initialization."""
    search = app.extensions['invenio-search']
    search.register_mappings('records', 'mock_module.mappings')

    assert 'records' in search.aliases
    assert set(search.aliases['records']) == set([
        'records-authorities',
        'records-bibliographic',
        'records-default-v1.0.0',
    ])
    assert set(search.mappings.keys()) == set([
        'records-authorities-authority-v1.0.0',
        'records-bibliographic-bibliographic-v1.0.0',
        'records-default-v1.0.0',
    ])
    assert 6 == search.number_of_indexes

    with patch('invenio_search.ext.iter_entry_points',
               return_value=template_entrypoints('invenio_search.templates')):
        if ES_VERSION[0] == 2:
            assert len(search.templates.keys()) == 2
            assert 'record-view-v1' in search.templates
            assert 'subdirectory-file-download-v1' in search.templates
        elif ES_VERSION[0] == 5:
            assert len(search.templates.keys()) == 1
            assert 'record-view-v5' in search.templates

    with app.app_context():

        current_search_client.indices.delete_alias('_all', '_all',
                                                   ignore=[400, 404])
        current_search_client.indices.delete('*')
        aliases = current_search_client.indices.get_alias()
        assert 0 == len(aliases)

    runner = CliRunner()
    script_info = ScriptInfo(create_app=lambda info: app)

    with runner.isolated_filesystem():
        result = runner.invoke(cmd, ['init'],
                               obj=script_info)
        with app.app_context():
            if ES_VERSION[0] == 2:
                assert current_search_client.indices.exists_template(
                    'subdirectory-file-download-v1')
                assert current_search_client.indices.exists_template(
                    'record-view-v1')
            elif ES_VERSION[0] == 5:
                assert current_search_client.indices.exists_template(
                    'record-view-v5')
        assert 0 == result.exit_code

    with app.app_context():
        aliases = current_search_client.indices.get_alias()
        assert 5 == sum(len(idx.get('aliases', {}))
                        for idx in aliases.values())

        assert current_search_client.indices.exists(
            list(search.mappings.keys())
        )

    # Clean-up:
    with app.app_context():
        result = runner.invoke(cmd, ['destroy'],
                               obj=script_info)
        assert 1 == result.exit_code

        result = runner.invoke(cmd, ['destroy', '--yes-i-know'],
                               obj=script_info)
        assert 0 == result.exit_code

        aliases = current_search_client.indices.get_alias()
        assert 0 == len(aliases)
