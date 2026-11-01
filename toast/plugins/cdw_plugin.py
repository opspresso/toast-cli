#!/usr/bin/env python3

import os
import shlex

import click

from toast import ui
from toast.plugins.base_plugin import BasePlugin


def list_directories(workspace_dir):
    """Return namespace and repository directories below WORKSPACE_DIR, sorted.

    The walk skips hidden directories and stops at a repository root, which has a
    `.git` directory or, for a worktree or submodule, a `.git` file. Nested GitLab
    namespaces are kept.
    """
    directories = []
    for root, children, _ in os.walk(workspace_dir):
        children[:] = sorted(name for name in children if not name.startswith("."))
        if root != workspace_dir:
            directories.append(root)
        if os.path.exists(os.path.join(root, ".git")):
            children.clear()
    return sorted(directories)


def find_current(workspace_dir, directories):
    """Return the directory that holds the working directory, or None outside them."""
    try:
        here = os.path.realpath(os.getcwd())
    except FileNotFoundError:  # The working directory was removed.
        return None
    relative = os.path.relpath(here, os.path.realpath(workspace_dir))
    if relative == os.curdir or relative.startswith(os.pardir + os.sep) or relative == os.pardir:
        return None
    by_relative = {os.path.relpath(path, workspace_dir): path for path in directories}
    while relative:
        if relative in by_relative:
            return by_relative[relative]
        relative = os.path.dirname(relative)
    return None


def match(query, directories, relative):
    """Return the directories QUERY names, best first.

    An exact relative path wins. Next come paths whose trailing components equal
    QUERY, such as `toast-cli` or `opspresso/toast-cli`. Otherwise every
    directory that `ui.fuzzy` matches is returned in rank order.
    """
    query = query.strip().rstrip("/")
    exact = [path for path in directories if relative(path) == query]
    if exact:
        return exact
    suffix = [path for path in directories if relative(path).endswith("/" + query)]
    if suffix:
        return suffix
    ranked = []
    for path in directories:
        found = ui.fuzzy(query, relative(path))
        if found:
            ranked.append((found[0], len(relative(path)), relative(path), path))
    return [path for *_, path in sorted(ranked)]


class CdwPlugin(BasePlugin):
    """Plugin for 'cdw' command - helps navigate to workspace directories."""

    name = "cdw"
    help = (
        "Navigate to a workspace directory\n\n"
        "Print the absolute path of a directory below ~/workspace. Without QUERY, pick from all "
        "namespaces and repositories; the one that holds the working directory is marked current. "
        "QUERY is an exact relative path, its last components such as a repository name, or letters "
        "to filter by. One match is printed without a picker. Several matches open a filtered picker; "
        "without a terminal the command fails and lists the paths to name instead."
    )
    category = "Workspace"
    examples = (
        ("toast cdw", "Pick a directory; the current repository is marked"),
        ("toast cdw toast-cli", "Print the only match without a picker"),
        ("toast cdw github.com/acme/api", "Name the exact path when names repeat"),
        ('c() { local d; d="$(toast cdw "$@")" || return; [ -z "$d" ] || cd -- "$d"; }', "Shell function: cd only when a path is printed"),
    )

    @classmethod
    def get_arguments(cls, func):
        return click.argument("query", nargs=-1, metavar="[QUERY]")(func)

    @classmethod
    def execute(cls, query=(), **kwargs):
        workspace_dir = os.path.expanduser("~/workspace")
        os.makedirs(workspace_dir, exist_ok=True)
        directories = list_directories(workspace_dir)

        if not directories:
            github_dir = os.path.join(workspace_dir, "github.com")
            os.makedirs(github_dir)
            ui.success(f"Created {github_dir}")
            ui.muted("Toast expects ~/workspace/{git-host}/{org}/{project}, for example:")
            ui.muted("  ~/workspace/github.com/opspresso/toast-cli")
            return

        def relative(path):
            return os.path.relpath(path, workspace_dir)

        query = " ".join(query).strip()
        current = find_current(workspace_dir, directories)

        if query:
            candidates = match(query, directories, relative)
            if not candidates:
                raise click.ClickException(f"No directory in {workspace_dir} matches '{query}'. Run 'toast cdw' to browse, or try fewer letters")
            title = f"Select a directory matching '{query}'"
        else:
            candidates = directories
            title = f"Select a directory in {workspace_dir}"

        if query and len(candidates) == 1:
            selected_dir = candidates[0]
        elif ui.is_interactive():
            selected_dir = ui.choose(candidates, title, current=current, label=relative)
        elif query:
            # A script cannot answer a picker, and guessing could change to the wrong repository.
            ui.muted(f"'{query}' matches {len(candidates)} directories:")
            for path in candidates:
                ui.muted(f"  {relative(path)}")
            raise click.ClickException(f"'{query}' is ambiguous. Name one path above, for example: toast cdw {shlex.quote(relative(candidates[0]))}")
        else:
            raise click.ClickException("Choosing a directory needs a terminal. Name one instead: toast cdw QUERY")

        if not selected_dir:
            ui.cancelled()
            return
        ui.fields([
            ("Workspace", workspace_dir),
            ("Current", relative(current) if current else "not in a workspace directory"),
            ("Target", relative(selected_dir)),
        ])
        ui.result(selected_dir)
