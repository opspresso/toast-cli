#!/usr/bin/env python3

import click
from toast import ui
from toast.plugins.base_plugin import BasePlugin
from toast.plugins.utils import run_command, spawn

NEW = "+ Add an EKS cluster"
DELETE = "- Delete a context"
ALL = "All contexts"


def list_contexts():
    return sorted(run_command(["kubectl", "config", "get-contexts", "-o=name"]).stdout.splitlines())


def complete_contexts(ctx, param, incomplete):
    # A completion must stay silent, so a failed kubectl offers nothing.
    try:
        result = spawn(["kubectl", "config", "get-contexts", "-o=name"])
    except click.ClickException:
        return []
    return [name for name in result.stdout.splitlines() if name.startswith(incomplete)]


class CtxPlugin(BasePlugin):
    """Plugin for 'ctx' command - manages Kubernetes contexts."""

    name = "ctx"
    help = "Manage Kubernetes contexts"
    category = "Kubernetes"
    examples = (
        ("toast ctx", "Pick a context"),
        ("toast ctx prod", "Switch to a named context"),
    )

    @classmethod
    def get_arguments(cls, func):
        return click.argument("context", required=False, shell_complete=complete_contexts)(func)

    @staticmethod
    def _use(context):
        run_command(["kubectl", "config", "use-context", context])
        ui.success(f"Switched to Kubernetes context {context}")

    @staticmethod
    def _add_cluster():
        region = run_command(["aws", "configure", "get", "region"]).stdout.strip()
        if not region:
            raise click.ClickException("No AWS region is set. Run: toast region")
        with ui.status(f"Listing EKS clusters in {region}"):
            result = run_command(["aws", "eks", "list-clusters", "--query", "clusters", "--region", region, "--output", "text"])
        clusters = sorted(result.stdout.split())
        if not clusters:
            ui.warning(f"No EKS clusters in {region}")
            return
        cluster = ui.choose(clusters, "Select an EKS cluster")
        if not cluster:
            ui.cancelled()
            return
        with ui.status(f"Updating kubeconfig for {cluster}"):
            run_command(["aws", "eks", "update-kubeconfig", "--name", cluster, "--alias", cluster, "--region", region])
        ui.success(f"Added Kubernetes context {cluster}")

    @staticmethod
    def _delete(contexts):
        selected = ui.choose(contexts + [ALL], "Select a context to delete")
        if not selected:
            ui.cancelled()
        elif selected == ALL:
            if ui.confirm(f"Delete all {len(contexts)} Kubernetes contexts?"):
                run_command(["kubectl", "config", "unset", "contexts"])
                ui.success("Deleted all Kubernetes contexts")
            else:
                ui.cancelled()
        elif ui.confirm(f"Delete Kubernetes context {selected}?"):
            run_command(["kubectl", "config", "delete-context", selected])
            ui.success(f"Deleted Kubernetes context {selected}")
        else:
            ui.cancelled()

    @classmethod
    def execute(cls, context=None, **kwargs):
        if context:
            cls._use(context)
            return

        contexts = list_contexts()
        current = spawn(["kubectl", "config", "current-context"]).stdout.strip()
        selected = ui.choose(contexts + [NEW] + ([DELETE] if contexts else []), "Select a Kubernetes context", current=current)

        if selected == NEW:
            cls._add_cluster()
        elif selected == DELETE:
            cls._delete(contexts)
        elif selected:
            cls._use(selected)
        else:
            ui.cancelled()
