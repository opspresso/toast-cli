#!/usr/bin/env python3

import click
import os
import shutil
import re
from urllib.parse import urlsplit
from toast import ui
from toast.plugins.base_plugin import BasePlugin
from toast.plugins.utils import run_command, spawn


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
                                raise click.ClickException(
                                    f"Invalid GITHUB_HOST in {config_file}. Set it to a host name such as "
                                    "github.com, or remove the line to use the workspace host"
                                )
                            return host
            except OSError as e:
                raise click.ClickException(f"Could not read {config_file}: {e}") from e

    return default_host


def sanitize_repo_name(repo_name):
    """Build a local clone directory name from a remote repository name."""
    return re.sub(r"[^A-Za-z0-9_.-]", "", repo_name or "").strip(".-") or "repo"


def redact_url(url):
    """Hide credentials in a Git URL before it is displayed.

    An HTTP user name is often a token, so it is hidden together with any password.
    An SSH user name such as git stays visible. Git itself receives the original URL.
    """
    parsed = urlsplit(url)
    if "@" not in parsed.netloc:
        return url
    userinfo, host = parsed.netloc.rsplit("@", 1)
    user, has_password, _ = userinfo.partition(":")
    if parsed.scheme in ("http", "https"):
        user = "***"
    elif has_password:
        user += ":***"
    return parsed._replace(netloc=f"{user}@{host}").geturl()


class GitPlugin(BasePlugin):
    """Plugin for 'git' command - handles Git repository operations."""

    name = "git"
    help = (
        "Manage Git repositories\n\n"
        "Run it in ~/workspace/{git-host}/{namespace}. Before it runs Git, it shows the "
        "host, namespace, absolute local path and action on stderr. Git output goes to "
        "stdout; Git progress, diagnostics and status go to stderr.\n\n"
        "push --mirror shows the remote and asks for a confirmation, because it overwrites "
        "remote branches and tags and deletes those that do not exist locally. --yes skips "
        "the confirmation of rm and push --mirror only."
    )
    category = "Workspace"
    commands = (
        ("clone", "Clone into this namespace (alias: cl)"),
        ("pull", "Pull the current branch (alias: p)"),
        ("push", "Push the current branch (alias: ps); --mirror after a confirmation"),
        ("branch", "Create and switch to --branch (alias: b)"),
        ("rm", "Remove the checkout after a confirmation"),
    )
    examples = (
        ("toast git my-repo clone", "Clone into this namespace"),
        ("toast git my-repo pull -r", "Pull with rebase"),
        ("toast git my-repo push -m", "Mirror push after a confirmation"),
        ("toast git my-repo rm", "Remove a checkout after a confirmation"),
    )

    @classmethod
    def get_arguments(cls, func):
        func = click.argument("command", required=True, shell_complete=cls.complete_command)(func)
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
            help="Push all refs with --mirror for repository migration, after a confirmation",
        )(func)
        func = click.option(
            "--yes", "-y", is_flag=True, help="Skip the confirmation of rm or push --mirror"
        )(func)
        return func

    @staticmethod
    def _confirm_remove(repo_name, repo_path):
        """Name what would be lost, because the removal cannot be undone."""
        status = spawn(["git", "status", "--short", "--branch"], cwd=repo_path)
        lines = status.stdout.splitlines()
        changed = sum(1 for line in lines if not line.startswith("##"))
        if changed:
            ui.warning(f"{repo_name} has {changed} uncommitted changes")
        if lines and "ahead" in lines[0]:
            ui.warning(f"{repo_name} has commits that are not pushed")
        return ui.confirm(f"Remove {repo_path}? This cannot be undone.")

    @staticmethod
    def _run_git(args, message, **kwargs):
        """Run Git: its stdout is the result, its stderr is about the run."""
        with ui.status(message):
            result = run_command(args, **kwargs)
        for line in result.stderr.strip().splitlines():
            ui.muted(f"  {line}")
        if result.stdout.strip():
            ui.result(result.stdout.rstrip("\n"))

    @classmethod
    def execute(
        cls,
        command,
        repo_name,
        branch=None,
        target=None,
        rebase=False,
        mirror=False,
        yes=False,
        **kwargs,
    ):
        aliases = {"cl": "clone", "b": "branch", "p": "pull", "ps": "push"}
        command = aliases.get(command, command)
        if command not in ("clone", "rm", "branch", "pull", "push"):
            raise click.UsageError(f"Unknown git command: {command}. Use clone, pull, push, branch or rm")
        if target is not None and command != "clone":
            raise click.UsageError("--target requires clone")
        if branch is not None and command != "branch":
            raise click.UsageError("--branch requires branch")
        if rebase and command != "pull":
            raise click.UsageError("--rebase requires pull")
        if mirror and command != "push":
            raise click.UsageError("--mirror requires push")
        if yes and not (command == "rm" or mirror):
            raise click.UsageError("--yes requires rm or push --mirror")

        current_path = os.getcwd()
        match = re.fullmatch(r".*/workspace/([^/]+)/(.+)", current_path)
        if not match:
            raise click.ClickException(
                f"{current_path} is not a workspace namespace directory. "
                "Change to ~/workspace/{git-host}/{namespace} first, for example "
                "cd ~/workspace/github.com/my-org"
            )
        host, namespace = match.groups()
        place = [("Host", host), ("Namespace", namespace)]

        if command == "clone":
            repo_url = None
            if repo_name.startswith(("https://", "http://", "ssh://", "git://")):
                repo_url = repo_name
                parsed = urlsplit(repo_url)
                if not parsed.hostname or not parsed.path.rstrip("/"):
                    raise click.UsageError(
                        "Clone URL must include a host and repository path, "
                        "for example https://github.com/my-org/my-repo.git"
                    )
                repo_name = parsed.path.rstrip("/").rsplit("/", 1)[-1]
            elif re.match(r"^[^/@:]+@[^/:]+:.+", repo_name):
                repo_url = repo_name
                repo_name = repo_url.split(":", 1)[1].rstrip("/").rsplit("/", 1)[-1]
            if repo_name.endswith(".git"):
                repo_name = repo_name[:-4]
            repo_name = sanitize_repo_name(repo_name)
            target_path = os.path.abspath(os.path.join(current_path, target or repo_name))
            if os.path.lexists(target_path):
                raise click.ClickException(
                    f"{target_path} already exists. Choose another directory with --target, "
                    "or use the existing checkout"
                )
            if repo_url is None:
                repo_url = f"git@{get_github_host()}:{namespace}/{repo_name}.git"
            ui.fields(place + [("Path", target_path), ("Source", redact_url(repo_url)), ("Action", "git clone")])
            cls._run_git(["git", "clone", repo_url, target_path], f"Cloning {repo_name}")
            ui.success(f"Cloned {repo_name} to {target_path}")
            return

        # Never rewrite the name of an existing repository: it could select a
        # different directory, especially for destructive operations.
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", repo_name):
            raise click.UsageError(
                f"Repository must be the name of a directory in {current_path}, "
                "without paths or special characters"
            )
        repo_path = os.path.join(current_path, repo_name)
        if os.path.islink(repo_path):
            raise click.ClickException(
                f"{repo_path} is a symlink. Run toast git in the namespace directory that holds the checkout"
            )
        if not os.path.isdir(repo_path):
            raise click.ClickException(
                f"{repo_path} does not exist. Clone it with: toast git {repo_name} clone"
            )
        is_worktree = os.path.exists(os.path.join(repo_path, ".git"))
        is_bare = all(os.path.exists(os.path.join(repo_path, part)) for part in ("HEAD", "objects", "refs"))
        if not (is_worktree or is_bare):
            raise click.ClickException(
                f"{repo_path} is not a Git repository. Check the repository name"
            )

        if command == "rm":
            ui.fields(place + [("Path", repo_path), ("Action", "remove the directory")])
            if not (yes or cls._confirm_remove(repo_name, repo_path)):
                ui.cancelled()
                return
            shutil.rmtree(repo_path)
            ui.success(f"Removed {repo_path}")
            return
        details = [("Path", repo_path)]
        if command == "branch":
            if not branch:
                raise click.UsageError("Branch name is required (--branch)")
            args = ["git", "checkout", "-b", branch]
            action = " ".join(args)
        elif command == "pull":
            args = ["git", "pull"] + (["--rebase"] if rebase else [])
            action = " ".join(args)
        elif mirror:
            # Push directly to the destination, preserving existing remotes.
            repo_url = f"git@{get_github_host()}:{namespace}/{repo_name}.git"
            args = ["git", "push", "--mirror", repo_url]
            action = "git push --mirror"
            details.append(("Remote", repo_url))
        else:
            args = ["git", "push"]
            action = "git push"
        ui.fields(place + details + [("Action", action)])
        if mirror and not (yes or ui.confirm(
            f"Mirror push to {repo_url}? This overwrites remote branches and tags "
            "and deletes remote refs that do not exist locally."
        )):
            ui.cancelled()
            return
        cls._run_git(args, f"Running {action} in {repo_name}", cwd=repo_path)
        ui.success(f"Finished {command} in {repo_name}")
