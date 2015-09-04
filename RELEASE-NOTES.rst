=======================
 Invenio-Search v0.1.3
=======================

Invenio-Search v0.1.3 was released on September 4, 2015.

About
-----

Invenio module for information retrieval.

*This is an experimental developer preview release.*

Security fixes
--------------

- Fixes potential XSS issues by changing search flash messages
  template so that they are not displayed as safe HTML by default.

Bug fixes
---------

- Adds missing `invenio_access` dependency and amends past upgrade
  recipes following its separation into standalone package.

Notes
-----

- Displaying HTML safe flash messages can be done by using one of
  these flash contexts: 'search-results-after(html_safe)', 'websearch-
  after-search-form(html_safe)' instead of the standard ones (which
  are the same without '(html safe)' at the end).

Installation
------------

   $ pip install invenio-search==0.1.3

Documentation
-------------

   http://invenio-search.readthedocs.org/en/v0.1.3

Happy hacking and thanks for flying Invenio-Search.

| Invenio Development Team
|   Email: info@invenio-software.org
|   IRC: #invenio on irc.freenode.net
|   Twitter: http://twitter.com/inveniosoftware
|   GitHub: https://github.com/inveniosoftware/invenio-search
|   URL: http://invenio-software.org
