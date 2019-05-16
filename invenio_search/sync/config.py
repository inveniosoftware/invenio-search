# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Invenio module for information retrieval."""

from __future__ import absolute_import, print_function

SEARCH_SYNC_JOBS = {}
"""Index sync job definitions.

Example:

.. code-block:: python

    SEARCH_SYNC_JOBS = {
        'records': {
            'cls': 'my_site.sync.RecordSyncJob',
            'params': {
                'rollover_threshold': 100,
                'old_es_client': ...,
                'new_es_client': ...,
            }
        }
    }
"""
