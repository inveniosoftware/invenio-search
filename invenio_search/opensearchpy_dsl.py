# SPDX-FileCopyrightText: 2026 RERO.
# SPDX-License-Identifier: MIT

"""DSL bundled with ``opensearch-py`` v3+, exposed like ``opensearch_dsl``.

``opensearch-dsl`` has been merged into ``opensearch-py`` and is not released
for v3 anymore: the DSL classes (``Search``, ``Q``, ...) are available at the
top-level of ``opensearchpy`` and the submodules (``query``, ``aggs``, ...) in
``opensearchpy.helpers``.
"""

from importlib import import_module

_HELPERS_SUBMODULES = {
    "aggs",
    "analysis",
    "document",
    "faceted_search",
    "field",
    "function",
    "index",
    "mapping",
    "query",
    "response",
    "search",
    "update_by_query",
    "utils",
    "wrappers",
}


def __getattr__(name):
    """Resolve the attribute in ``opensearchpy.helpers`` or ``opensearchpy``."""
    try:
        if name in _HELPERS_SUBMODULES:
            return import_module(f"opensearchpy.helpers.{name}")
        return getattr(import_module("opensearchpy"), name)
    except ModuleNotFoundError as e:
        # e.g. introspection (pytest, doctest) without opensearch-py v3 installed
        raise AttributeError(name) from e
