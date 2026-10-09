#!/usr/bin/env python3

import os
import configparser
import io
from rich.console import Console
import click
from toast.plugins.am_plugin import show_identity
from toast.plugins.base_plugin import BasePlugin
from toast.plugins.utils import select_from_list, write_private_file

console = Console()


class EnvPlugin(BasePlugin):
    """Plugin for 'env' command - manages AWS profiles."""

    name = "env"
    help = "Manage AWS profiles"

    @classmethod
    def execute(cls, **kwargs):
        # AWS credentials file path
        credentials_path = os.path.expanduser(os.environ.get("AWS_SHARED_CREDENTIALS_FILE", "~/.aws/credentials"))

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

        # Get current default profile
        current_default = None
        if "default" in profiles:
            current_default = "default"

        # Display current default profile if exists
        if current_default:
            console.print(f"Current default profile: {current_default}", style="bold cyan")

        # User selects profile
        selected_profile = select_from_list(profiles, "Select AWS Profile")

        if selected_profile:
            if selected_profile == "default":
                console.print("Already the default profile.", style="yellow")
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

            console.print(f"✓ Set '{selected_profile}' as default profile.", style="bold green")

            show_identity(profile="default")
        else:
            console.print("No profile selected.", style="yellow")
