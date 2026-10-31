#!/usr/bin/env python3

import click
from toast import ui
from toast.plugins.base_plugin import BasePlugin
from toast.plugins.utils import run_command, spawn


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

        # `aws configure get` exits 1 without output when no region is set.
        current = spawn(["aws", "configure", "get", "default.region"])
        if current.returncode and current.stderr.strip():
            raise click.ClickException(current.stderr.strip())

        with ui.status("Listing AWS regions"):
            result = run_command(["aws", "ec2", "describe-regions", "--query", "Regions[].RegionName", "--output", "text"])
        regions = sorted(result.stdout.split())
        if not regions:
            raise click.ClickException("No regions found")

        selected = ui.choose(regions, "Select an AWS region", current=current.stdout.strip())
        if selected:
            cls._apply(selected)
        else:
            ui.cancelled()
