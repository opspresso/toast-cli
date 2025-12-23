#!/usr/bin/env python3

import click
import subprocess
import json
from toast.plugins.base_plugin import BasePlugin
from toast.plugins.utils import check_aws_cli, select_from_list


class SsmPlugin(BasePlugin):
    """Plugin for 'ssm' command - AWS SSM Parameter Store operations."""

    name = "ssm"
    help = "AWS SSM Parameter Store operations"

    @classmethod
    def get_arguments(cls, func):
        func = click.argument("command", required=False)(func)
        func = click.argument("name", required=False)(func)
        func = click.argument("value", required=False)(func)
        func = click.option("--region", "-r", help="AWS region")(func)
        return func

    @classmethod
    def execute(cls, command=None, name=None, value=None, region=None, **kwargs):
        # Check AWS CLI availability
        if not check_aws_cli():
            click.echo("Error: AWS CLI not found. Please install it to use this feature.")
            return

        # Build base AWS command with optional region
        def aws_cmd(args):
            cmd = ["aws", "ssm"] + args
            if region:
                cmd.extend(["--region", region])
            return cmd

        # Handle commands
        if command in ("g", "get"):
            cls._get_parameter(name, aws_cmd)

        elif command in ("p", "put"):
            cls._put_parameter(name, value, aws_cmd)

        elif command in ("d", "delete", "rm"):
            cls._delete_parameter(name, aws_cmd)

        elif command == "ls":
            cls._list_parameters(name, aws_cmd)

        elif command is None:
            # Default: interactive mode - list and select parameter
            cls._interactive_mode(aws_cmd)

        else:
            # If command looks like a parameter name (starts with /), treat as get
            if command and command.startswith("/"):
                cls._get_parameter(command, aws_cmd)
            else:
                click.echo(f"Unknown command: {command}")
                click.echo()
                cls._show_usage()

    @classmethod
    def _show_usage(cls):
        """Show usage information."""
        click.echo("Usage: toast ssm <command> [args...]")
        click.echo()
        click.echo("Commands:")
        click.echo("  (none)                    - Interactive mode: browse and select parameters")
        click.echo("  ls [path]                 - List parameters (optionally filter by path)")
        click.echo("  g|get <name>              - Get parameter value (decrypted)")
        click.echo("  p|put <name> <value>      - Put parameter as SecureString")
        click.echo("  d|delete|rm <name>        - Delete parameter")
        click.echo()
        click.echo("Options:")
        click.echo("  -r, --region <region>     - Specify AWS region")
        click.echo()
        click.echo("Examples:")
        click.echo("  toast ssm                           # Interactive browse")
        click.echo("  toast ssm ls /toast/                # List parameters under /toast/")
        click.echo("  toast ssm get /my/param             # Get parameter value")
        click.echo("  toast ssm put /my/param 'secret'    # Store as SecureString")
        click.echo("  toast ssm rm /my/param              # Delete parameter")

    @classmethod
    def _get_parameter(cls, name, aws_cmd):
        """Get parameter value with decryption."""
        if not name:
            click.echo("Error: Parameter name is required.")
            click.echo("Usage: toast ssm get <name>")
            return

        try:
            result = subprocess.run(
                aws_cmd([
                    "get-parameter",
                    "--name", name,
                    "--with-decryption",
                    "--output", "json"
                ]),
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                if "ParameterNotFound" in result.stderr:
                    click.echo(f"Error: Parameter '{name}' not found.")
                else:
                    click.echo(f"Error: {result.stderr}")
                return

            response = json.loads(result.stdout)
            param = response.get("Parameter", {})
            value = param.get("Value", "")
            param_type = param.get("Type", "")
            last_modified = param.get("LastModifiedDate", "")

            click.echo(f"Name: {name}")
            click.echo(f"Type: {param_type}")
            if last_modified:
                click.echo(f"Last Modified: {last_modified}")
            click.echo("-" * 40)
            click.echo(value)

        except json.JSONDecodeError:
            click.echo("Error: Failed to parse AWS response.")
        except Exception as e:
            click.echo(f"Error: {e}")

    @classmethod
    def _put_parameter(cls, name, value, aws_cmd):
        """Put parameter as SecureString."""
        if not name:
            click.echo("Error: Parameter name is required.")
            click.echo("Usage: toast ssm put <name> <value>")
            return

        if not value:
            click.echo("Error: Parameter value is required.")
            click.echo("Usage: toast ssm put <name> <value>")
            return

        # Confirm before overwriting
        if not click.confirm(f"Store '{name}' as SecureString?"):
            click.echo("Operation cancelled.")
            return

        try:
            result = subprocess.run(
                aws_cmd([
                    "put-parameter",
                    "--name", name,
                    "--value", value,
                    "--type", "SecureString",
                    "--overwrite",
                    "--output", "json"
                ]),
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                click.echo(f"Error: {result.stderr}")
                return

            response = json.loads(result.stdout)
            version = response.get("Version", "")
            click.echo(f"Successfully stored '{name}' (Version: {version})")

        except json.JSONDecodeError:
            click.echo("Error: Failed to parse AWS response.")
        except Exception as e:
            click.echo(f"Error: {e}")

    @classmethod
    def _delete_parameter(cls, name, aws_cmd):
        """Delete parameter."""
        if not name:
            click.echo("Error: Parameter name is required.")
            click.echo("Usage: toast ssm delete <name>")
            return

        # Confirm before deleting
        if not click.confirm(f"Delete parameter '{name}'? This cannot be undone."):
            click.echo("Operation cancelled.")
            return

        try:
            result = subprocess.run(
                aws_cmd([
                    "delete-parameter",
                    "--name", name
                ]),
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                if "ParameterNotFound" in result.stderr:
                    click.echo(f"Error: Parameter '{name}' not found.")
                else:
                    click.echo(f"Error: {result.stderr}")
                return

            click.echo(f"Successfully deleted '{name}'")

        except Exception as e:
            click.echo(f"Error: {e}")

    @classmethod
    def _list_parameters(cls, path, aws_cmd):
        """List parameters, optionally filtered by path."""
        try:
            if path:
                # List by path
                result = subprocess.run(
                    aws_cmd([
                        "get-parameters-by-path",
                        "--path", path,
                        "--recursive",
                        "--output", "json"
                    ]),
                    capture_output=True,
                    text=True,
                )
            else:
                # Describe all parameters
                result = subprocess.run(
                    aws_cmd([
                        "describe-parameters",
                        "--output", "json"
                    ]),
                    capture_output=True,
                    text=True,
                )

            if result.returncode != 0:
                click.echo(f"Error: {result.stderr}")
                return

            response = json.loads(result.stdout)

            if path:
                parameters = response.get("Parameters", [])
            else:
                parameters = response.get("Parameters", [])

            if not parameters:
                click.echo("No parameters found.")
                return

            click.echo(f"\nAWS SSM Parameters{' under ' + path if path else ''}:")
            click.echo("=" * 60)

            for param in parameters:
                param_name = param.get("Name", "")
                param_type = param.get("Type", "")
                last_modified = param.get("LastModifiedDate", "")

                if last_modified and not isinstance(last_modified, str):
                    from datetime import datetime
                    last_modified = datetime.fromtimestamp(last_modified).strftime("%Y-%m-%d %H:%M:%S")

                click.echo(f"{param_name}")
                click.echo(f"  Type: {param_type}, Modified: {last_modified}")

        except json.JSONDecodeError:
            click.echo("Error: Failed to parse AWS response.")
        except Exception as e:
            click.echo(f"Error: {e}")

    @classmethod
    def _interactive_mode(cls, aws_cmd):
        """Interactive mode: browse and select parameters."""
        click.echo("Loading parameters from AWS SSM...")

        try:
            # Get all parameters
            result = subprocess.run(
                aws_cmd([
                    "describe-parameters",
                    "--output", "json"
                ]),
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                click.echo(f"Error: {result.stderr}")
                return

            response = json.loads(result.stdout)
            parameters = response.get("Parameters", [])

            if not parameters:
                click.echo("No parameters found.")
                return

            # Build list for fzf
            param_names = [p.get("Name", "") for p in parameters]
            param_names.sort()

            # Add action options
            options = ["[New] Create new parameter..."] + param_names

            selected = select_from_list(options, "Select parameter")

            if not selected:
                click.echo("No selection made.")
                return

            if selected == "[New] Create new parameter...":
                # Create new parameter
                cls._create_new_parameter(aws_cmd)
            else:
                # Show parameter and offer actions
                cls._parameter_actions(selected, aws_cmd)

        except json.JSONDecodeError:
            click.echo("Error: Failed to parse AWS response.")
        except Exception as e:
            click.echo(f"Error: {e}")

    @classmethod
    def _create_new_parameter(cls, aws_cmd):
        """Create a new parameter interactively."""
        name = click.prompt("Parameter name (e.g., /my/secret)")
        if not name:
            click.echo("Operation cancelled.")
            return

        value = click.prompt("Parameter value", hide_input=True)
        if not value:
            click.echo("Operation cancelled.")
            return

        cls._put_parameter(name, value, aws_cmd)

    @classmethod
    def _parameter_actions(cls, name, aws_cmd):
        """Show parameter value and offer actions."""
        # First, get and display the parameter
        try:
            result = subprocess.run(
                aws_cmd([
                    "get-parameter",
                    "--name", name,
                    "--with-decryption",
                    "--output", "json"
                ]),
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                click.echo(f"Error: {result.stderr}")
                return

            response = json.loads(result.stdout)
            param = response.get("Parameter", {})
            current_value = param.get("Value", "")
            param_type = param.get("Type", "")
            last_modified = param.get("LastModifiedDate", "")

            click.echo()
            click.echo(f"Name: {name}")
            click.echo(f"Type: {param_type}")
            if last_modified:
                click.echo(f"Last Modified: {last_modified}")
            click.echo("-" * 40)
            click.echo(current_value)
            click.echo("-" * 40)
            click.echo()

            # Offer actions
            actions = [
                "Copy value (print only)",
                "Update value",
                "Delete parameter",
                "Cancel"
            ]

            selected = select_from_list(actions, "Select action")

            if selected == "Update value":
                new_value = click.prompt("New value", hide_input=True)
                if new_value:
                    cls._put_parameter(name, new_value, aws_cmd)
            elif selected == "Delete parameter":
                cls._delete_parameter(name, aws_cmd)
            elif selected == "Copy value (print only)":
                click.echo(current_value)
            else:
                click.echo("Operation cancelled.")

        except json.JSONDecodeError:
            click.echo("Error: Failed to parse AWS response.")
        except Exception as e:
            click.echo(f"Error: {e}")
