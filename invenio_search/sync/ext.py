# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Index syncing extension."""

from __future__ import absolute_import, print_function

from flask import current_app
from werkzeug.utils import cached_property

from ..utils import obj_or_import_string
from . import config
from .cli import index_cmd


class InvenioIndexSync(object):
    """Invenio index sync extension."""

    def __init__(self, app=None, **kwargs):
        """Extension initialization.

        :param app: An instance of :class:`~flask.app.Flask`.
        """
        self._clients = {}

        if app:
            self.init_app(app, **kwargs)

    @cached_property
    def jobs(self):
        """Get all configured sync jobs."""
        jobs_config = current_app.config.get('SEARCH_SYNC_JOBS', {})
        for job_id, job_cfg in jobs_config.items():
            job_cfg['cls'] = obj_or_import_string(job_cfg['cls'])
        return jobs_config

    def init_app(self, app):
        """Flask application initialization.

        :param app: An instance of :class:`~flask.app.Flask`.
        """
        self.init_config(app)
        app.cli.add_command(index_cmd)
        app.extensions['invenio-index-sync'] = self

    @staticmethod
    def init_config(app):
        """Initialize configuration.

        :param app: An instance of :class:`~flask.app.Flask`.
        """
        for k in dir(config):
            if k.startswith('SEARCH_SYNC_'):
                app.config.setdefault(k, getattr(config, k))
