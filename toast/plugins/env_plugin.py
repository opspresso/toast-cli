#!/usr/bin/env python3

import os
import configparser
import io
import click
from toast import ui
from toast.plugins.am_plugin import show_identity
from toast.plugins.base_plugin import BasePlugin
from toast.plugins.utils import write_private_file


def credentials_file():
    return os.path.expanduser(os.environ.get("AWS_SHARED_CREDENTIALS_FILE", "~/.aws/credentials"))


def complete_profiles(ctx, param, incomplete):
    config = configparser.ConfigParser(interpolation=None)
    config.read(credentials_file(), encoding="utf-8")
    return [name for name in config.sections() if name.startswith(incomplete)]


class EnvPlugin(BasePlugin):
    """Plugin for 'env' command - manages AWS profiles."""

    name = "env"
    help = "Manage AWS profiles"
    category = "AWS"
    examples = (
        ("toast env", "Pick the default profile"),
        ("toast env prod", "Switch to a named profile"),
    )

    @classmethod
    def get_arguments(cls, func):
        return click.argument("profile", required=False, shell_complete=complete_profiles)(func)

    @classmethod
    def execute(cls, profile=None, **kwargs):
        credentials_path = credentials_file()

        # Check if file exists
        if not os.path.exists(credentials_path):
            raise click.ClickException(f"AWS credentials file not found: {credentials_path}")

        # Parse credentials file using configparser
        config = configparser.ConfigParser(interpolation=None)
        config.read(credentials_path, encoding="utf-8")

        # Extract profile list
        profiles = config.sections()

        if not profiles:
            raise click.ClickException("No profiles found in AWS credentials file")

        if profile and profile not in profiles:
            raise click.ClickException(f"Profile '{profile}' is not in {credentials_path}")

        # User selects profile
        selected_profile = profile or ui.choose(profiles, "Select an AWS profile", current="default" if "default" in profiles else None)

        if selected_profile:
            if selected_profile == "default":
                ui.muted("Already the default profile")
                return

            # Get credentials from selected profile
            aws_access_key_id = config[selected_profile].get(
                "aws_access_key_id", ""
            )
            aws_secret_access_key = config[selected_profile].get(
                "aws_secret_access_key", ""
            )
            aws_session_token = config[selected_profile].get(
                "aws_session_token", ""
            )

            if not aws_access_key_id or not aws_secret_access_key:
                raise click.ClickException(f"Profile '{selected_profile}' has no static access key pair")

            # Modify credentials file directly to set default profile
            if "default" not in config:
                config.add_section("default")

            config["default"]["aws_access_key_id"] = aws_access_key_id
            config["default"]["aws_secret_access_key"] = aws_secret_access_key

            # Set session token if available
            if aws_session_token:
                config["default"]["aws_session_token"] = aws_session_token
            elif "aws_session_token" in config["default"]:
                # Remove existing token when switching to profile without token
                config.remove_option("default", "aws_session_token")

            serialized = io.StringIO()
            config.write(serialized)
            write_private_file(credentials_path, serialized.getvalue())

            ui.success(f"Set {selected_profile} as the default profile")

            show_identity(profile="default")
        else:
            ui.cancelled()
