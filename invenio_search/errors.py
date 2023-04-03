# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Invenio search errors."""


class IndexAlreadyExistsError(Exception):
    """Raised when an index or alias already exists during index creation."""


class NotAllowedMappingUpdate(Exception):
    """Raised when attempted mapping update is not allowed."""
