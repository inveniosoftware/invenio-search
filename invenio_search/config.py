# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Configuration options for Invenio-Search.

The documentation for the configuration is in docs/configuration.rst.
"""

#
# ELASTIC configuration
#

SEARCH_CLIENT_CONFIG = None
"""Dictionary of options for the Elasticsearch/OpenSearch client.

The value of this variable is passed to :py:class:`elasticsearch.Elasticsearch`
(or :py:class:`opensearchpy.OpenSearch`) as keyword arguments and is used to configure
the client. See the available keyword arguments in the two following classes:

- :py:class:`elasticsearch.Elasticsearch`
- :py:class:`elasticsearch.Transport`

Or:

- :py:class:`opensearchpy.OpenSearch`
- :py:class:`opensearchpy.Transport`

If you specify the key ``hosts`` in this dictionary, the configuration variable
:py:class:`~invenio_search.config.SEARCH_HOSTS` will have no effect.
"""

SEARCH_HOSTS = None  # default localhost
"""Search cluster hosts.

By default, Invenio connects to ``localhost:9200``.

The value of this variable is a list of dictionaries, where each dictionary
represents a host. The available keys in each dictionary is determined by the
connection class:

- :py:class:`elasticsearch.connection.Urllib3HttpConnection` (default)
- :py:class:`elasticsearch.connection.RequestsHttpConnection`

You can change the connection class via the
:py:class:`~invenio_search.config.SEARCH_CLIENT_CONFIG`. If you specified the
``hosts`` key in :py:class:`~invenio_search.config.SEARCH_CLIENT_CONFIG` then
this configuration variable will have no effect.
"""

SEARCH_ELASTIC_HOSTS = None
"""Deprecated alias for ``SEARCH_HOSTS``."""


SEARCH_MAPPINGS = None  # loads all mappings and creates aliases for them
"""List of aliases for which, their search mappings should be created.

- If `None` all aliases (and their search mappings) defined through the
  ``invenio_search.mappings`` entry point in setup.py will be created.
- Provide an empty list ``[]`` if no aliases (or their search mappings)
  should be created.

For example if you don't want to create aliases
and their mappings for `authors`:

.. code-block:: python

    # in your `setup.py` you would specify:
    entry_points={
        'invenio_search.mappings': [
            'records = invenio_foo_bar.mappings',
            'authors = invenio_foo_bar.mappings',
        ],
    }

    # and in your config.py
    SEARCH_MAPPINGS = ['records']
"""

SEARCH_RESULTS_MIN_SCORE = None
"""If set, the `min_score` parameter is added to each search request body.

The `min_score` parameter excludes results which have a `_score` less than
the minimum specified in `min_score`.

Note that the `max_score` varies depending on the number of results for a given
search query and it is not absolute value. Therefore, setting `min_score` too
high can lead to 0 results because it can be higher than any result's `_score`.

Please refer to `Elasticsearch min_score documentation
<https://www.elastic.co/guide/en/elasticsearch/reference/current/
search-request-min-score.html>`_ for more information.
"""

SEARCH_INDEX_PREFIX = ""
"""Any index, alias and templates will be prefixed with this string.

Useful to host multiple instances of the app on the same Elasticsearch cluster,
for example on one app you can set it to `dev-` and on the other to `prod-`,
and each will create non-colliding indices prefixed with the corresponding
string.

Usage example:

.. code-block:: python

    # in your config.py
    SEARCH_INDEX_PREFIX = 'prod-'

For templates, ensure that the prefix `__SEARCH_INDEX_PREFIX__` is added to
your index names. This pattern will be replaced by the prefix config value.

Usage example in your template.json:

.. code-block:: json

    {
        "index_patterns": ["__SEARCH_INDEX_PREFIX__myindex-name-*"]
    }
"""
