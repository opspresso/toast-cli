#!/usr/bin/env python3

import click
import os
import shutil
import re
from urllib.parse import urlsplit
from rich.console import Console
from toast.plugins.base_plugin import BasePlugin
from toast.plugins.utils import run_command

console = Console()


def get_github_host():
    """Read GITHUB_HOST from .toast-config file or extract from path."""
    current_path = os.getcwd()

    # First, try to extract host from the workspace path pattern
    # Matches: /Users/user/workspace/{github-host}/{org} or /workspace/{github-host}/{org}
    pattern = r"^(.*)/workspace/([^/]+)/([^/]+)"
    match = re.match(pattern, current_path)

    default_host = "github.com"

    if match:
        default_host = match.group(2)

    config_locations = []

    if match:
        # If in org directory, check org-specific config first
        org_dir = os.path.join(
            match.group(1), "workspace", match.group(2), match.group(3)
        )
        config_locations.append(os.path.join(org_dir, ".toast-config"))

    # Add current directory config
    config_locations.append(os.path.join(current_path, ".toast-config"))

    for config_file in config_locations:
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GITHUB_HOST="):
                            host = line.split("=", 1)[1].strip()
                            if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", host):
                                raise click.ClickException(f"Invalid GITHUB_HOST in {config_file}")
                            return host
            except OSError as e:
                raise click.ClickException(f"Could not read {config_file}: {e}") from e

    return default_host


def sanitize_repo_name(repo_name):
    """Build a local clone directory name from a remote repository name."""
    return re.sub(r"[^A-Za-z0-9_.-]", "", repo_name or "").strip(".-") or "repo"


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
        aliases = {"cl": "clone", "b": "branch", "p": "pull", "ps": "push"}
        command = aliases.get(command, command)
        if command not in ("clone", "rm", "branch", "pull", "push"):
            raise click.UsageError(f"Unknown git command: {command}")
        if target is not None and command != "clone":
            raise click.UsageError("--target requires clone")
        if branch is not None and command != "branch":
            raise click.UsageError("--branch requires branch")
        if rebase and command != "pull":
            raise click.UsageError("--rebase requires pull")
        if mirror and command != "push":
            raise click.UsageError("--mirror requires push")

        current_path = os.getcwd()
        match = re.fullmatch(r".*/workspace/([^/]+)/(.+)", current_path)
        if not match:
            raise click.ClickException(
                "Current directory must be in ~/workspace/{git-host}/{namespace}"
            )
        namespace = match.group(2)

        if command == "clone":
            repo_url = None
            if repo_name.startswith(("https://", "http://", "ssh://", "git://")):
                repo_url = repo_name
                parsed = urlsplit(repo_url)
                if not parsed.hostname or not parsed.path.rstrip("/"):
                    raise click.UsageError("Clone URL must include a host and repository path")
                repo_name = parsed.path.rstrip("/").rsplit("/", 1)[-1]
            elif re.match(r"^[^/@:]+@[^/:]+:.+", repo_name):
                repo_url = repo_name
                repo_name = repo_url.split(":", 1)[1].rstrip("/").rsplit("/", 1)[-1]
            if repo_name.endswith(".git"):
                repo_name = repo_name[:-4]
            repo_name = sanitize_repo_name(repo_name)
            target_path = os.path.abspath(os.path.join(current_path, target or repo_name))
            if os.path.lexists(target_path):
                raise click.ClickException(f"Target directory '{target or repo_name}' already exists")
            if repo_url is None:
                repo_url = f"git@{get_github_host()}:{namespace}/{repo_name}.git"
            console.print(f"Cloning {repo_name} into {target_path}...", style="cyan", markup=False)
            run_command(["git", "clone", repo_url, target_path])
            console.print(f"✓ Successfully cloned {repo_name} to {target_path}", style="bold green", markup=False)
            return

        # Never rewrite the name of an existing repository: it could select a
        # different directory, especially for destructive operations.
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", repo_name):
            raise click.UsageError("Repository must be a directory name, without paths or special characters")
        repo_path = os.path.join(current_path, repo_name)
        if not os.path.isdir(repo_path) or os.path.islink(repo_path):
            raise click.ClickException(f"Repository directory '{repo_name}' does not exist or is a symlink")
        is_worktree = os.path.exists(os.path.join(repo_path, ".git"))
        is_bare = all(os.path.exists(os.path.join(repo_path, part)) for part in ("HEAD", "objects", "refs"))
        if not (is_worktree or is_bare):
            raise click.ClickException(f"'{repo_name}' is not a Git repository")

        if command == "rm":
            shutil.rmtree(repo_path)
            console.print(f"✓ Successfully removed {repo_path}", style="bold green", markup=False)
            return
        if command == "branch":
            if not branch:
                raise click.UsageError("Branch name is required (--branch)")
            args = ["git", "checkout", "-b", branch]
        elif command == "pull":
            args = ["git", "pull"] + (["--rebase"] if rebase else [])
        elif mirror:
            # Push directly to the destination, preserving existing remotes.
            repo_url = f"git@{get_github_host()}:{namespace}/{repo_name}.git"
            args = ["git", "push", "--mirror", repo_url]
        else:
            args = ["git", "push"]
        run_command(args, cwd=repo_path)
        console.print(f"✓ Successfully completed {command} for {repo_name}", style="bold green", markup=False)
