# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2018 CERN.
# Copyright (C) 2022 Graz University of Technology.
# Copyright (C) 2022 TU Wien.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.


"""Test CLI."""

from __future__ import absolute_import, print_function

import ast

import pytest
from click.testing import CliRunner
from flask.cli import ScriptInfo
from mock import patch

from invenio_search.cli import index as cmd
from invenio_search.engine import _fixed_search_version, search
from invenio_search.proxies import current_search_client


def test_init(app, template_entrypoints):
    """Run client initialization."""
    suffix = "-abc"
    search = app.extensions["invenio-search"]
    search._current_suffix = suffix
    search.register_mappings("records", "mock_module.mappings")

    assert "records" in search.aliases
    assert set(search.aliases["records"]) == {
        "records-authorities",
        "records-bibliographic",
        "records-default-v1.0.0",
    }
    assert set(search.aliases["records"]["records-authorities"]) == {
        "records-authorities-authority-v1.0.0",
    }
    assert set(search.aliases["records"]["records-bibliographic"]) == {
        "records-bibliographic-bibliographic-v1.0.0",
    }
    assert set(search.mappings.keys()) == {
        "records-authorities-authority-v1.0.0",
        "records-bibliographic-bibliographic-v1.0.0",
        "records-default-v1.0.0",
    }
    assert 3 == len(search.mappings)

    with patch(
        "invenio_search.ext.iter_entry_points",
        return_value=template_entrypoints("invenio_search.templates"),
    ):
        if _fixed_search_version[0] == 2:
            assert len(search.templates.keys()) == 2
            assert "record-view-v1" in search.templates
            assert "subdirectory-file-download-v1" in search.templates
        else:
            assert len(search.templates.keys()) == 1
            assert (
                "record-view-v{}".format(_fixed_search_version[0]) in search.templates
            )

    current_search_client.indices.delete_alias("_all", "_all", ignore=[400, 404])
    current_search_client.indices.delete("*")
    aliases = current_search_client.indices.get_alias()
    assert 0 == len(aliases)

    runner = CliRunner()
    script_info = ScriptInfo(create_app=lambda: app)

    with runner.isolated_filesystem():
        result = runner.invoke(cmd, ["init", "--force"], obj=script_info)
        assert result.exit_code == 0
        if _fixed_search_version[0] == 2:
            assert current_search_client.indices.exists_template(
                "subdirectory-file-download-v1"
            )
            assert current_search_client.indices.exists_template("record-view-v1")
        else:
            assert current_search_client.indices.exists_template(
                "record-view-v{}".format(_fixed_search_version[0])
            )
        assert 0 == result.exit_code

    aliases = current_search_client.indices.get_alias()
    assert 8 == sum(len(idx.get("aliases", {})) for idx in aliases.values())

    assert current_search_client.indices.exists(list(search.mappings.keys()))

    # Clean-up:
    result = runner.invoke(cmd, ["destroy"], obj=script_info)
    assert 1 == result.exit_code

    result = runner.invoke(cmd, ["destroy", "--yes-i-know"], obj=script_info)
    assert 0 == result.exit_code

    aliases = current_search_client.indices.get_alias()
    assert 0 == len(aliases)


def test_list(app):
    """Run listing of mappings."""
    suffix = "-abc"
    app.config["SEARCH_MAPPINGS"] = ["records"]
    search = app.extensions["invenio-search"]
    search._current_suffix = suffix
    search.register_mappings("authors", "mock_module.mappings")
    search.register_mappings("records", "mock_module.mappings")

    runner = CliRunner()
    script_info = ScriptInfo(create_app=lambda: app)

    result = runner.invoke(cmd, ["list", "--only-aliases"], obj=script_info)
    # Turn cli outputted str presentation of Python list into a list
    assert set(ast.literal_eval(result.output)) == {"records", "authors"}

    result = runner.invoke(cmd, ["list"], obj=script_info)
    assert result.output == (
        "├──authors\n"
        "│  └──authors-authors-v1.0.0\n"
        "└──records *\n"
        "   ├──records-authorities\n"
        "   │  └──records-authorities-authority-v1.0.0\n"
        "   ├──records-bibliographic\n"
        "   │  └──records-bibliographic-bibliographic-v1.0.0\n"
        "   └──records-default-v1.0.0\n\n"
    )


def test_check(app):
    runner = CliRunner()
    script_info = ScriptInfo(create_app=lambda: app)

    result = runner.invoke(cmd, ["check"], obj=script_info)
    assert result.exit_code == 0

    with patch(
        "invenio_search.cli.search.VERSION",
        return_value=(_fixed_search_version[0] + 1, 0, 0),
    ):
        result = runner.invoke(cmd, ["check"], obj=script_info)
        assert result.exit_code != 0


def test_create_put_and_delete(app):
    runner = CliRunner()
    script_info = ScriptInfo(create_app=lambda: app)
    name = "test-index-name"

    result = runner.invoke(
        cmd,
        [
            "create",
            "--verbose",
            name,
            "--body",
            "./tests/mock_module/mappings/authors/authors-v1.0.0.json",
        ],
        obj=script_info,
    )
    assert result.exit_code == 0
    assert name in list(current_search_client.indices.get("*").keys())

    doc_type = "_doc" if _fixed_search_version[0] > 5 else "recid"
    result = runner.invoke(
        cmd,
        [
            "put",
            name,
            doc_type,
            "--verbose",
            "--identifier",
            1,
            "--body",
            "./tests/mock_module/mappings/authors/authors-v1.0.0.json",
        ],
        obj=script_info,
    )
    assert result.exit_code == 0
    current_search_client.get(index=name, doc_type=doc_type, id=1)
    with pytest.raises(search.exceptions.NotFoundError):
        current_search_client.get(index=name, doc_type=doc_type, id=2)

    result = runner.invoke(
        cmd,
        [
            "delete",
            "--verbose",
            "--yes-i-know",
            "--force",
            name,
        ],
        obj=script_info,
    )
    assert result.exit_code == 0
    assert name not in list(current_search_client.indices.get("*").keys())
