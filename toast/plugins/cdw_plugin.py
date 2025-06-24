#!/usr/bin/env python3

import click
import subprocess
import os
from toast.plugins.base_plugin import BasePlugin
from toast.plugins.utils import select_from_list


class CdwPlugin(BasePlugin):
    """Plugin for 'cdw' command - helps navigate to workspace directories."""

    name = "cdw"
    help = "Navigate to a workspace directory"

    @classmethod
    def execute(cls, **kwargs):
        workspace_dir = os.path.expanduser("~/workspace")
        if not os.path.exists(workspace_dir):
            os.makedirs(workspace_dir)

        result = subprocess.run(
            ["find", workspace_dir, "-mindepth", "1", "-maxdepth", "2", "-type", "d"],
            capture_output=True,
            text=True,
        )
        directories = sorted(result.stdout.splitlines())

        if not directories:
            click.echo("No directories found in ~/workspace.")
            return

        selected_dir = select_from_list(directories, "Select a directory")

        if selected_dir:
            click.echo(selected_dir)
        else:
            click.echo("No directory selected.", err=True)
