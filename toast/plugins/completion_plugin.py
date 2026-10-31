#!/usr/bin/env python3

import os

import click
from click.shell_completion import get_completion_class

from toast.plugins.base_plugin import BasePlugin


class CompletionPlugin(BasePlugin):
    """Plugin for 'completion' command - prints a shell completion script."""

    name = "completion"
    help = "Print the shell completion script"
    examples = (
        ('eval "$(toast completion zsh)"', "Enable completion in ~/.zshrc"),
        ("toast completion fish | source", "Enable completion in fish"),
    )

    @classmethod
    def get_arguments(cls, func):
        return click.argument("shell", required=False, type=click.Choice(["bash", "zsh", "fish"]))(func)

    @classmethod
    def execute(cls, shell=None, **kwargs):
        shell = shell or os.path.basename(os.environ.get("SHELL", ""))
        completion = get_completion_class(shell)
        if completion is None:
            raise click.UsageError("Name a shell: bash, zsh or fish")
        root = click.get_current_context().find_root().command
        click.echo(completion(root, {}, "toast", "_TOAST_COMPLETE").source())
