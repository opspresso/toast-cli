#!/usr/bin/env python3

import click
import os
import re
import subprocess
import json
from datetime import datetime
from toast.plugins.base_plugin import BasePlugin
from toast.plugins.utils import (
    check_aws_cli,
    get_ssm_parameter,
    compare_contents,
    show_diff,
    compute_hash,
    select_sync_action,
)


class PromptPlugin(BasePlugin):
    """Plugin for 'prompt' command - manages .prompt.md files."""

    name = "prompt"
    help = "Manage .prompt.md files"

    @classmethod
    def get_arguments(cls, func):
        func = click.argument("command", required=False)(func)
        return func

    @classmethod
    def execute(cls, command=None, **kwargs):
        # Get the current path
        current_path = os.getcwd()

        # Check if .prompt.md exists in the current directory
        local_prompt_path = os.path.join(current_path, ".prompt.md")

        # Check if the current path matches the workspace pattern
        pattern = r"^(.*/workspace/github.com/[^/]+/[^/]+).*$"
        match = re.match(pattern, current_path)

        # Handle different commands
        if command == "ls":
            # List all parameters under /toast/ in AWS SSM Parameter Store
            try:
                # Check if aws CLI is available
                result = subprocess.run(
                    ["aws", "--version"], capture_output=True, text=True
                )
                if result.returncode != 0:
                    click.echo(
                        "Error: AWS CLI not found. Please install it to use this feature."
                    )
                    return

                click.echo(
                    "Listing all .prompt.md parameters in AWS SSM Parameter Store..."
                )

                # List parameters with path /toast/local/
                result = subprocess.run(
                    [
                        "aws",
                        "ssm",
                        "get-parameters-by-path",
                        "--path",
                        "/toast/local/",
                        "--recursive",
                        "--output",
                        "json",
                    ],
                    capture_output=True,
                    text=True,
                )

                if result.returncode != 0:
                    click.echo(f"Error listing parameters: {result.stderr}")
                    return

                try:
                    response = json.loads(result.stdout)
                    parameters = response.get("Parameters", [])

                    if not parameters:
                        click.echo("No parameters found under /toast/local/ path.")
                        return

                    click.echo("\nAWS SSM Parameters:")
                    click.echo("=" * 50)

                    # Filter parameters containing prompt-md
                    prompt_params = [
                        p for p in parameters if "prompt-md" in p.get("Name", "")
                    ]

                    for param in prompt_params:
                        param_name = param.get("Name", "")
                        last_modified = param.get("LastModifiedDate", "")

                        # Format the date if it exists (it's a timestamp in AWS response)
                        if last_modified and not isinstance(last_modified, str):
                            last_modified = datetime.fromtimestamp(
                                last_modified
                            ).strftime("%Y-%m-%d %H:%M:%S")

                        click.echo(f"{param_name} (Last Modified: {last_modified})")

                except json.JSONDecodeError:
                    click.echo("Error parsing AWS SSM response.")
            except Exception as e:
                click.echo(f"Error: {e}")

        elif command == "up":
            # Upload local .prompt.md file to AWS SSM Parameter Store
            if not os.path.exists(local_prompt_path):
                click.echo("Error: .prompt.md not found in current directory.")
                return

            if not match:
                click.echo(
                    "Error: Current directory is not in a recognized workspace structure."
                )
                return

            # Extract project and org info
            project_root = match.group(1)
            project_name = os.path.basename(project_root)
            org_name = os.path.basename(os.path.dirname(project_root))

            # Create the SSM parameter path
            ssm_path = f"/toast/local/{org_name}/{project_name}/prompt-md"

            # Ask for confirmation before proceeding
            if not click.confirm(f"Upload .prompt.md to AWS SSM at {ssm_path}?"):
                click.echo("Operation cancelled.")
                return

            # Read the local .prompt.md file
            with open(local_prompt_path, "r") as file:
                content = file.read()

            # Upload to SSM as SecureString
            try:
                # Check if aws CLI is available
                result = subprocess.run(
                    ["aws", "--version"], capture_output=True, text=True
                )
                if result.returncode != 0:
                    click.echo(
                        "Error: AWS CLI not found. Please install it to use this feature."
                    )
                    return

                # Upload to SSM
                click.echo(
                    f"Uploading .prompt.md to AWS SSM Parameter Store at {ssm_path}..."
                )

                # Create a temporary file to avoid command line issues with quotes
                temp_file_path = os.path.expanduser("~/toast_temp_prompt.txt")
                with open(temp_file_path, "w") as temp_file:
                    temp_file.write(content)

                # Use AWS CLI to put the parameter
                result = subprocess.run(
                    [
                        "aws",
                        "ssm",
                        "put-parameter",
                        "--name",
                        ssm_path,
                        "--type",
                        "SecureString",
                        "--value",
                        "file://" + temp_file_path,
                        "--overwrite",
                    ],
                    capture_output=True,
                    text=True,
                )

                # Remove the temporary file
                os.remove(temp_file_path)

                if result.returncode == 0:
                    click.echo(
                        f"Successfully uploaded .prompt.md to AWS SSM at {ssm_path}"
                    )
                else:
                    click.echo(f"Error uploading to AWS SSM: {result.stderr}")
            except Exception as e:
                click.echo(f"Error: {e}")

        elif command == "down" or command == "dn":
            # Download .prompt.md file from AWS SSM Parameter Store
            if not match:
                click.echo(
                    "Error: Current directory is not in a recognized workspace structure."
                )
                return

            # Extract project and org info
            project_root = match.group(1)
            project_name = os.path.basename(project_root)
            org_name = os.path.basename(os.path.dirname(project_root))

            # Create the SSM parameter path
            ssm_path = f"/toast/local/{org_name}/{project_name}/prompt-md"

            # Ask for confirmation before proceeding
            overwrite_msg = (
                " (will overwrite existing file)"
                if os.path.exists(local_prompt_path)
                else ""
            )
            if not click.confirm(
                f"Download .prompt.md from AWS SSM at {ssm_path}{overwrite_msg}?"
            ):
                click.echo("Operation cancelled.")
                return

            # Download from SSM
            try:
                # Check if aws CLI is available
                result = subprocess.run(
                    ["aws", "--version"], capture_output=True, text=True
                )
                if result.returncode != 0:
                    click.echo(
                        "Error: AWS CLI not found. Please install it to use this feature."
                    )
                    return

                # Try to get the parameter
                click.echo(f"Downloading from AWS SSM Parameter Store at {ssm_path}...")
                result = subprocess.run(
                    [
                        "aws",
                        "ssm",
                        "get-parameter",
                        "--name",
                        ssm_path,
                        "--with-decryption",
                        "--output",
                        "json",
                    ],
                    capture_output=True,
                    text=True,
                )

                if result.returncode != 0:
                    click.echo(
                        f"Error: Parameter not found in AWS SSM or access denied."
                    )
                    return

                # Parse the JSON response
                try:
                    response = json.loads(result.stdout)
                    parameter_value = response.get("Parameter", {}).get("Value", "")

                    if not parameter_value:
                        click.echo("Error: Retrieved parameter has no value.")
                        return

                    # Write to local .prompt.md file
                    with open(local_prompt_path, "w") as file:
                        file.write(parameter_value)

                    click.echo(
                        f"Successfully downloaded .prompt.md from AWS SSM and saved to {local_prompt_path}"
                    )
                except json.JSONDecodeError:
                    click.echo("Error parsing AWS SSM response.")
            except Exception as e:
                click.echo(f"Error: {e}")

        elif command == "sync":
            # Compare local and SSM, then choose action
            if not match:
                click.echo(
                    "Error: Current directory is not in a recognized workspace structure."
                )
                return

            if not check_aws_cli():
                click.echo(
                    "Error: AWS CLI not found. Please install it to use this feature."
                )
                return

            # Extract project and org info
            project_root = match.group(1)
            project_name = os.path.basename(project_root)
            org_name = os.path.basename(os.path.dirname(project_root))
            ssm_path = f"/toast/local/{org_name}/{project_name}/prompt-md"

            click.echo(f"Comparing .prompt.md with SSM: {ssm_path}")
            click.echo("=" * 60)

            # Get local content
            local_content = None
            if os.path.exists(local_prompt_path):
                with open(local_prompt_path, "r") as file:
                    local_content = file.read()

            # Get SSM content
            remote_content, last_modified, error = get_ssm_parameter(ssm_path)
            if error:
                click.echo(f"Error fetching SSM parameter: {error}")
                return

            # Compare
            status = compare_contents(local_content, remote_content)

            # Display status
            local_hash = compute_hash(local_content) if local_content else "-"
            remote_hash = compute_hash(remote_content) if remote_content else "-"

            click.echo(f"Local:  {local_hash if local_content else '(not found)'}")
            click.echo(f"SSM:    {remote_hash if remote_content else '(not found)'}")

            if last_modified:
                click.echo(f"SSM Last Modified: {last_modified}")

            click.echo("")

            if status == "both_missing":
                click.echo("Neither local file nor SSM parameter exists.")
                return

            if status == "identical":
                click.echo("✓ Files are identical. No action needed.")
                return

            # Show diff if both exist and different
            if status == "different":
                click.echo("Differences found:")
                click.echo("-" * 40)
                diff_lines = show_diff(local_content, remote_content)
                for line in diff_lines[:50]:  # Limit output
                    if line.startswith("+") and not line.startswith("+++"):
                        click.secho(line.rstrip(), fg="green")
                    elif line.startswith("-") and not line.startswith("---"):
                        click.secho(line.rstrip(), fg="red")
                    else:
                        click.echo(line.rstrip())
                if len(diff_lines) > 50:
                    click.echo(f"... ({len(diff_lines) - 50} more lines)")
                click.echo("-" * 40)
            elif status == "local_only":
                click.echo("Local file exists, but SSM parameter does not.")
            elif status == "remote_only":
                click.echo("SSM parameter exists, but local file does not.")

            click.echo("")

            # Let user choose action
            action = select_sync_action(status, ".prompt.md")

            if action == "upload":
                # Upload local to SSM
                click.echo(f"Uploading .prompt.md to SSM...")
                temp_file_path = os.path.expanduser("~/toast_temp_prompt.txt")
                with open(temp_file_path, "w") as temp_file:
                    temp_file.write(local_content)

                result = subprocess.run(
                    [
                        "aws",
                        "ssm",
                        "put-parameter",
                        "--name",
                        ssm_path,
                        "--type",
                        "SecureString",
                        "--value",
                        "file://" + temp_file_path,
                        "--overwrite",
                    ],
                    capture_output=True,
                    text=True,
                )
                os.remove(temp_file_path)

                if result.returncode == 0:
                    click.echo(f"✓ Successfully uploaded to {ssm_path}")
                else:
                    click.echo(f"Error uploading: {result.stderr}")

            elif action == "download":
                # Download SSM to local
                click.echo(f"Downloading from SSM to .prompt.md...")
                with open(local_prompt_path, "w") as file:
                    file.write(remote_content)
                click.echo(f"✓ Successfully downloaded to {local_prompt_path}")

            else:
                click.echo("Operation cancelled.")

        else:
            # Default behavior without a command - suggest using subcommands
            if os.path.exists(local_prompt_path):
                click.echo(f"Found .prompt.md in current directory: {local_prompt_path}")
                click.echo("Use 'toast prompt up' to upload to AWS SSM")
            else:
                click.echo(".prompt.md not found in current directory.")

                if match:
                    # Extract the project root path
                    project_root = match.group(1)
                    project_name = os.path.basename(project_root)
                    org_name = os.path.basename(os.path.dirname(project_root))

                    # Create the SSM parameter path
                    ssm_path = f"/toast/local/{org_name}/{project_name}/prompt-md"
                    click.echo(
                        f"Use 'toast prompt down' to check if {ssm_path} exists in AWS SSM"
                    )
                else:
                    click.echo(
                        "Current directory is not in a recognized workspace structure."
                    )
