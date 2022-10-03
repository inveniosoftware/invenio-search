..
    This file is part of Invenio.
    Copyright (C) 2015-2022 CERN.

    Invenio is free software; you can redistribute it and/or modify it
    under the terms of the MIT License; see LICENSE file for more details.

..  _installation:

Installation
============

Invenio-Search is on PyPI. When you install Invenio-Search you must specify the
appropriate extras dependency for the version of Elasticsearch or OpenSearch you use:

.. code-block:: console

    $ # For Elasticsearch 7.x:
    $ pip install invenio-search[elasticsearch7]

    $ # For OpenSearch 2.x:
    $ pip install invenio-search[opensearch2]

Also note that installing multiple conflicting dependencies (e.g.
`invenio-search[opensearch2,elasticsearch7]`) will result in an error at runtime.
