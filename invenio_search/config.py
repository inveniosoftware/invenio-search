# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Configuration options for Invenio-Search."""

#
# ELASTIC configuration
#

SEARCH_ELASTIC_HOSTS = None  # default localhost
"""Elasticsearch hosts for the client.

By default the client connects to ``localhost:9200``. Below is an example of
connecting to three hosts via HTTPS with Basic authentication and switching of
SSL certificate verification:

.. code-block:: python

    params = dict(
        port=443,
        http_auth=('myuser', 'mypassword'),
        use_ssl=True,
        verify_certs=False,
    )
    SEARCH_ELASTIC_HOSTS = [
        dict(host='node1', **params),
        dict(host='node2', **params),
        dict(host='node3', **params),
    ]


The underlying library handles connection pooling and load-balancing between
the different nodes. Please see
`Elasticsearch client <https://elasticsearch-py.readthedocs.io/>`_
for further details.
"""

SEARCH_CLIENT_CONFIG = None
"""Elasticsearch client configuration.

If provided, this configuration dictionary will be passed to the initialization
of the :class:`elasticsearch:elasticsearch.Elasticsearch` client instance used
by the module.


If not set, for the ``hosts`` key, :py:data:`.SEARCH_ELASTIC_HOSTS` will be
used and for the ``connection_class`` key
:class:`elasticsearch:elasticsearch.connection.RequestsHttpConnection`.

Example value:

.. code-block:: python

   # e.g. for smaller/slower machines or development/CI you might want to be a
   # bit more relaxed in terms of timeouts and failure retries.
   dict(timeout=30, max_retries=5,
   )
"""

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
