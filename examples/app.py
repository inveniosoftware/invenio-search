# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
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


"""Minimal Flask application example for development.

Make sure that ``elasticsearch`` server is running:

.. code-block:: console

   $ elasticsearch
   ... version[2.0.0] ...

Create database and tables:

.. code-block:: console

   $ flask -a app.py db init
   $ flask -a app.py db create

Create a user:

.. code-block:: console

   $ flask -a app.py users create info@invenio-software.org -a

Upload sample records::

.. code-block:: console

   $ cd examples
   $ echo '{"title": "Public", "body": "test 1", "public": 1}' > public.json
   $ echo '{"title": "Private", "body": "test 2", "public": 0}' > private.json
   $ flask --app app index put demo example -b public.json
   $ flask --app app index put demo example -b private.json
   $ flask --app app run

Try to perform some queries from browser:

.. code-block:: console

   $ open http://localhost:5000/?q=body:test

"""

from __future__ import absolute_import, print_function

from elasticsearch_dsl.query import Bool, Q, QueryString
from flask import Flask, jsonify, request
from flask_babelex import Babel
from flask_cli import FlaskCLI
from flask_mail import Mail
from flask_menu import Menu
from flask_security import current_user
from invenio_accounts import InvenioAccounts
from invenio_accounts.views import blueprint
from invenio_db import InvenioDB

from invenio_search import InvenioSearch, RecordsSearch

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
    SEARCH_ELASTIC_KEYWORD_MAPPING={None: ['_all']},
)
FlaskCLI(app)
Babel(app)
Mail(app)
Menu(app)
InvenioDB(app)
InvenioAccounts(app)

app.register_blueprint(blueprint)

search = InvenioSearch(app)
search.register_mappings('records', 'data')


class ExampleSearch(RecordsSearch):
    """Example search class."""

    class Meta:
        index = 'demo'
        doc_types = ['example']
        fields = ('*', )
        facets = {}

    def __init__(self, **kwargs):
        """Initialize instance."""
        super(ExampleSearch, self).__init__(**kwargs)
        if not current_user.is_authenticated:
            self.query = self.query._proxied & Q(
                Bool(filter=[Q('term', public=1)])
            )


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
    search = ExampleSearch.faceted_search(
        search=search
    )
    return jsonify(search.execute().to_dict())
