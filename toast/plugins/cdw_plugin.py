#!/usr/bin/env python3

import os

from toast import ui
from toast.plugins.base_plugin import BasePlugin


class CdwPlugin(BasePlugin):
    """Plugin for 'cdw' command - helps navigate to workspace directories."""

    name = "cdw"
    help = "Navigate to a workspace directory"
    category = "Workspace"
    examples = (
        ('cd "$(toast cdw)"', "Go to a repository"),
    )

    @classmethod
    def execute(cls, **kwargs):
        workspace_dir = os.path.expanduser("~/workspace")
        os.makedirs(workspace_dir, exist_ok=True)

        # Prune repository internals while supporting nested GitLab namespaces.
        directories = []
        for root, children, _ in os.walk(workspace_dir):
            children[:] = sorted(name for name in children if not name.startswith("."))
            if root != workspace_dir:
                directories.append(root)
            if os.path.exists(os.path.join(root, ".git")):
                children.clear()
        directories.sort()

        if not directories:
            github_dir = os.path.join(workspace_dir, "github.com")
            os.makedirs(github_dir)
            ui.success(f"Created {github_dir}")
            ui.muted("Toast expects ~/workspace/{git-host}/{org}/{project}, for example:")
            ui.muted("  ~/workspace/github.com/opspresso/toast-cli")
            return

        selected_dir = ui.choose(directories, "Select a directory", label=lambda path: os.path.relpath(path, workspace_dir))

        if selected_dir:
            ui.result(selected_dir)
        else:
            ui.cancelled()
