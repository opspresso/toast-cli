#!/usr/bin/env python3

import click
import os
from importlib.metadata import version
from rich.console import Console

console = Console()


def display_logo():
    """Display the toast-cli ASCII logo"""
    logo_lines = [
        " _                  _           _ _",
        "| |_ ___   __ _ ___| |_     ___| (_)",
        "| __/ _ \ / _` / __| __|__ / __| | |",
        "| || (_) | (_| \__ \ ||___| (__| | |",
        " \__\___/ \__,_|___/\__|   \___|_|_|",
    ]

    console.print()
    for i, line in enumerate(logo_lines):
        if i == len(logo_lines) - 1:
            # Last line: append version on the same line
            console.print(line, style="bold yellow", end="")
            console.print(f"   {get_version()}", style="bold cyan", highlight=False)
        else:
            console.print(line, style="bold yellow", highlight=False)
    console.print("=" * 80, style="dim")


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
