#!/usr/bin/env python3

from rich.console import Console
from toast.plugins.base_plugin import BasePlugin
from toast.plugins.utils import run_command, select_from_list

console = Console()


class CtxPlugin(BasePlugin):
    """Plugin for 'ctx' command - manages Kubernetes contexts."""

    name = "ctx"
    help = "Manage Kubernetes contexts"

    @classmethod
    def execute(cls, **kwargs):
        result = run_command(
            ["kubectl", "config", "get-contexts", "-o=name"],
        )
        contexts = sorted(result.stdout.splitlines())
        contexts.append("[New...]")
        if len(contexts) > 1:
            contexts.append("[Del...]")

        selected_ctx = select_from_list(contexts, "Select a Kubernetes context")

        if selected_ctx == "[New...]":
            region = run_command(
                ["aws", "configure", "get", "region"]
            )
            region = region.stdout.strip()

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
                console.print("No EKS clusters found.", style="yellow")
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
                console.print(f"✓ Updated kubeconfig for {selected_cluster}", style="bold green")
            else:
                console.print("No cluster selected.", style="yellow")
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
                console.print("✓ Deleted all Kubernetes contexts.", style="bold green")
            elif selected_to_delete:
                run_command(
                    ["kubectl", "config", "delete-context", selected_to_delete]
                )
                console.print(f"✓ Deleted Kubernetes context: {selected_to_delete}", style="bold green")
            else:
                console.print("No context selected for deletion.", style="yellow")
        elif selected_ctx:
            run_command(["kubectl", "config", "use-context", selected_ctx])
            console.print(f"✓ Switched to Kubernetes context: {selected_ctx}", style="bold green")
        else:
            console.print("No context selected.", style="yellow")
