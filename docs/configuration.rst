..
    This file is part of Invenio.
    Copyright (C) 2015-2019 CERN.

    Invenio is free software; you can redistribute it and/or modify it
    under the terms of the MIT License; see LICENSE file for more details.

Configuration
=============

The Elasticsearch client in Invenio is configured using the two configuration
variables :py:class:`~invenio_search.config.SEARCH_CLIENT_CONFIG` and
:py:class:`~invenio_search.config.SEARCH_ELASTIC_HOSTS`.

Invenio-Search relies on the following two Python packages to integrate with
Elasticsearch:

- `elasitcsearch <https://pypi.org/project/elasticsearch/>`_
- `elasitcsearch-dsl <https://pypi.org/project/elasticsearch-dsl/>`_

Hosts
-----
The hosts which the Elasticsearch client in Invenio should use are configured
using the configuration variable:

.. autodata:: invenio_search.config.SEARCH_ELASTIC_HOSTS

Clusters
~~~~~~~~
Normally in a production environment, you will run an Elasticsearch cluster on
one or more dedicated nodes. Following is an example of how you configure
Invenio to use such as cluster:

.. code-block:: python

    SEARCH_ELASTIC_HOSTS = [
        dict(host='es1.example.org'),
        dict(host='es2.example.org'),
        dict(host='es3.example.org'),
    ]

Elasticsearch will manage a connection pool to all of these hosts, and will
automatically take nodes out if they fail.

Basic authentication and SSL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
By default all traffic to Elasticsearch is via unencrypted HTTP because
Elasticsearch does not come with built-in support for SSL unless you pay for
the expensive enterprise X-Pack addition. A cheap alternative to X-Pack, is to
simply setup a proxy (e.g. nginx) on each node with SSL and
HTTP basic authentication support.

Following is an example of how you configure Invenio to use SSL and Basic
authentication when connecting to Elasticsearch:

.. code-block:: python

    params = dict(
        port=443,
        http_auth=('myuser', 'mypassword'),
        use_ssl=True,
    )
    SEARCH_ELASTIC_HOSTS = [
        dict(host='node1', **params),
        dict(host='node2', **params),
        dict(host='node3', **params),
    ]

Self-signed certificates
~~~~~~~~~~~~~~~~~~~~~~~~
In case you are using self-signed SSL certificates on proxies in front of
Elasticsearch, you will need to provide the ``ca_certs`` option:

.. code-block:: python

    params = dict(
        port=443,
        http_auth=('myuser', 'mypassword'),
        use_ssl=True,
        ca_certs='/etc/pki/tls/mycert.pem',
    )
    SEARCH_ELASTIC_HOSTS = [
        dict(host='node1', **params),
        # ...
    ]

**Disabling SSL certificate verification**

.. warning::

    We **strongly discourage** you to use this method. Instead, use the method
    with the ``ca_certs`` option documented above.

    Disabling verification of SSL certificates will e.g.  allow
    man-in-the-middle attacks and give you a false sense of security (thus you
    could simply use plain unencrypted HTTP instead).

If you are using a self-signed certificate, you may also disable verification
of the SSL certificate, using the ``verify_certs`` option:

.. code-block:: python


    import urllib3
    urllib3.disable_warnings(
        urllib3.exceptions.InsecureRequestWarning
    )

    params = dict(
        port=443,
        http_auth=('myuser', 'mypassword'),
        use_ssl=True,
        verify_certs=False,
        ssl_show_warn=False, # only from 7.x+
    )
    SEARCH_ELASTIC_HOSTS = [
        dict(host='node1', **params),
        # ...
    ]

Above example will also disable the two warnings (``InsecureRequestWarning``
and a ``UserWarning``) using the ``ssl_show_warn`` option and urllib3 feature.
Again, we **strongly discourage** you from using this method. The warnings are
there for a reason!

Other host options
~~~~~~~~~~~~~~~~~~
For a full list of options for configuring the hosts, see the connection
classes documentation:

- :py:class:`elasticsearch.connection.Urllib3HttpConnection` (default)
- :py:class:`elasticsearch.connection.RequestsHttpConnection`

Other options include e.g.:

- ``url_prefix``
- ``client_cert``
- ``client_key``


Client options
--------------
More advanced options for the Elasticsearch client are configured via the
configuration variable:

.. autodata:: invenio_search.config.SEARCH_CLIENT_CONFIG

Timeouts
~~~~~~~~
If you are running Elasticsearch on a smaller/slower machine (e.g. for
development or CI) you might want to be a bit more relaxed in terms of timeouts
and failure retries:

.. code-block:: python

    SEARCH_CLIENT_CONFIG = dict(
        timeout=30,
        max_retries=5,
    )

Connection class
~~~~~~~~~~~~~~~~
You can change the default connection class by setting the ``connection_class``
key (e.g. use requests library instead of urllib3):

.. code-block:: python

    from elasticsearch.connection import RequestsHttpConnection

    SEARCH_CLIENT_CONFIG = dict(
        connection_class=RequestsHttpConnection
    )

Note, that the default urllib3 connection class is more lightweight and
performant than the requests library. Only use requests library for advanced
features like e.g. custom authentication plugins.

Connection pooling
~~~~~~~~~~~~~~~~~~
By default urllib3 will open up to 10 connections to each node, if your
application calls for more parallelism, use the ``maxsize`` parameter to raise
the limit:

.. code-block:: python

    SEARCH_CLIENT_CONFIG = dict(
        # allow up to 25 connections to each node
        maxsize=25,
    )

Hosts via client config
~~~~~~~~~~~~~~~~~~~~~~~
Note, you may also use :py:class:`~invenio_search.config.SEARCH_CLIENT_CONFIG`
instead of :py:class:`~invenio_search.config.SEARCH_ELASTIC_HOSTS` to configure
the Elasticsearch hosts:

.. code-block:: python

    SEARCH_CLIENT_CONFIG = dict(
        hosts=[
            dict(host='es1.example.org'),
            dict(host='es2.example.org'),
            dict(host='es3.example.org'),
        ]
    )

Other client options
~~~~~~~~~~~~~~~~~~~~
For a full list of options for configuring the client, see the transport
class documentation:

- :py:class:`elasticsearch.Elasticsearch`
- :py:class:`elasticsearch.Transport`

Other options include e.g.:

- ``url_prefix``
- ``client_cert``
- ``client_key``

Index prefixing
---------------
Elasticsearch does not provide the concept of virtual hosts, and thus the only
way to use a single Elasticsearch cluster with multiple Invenio instances is
via prefixing index, alias and template names. This is defined via the
configuration variable:

.. warning::

    Note that index prefixing is only prefixing. Multiple Invenio instances
    sharing the same Elasticsearch cluster all have access to each other's
    indexes unless you use something like https://readonlyrest.com or the
    commercial X-Pack from Elasticsearch.

.. autodata:: invenio_search.config.SEARCH_INDEX_PREFIX


Index creation
--------------
Invenio will by default create all aliases and indexes registered into the
``invenio_search.mappings`` entry point. If this is not desirable for some
reason, you can control which indexes are being created via the configuration
variable:

.. autodata:: invenio_search.config.SEARCH_MAPPINGS
