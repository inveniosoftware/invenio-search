# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

r"""Elasticsearch management for Invenio.

Allows retrieving records from a configurable backend (currently, from
Elasticsearch).

Initialization
--------------

To be able to retrieve information from *somewhere*, we first need to setup
this *somewhere*. So make sure you have the correct version of Elasticsearch
installed and running (currently, version 6.x and 7.x are supported).

For running an Elasticsearch instance we recommend using
`Docker <https://docs.docker.com/install/>`_ and the official images `provided
by Elastic <https://www.docker.elastic.co/>`_:

.. code-block:: console

    $ docker run -d \
        -p 9200:9200 \
        -e "discovery.type=single-node" \
        docker.elastic.co/elasticsearch/elasticsearch-oss:7.2.0

In this case, we are using Elasticsearch v7, so make sure to install
``invenio-search`` with the appropriate extras:

.. code-block:: console

    pip install invenio-search[elasticsearch7]

.. _creating_index:

Creating index
~~~~~~~~~~~~~~

To be able to run flask CLI commands later, we first need to have a Flask app,
so create the following ``app.py`` file:

.. code-block:: python

    # app.py
    from flask import Flask
    from invenio_search import InvenioSearch

    app = Flask('myapp')
    search = InvenioSearch(app)

This will create an empty index, which is not very useful, so let's add some
mappings. To not reinvent the wheel, let's reuse the mappings from the example
application. Copy the ``examples`` directory from
`Invenio-Search <https://github.com/inveniosoftware/invenio-search>`_.
Add the following line at the end of ``app.py`` file that you just created:

.. code-block:: python

    # app.py
    ...
    search.register_mappings('demo', 'examples.data')

The above code will search the directory ``examples/data`` and load all the
mapping files it can find there for Elasticsearch. You can read more about the
Elasticsearch mappings in `the official documentation <https://www.elastic.co/
guide/en/elasticsearch/guide/current/mapping-intro.html>`_.

Now we can finally create the indexes. Each file in the mappings will create a
new index and a top-level alias with the name ``demo``.

.. code-block:: console

   $ export FLASK_APP=app.py
   $ flask index init

You can verify that the indices were created correctly by performing the
following requests:

.. code-block:: console

    $ # Fetch information about the "demo" alias
    $ curl http://localhost:9200/demo
    $ # Fetch information about the "demo-default-v1.0.0" alias
    $ curl http://localhost:9200/demo-default-v1.0.0

.. note::

    In earlier versions of Invenio-Search ``demo-default-v1.0.0`` was an
    index but is now a write alias pointing to a suffixed index. Read more
    about write aliases and suffixes in the Aliases_ section.

Let's index some data. Open ``flask shell`` and index a document with the
following code:

.. code-block:: python

    import json
    from invenio_search import current_search_client

    current_search_client.index(
        index='demo-default-v1.0.0',
        body=json.dumps({
            'title': 'Hello invenio-search',
            'body': 'test 1'
        })
    )

No error message? Good! You can see that your new document was indexed by
going to http://localhost:9200/demo/_search.

Searching for data
~~~~~~~~~~~~~~~~~~

Let's try to retrieve data in a programmatic way. Start a Python REPL and run
the following commands.

First, let's initialize app from the ``app.py`` file that we created in the
previous step.
Python REPL.

.. code-block:: python

   from app import app

We will need a Flask application context, so let's push one:

.. code-block:: python

   app.app_context().push()

Create a custom search class that will search for ``example`` type of
documents inside the ``demo`` alias (or you could use the default
``RecordsSearch`` class to search for all document types in all indexes):

.. code-block:: python

   from invenio_search import RecordsSearch
   class ExampleSearch(RecordsSearch):
       class Meta:
           index = 'demo'
           fields = ('*', )
           facets = {}
   search = ExampleSearch()

Let's find all documents:

.. code-block:: python

   response = search.execute()
   response.to_dict()

If everything went well, you should now see that we have 1 hit - a document
with ``Hello invenio-search`` title. If you get the ``TransportError(404,
'index_not_found_exception', 'no such index')`` error - it means that you
forgot to create the index (follow the steps from :ref:`creating_index` to
see how to setup an index and add example data).

Creating a search page
~~~~~~~~~~~~~~~~~~~~~~

Let's create a simple web page where you can send queries to the Elasticsearch
and see the results.
Create a new app.py file with a route.

.. code-block:: python

    # app.py
    from elasticsearch_dsl.query import QueryString
    from flask import Flask, jsonify, request
    from invenio_search import InvenioSearch, RecordsSearch

    app = Flask('myapp')

    search = InvenioSearch(app)

    # This line is needed to be able to call `flask index init`
    search.register_mappings('demo', 'examples.data')


    @app.route('/', methods=['GET', 'POST'])
    def index():
        search = RecordsSearch()
        if 'q' in request.values:
            search = search.query(QueryString(query=request.values.get('q')))

        return jsonify(search.execute().to_dict())

Run example development server:

.. code-block:: console

   $ FLASK_DEBUG=1 FLASK_APP=app.py flask run -p 5000

And now you can perform search queries:

.. code-block:: console

   $ curl http://localhost:5000/?q=body:test

Filtering
~~~~~~~~~
To filter out some documents, you can create your own search class. Let's try
to remove all private documents from the search results (by ``private``
documents, we understand all the documents that have ``public`` attribute set
to 0).

Open ``flask shell`` and add one public and one private document to
Elasticsearch:

.. code-block:: python

    import json
    from invenio_search import current_search_client

    # Index public document
    current_search_client.index(
        index='demo-default-v1.0.0',
        body=json.dumps({
            'title': 'Public',
            'body': 'test 1',
            'public': 1
        })
    )
    # Index private document
    current_search_client.index(
        index='demo-default-v1.0.0',
        body=json.dumps({
            'title': 'Private',
            'body': 'test 1',
            'public': 0
        })
    )

Now, create a new search class that will return all documents of type
``example`` from the ``demo`` index and select only the public ones
(documents where ``public`` is set to 1):

.. code-block:: python

    # app.py
    from elasticsearch_dsl.query import Bool, Q, QueryString

    class PublicSearch(RecordsSearch):
        class Meta:
            index = 'demo'
            fields = ('*', )
            facets = {}

        def __init__(self, **kwargs):
            super(PublicSearch, self).__init__(**kwargs)
            self.query = Q(
                Bool(filter=[Q('term', public=1)])
            )

Update the ``index`` function and replace the search class with our new
``PublicSearch`` class:

.. code-block:: python

    # app.py
    @app.route('/', methods=['GET', 'POST'])
    def index():
        search = PublicSearch()
        ...

Now, you can search for documents with ``test`` in the body.

.. code-block:: console

   $ curl http://localhost:5000/?q=body:test

You should find only one document - the one with ``Public`` title.

This is a very simple example of how to filter out some records. If you want
to see how to hide some records if the user is not logged in, check out the
:ref:`examplesapp`. If you want to define role based access rights control,
check the invenio-access_ module.


Miscellaneous
-------------

Elasticsearch version support
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Because of the breaking changes that are introduced in Elasticsearch between
major versions in relation to mappings, a specific directory structure has to
be followed, in order to specify which JSON mapping files will be used for
creating the Elasticsearch indices. For backwards compatibility with existing
Invenio modules and installations, for Elasticsearch 2, mappings will be loaded
from the root level of the package directory. You can see a full example in the
``examples/data`` directory of the Invenio-Search repository:

.. code-block:: console

    $ tree --dirsfirst examples/data

    examples/data
    +- demo            # Elasticsearch 2 mappings
    |  +- authorities
    |  |  +- authority-v1.0.0.json
    |  +- bibliographic
    |  |  +- bibliographic-v1.0.0.json
    |  +- default-v1.0.0.json
    +- v5
    |  +- demo        # Elasticsearch 5 mappings
    |  |  +- authorities
    |  |  |  +- authority-v1.0.0.json
    |  |  +- bibliographic
    |  |  |  +- bibliographic-v1.0.0.json
    |  |  +- default-v1.0.0.json
    |  +- __init__.py
    +-- __init__.py


Elasticsearch plugins
~~~~~~~~~~~~~~~~~~~~~

For convenience, you can install a plugin like `Elastic HQ
<http://www.elastichq.org/>`_ for easy introspection of your indexes and their
content. Otherwise, you can use curl as described `in the official
documentation <https://www.elastic.co/guide/en/elasticsearch/guide/current/
_talking_to_elasticsearch.html>`_.

.. _invenio-access:  https://invenio-access.readthedocs.io/

.. _Aliases:

Indexes and aliases
~~~~~~~~~~~~~~~~~~~

.. graphviz::

    digraph D {
        rankdir="LR"
        node[shape=record]

        R[label="records", style=rounded]
        RD[label="records-dataset-v1.0.0", style="rounded,dashed"]
        RP[label="records-paper-v1.0.0", style="rounded,dashed"]
        RDI[label="records-dataset-v1.0.0-1564056972"]
        RPI[label="records-paper-v1.0.0-1564056972"]

        A[label="authors", style=rounded]
        AA[label="authors-author-v1.0.0", style="rounded,dashed"]
        AAI[label="authors-author-v1.0.0-1564056972"]

        R -> RDI
        R -> RPI
        RP -> RPI
        RD -> RDI

        A -> AAI
        AA -> AAI
    }

Indexes and aliases are organized as seen in the graph above. This example has
three "concrete" indexes:

- ``authors-author-v1.0.0-1564056972``
- ``records-dataset-v1.0.0-1564056972``
- ``records-paper-v1.0.0-1564056972``

They all share the suffix ``1564056972``. Each index though has also a
corresponding "write alias" with its un-suffixed name:

- ``authors-author-v1.0.0 -> authors-author-v1.0.0-1564056972``
- ``records-dataset-v1.0.0 -> records-dataset-v1.0.0-1564056972``
- ``records-paper-v1.0.0 -> records-paper-v1.0.0-1564056972``

The other aliases in the example, ``records`` and ``authors``, are top-level
aliases pointing to all the indexes in their same hierarchy:

- ``authors -> authors-author-v1.0.0-1564056972``
- ``records -> records-dataset-v1.0.0-1564056972``
- ``records -> records-paper-v1.0.0-1564056972``

Top-level **aliases** are aliases that can point to one or multiple
indexes. The purpose of these aliases is to group indexes and be able to
perform searches over multiple indexes. These aliases should never be indexed
to as the indexing will fail if they point to multiple indexes.

The other type of alias is the **write alias** which is an alias that only
points to a single index and has the same name as the index without the suffix.
This alias should be used whenever you need to index something. The name of the
write alias is the same as the un-prefixed index name, which allows backwards
compatibilty with previous versions of Invenio-Search.

An **index** ends with a suffix which is the timestamp of the index creation
time. The suffix allows multiple revisions of the same index to exist at the
same time. This is useful if you want to update the mappings of an index and
migrate to a new index. With suffixes, it's possible to keep the two versions
of the same index and sync them. When the migration is completed the write
alias can be pointed to the new index and the application will use the new
index. This allows in-cluster migrations without any downtime.

More information about index migrations can be found in the
`Invenio-Index-Migrator
<https://github.com/inveniosoftware/invenio-index-migrator>`_.
"""

from __future__ import absolute_import, print_function

from .api import RecordsSearch, UnPrefixedRecordsSearch
from .ext import InvenioSearch
from .proxies import current_search, current_search_client
from .version import __version__

__all__ = (
    '__version__',
    'InvenioSearch',
    'RecordsSearch',
    'UnPrefixedRecordsSearch',
    'current_search',
    'current_search_client',
)
