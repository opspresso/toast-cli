#!/usr/bin/env python3

import subprocess
import json
from rich.console import Console
from toast.plugins.base_plugin import BasePlugin

console = Console()


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
                console.print_json(json.dumps(json_data))
            else:
                console.print("✗ Error fetching AWS caller identity.", style="bold red")
        except Exception as e:
            console.print(f"✗ Error fetching AWS caller identity: {e}", style="bold red")
