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

   $ flask -a app.py users create -e info@invenio-software.org -a
   $ flask -a app.py users activate -u info@invenio-software.org

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

from flask import Flask, jsonify, request
from flask_babelex import Babel
from flask_cli import FlaskCLI
from flask_mail import Mail
from flask_menu import Menu
from flask_security import current_user
from invenio_accounts import InvenioAccounts
from invenio_accounts.views import blueprint
from invenio_db import InvenioDB

from invenio_search import InvenioSearch, Query, current_search_client

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


def authenticated_query(query, **kwargs):
    """Enhance query with user authentication rules."""
    from invenio_query_parser.ast import AndOp, DoubleQuotedValue, Keyword, \
        KeywordOp
    if not current_user.is_authenticated():
        query.body['_source'] = {'exclude': ['public']}
        query.query = AndOp(
            KeywordOp(Keyword('public'), DoubleQuotedValue(1)),
            query.query
        )

app.config['SEARCH_QUERY_ENHANCERS'] = [authenticated_query]


@app.route('/', methods=['GET', 'POST'])
def index():
    """Query Elasticsearch using Invenio query syntax."""
    page = request.values.get('page', 1, type=int)
    size = request.values.get('size', 1, type=int)
    query = Query(request.values.get('q', ''))[(page-1)*size:page*size]
    response = current_search_client.search(
        index=request.values.get('index', 'demo'),
        doc_type=request.values.get('type'),
        body=query.body,
    )
    return jsonify(**response)
