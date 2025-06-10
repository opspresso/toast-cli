#!/usr/bin/env python3

import click
import os
import subprocess
import re
from toast.plugins.base_plugin import BasePlugin


def get_github_host():
    """Read GITHUB_HOST from .toast-config file or return default."""
    config_file = ".toast-config"
    default_host = "github.com"

    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GITHUB_HOST="):
                        host = line.split("=", 1)[1]
                        return host
        except Exception as e:
            click.echo(f"Warning: Could not read {config_file}: {e}")

    return default_host


class GitPlugin(BasePlugin):
    """Plugin for 'git' command - handles Git repository operations."""

    name = "git"
    help = "Manage Git repositories"

    @classmethod
    def get_arguments(cls, func):
        func = click.argument("repo_name", required=True)(func)
        func = click.argument("command", required=True)(func)
        func = click.option("--branch", "-b", help="Branch name for branch operation")(
            func
        )
        func = click.option(
            "--target", "-t", help="Target directory name for clone operation"
        )(func)
        func = click.option(
            "--rebase", "-r", is_flag=True, help="Use rebase when pulling"
        )(func)
        return func

    @classmethod
    def execute(
        cls, repo_name, command, branch=None, target=None, rebase=False, **kwargs
    ):
        # Get the current path
        current_path = os.getcwd()

        # Check if the current path matches the expected pattern
        pattern = r"^.*/workspace/github.com/([^/]+)$"
        match = re.match(pattern, current_path)

        if not match:
            click.echo(
                "Error: Current directory must be in ~/workspace/github.com/{username} format"
            )
            return

        # Extract username from the path
        username = match.group(1)

        if command == "clone" or command == "cl":
            # Determine the target directory name
            target_dir = target if target else repo_name

            # Get GitHub host from config or use default
            github_host = get_github_host()

            # Construct the repository URL
            repo_url = f"git@{github_host}:{username}/{repo_name}.git"

            # Target path in the current directory
            target_path = os.path.join(current_path, target_dir)

            # Check if the target directory already exists
            if os.path.exists(target_path):
                click.echo(f"Error: Target directory '{target_dir}' already exists")
                return

            # Clone the repository
            click.echo(f"Cloning {repo_url} into {target_path}...")
            try:
                result = subprocess.run(
                    ["git", "clone", repo_url, target_path],
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    click.echo(f"Successfully cloned {repo_name} to {target_path}")
                else:
                    click.echo(f"Error cloning repository: {result.stderr}")
            except Exception as e:
                click.echo(f"Error executing git command: {e}")

        elif command == "rm":
            # Path to the repository
            repo_path = os.path.join(current_path, repo_name)

            # Check if the repository exists
            if not os.path.exists(repo_path):
                click.echo(f"Error: Repository directory '{repo_name}' does not exist")
                return

            try:
                # Remove the repository
                subprocess.run(["rm", "-rf", repo_path], check=True)
                click.echo(f"Successfully removed {repo_path}")
            except Exception as e:
                click.echo(f"Error removing repository: {e}")

        elif command == "branch" or command == "b":
            # Path to the repository
            repo_path = os.path.join(current_path, repo_name)

            # Check if the repository exists
            if not os.path.exists(repo_path):
                click.echo(f"Error: Repository directory '{repo_name}' does not exist")
                return

            # Check if branch name is provided
            if not branch:
                click.echo("Error: Branch name is required for branch command")
                return

            try:
                # Change to the repository directory
                os.chdir(repo_path)

                # Create the new branch
                result = subprocess.run(
                    ["git", "checkout", "-b", branch],
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    click.echo(f"Successfully created branch '{branch}' in {repo_name}")
                else:
                    click.echo(f"Error creating branch: {result.stderr}")

                # Return to the original directory
                os.chdir(current_path)
            except Exception as e:
                # Return to the original directory in case of error
                os.chdir(current_path)
                click.echo(f"Error executing git command: {e}")

        elif command == "pull" or command == "p":
            # Path to the repository
            repo_path = os.path.join(current_path, repo_name)

            # Check if the repository exists
            if not os.path.exists(repo_path):
                click.echo(f"Error: Repository directory '{repo_name}' does not exist")
                return

            try:
                # Change to the repository directory
                os.chdir(repo_path)

                # Execute git pull with or without rebase option
                click.echo(f"Pulling latest changes for {repo_name}...")

                # Set up command with or without --rebase flag
                git_command = ["git", "pull", "--rebase"] if rebase else ["git", "pull"]

                result = subprocess.run(
                    git_command,
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    rebase_msg = "with rebase " if rebase else ""
                    click.echo(
                        f"Successfully pulled {rebase_msg}latest changes for {repo_name}"
                    )
                else:
                    click.echo(f"Error pulling repository: {result.stderr}")

                # Return to the original directory
                os.chdir(current_path)
            except Exception as e:
                # Return to the original directory in case of error
                os.chdir(current_path)
                click.echo(f"Error executing git command: {e}")

        else:
            click.echo(f"Unknown command: {command}")
            click.echo("Available commands: clone, rm, branch, pull")
