# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2022 CERN.
# Copyright (C) 2022 Graz University of Technology.
# Copyright (C) 2022 TU Wien.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Test CLI."""

import ast

import pytest
from click.testing import CliRunner
from flask.cli import ScriptInfo
from mock import patch

from invenio_search.cli import index as cmd
from invenio_search.engine import ES, OS, SEARCH_DISTRIBUTION, search
from invenio_search.proxies import current_search_client


def _get_version():
    """Get filename postfix with current ES/OS version."""
    search_major_version = search.VERSION[0]
    version = "v{}" if SEARCH_DISTRIBUTION == ES else "os-v{}"
    return version.format(search_major_version)


def test_init(app, template_entrypoints):
    """Run client initialization."""
    suffix = "-abc"
    invenio_search = app.extensions["invenio-search"]
    invenio_search._current_suffix = suffix
    invenio_search.register_mappings("records", "mock_module.mappings")

    assert "records" in invenio_search.aliases
    assert set(invenio_search.aliases["records"]) == {
        "records-authorities",
        "records-bibliographic",
        "records-default-v1.0.0",
    }
    assert set(invenio_search.aliases["records"]["records-authorities"]) == {
        "records-authorities-authority-v1.0.0",
    }
    assert set(invenio_search.aliases["records"]["records-bibliographic"]) == {
        "records-bibliographic-bibliographic-v1.0.0",
    }
    assert set(invenio_search.mappings.keys()) == {
        "records-authorities-authority-v1.0.0",
        "records-bibliographic-bibliographic-v1.0.0",
        "records-default-v1.0.0",
    }
    assert 3 == len(invenio_search.mappings)

    with patch(
        "invenio_search.ext.iter_entry_points",
        return_value=template_entrypoints("invenio_search.templates"),
    ):
        assert len(invenio_search.templates.keys()) == 1
        assert "record-view-{}".format(_get_version()) in invenio_search.templates

    current_search_client.indices.delete_alias("_all", "_all", ignore=[400, 404])
    current_search_client.indices.delete("*")
    aliases = current_search_client.indices.get_alias()
    assert 0 == len(aliases)

    runner = CliRunner()
    script_info = ScriptInfo(create_app=lambda: app)

    with runner.isolated_filesystem():
        result = runner.invoke(cmd, ["init", "--force"], obj=script_info)
        assert result.exit_code == 0
        assert current_search_client.indices.exists_template(
            "record-view-{}".format(_get_version())
        )
        assert 0 == result.exit_code

    aliases = current_search_client.indices.get_alias()
    assert 8 == sum(len(idx.get("aliases", {})) for idx in aliases.values())

    assert current_search_client.indices.exists(list(invenio_search.mappings.keys()))

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
    invenio_search = app.extensions["invenio-search"]
    invenio_search._current_suffix = suffix
    invenio_search.register_mappings("authors", "mock_module.mappings")
    invenio_search.register_mappings("records", "mock_module.mappings")

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

    wrong_version = search.VERSION[0] + 1
    with patch(
        "invenio_search.cli.search.VERSION",
        return_value=(wrong_version, 0, 0),
    ):
        result = runner.invoke(cmd, ["check"], obj=script_info)
        assert result.exit_code > 0


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

    is_OS = SEARCH_DISTRIBUTION == OS
    is_ES = SEARCH_DISTRIBUTION == ES
    result = runner.invoke(
        cmd,
        [
            "put",
            name,
            "--verbose",
            "--identifier",
            1,
            "--body",
            "./tests/mock_module/mappings/authors/authors-v1.0.0.json",
        ],
        obj=script_info,
    )
    assert result.exit_code == 0

    current_search_client.get(index=name, id=1)
    with pytest.raises(search.NotFoundError):
        current_search_client.get(index=name, id=2)

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
