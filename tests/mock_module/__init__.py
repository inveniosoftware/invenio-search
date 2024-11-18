# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2017-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Mock module used to test loading of ES resources."""

from invenio_search.api import dsl


class Address(dsl.InnerDoc):
    """Address innder document."""

    street = dsl.Text()
    city = dsl.Text()
    zip = dsl.Keyword()


class Organization(dsl.Document):
    """Organization document."""

    class Index:
        """Index configuration."""

        name = "organizations-organization-v1.0.0"

    title = dsl.Text()
    acronym = dsl.Keyword()
    address = dsl.Object(Address)


def mock_mapping(ext):
    """Mock mapping."""
    index = Organization._index
    mapping = index.to_dict()

    ext.mappings[index._name] = mapping
    ext.aliases["organizations"] = {"organizations-organization": {index._name: None}}
