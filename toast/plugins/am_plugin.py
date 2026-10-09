#!/usr/bin/env python3

import json
from rich.console import Console
from toast.plugins.base_plugin import BasePlugin
from toast.plugins.utils import run_command

console = Console()


def show_identity(profile=None):
    args = ["aws", "sts", "get-caller-identity", "--output", "json"]
    if profile:
        args += ["--profile", profile]
    result = run_command(args)
    console.print_json(data=json.loads(result.stdout))


class AmPlugin(BasePlugin):
    """Plugin for 'am' command - shows AWS caller identity."""

    name = "am"
    help = "Show AWS caller identity"

    @classmethod
    def execute(cls, **kwargs):
        show_identity()
