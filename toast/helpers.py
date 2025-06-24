#!/usr/bin/env python3

import click
import os
import pkg_resources


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
    """Get the version from the VERSION file"""
    try:
        # Try to get the version from the package resource
        version = (
            pkg_resources.resource_string("toast_cli", "VERSION")
            .decode("utf-8")
            .strip()
        )
        return version
    except Exception:
        try:
            # Try again with a different package name
            version = (
                pkg_resources.resource_string("toast", "../VERSION")
                .decode("utf-8")
                .strip()
            )
            return version
        except Exception:
            try:
                # Fallback to the local file path for development
                version_file = os.path.join(os.path.dirname(__file__), "..", "VERSION")
                if os.path.exists(version_file):
                    with open(version_file, "r") as f:
                        version = f.read().strip()
                        return version
                return "v3.0.0.dev1"
            except Exception:
                return "v3.0.0.dev2"


class CustomHelpCommand(click.Command):
    def get_help(self, ctx):
        display_logo()
        return super().get_help(ctx)


class CustomHelpGroup(click.Group):
    def get_help(self, ctx):
        display_logo()
        return super().get_help(ctx)
