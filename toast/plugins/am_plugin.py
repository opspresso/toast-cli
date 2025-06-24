#!/usr/bin/env python3

import click
import subprocess
import json
from rich.console import Console
from toast.plugins.base_plugin import BasePlugin


class AmPlugin(BasePlugin):
    """Plugin for 'am' command - shows AWS caller identity."""

    name = "am"
    help = "Show AWS caller identity"

    @classmethod
    def execute(cls, **kwargs):
        try:
            result = subprocess.run(
                ["aws", "sts", "get-caller-identity"], capture_output=True, text=True
            )
            if result.returncode == 0:
                # Parse JSON and print with rich
                json_data = json.loads(result.stdout)
                console = Console()
                console.print_json(json.dumps(json_data))
            else:
                click.echo("Error fetching AWS caller identity.")
        except Exception as e:
            click.echo(f"Error fetching AWS caller identity: {e}")
