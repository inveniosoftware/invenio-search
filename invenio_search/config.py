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
