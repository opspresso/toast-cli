#!/usr/bin/env python3

import click
from toast.plugins.base_plugin import BasePlugin
from toast.plugins.storage import run_file_sync


class DotPlugin(BasePlugin):
    """Plugin for 'dot' command - manages .env.local files."""

    name = "dot"
    help = "Manage .env.local files"

    @classmethod
    def get_arguments(cls, func):
        func = click.argument("command", required=False)(func)
        return func

    @classmethod
    def execute(cls, command=None, **kwargs):
        run_file_sync("env-local", ".env.local", command)
