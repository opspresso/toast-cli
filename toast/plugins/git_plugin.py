#!/usr/bin/env python3

import click
import os
import subprocess
import re
from rich.console import Console
from toast.plugins.base_plugin import BasePlugin

console = Console()


def get_github_host():
    """Read GITHUB_HOST from .toast-config file or extract from path."""
    current_path = os.getcwd()

    # First, try to extract host from the workspace path pattern
    # Matches: /Users/user/workspace/{github-host}/{org} or /workspace/{github-host}/{org}
    pattern = r"^(.*)/workspace/([^/]+)/([^/]+)"
    match = re.match(pattern, current_path)

    default_host = "github.com"
    extracted_host = None

    if match:
        extracted_host = match.group(2)
        # Use extracted host as default if it looks like a GitHub host
        if "github" in extracted_host.lower() or extracted_host.endswith(".com"):
            default_host = extracted_host

    config_locations = []

    if match:
        # If in org directory, check org-specific config first
        org_dir = os.path.join(
            match.group(1), "workspace", match.group(2), match.group(3)
        )
        config_locations.append(os.path.join(org_dir, ".toast-config"))

    # Add current directory config
    config_locations.append(".toast-config")

    for config_file in config_locations:
        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GITHUB_HOST="):
                            host = line.split("=", 1)[1].strip()
                            return host
            except Exception as e:
                console.print(f"Warning: Could not read {config_file}: {e}", style="yellow")

    return default_host


def sanitize_repo_name(repo_name):
    """Sanitize repository name by removing invalid characters."""
    if not repo_name:
        return "repo"

    # Remove or replace invalid characters for repository names
    # Git repository names should only contain: letters, numbers, hyphens, underscores, dots
    # Remove: /, \, :, *, ?, ", <, >, |, and other special characters
    invalid_chars = [
        "/",
        "\\",
        ":",
        "*",
        "?",
        '"',
        "<",
        ">",
        "|",
        " ",
        "@",
        "#",
        "$",
        "%",
        "^",
        "&",
        "(",
        ")",
        "+",
        "=",
        "[",
        "]",
        "{",
        "}",
        ";",
        ",",
    ]

    sanitized = repo_name
    for char in invalid_chars:
        sanitized = sanitized.replace(char, "")

    # Remove leading/trailing dots and hyphens as they're not valid
    sanitized = sanitized.strip(".-")

    # Ensure it's not empty after sanitization
    if not sanitized:
        sanitized = "repo"

    return sanitized


class GitPlugin(BasePlugin):
    """Plugin for 'git' command - handles Git repository operations."""

    name = "git"
    help = "Manage Git repositories"

    @classmethod
    def get_arguments(cls, func):
        func = click.argument("command", required=True)(func)
        func = click.argument("repo_name", required=True)(func)
        func = click.option("--branch", "-b", help="Branch name for branch operation")(
            func
        )
        func = click.option(
            "--target", "-t", help="Target directory name for clone operation"
        )(func)
        func = click.option(
            "--rebase", "-r", is_flag=True, help="Use rebase when pulling"
        )(func)
        func = click.option(
            "--mirror",
            "-m",
            is_flag=True,
            help="Push with --mirror flag for repository migration",
        )(func)
        return func

    @classmethod
    def execute(
        cls,
        command,
        repo_name,
        branch=None,
        target=None,
        rebase=False,
        mirror=False,
        **kwargs,
    ):
        # Sanitize repository name
        original_repo_name = repo_name
        repo_name = sanitize_repo_name(repo_name)

        if original_repo_name != repo_name:
            console.print(
                f"Repository name sanitized: '{original_repo_name}' -> '{repo_name}'",
                style="yellow"
            )

        # Get the current path
        current_path = os.getcwd()

        # Check if the current path matches the expected pattern
        pattern = r"^.*/workspace/([^/]+)/([^/]+)"
        match = re.match(pattern, current_path)

        if not match:
            console.print(
                "✗ Error: Current directory must be in ~/workspace/{github-host}/{username} format",
                style="bold red"
            )
            return

        # Extract username from the path (host is handled by get_github_host())
        username = match.group(2)

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
                console.print(f"✗ Error: Target directory '{target_dir}' already exists", style="bold red")
                return

            # Clone the repository
            console.print(f"Cloning {repo_url} into {target_path}...", style="cyan")
            try:
                result = subprocess.run(
                    ["git", "clone", repo_url, target_path],
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    console.print(f"✓ Successfully cloned {repo_name} to {target_path}", style="bold green")
                else:
                    console.print(f"✗ Error cloning repository: {result.stderr}", style="bold red")
            except Exception as e:
                console.print(f"✗ Error executing git command: {e}", style="bold red")

        elif command == "rm":
            # Path to the repository
            repo_path = os.path.join(current_path, repo_name)

            # Check if the repository exists
            if not os.path.exists(repo_path):
                console.print(f"✗ Error: Repository directory '{repo_name}' does not exist", style="bold red")
                return

            try:
                # Remove the repository
                subprocess.run(["rm", "-rf", repo_path], check=True)
                console.print(f"✓ Successfully removed {repo_path}", style="bold green")
            except Exception as e:
                console.print(f"✗ Error removing repository: {e}", style="bold red")

        elif command == "branch" or command == "b":
            # Path to the repository
            repo_path = os.path.join(current_path, repo_name)

            # Check if the repository exists
            if not os.path.exists(repo_path):
                console.print(f"✗ Error: Repository directory '{repo_name}' does not exist", style="bold red")
                return

            # Check if branch name is provided
            if not branch:
                console.print("✗ Error: Branch name is required for branch command", style="bold red")
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
                    console.print(f"✓ Successfully created branch '{branch}' in {repo_name}", style="bold green")
                else:
                    console.print(f"✗ Error creating branch: {result.stderr}", style="bold red")

                # Return to the original directory
                os.chdir(current_path)
            except Exception as e:
                # Return to the original directory in case of error
                os.chdir(current_path)
                console.print(f"✗ Error executing git command: {e}", style="bold red")

        elif command == "pull" or command == "p":
            # Path to the repository
            repo_path = os.path.join(current_path, repo_name)

            # Check if the repository exists
            if not os.path.exists(repo_path):
                console.print(f"✗ Error: Repository directory '{repo_name}' does not exist", style="bold red")
                return

            try:
                # Change to the repository directory
                os.chdir(repo_path)

                # Execute git pull with or without rebase option
                console.print(f"Pulling latest changes for {repo_name}...", style="cyan")

                # Set up command with or without --rebase flag
                git_command = ["git", "pull", "--rebase"] if rebase else ["git", "pull"]

                result = subprocess.run(
                    git_command,
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    rebase_msg = "with rebase " if rebase else ""
                    console.print(
                        f"✓ Successfully pulled {rebase_msg}latest changes for {repo_name}",
                        style="bold green"
                    )
                else:
                    console.print(f"✗ Error pulling repository: {result.stderr}", style="bold red")

                # Return to the original directory
                os.chdir(current_path)
            except Exception as e:
                # Return to the original directory in case of error
                os.chdir(current_path)
                console.print(f"✗ Error executing git command: {e}", style="bold red")

        elif command == "push" or command == "ps":
            # Path to the repository
            repo_path = os.path.join(current_path, repo_name)

            # Check if the repository exists
            if not os.path.exists(repo_path):
                console.print(f"✗ Error: Repository directory '{repo_name}' does not exist", style="bold red")
                return

            try:
                # Change to the repository directory
                os.chdir(repo_path)

                if mirror:
                    # Mirror push for repository migration
                    # Get GitHub host from config or use default
                    github_host = get_github_host()

                    # Construct the repository URL using the same logic as clone
                    repo_url = f"git@{github_host}:{username}/{repo_name}.git"

                    console.print(f"Mirror pushing {repo_name} to {repo_url}...", style="cyan")

                    # Add new remote for mirror push
                    subprocess.run(
                        ["git", "remote", "remove", "mirror-origin"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )

                    result = subprocess.run(
                        ["git", "remote", "add", "mirror-origin", repo_url],
                        capture_output=True,
                        text=True,
                    )

                    if result.returncode != 0:
                        console.print(f"✗ Error adding mirror remote: {result.stderr}", style="bold red")
                        os.chdir(current_path)
                        return

                    # Execute mirror push
                    result = subprocess.run(
                        ["git", "push", "--mirror", "mirror-origin"],
                        capture_output=True,
                        text=True,
                    )

                    if result.returncode == 0:
                        console.print(f"✓ Successfully mirror pushed {repo_name}", style="bold green")
                    else:
                        console.print(f"✗ Error mirror pushing repository: {result.stderr}", style="bold red")
                else:
                    # Regular push
                    console.print(f"Pushing {repo_name}...", style="cyan")

                    result = subprocess.run(
                        ["git", "push"],
                        capture_output=True,
                        text=True,
                    )

                    if result.returncode == 0:
                        console.print(f"✓ Successfully pushed {repo_name}", style="bold green")
                    else:
                        console.print(f"✗ Error pushing repository: {result.stderr}", style="bold red")

                # Return to the original directory
                os.chdir(current_path)
            except Exception as e:
                # Return to the original directory in case of error
                os.chdir(current_path)
                console.print(f"✗ Error executing git command: {e}", style="bold red")

        else:
            console.print(f"✗ Unknown command: {command}", style="bold red")
            console.print(
                "Available commands: clone (cl), rm, branch (b), pull (p), push (ps)",
                style="yellow"
            )
