#!/usr/bin/env python3

import click
import subprocess
from rich.console import Console
from toast.plugins.base_plugin import BasePlugin
from toast.plugins.utils import run_command, select_from_list

console = Console()


class RegionPlugin(BasePlugin):
    """Plugin for 'region' command - sets AWS region."""

    name = "region"
    help = "Set AWS region"

    @classmethod
    def execute(cls, **kwargs):
        # Check current AWS region setting
        current_region_result = subprocess.run(
            ["aws", "configure", "get", "default.region"],
            capture_output=True,
            text=True,
        )
        if current_region_result.returncode and current_region_result.stderr.strip():
            raise click.ClickException(current_region_result.stderr.strip())
        current_region = current_region_result.stdout.strip()
        if current_region:
            console.print(f"Current AWS region: {current_region}", style="bold cyan")
        else:
            console.print("No AWS region is currently set.", style="yellow")

        # Get available region list
        result = run_command(
            [
                "aws",
                "ec2",
                "describe-regions",
                "--query",
                "Regions[].RegionName",
                "--output",
                "text",
            ],
        )
        regions = sorted(result.stdout.split())
        if not regions:
            raise click.ClickException("No regions found")

        selected_region = select_from_list(regions, "Select AWS Region")

        if selected_region:
            run_command(
                ["aws", "configure", "set", "default.region", selected_region]
            )
            run_command(["aws", "configure", "set", "default.output", "json"])
            console.print(f"✓ Set AWS region to {selected_region}", style="bold green")
        else:
            console.print("No region selected.", style="yellow")
