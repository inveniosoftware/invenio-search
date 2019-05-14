# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.


"""Module tests."""

from __future__ import absolute_import, print_function

from collections import defaultdict

import pytest
from elasticsearch import VERSION as ES_VERSION
from flask import Flask
from mock import patch

from invenio_search import InvenioSearch, current_search, current_search_client
from invenio_search.errors import IndexAlreadyExistsError


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
            hosts=None, timeout=30, foo='bar')


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


@pytest.mark.parametrize(
    ('suffix', 'create_index', 'create_alias', 'expected'), [
        ('', 'authors-authors-v1.0.0', None, []),
        ('', None, 'authors-authors-v1.0.0', []),
        ('-abc', 'authors-authors-v1.0.0', None, []),
        ('-test', 'authors-authors-not-exist', None, [
            'authors-authors-v1.0.0-test',
            'authors-authors-v1.0.0',
            'authors',
        ]),
    ]
)
def test_creating_alias_existing_index(app, suffix, create_index, create_alias,
                                       expected):
    """Test creating new alias and index where there already exists one."""
    search = app.extensions['invenio-search']
    search.register_mappings('authors', 'mock_module.mappings')
    search._current_suffix = suffix
    current_search_client.indices.delete_alias('_all', '_all', ignore=[400,
                                                                       404])
    current_search_client.indices.delete('*')
    new_indexes = []
    if create_index:
        current_search_client.indices.create(index=create_index)
        new_indexes.append(create_index)
    if create_alias:
        write_alias_index = '{}-suffix'.format(create_alias)
        current_search_client.indices.create(
            index=write_alias_index
        )
        new_indexes.append(write_alias_index)
        current_search_client.indices.put_alias(
            index=write_alias_index,
            name=create_alias,
        )
    if expected:
        results = list(current_search.create(ignore=None))
        assert len(results) == len(expected)
        for result in results:
            assert result[0] in expected
        indices = current_search_client.indices.get('*')
        index_names = list(indices.keys())
        alias_names = []
        for index in index_names:
            alias_names.extend(list(indices[index]['aliases'].keys()))
        for index, _ in results:
            if index.endswith(suffix):
                assert sorted(index_names) == sorted([index] + new_indexes)
            else:
                assert index in alias_names
    else:
        with pytest.raises(Exception):
            results = list(current_search.create(ignore=None))
        indices = current_search_client.indices.get('*')
        index_names = list(indices.keys())
        assert index_names == new_indexes
        if create_index:
            assert len(indices[create_index]['aliases']) == 0


@pytest.mark.parametrize(('aliases_config', 'prefix', 'expected_aliases'), [
    (['authors'], 'test-', ['authors']),
    (['authors', 'records'], 'dev-', ['records', 'authors']),
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
    prefix = prefix_value or ''
    search = app.extensions['invenio-search']
    search._current_suffix = suffix
    search.register_mappings('records', 'mock_module.mappings')

    # clean-up in case something failed previously
    current_search_client.indices.delete('*')
    # create indices and test
    list(search.create())
    es_indices = current_search_client.indices.get_alias()

    def _f(name):  # formatting helper
        return name.format(p=prefix, s=suffix)

    assert set(es_indices.keys()) == {
        _f('{p}records-authorities-authority-v1.0.0{s}'),
        _f('{p}records-bibliographic-bibliographic-v1.0.0{s}'),
        _f('{p}records-default-v1.0.0{s}'),
    }
    # Build set of aliases
    es_aliases = defaultdict(set)
    for index, info in es_indices.items():
        for alias in info.get('aliases', {}):
            es_aliases[alias].add(index)

    auth_idx = {_f('{p}records-authorities-authority-v1.0.0{s}')}
    bib_idx = {_f('{p}records-bibliographic-bibliographic-v1.0.0{s}')}
    default_idx = {_f('{p}records-default-v1.0.0{s}')}
    all_indices = auth_idx | bib_idx | default_idx
    assert es_aliases == {
        _f('{p}records-authorities-authority-v1.0.0'): auth_idx,
        _f('{p}records-bibliographic-bibliographic-v1.0.0'): bib_idx,
        _f('{p}records-default-v1.0.0'): default_idx,
        _f('{p}records-authorities'): auth_idx,
        _f('{p}records-bibliographic'): bib_idx,
        _f('{p}records'): all_indices,
    }
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

    def _test_prefix_replaced_in_body(name, prefix_value, tpl_key):
        """Test that the prefix is replaced in the body when defined."""
        if prefix_value:
            tpl = current_search_client.indices.get_template(name)
            assert name in tpl
            assert _contains_prefix(prefix_value, tpl[name][tpl_key])

    app.config['SEARCH_INDEX_PREFIX'] = prefix_value
    search = app.extensions['invenio-search']
    with patch('invenio_search.ext.iter_entry_points',
               return_value=template_entrypoints('invenio_search.templates')):
        # clean-up in case something failed previously
        current_search_client.indices.delete_template('*')
        # create templates
        list(search.put_templates())

        if ES_VERSION[0] == 2:
            assert len(search.templates.keys()) == 2
            name = 'record-view-v1'
            prefixed = (prefix_value or '') + name
            assert name in search.templates
            assert current_search_client.indices.exists_template(prefixed)
            _test_prefix_replaced_in_body(prefixed, prefix_value, 'template')
            name = 'subdirectory-file-download-v1'
            prefixed = (prefix_value or '') + name
            assert name in search.templates
            assert current_search_client.indices.exists_template(prefixed)
            _test_prefix_replaced_in_body(prefixed, prefix_value, 'template')
        elif ES_VERSION[0] == 5:
            assert len(search.templates.keys()) == 1
            name = 'record-view-v{0}'.format(ES_VERSION[0])
            prefixed = (prefix_value or '') + name
            assert name in search.templates
            assert current_search_client.indices.exists_template(prefixed)
            _test_prefix_replaced_in_body(prefixed, prefix_value, 'template')
        else:
            assert len(search.templates.keys()) == 1
            name = 'record-view-v{0}'.format(ES_VERSION[0])
            prefixed = (prefix_value or '') + name
            assert name in search.templates
            assert current_search_client.indices.exists_template(prefixed)
            _test_prefix_replaced_in_body(
                prefixed, prefix_value, 'index_patterns')

        # clean-up
        current_search_client.indices.delete_template('*')


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


def test_current_suffix(app):
    """Test generating current suffix."""
    search = app.extensions['invenio-search']
    suffix = search.current_suffix
    assert suffix == search.current_suffix


def test_not_dry_run_and_index_exists(app):
    """Test create_index and no dry run when index exists."""
    current_search_client.indices.delete('*')
    current_search_client.indices.create(
        index='records-default-v1.0.0',
        body=""
    )
    search = app.extensions['invenio-search']
    search.register_mappings('records', 'mock_module.mappings')
    with pytest.raises(IndexAlreadyExistsError):
        list(search.create())
