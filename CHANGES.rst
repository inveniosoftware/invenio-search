..
    This file is part of Invenio.
    Copyright (C) 2015-2019 CERN.

    Invenio is free software; you can redistribute it and/or modify it
    under the terms of the MIT License; see LICENSE file for more details.

Changes
=======

Version 1.1.0 (released 2019-02-25)

- Deprecates Elasticsearch v2

- Adds support for Elasticsearch indices prefix

Version 1.0.2 (released 2018-10-23)

- Updates the urllib3 dependency version pin.

- Pins elasticsearch-dsl to <6.2.0, because of a breaking change in the
  handling of empty queries.

- Adds the SEARCH_CLIENT_CONFIG configuration variable, allowing more complex
  configuration to be passed to the Elasticsearch client initialization.

Version 1.0.1 (released 2018-06-13)

- Fixes issues with idna/urllib3 dependencies conflicts.

- Adds SEARCH_RESULTS_MIN_SCORE configuration variable to allow excluding
  search results which have a score less than the specified value.

Version 1.0.0 (released 2018-03-23)

- Initial public release.
