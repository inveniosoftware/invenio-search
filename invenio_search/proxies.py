# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Proxy objects for easier access to application objects."""

from flask import current_app
from werkzeug.local import LocalProxy


def _get_current_search():
    """Return current state of the search extension."""
    return current_app.extensions['invenio-search']


def _get_current_search_client():
    """Return current search client."""
    return _get_current_search().client


current_search = LocalProxy(_get_current_search)
current_search_client = LocalProxy(_get_current_search_client)
