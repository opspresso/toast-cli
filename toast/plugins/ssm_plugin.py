#!/usr/bin/env python3

import click
import subprocess
import json
from rich.console import Console
from toast.plugins.base_plugin import BasePlugin

console = Console()
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
            console.print(f"✗ Error: AWS CLI not found. Please install it to use this feature.", style="bold red")
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
                console.print(f"Unknown command: {command}")
                console.print()
                cls._show_usage()

    @classmethod
    def _show_usage(cls):
        """Show usage information."""
        console.print("Usage: toast ssm <command> [args...]")
        console.print()
        console.print("Commands:")
        console.print("  (none)                    - Interactive mode: browse and select parameters")
        console.print("  ls [path]                 - List parameters (optionally filter by path)")
        console.print("  g|get <name>              - Get parameter value (decrypted)")
        console.print("  p|put <name> <value>      - Put parameter as SecureString")
        console.print("  d|delete|rm <name>        - Delete parameter")
        console.print()
        console.print("Options:")
        console.print("  -r, --region <region>     - Specify AWS region")
        console.print()
        console.print("Examples:")
        console.print("  toast ssm                           # Interactive browse")
        console.print("  toast ssm ls /toast/                # List parameters under /toast/")
        console.print("  toast ssm get /my/param             # Get parameter value")
        console.print("  toast ssm put /my/param 'secret'    # Store as SecureString")
        console.print("  toast ssm rm /my/param              # Delete parameter")

    @classmethod
    def _get_parameter(cls, name, aws_cmd):
        """Get parameter value with decryption."""
        if not name:
            console.print(f"✗ Error: Parameter name is required.", style="bold red")
            console.print("Usage: toast ssm get <name>")
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
                    console.print(f"✗ Error: Parameter '{name}' not found.", style="bold red")
                else:
                    console.print(f"✗ Error: {result.stderr}", style="bold red")
                return

            response = json.loads(result.stdout)
            param = response.get("Parameter", {})
            value = param.get("Value", "")
            param_type = param.get("Type", "")
            last_modified = param.get("LastModifiedDate", "")

            console.print(f"Name: {name}")
            console.print(f"Type: {param_type}")
            if last_modified:
                console.print(f"Last Modified: {last_modified}")
            console.print("-" * 40)
            console.print(value)

        except json.JSONDecodeError:
            console.print(f"✗ Error: Failed to parse AWS response.", style="bold red")
        except Exception as e:
            console.print(f"✗ Error: {e}", style="bold red")

    @classmethod
    def _put_parameter(cls, name, value, aws_cmd):
        """Put parameter as SecureString."""
        if not name:
            console.print(f"✗ Error: Parameter name is required.", style="bold red")
            console.print("Usage: toast ssm put <name> <value>")
            return

        if not value:
            console.print(f"✗ Error: Parameter value is required.", style="bold red")
            console.print("Usage: toast ssm put <name> <value>")
            return

        # Confirm before overwriting
        if not click.confirm(f"Store '{name}' as SecureString?"):
            console.print("Operation cancelled.")
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
                console.print(f"✗ Error: {result.stderr}", style="bold red")
                return

            response = json.loads(result.stdout)
            version = response.get("Version", "")
            console.print(f"✓ Successfully stored '{name}' (Version: {version})", style="bold green")

        except json.JSONDecodeError:
            console.print(f"✗ Error: Failed to parse AWS response.", style="bold red")
        except Exception as e:
            console.print(f"✗ Error: {e}", style="bold red")

    @classmethod
    def _delete_parameter(cls, name, aws_cmd):
        """Delete parameter."""
        if not name:
            console.print(f"✗ Error: Parameter name is required.", style="bold red")
            console.print("Usage: toast ssm delete <name>")
            return

        # Confirm before deleting
        if not click.confirm(f"Delete parameter '{name}'? This cannot be undone."):
            console.print("Operation cancelled.")
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
                    console.print(f"✗ Error: Parameter '{name}' not found.", style="bold red")
                else:
                    console.print(f"✗ Error: {result.stderr}", style="bold red")
                return

            console.print(f"✓ Successfully deleted '{name}'", style="bold green")

        except Exception as e:
            console.print(f"✗ Error: {e}", style="bold red")

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
                console.print(f"✗ Error: {result.stderr}", style="bold red")
                return

            response = json.loads(result.stdout)

            if path:
                parameters = response.get("Parameters", [])
            else:
                parameters = response.get("Parameters", [])

            if not parameters:
                console.print(f"No parameters found.", style="yellow")
                return

            console.print(f"\nAWS SSM Parameters{' under ' + path if path else ''}:")
            console.print("=" * 60)

            for param in parameters:
                param_name = param.get("Name", "")
                param_type = param.get("Type", "")
                last_modified = param.get("LastModifiedDate", "")

                if last_modified and not isinstance(last_modified, str):
                    from datetime import datetime
                    last_modified = datetime.fromtimestamp(last_modified).strftime("%Y-%m-%d %H:%M:%S")

                console.print(f"{param_name}")
                console.print(f"  Type: {param_type}, Modified: {last_modified}")

        except json.JSONDecodeError:
            console.print(f"✗ Error: Failed to parse AWS response.", style="bold red")
        except Exception as e:
            console.print(f"✗ Error: {e}", style="bold red")

    @classmethod
    def _interactive_mode(cls, aws_cmd):
        """Interactive mode: browse and select parameters."""
        console.print("Loading parameters from AWS SSM...")

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
                console.print(f"✗ Error: {result.stderr}", style="bold red")
                return

            response = json.loads(result.stdout)
            parameters = response.get("Parameters", [])

            if not parameters:
                console.print(f"No parameters found.", style="yellow")
                return

            # Build list for fzf
            param_names = [p.get("Name", "") for p in parameters]
            param_names.sort()

            # Add action options
            options = ["[New] Create new parameter..."] + param_names

            selected = select_from_list(options, "Select parameter")

            if not selected:
                console.print(f"No selection made.", style="yellow")
                return

            if selected == "[New] Create new parameter...":
                # Create new parameter
                cls._create_new_parameter(aws_cmd)
            else:
                # Show parameter and offer actions
                cls._parameter_actions(selected, aws_cmd)

        except json.JSONDecodeError:
            console.print(f"✗ Error: Failed to parse AWS response.", style="bold red")
        except Exception as e:
            console.print(f"✗ Error: {e}", style="bold red")

    @classmethod
    def _create_new_parameter(cls, aws_cmd):
        """Create a new parameter interactively."""
        name = click.prompt("Parameter name (e.g., /my/secret)")
        if not name:
            console.print("Operation cancelled.")
            return

        value = click.prompt("Parameter value", hide_input=True)
        if not value:
            console.print("Operation cancelled.")
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
                console.print(f"✗ Error: {result.stderr}", style="bold red")
                return

            response = json.loads(result.stdout)
            param = response.get("Parameter", {})
            current_value = param.get("Value", "")
            param_type = param.get("Type", "")
            last_modified = param.get("LastModifiedDate", "")

            console.print()
            console.print(f"Name: {name}")
            console.print(f"Type: {param_type}")
            if last_modified:
                console.print(f"Last Modified: {last_modified}")
            console.print("-" * 40)
            console.print(current_value)
            console.print("-" * 40)
            console.print()

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
                console.print(current_value)
            else:
                console.print("Operation cancelled.")

        except json.JSONDecodeError:
            console.print(f"✗ Error: Failed to parse AWS response.", style="bold red")
        except Exception as e:
            console.print(f"✗ Error: {e}", style="bold red")
