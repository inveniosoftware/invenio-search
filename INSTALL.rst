..
    This file is part of Invenio.
    Copyright (C) 2015-2018 CERN.

    Invenio is free software; you can redistribute it and/or modify it
    under the terms of the MIT License; see LICENSE file for more details.

..  _installation:

Installation
============

Invenio-Search is on PyPI. When you install Invenio-Search you must specify the
appropriate extras dependency for the version of Elasticsearch you use:

.. code-block:: console

    $ # For Elasticsearch 6.x:
    $ pip install invenio-search[elasticsearch6]

    $ # For Elasticsearch 7.x:
    $ pip install invenio-search[elasticsearch7]

Elasticsearch v2 and v5 support still exists in Invenio-Search but will be
deprecated in future releases so using v6 or v7 is recommended.