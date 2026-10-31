#!/usr/bin/env python3

import subprocess

import click
from toast import ui
from toast.plugins.base_plugin import BasePlugin
from toast.plugins.utils import run_command, select_from_list


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
        return click.argument("context", required=False)(func)

    @classmethod
    def execute(cls, context=None, **kwargs):
        if context:
            run_command(["kubectl", "config", "use-context", context])
            ui.success(f"Switched to Kubernetes context: {context}")
            return

        result = run_command(
            ["kubectl", "config", "get-contexts", "-o=name"],
        )
        contexts = sorted(result.stdout.splitlines())
        contexts.append("[New...]")
        if len(contexts) > 1:
            contexts.append("[Del...]")

        current = subprocess.run(["kubectl", "config", "current-context"], capture_output=True, text=True).stdout.strip()
        selected_ctx = select_from_list(contexts, "Select a Kubernetes context", current=current)

        if selected_ctx == "[New...]":
            region = run_command(
                ["aws", "configure", "get", "region"]
            )
            region = region.stdout.strip()
            if not region:
                raise click.ClickException("No AWS region is set. Run: toast region")

            result = run_command(
                [
                    "aws",
                    "eks",
                    "list-clusters",
                    "--query",
                    "clusters",
                    "--region",
                    region,
                    "--output",
                    "text",
                ],
            )
            clusters = sorted(result.stdout.split())
            if not clusters:
                ui.warning("No EKS clusters found.")
                return

            selected_cluster = select_from_list(clusters, "Select an EKS cluster")

            if selected_cluster:
                run_command(
                    [
                        "aws",
                        "eks",
                        "update-kubeconfig",
                        "--name",
                        selected_cluster,
                        "--alias",
                        selected_cluster,
                        "--region",
                        region,
                    ]
                )
                ui.success(f"Updated kubeconfig for {selected_cluster}")
            else:
                ui.muted("No cluster selected.")
        elif selected_ctx == "[Del...]":
            delete_contexts = [
                ctx for ctx in contexts if ctx not in ("[New...]", "[Del...]")
            ]
            delete_contexts.append("[All...]")
            selected_to_delete = select_from_list(
                delete_contexts, "Select a context to delete"
            )
            if selected_to_delete == "[All...]":
                run_command(["kubectl", "config", "unset", "contexts"])
                ui.success("Deleted all Kubernetes contexts.")
            elif selected_to_delete:
                run_command(
                    ["kubectl", "config", "delete-context", selected_to_delete]
                )
                ui.success(f"Deleted Kubernetes context: {selected_to_delete}")
            else:
                ui.muted("No context selected for deletion.")
        elif selected_ctx:
            run_command(["kubectl", "config", "use-context", selected_ctx])
            ui.success(f"Switched to Kubernetes context: {selected_ctx}")
        else:
            ui.muted("No context selected.")
