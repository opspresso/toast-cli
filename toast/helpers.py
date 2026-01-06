#!/usr/bin/env python3

import click
import os
from importlib.metadata import version


def display_logo():
    """Display the toast-cli ASCII logo"""
    logo = """
 _                  _           _ _
| |_ ___   __ _ ___| |_     ___| (_)
| __/ _ \ / _` / __| __|__ / __| | |
| || (_) | (_| \__ \ ||___| (__| | |
 \__\___/ \__,_|___/\__|   \___|_|_|   {0}
""".format(
        get_version()
    )
    click.echo(logo)
    click.echo("=" * 80)


def get_version():
    """Get the version from package metadata"""
    try:
        # Get version from installed package metadata
        return version("toast-cli")
    except Exception:
        # Fallback to VERSION file for development environment
        version_file = os.path.join(os.path.dirname(__file__), "..", "VERSION")
        if os.path.exists(version_file):
            with open(version_file, "r") as f:
                return f.read().strip()
        return "unknown"


class CustomHelpCommand(click.Command):
    def get_help(self, ctx):
        display_logo()
        return super().get_help(ctx)


class CustomHelpGroup(click.Group):
    def get_help(self, ctx):
        display_logo()
        return super().get_help(ctx)
