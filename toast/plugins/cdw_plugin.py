#!/usr/bin/env python3

import click
import subprocess
import os
from toast.plugins.base_plugin import BasePlugin
from toast.plugins.utils import select_from_list
from rich.console import Console

console = Console()


class CdwPlugin(BasePlugin):
    """Plugin for 'cdw' command - helps navigate to workspace directories."""

    name = "cdw"
    help = "Navigate to a workspace directory"

    @classmethod
    def execute(cls, **kwargs):
        workspace_dir = os.path.expanduser("~/workspace")
        if not os.path.exists(workspace_dir):
            os.makedirs(workspace_dir)
            console.print(f"✓ Created workspace directory: {workspace_dir}", style="bold green")

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
            console.print(f"✓ Created default directory structure: {github_dir}", style="bold green")
            console.print()
            console.print("Toast-cli expects the following workspace structure:", style="bold cyan")
            console.print("  ~/workspace/{github-host}/{org}/{project}", style="yellow")
            console.print()
            console.print("Examples:", style="bold cyan")
            console.print("  ~/workspace/github.com/opspresso/toast-cli", style="dim")
            console.print("  ~/workspace/github.enterprise.com/myorg/myproject", style="dim")
            console.print()
            console.print("You can now create your organization and project directories:", style="bold cyan")
            console.print(f"  mkdir -p {github_dir}/{{org}}/{{project}}", style="bold yellow")
            return

        selected_dir = select_from_list(directories, "Select a directory")

        if selected_dir:
            click.echo(selected_dir)
        else:
            console.print("No directory selected.", style="bold red", stderr=True)
