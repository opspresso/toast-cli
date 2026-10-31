#!/usr/bin/env python3

import click
import subprocess
from toast import ui
from toast.plugins.base_plugin import BasePlugin
from toast.plugins.utils import run_command, select_from_list


class RegionPlugin(BasePlugin):
    """Plugin for 'region' command - sets AWS region."""

    name = "region"
    help = "Set AWS region"
    category = "AWS"
    examples = (
        ("toast region", "Pick the default region"),
        ("toast region ap-northeast-2", "Switch to a named region"),
    )

    @classmethod
    def get_arguments(cls, func):
        return click.argument("region", required=False)(func)

    @staticmethod
    def _apply(region):
        run_command(["aws", "configure", "set", "default.region", region])
        run_command(["aws", "configure", "set", "default.output", "json"])
        ui.success(f"Set AWS region to {region}")

    @classmethod
    def execute(cls, region=None, **kwargs):
        if region:
            cls._apply(region)
            return

        current = subprocess.run(
            ["aws", "configure", "get", "default.region"],
            capture_output=True,
            text=True,
        )
        if current.returncode and current.stderr.strip():
            raise click.ClickException(current.stderr.strip())

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

        selected = select_from_list(regions, "Select AWS Region", current=current.stdout.strip())
        if selected:
            cls._apply(selected)
        else:
            ui.muted("No region selected.")
