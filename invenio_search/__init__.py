# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2018 CERN.
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
installed and running (currently, version 2.x and 5.x are supported):

.. code-block:: console

   $ elasticsearch --version
   Version: 2.4.6, Build: 5376dca/2017-07-18T12:17:44Z, JVM: 1.8.0_144

In this case, we are using version 2 of Elasticsearch, so make sure to install
``invenio-search`` with the appropriate extras:

.. code-block:: console

    pip install invenio-search[elasticsearch2]

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
application. Add the following line at the end of ``app.py`` file that you
have just created:

.. code-block:: python

    # app.py
    ...
    search.register_mappings('demo', 'examples.data')

The above code will look into directory ``examples/data`` and load all the
mapping files it can find there into Elasticsearch (each file will create a new
index). It will also add ``demo`` as an alias to each of the indexes.

You can read more about the Elasticsearch mappings on elasticsearch website
(https://www.elastic.co/guide/en/elasticsearch/guide/current/mapping-intro.html).
Now we can finally create the index.

.. code-block:: console

   $ export FLASK_APP=app.py
   $ flask index init

If you are running Elasticsearch on your local machine, you can see that the
indices were created correctly by going to this URL:
http://localhost:9200/demo

Let's put some data inside

.. code-block:: console

   $ echo '{"title": "Hello invenio-search", "body": "test 1"}' | \
         flask index put demo-default-v1.0.0 example

No error message? Good! You can see that your new document was indexed by
going to this URL: http://localhost:9200/demo/_search

Searching for data
~~~~~~~~~~~~~~~~~~

Let's try to retrieve data in a programmatic way. Start a Python REPL and run
the following commands.

First, let's initialize app from the ``app.py`` file that we created in the
previous step.
Python REPL.

.. code-block:: python

   from app import app

Create a custom search class that will search for ``example`` type of
documents inside the ``demo`` index (or you could use the default
``RecordsSearch`` class to search for all document types in all indexes):

.. code-block:: python

   from invenio_search import RecordsSearch
   class ExampleSearch(RecordsSearch):
       class Meta:
           index = 'demo'
           doc_types = ['example']
           fields = ('*', )
           facets = {}
   search = ExampleSearch()

We will need a Flask application context, so let's push one:

.. code-block:: python

   app.app_context().push()

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

First, let's add one public and one private document to Elasticsearch:

.. code-block:: console

    $ echo '{"title": "Public", "body": "test 1", "public": 1}' | \
        flask index put demo-default-v1.0.0 example
    $ echo '{"title": "Private", "body": "test 2", "public": 0}' | \
        flask index put demo-default-v1.0.0 example

Now, create a new search class that will return all documents of type
``example`` from the ``demo`` index and select only the public ones
(documents where ``public`` is set to 1):

.. code-block:: python

    # app.py
    from elasticsearch_dsl.query import Bool, Q, QueryString

    class PublicSearch(RecordsSearch):
        class Meta:
            index = 'demo'
            doc_types = ['example']
            fields = ('*', )
            facets = {}

        def __init__(self, **kwargs):
            super(PublicSearch, self).__init__(**kwargs)
            self.query = self.query._proxied & Q(
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
``examples/data`` directory of the ``invenio-search`` repository:

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

For convenience, you can install a plugin like Elastic HQ
(http://www.elastichq.org/) for easy introspection of your indexes and their
content. Otherwise, you can use curl (as described here:
https://www.elastic.co/guide/en/elasticsearch/guide/current/_talking_to_elasticsearch.html).

.. _invenio-access:  https://invenio-access.readthedocs.io/

"""

from __future__ import absolute_import, print_function

from .api import RecordsSearch
from .ext import InvenioSearch
from .proxies import current_search, current_search_client
from .version import __version__

__all__ = (
    '__version__',
    'InvenioSearch',
    'RecordsSearch',
    'current_search',
    'current_search_client',
)
