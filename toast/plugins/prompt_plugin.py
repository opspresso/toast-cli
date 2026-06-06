#!/usr/bin/env python3

import click
from toast.plugins.base_plugin import BasePlugin
from toast.plugins.storage import run_file_sync


class PromptPlugin(BasePlugin):
    """Plugin for 'prompt' command - manages .prompt.md files."""

    name = "prompt"
    help = "Manage .prompt.md files"

    @classmethod
    def get_arguments(cls, func):
        func = click.argument("command", required=False)(func)
        return func

    @classmethod
    def execute(cls, command=None, **kwargs):
        run_file_sync("prompt-md", ".prompt.md", command)
