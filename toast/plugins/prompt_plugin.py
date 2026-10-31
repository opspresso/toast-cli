#!/usr/bin/env python3

import click
from toast.plugins.base_plugin import BasePlugin
from toast.plugins.storage import run_file_sync


class PromptPlugin(BasePlugin):
    """Plugin for 'prompt' command - manages .prompt.md files."""

    name = "prompt"
    help = "Manage .prompt.md files"
    category = "Workspace"
    commands = (
        ("sync", "Compare, then choose a direction (default)"),
        ("up", "Upload to the env-store"),
        ("down", "Download from the env-store (alias: dn)"),
        ("diff", "Show the masked differences"),
        ("ls", "List the entries in the env-store"),
    )
    examples = (
        ("toast prompt", "Sync .prompt.md with the env-store"),
        ("toast prompt down", "Download .prompt.md"),
    )

    @classmethod
    def get_arguments(cls, func):
        func = click.argument("command", required=False, shell_complete=cls.complete_command)(func)
        return func

    @classmethod
    def execute(cls, command=None, **kwargs):
        run_file_sync("prompt-md", ".prompt.md", command)
