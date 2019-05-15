# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.


"""Minimal Flask application example for development.

SPHINX-START

Run the ElasticSearch and Redis server.

Run example development server:

.. code-block:: console

   $ pip install -e .[all]
   $ cd examples
   $ ./app-setup.sh
   $ ./app-fixtures.sh

Run example development server:

.. code-block:: console

   $ FLASK_DEBUG=1 FLASK_APP=app.py flask run -p 5000

Try to perform some search queries:

.. code-block:: console

   $ curl http://localhost:5000/?q=body:test

To be able to uninstall the example app:

.. code-block:: console

   $ ./app-teardown.sh

SPHINX-END
"""

from __future__ import absolute_import, print_function

import os

from elasticsearch import VERSION as ES_VERSION
from elasticsearch_dsl.query import Bool, Q, QueryString
from flask import Flask, jsonify, request
from flask_menu import Menu
from flask_security import current_user
from invenio_accounts import InvenioAccounts
from invenio_accounts.views import blueprint
from invenio_db import InvenioDB

from invenio_search import InvenioSearch, RecordsSearch, current_search_client

# Create Flask application
app = Flask(__name__)
app.config.update(
    ACCOUNTS_USE_CELERY=False,
    CELERY_ALWAYS_EAGER=True,
    CELERY_CACHE_BACKEND="memory",
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
    CELERY_RESULT_BACKEND="cache",
    MAIL_SUPPRESS_SEND=True,
    SECRET_KEY="CHANGE_ME",
    SECURITY_PASSWORD_SALT="CHANGE_ME_ALSO",
    SQLALCHEMY_DATABASE_URI=os.getenv('SQLALCHEMY_DATABASE_URI',
                                      'sqlite:///instance/test.db'),
)
Menu(app)
InvenioDB(app)
InvenioAccounts(app)

app.register_blueprint(blueprint)

search = InvenioSearch(app)
search.register_mappings('demo', 'data')


@app.cli.command()
def fixtures():
    """Example fixtures."""
    # Index sample records
    current_search_client.index(
        index='demo-default-v1.0.0',
        body={'title': 'Public', 'body': 'test 1', 'public': 1},
        doc_type='example' if ES_VERSION[0] < 7 else '_doc'
    )
    current_search_client.index(
        index='demo-default-v1.0.0',
        body={'title': 'Private', 'body': 'test 2', 'public': 0},
        doc_type='example' if ES_VERSION[0] < 7 else '_doc'
    )


class ExampleSearch(RecordsSearch):
    """Example search class."""

    class Meta:
        """Configuration for ``RecordsSearch`` class."""

        index = 'demo'
        fields = ('*', )
        facets = {}

    def __init__(self, **kwargs):
        """Initialize instance."""
        super(ExampleSearch, self).__init__(**kwargs)
        if not current_user.is_authenticated:
            if self.query._proxied:
                self.query = self.query._proxied & Q(
                    Bool(filter=[Q('term', public=1)]))
            else:
                self.query = Q(Bool(filter=[Q('term', public=1)]))


@app.route('/', methods=['GET', 'POST'])
def index():
    """Query Elasticsearch using Invenio query syntax."""
    page = request.values.get('page', 1, type=int)
    size = request.values.get('size', 2, type=int)
    search = ExampleSearch()[(page - 1) * size:page * size]
    if 'q' in request.values:
        search = search.query(QueryString(query=request.values.get('q')))

    search = search.sort(
        request.values.get('sort', 'title')
    )
    search = ExampleSearch.faceted_search(search=search)
    results = search.execute().to_dict()
    return jsonify({'hits': results.get('hits')})
