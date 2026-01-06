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
            click.echo(f"Created workspace directory: {workspace_dir}")

        result = subprocess.run(
            ["find", workspace_dir, "-mindepth", "1", "-maxdepth", "2", "-type", "d"],
            capture_output=True,
            text=True,
        )
        directories = sorted(result.stdout.splitlines())

        if not directories:
            # Create default github.com directory structure
            github_dir = os.path.join(workspace_dir, "github.com")
            os.makedirs(github_dir, exist_ok=True)
            click.echo(f"Created default directory structure: {github_dir}")
            click.echo("")
            click.echo("Toast-cli expects the following workspace structure:")
            click.echo("  ~/workspace/{{github-host}}/{{org}}/{{project}}")
            click.echo("")
            click.echo("Examples:")
            click.echo("  ~/workspace/github.com/opspresso/toast-cli")
            click.echo("  ~/workspace/github.enterprise.com/myorg/myproject")
            click.echo("")
            click.echo("You can now create your organization and project directories:")
            click.echo(f"  mkdir -p {github_dir}/{{org}}/{{project}}")
            return

        selected_dir = select_from_list(directories, "Select a directory")

        if selected_dir:
            click.echo(selected_dir)
        else:
            click.echo("No directory selected.", err=True)
