=======================
 Invenio-Search v0.1.4
=======================

Invenio-Search v0.1.4 was released on October 2, 2015.

About
-----

Invenio module for information retrieval.

*This is an experimental developer preview release.*

Incompatible changes
--------------------

- Removes search service plugins that are going to be re-implemented
  using the new API. (#17) (addresses inveniosoftware/invenio#3233)
  (#13)

Bug fixes
---------

- Upgrades the minimum versions for invenio-base, invenio-ext,
  invenio-query-parser, invenio-utils, invenio-upgrader and invenio-
  testing.
- Removes dependencies to invenio.testsuite and replaces them with
  invenio_testing.
- Removes dependencies to invenio.utils and replaces them with
  invenio_utils.
- Removes dependencies to invenio.ext and replaces them with
  invenio_ext.
- Removes calls to PluginManager consider_setuptools_entrypoints()
  which was removed in PyTest 2.8.0.
- Adds missing `invenio_base` dependency.

Installation
------------

   $ pip install invenio-search==0.1.4

Documentation
-------------

   http://invenio-search.readthedocs.org/en/v0.1.4

Happy hacking and thanks for flying Invenio-Search.

| Invenio Development Team
|   Email: info@invenio-software.org
|   IRC: #invenio on irc.freenode.net
|   Twitter: http://twitter.com/inveniosoftware
|   GitHub: https://github.com/inveniosoftware/invenio-search
|   URL: http://invenio-software.org
