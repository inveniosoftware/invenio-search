Installation
============

Invenio-Search is on PyPI. When you install Invenio-Search you must specify the
appropriate extras dependency for the version of Elasticsearch you use:

.. code-block:: console

    $ # For Elasticsearch 2.x:
    $ pip install invenio-search[elasticsearch2]

    $ # For Elasticsearch 5.x:
    $ pip install invenio-search[elasticsearch5]

Support for Elasticsearch version 6.x will be added as soon as the
`elasticsearch-dsl <https://pypi.python.org/pypi/elasticsearch-dsl>`_ library
officially supports it.
