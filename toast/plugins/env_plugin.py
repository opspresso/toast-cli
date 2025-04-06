#!/usr/bin/env python3

import os
import configparser
import subprocess
import json
import click
from rich.console import Console
from toast.plugins.base_plugin import BasePlugin
from toast.plugins.utils import select_from_list

class EnvPlugin(BasePlugin):
    """Plugin for 'env' command - manages AWS profiles."""

    name = "env"
    help = "Manage AWS profiles"

    @classmethod
    def execute(cls, **kwargs):
        try:
            # AWS credentials file path
            credentials_path = os.path.expanduser("~/.aws/credentials")

            # Check if file exists
            if not os.path.exists(credentials_path):
                click.echo(f"AWS credentials file not found: {credentials_path}")
                return

            # Parse credentials file using configparser
            config = configparser.ConfigParser()
            config.read(credentials_path)

            # Extract profile list
            profiles = config.sections()

            if not profiles:
                click.echo("No profiles found in AWS credentials file.")
                return

            # Get current default profile
            current_default = None
            if 'default' in profiles:
                current_default = 'default'

            # Display current default profile if exists
            if current_default:
                click.echo(f"Current default profile: {current_default}")

            # User selects profile
            selected_profile = select_from_list(profiles, "Select AWS Profile")

            if selected_profile:
                if selected_profile == 'default':
                    click.echo("Already the default profile.")
                    return

                # Get credentials from selected profile
                aws_access_key_id = config[selected_profile].get('aws_access_key_id', '')
                aws_secret_access_key = config[selected_profile].get('aws_secret_access_key', '')
                aws_session_token = config[selected_profile].get('aws_session_token', '')

                # Modify credentials file directly to set default profile
                if 'default' not in config:
                    config.add_section('default')

                config['default']['aws_access_key_id'] = aws_access_key_id
                config['default']['aws_secret_access_key'] = aws_secret_access_key

                # Set session token if available
                if aws_session_token:
                    config['default']['aws_session_token'] = aws_session_token
                elif 'aws_session_token' in config['default']:
                    # Remove existing token when switching to profile without token
                    config.remove_option('default', 'aws_session_token')

                # Save changes to file
                with open(credentials_path, 'w') as configfile:
                    config.write(configfile)

                click.echo(f"Set '{selected_profile}' as default profile.")

                try:
                    result = subprocess.run(["aws", "sts", "get-caller-identity"], capture_output=True, text=True)
                    if result.returncode == 0:
                        # Parse JSON and print with rich
                        json_data = json.loads(result.stdout)
                        console = Console()
                        console.print_json(json.dumps(json_data))
                    else:
                        click.echo("Error fetching AWS caller identity.")
                except Exception as e:
                    click.echo(f"Error fetching AWS caller identity: {e}")
            else:
                click.echo("No profile selected.")
        except Exception as e:
            click.echo(f"Error while managing AWS profiles: {e}")
