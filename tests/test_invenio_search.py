# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.


"""Module tests."""

from __future__ import absolute_import, print_function

import pytest
from elasticsearch import VERSION as ES_VERSION
from elasticsearch.connection import RequestsHttpConnection
from flask import Flask
from mock import patch

from invenio_search import InvenioSearch, current_search, current_search_client


def test_version():
    """Test version import."""
    from invenio_search import __version__
    assert __version__


def test_init():
    """Test extension initialization."""
    app = Flask('testapp')
    ext = InvenioSearch(app)
    assert 'invenio-search' in app.extensions

    app = Flask('testapp')
    ext = InvenioSearch()
    assert 'invenio-search' not in app.extensions
    ext.init_app(app)
    assert 'invenio-search' in app.extensions


def test_client_config():
    """Test Elasticsearch client configuration."""
    app = Flask('testapp')
    app.config['SEARCH_CLIENT_CONFIG'] = {'timeout': 30, 'foo': 'bar'}
    with patch('elasticsearch.Elasticsearch.__init__') as mock_es_init:
        mock_es_init.return_value = None
        ext = InvenioSearch(app)
        es_client = ext.client  # trigger client initialization
        mock_es_init.assert_called_once_with(
            hosts=None, connection_class=RequestsHttpConnection,
            timeout=30, foo='bar')


def test_flush_and_refresh(app):
    """Test flush and refresh."""
    search = app.extensions['invenio-search']
    search.flush_and_refresh('_all')


def test_client_reference():
    """Test client reference."""
    client1 = {'name': 'client1'}
    client2 = {'name': 'client2'}

    app1 = Flask('testapp1')
    app2 = Flask('testapp2')

    ext = InvenioSearch()
    assert 'invenio-search' not in app1.extensions
    assert 'invenio-search' not in app2.extensions

    ext.init_app(app1, client=client1)
    assert 'invenio-search' in app1.extensions

    ext.init_app(app2, client=client2)
    assert 'invenio-search' in app2.extensions

    with app1.app_context():
        assert current_search_client == client1

    with app2.app_context():
        assert current_search_client == client2


def test_default_client(app):
    """Test default client."""
    current_search_client.cluster.health(
        wait_for_status='yellow', request_timeout=1
    )


def test_load_entry_point_group(template_entrypoints):
    """Test entry point loading."""
    app = Flask('testapp')
    ext = InvenioSearch(app)
    ep_group = 'test'

    def mock_entry_points_mappings(group=None):
        assert group == ep_group

        class ep(object):

            name = 'records'
            module_name = 'mock_module.mappings'

        yield ep

    assert len(ext.mappings) == 0
    with patch('invenio_search.ext.iter_entry_points',
               mock_entry_points_mappings):
        ext.load_entry_point_group_mappings(
            entry_point_group_mappings=ep_group)
    assert len(ext.mappings) == 3
    # Check that mappings are loaded from the correct folder depending on the
    # ES version.
    if ES_VERSION[0] > 2:
        mappings_dir = 'mock_module/mappings/v{}/records'.format(ES_VERSION[0])
        assert all(mappings_dir in path for path in ext.mappings.values())

    with patch('invenio_search.ext.iter_entry_points',
               return_value=template_entrypoints('invenio_search.templates')):
        if ES_VERSION[0] == 2:
            assert len(ext.templates.keys()) == 2
        elif ES_VERSION[0] == 5:
            assert len(ext.templates.keys()) == 1


@pytest.mark.parametrize(('aliases_config', 'expected_aliases'), [
    (None, ['records', 'authors']),
    (['records', 'authors'], ['records', 'authors']),
    (['authors'], ['authors']),
    ([], []),
    (['does_not_exist'], []),
])
def test_whitelisted_aliases(app, aliases_config, expected_aliases):
    """Test functionality of active aliases configuration variable."""
    all_aliases = dict(
        authors=['authors', 'authors-authors-v1.0.0'],
        records=[
            'records',
            'records-default-v1.0.0',
            'records-authorities',
            'records-authorities-authority-v1.0.0',
            'records-bibliographic',
            'records-bibliographic-bibliographic-v1.0.0',
        ]
    )

    orig = app.config['SEARCH_MAPPINGS']

    search = app.extensions['invenio-search']
    search.register_mappings('records', 'mock_module.mappings')
    search.register_mappings('authors', 'mock_module.mappings')

    app.config.update(SEARCH_MAPPINGS=aliases_config)

    current_search_client.indices.delete_alias('_all', '_all', ignore=[400,
                                                                       404])
    current_search_client.indices.delete('*')
    list(current_search.create(ignore=None))

    aliases = current_search_client.indices.get_alias()
    if expected_aliases == []:
        assert 0 == len(aliases)
    else:
        for expected_alias in expected_aliases:
            all_expected = all_aliases[expected_alias]
            assert current_search_client.indices.exists(all_expected)

    app.config['SEARCH_MAPPINGS'] = orig


@pytest.mark.parametrize(('aliases_config', 'prefix', 'expected_aliases'), [
    (['authors'], 'test-', ['test-authors']),
    (['authors', 'records'], 'dev-', ['dev-records', 'dev-authors']),
])
def test_prefix_search_mappings(app, aliases_config, prefix, expected_aliases):
    """Test that indices are created when prefix & search mappings are set."""
    app.config.update(
        SEARCH_MAPPINGS=aliases_config,
        SEARCH_INDEX_PREFIX=prefix,
    )

    search = app.extensions['invenio-search']
    search.register_mappings('records', 'mock_module.mappings')
    search.register_mappings('authors', 'mock_module.mappings')

    active_aliases = search.active_aliases

    assert len(active_aliases) == len(expected_aliases)
    for expected_alias in expected_aliases:
        assert expected_alias in active_aliases


def _test_prefix_indices(app, prefix_value):
    """Assert that each index name contains the prefix."""
    app.config['SEARCH_INDEX_PREFIX'] = prefix_value
    suffix = '-abc'
    search = app.extensions['invenio-search']
    search.register_mappings('records', 'mock_module.mappings', suffix=suffix)

    assert set(search.mappings.keys()) == {
        '{0}records-authorities-authority-v1.0.0{1}'.format(
            prefix_value or '', suffix
        ),
        '{0}records-bibliographic-bibliographic-v1.0.0{1}'.format(
            prefix_value or '', suffix),
        '{0}records-default-v1.0.0{1}'.format(prefix_value or '', suffix)
    }

    # clean-up in case something failed previously
    current_search_client.indices.delete('*')
    # create indices and test
    list(search.create())
    assert current_search_client.indices.exists(list(search.mappings.keys()))
    # clean-up
    current_search_client.indices.delete('*')


def test_indices_prefix_empty_value(app):
    """Test indices creation with prefix value empty string."""
    prefix_value = ''
    _test_prefix_indices(app, prefix_value)


def test_indices_prefix_none_value(app):
    """Test indices creation with a prefix value None."""
    prefix_value = None
    _test_prefix_indices(app, prefix_value)


def test_indices_prefix_some_value(app):
    """Test indices creation with a prefix value `myprefix-`."""
    prefix_value = 'myprefix-'
    _test_prefix_indices(app, prefix_value)


def _test_prefix_templates(app, prefix_value, template_entrypoints):
    """Assert that templates take into account the prefix name."""

    def _contains_prefix(prefix_value, string_or_list):
        """Return True if the prefix value is in the input list or string."""
        if isinstance(string_or_list, list):
            return all([True for match in string_or_list
                        if prefix_value in match])
        else:
            return prefix_value in string_or_list

    def _test_prefix_replaced_in_body(prefix_value, tpl_key):
        """Test that the prefix is replaced in the body when defined."""
        if prefix_value:
            tpl = current_search_client.indices.get_template(name)
            assert name in tpl
            assert _contains_prefix(prefix_value, tpl[name][tpl_key])

    app.config['SEARCH_INDEX_PREFIX'] = prefix_value
    search = app.extensions['invenio-search']
    with patch('invenio_search.ext.iter_entry_points',
               return_value=template_entrypoints('invenio_search.templates')):
        # create templates
        list(search.put_templates())

        if ES_VERSION[0] == 2:
            assert len(search.templates.keys()) == 2
            name = '{0}record-view-v1'.format(prefix_value or '')
            assert name in search.templates
            assert current_search_client.indices.exists_template(name)
            name = '{0}subdirectory-file-download-v1'.format(
                prefix_value or '')
            assert name in search.templates
            assert current_search_client.indices.exists_template(name)
            _test_prefix_replaced_in_body(prefix_value, 'template')
        elif ES_VERSION[0] == 5:
            assert len(search.templates.keys()) == 1
            name = '{0}record-view-v{1}'.format(
                prefix_value or '', ES_VERSION[0])
            assert name in search.templates
            assert current_search_client.indices.exists_template(name)
            _test_prefix_replaced_in_body(prefix_value, 'template')
        else:
            assert len(search.templates.keys()) == 1
            name = '{0}record-view-v{1}'.format(
                prefix_value or '', ES_VERSION[0])
            assert name in search.templates
            assert current_search_client.indices.exists_template(name)
            _test_prefix_replaced_in_body(prefix_value, 'index_patterns')


def test_templates_prefix_empty_value(app, template_entrypoints):
    """Test templates creation with prefix value empty string."""
    prefix_value = ''
    _test_prefix_templates(app, prefix_value, template_entrypoints)


def test_templates_prefix_none_value(app, template_entrypoints):
    """Test templates creation with a prefix value None."""
    prefix_value = None
    _test_prefix_templates(app, prefix_value, template_entrypoints)


def test_templates_prefix_some_value(app, template_entrypoints):
    """Test templates creation with a prefix value `myprefix-`."""
    prefix_value = 'myprefix-'
    _test_prefix_templates(app, prefix_value, template_entrypoints)
