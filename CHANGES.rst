..
    This file is part of Invenio.
    Copyright (C) 2015-2024 CERN.
    Copyright (C) 2024-2025 Graz University of Technology.

    Invenio is free software; you can redistribute it and/or modify it
    under the terms of the MIT License; see LICENSE file for more details.

Changes
=======

Version 3.1.0 (released 2025-07-01)

- fix: pkg_resources DeprecationWarning

Version 3.0.0 (released 2024-12-06)

- setup: change to reusable workflows
- setup: bump major dependencies

Version v2.4.1 (released 2024-08-07)

- fix: avoid closing db session

Version v2.4.0 (released 2024-08-02)

- cli: add "--check/--no-check" flag for mapping updates
- ext: report attempted mappings update on failure (#224)

Version 2.3.1 (released 2024-03-04)

- search: The component_templates do not need to specify the SEARCH_INDEX_PREFIX

Version 2.3.0 (released 2024-02-26)

- search: Add options for component_templates and index_templates

Version 2.2.1 (released 2024-02-19)

- ext: fix update mapping comparison

Version 2.2.0 (released 2023-04-06)

- cli: adds interface for updating mappings

Version 2.1.0 (released 2022-10-03)

- Adds support for OpenSearch v2

Version 2.0.0 (released 2022-09-22)

- Removes Elasticsearch < v7
- Adds support for OpenSearch v1

Version 1.4.2 (released 2021-07-20)

- Pin elasticsearch to lower than 7.14 due to built in product check.

Version 1.4.1 (released 2020-10-19)

- Fix bouncing search results for BaseRecordSearchV2.

Version 1.4.0 (released 2020-09-18)

- Adds new search class that can be initialised only from arguments to the
  constructor.

Version 1.3.1 (released 2020-05-07)

- Set Sphinx ``<3.0.0`` because of errors related to application context.
- Stop using example app, keep only files referenced in the docs.

Version 1.3.0 (released 2020-03-10)

- Centralize dependency management via Invenio-Base.

Version 1.2.4 (released 2020-05-07)

- Set Sphinx ``<3.0.0`` because of errors related to application context.
- Stop using example app, keep only files referenced in the docs.

Version 1.2.3 (released 2019-10-07)

- Changes the naming strategy for templates to avoid inclusion of slashes ("/")

Version 1.2.2 (released 2019-08-08)

- Adds option ignore_existing which is ignoring indexes which are already in ES.
- Adds option to create/delete only selected indexes.

Version 1.2.1 (released 2019-07-31)

- Unpins ``urllib3`` and ``idna`` since ``requests`` is not a direct dependency
  of the package now.

Version 1.2.0 (released 2019-07-29)

- Adds full Elasticsearch v7 support
- Better prefixing integration
- Introduces index suffixes and write aliases
- Refactored the way indices and aliases are stored and created
- ``invenio_search.utils.schema_to_index`` is deprecated (moved to
  ``invenio-indexer``)
- Deprecates Elasticsearch v5

Version 1.1.1 (released 2019-06-25)

- Fixes prefixing for whitelisted aliases and the RecordSearch class.
- Adds basic Elasticsearch v7 support.

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
