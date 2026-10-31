#!/usr/bin/env python3

import json

from toast import ui
from toast.plugins.base_plugin import BasePlugin
from toast.plugins.utils import run_command


def show_identity(profile=None):
    args = ["aws", "sts", "get-caller-identity", "--output", "json"]
    if profile:
        args += ["--profile", profile]
    with ui.status("Reading the AWS identity"):
        result = run_command(args)
    ui.json_result(json.loads(result.stdout))


class AmPlugin(BasePlugin):
    """Plugin for 'am' command - shows AWS caller identity."""

    name = "am"
    help = "Show AWS caller identity"
    category = "AWS"
    examples = (
        ("toast am", "Show the current account and role"),
    )

    @classmethod
    def execute(cls, **kwargs):
        show_identity()
