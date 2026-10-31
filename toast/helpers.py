#!/usr/bin/env python3

import click
import os
from importlib.metadata import PackageNotFoundError, version
from rich.console import Console

console = Console()


def display_logo():
    """Display the toast-cli ASCII logo"""
    logo_lines = [
        r" _                  _           _ _",
        r"| |_ ___   __ _ ___| |_     ___| (_)",
        r"| __/ _ \ / _` / __| __|__ / __| | |",
        r"| || (_) | (_| \__ \ ||___| (__| | |",
        r" \__\___/ \__,_|___/\__|   \___|_|_|",
    ]

    console.print()
    for i, line in enumerate(logo_lines):
        if i == len(logo_lines) - 1:
            # Last line: append version on the same line
            console.print(line, style="bold yellow", end="")
            console.print(f"   {get_version()}", style="bold cyan", highlight=False)
        else:
            console.print(line, style="bold yellow", highlight=False)
    console.print("─" * min(console.width, 80), style="dim")


def get_version():
    """Get the version from package metadata"""
    try:
        # Get version from installed package metadata
        return version("toast-cli")
    except PackageNotFoundError:
        # Fallback to VERSION file for development environment
        version_file = os.path.join(os.path.dirname(__file__), "..", "VERSION")
        if os.path.exists(version_file):
            with open(version_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        return "unknown"


def format_examples(formatter, examples):
    if examples:
        with formatter.section("Examples"):
            formatter.write_dl(examples)


class CustomHelpCommand(click.Command):
    """Help for one command, with the plugin's usage examples."""

    def __init__(self, *args, examples=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.examples = examples

    def format_epilog(self, ctx, formatter):
        format_examples(formatter, self.examples)
        super().format_epilog(ctx, formatter)


class CustomHelpGroup(click.Group):
    """Top-level help: the logo, then commands grouped by what they act on."""

    def get_help(self, ctx):
        display_logo()
        return super().get_help(ctx)

    def format_commands(self, ctx, formatter):
        sections = {}
        for name in self.list_commands(ctx):
            command = self.get_command(ctx, name)
            if command is not None and not command.hidden:
                sections.setdefault(getattr(command, "category", "General"), []).append(
                    (name, command.get_short_help_str(limit=max(40, formatter.width - 14)))
                )
        for title in sorted(sections, key=lambda section: (section == "General", section)):
            with formatter.section(title):
                formatter.write_dl(sections[title])
