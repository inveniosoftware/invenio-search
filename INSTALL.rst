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

    $ # For OpenSearch 1.x:
    $ pip install invenio-search[opensearch1]

Note that Elasticsearch v2 and v5 support still exists in Invenio-Search but will be
deprecated in future releases so using ESv7 or OSv1 is recommended.

Also note that installing multiple conflicting dependencies (e.g.
`invenio-search[opensearch1,elasticsearch7]`) will result in undefined behavior and
should be avoided!
