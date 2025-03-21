#!/usr/bin/env python3

import click
import subprocess
from toast.plugins.base_plugin import BasePlugin
from toast.plugins.utils import select_from_list

class CtxPlugin(BasePlugin):
    """Plugin for 'ctx' command - manages Kubernetes contexts."""

    name = "ctx"
    help = "Manage Kubernetes contexts"

    @classmethod
    def execute(cls, **kwargs):
        result = subprocess.run(["kubectl", "config", "get-contexts", "-o=name"], capture_output=True, text=True)
        if result.returncode != 0:
            click.echo("Error fetching Kubernetes contexts. Is kubectl configured correctly?")
            return

        contexts = sorted(result.stdout.splitlines())
        contexts.append("[New...]")
        if len(contexts) > 1:
            contexts.append("[Del...]")

        selected_ctx = select_from_list(contexts, "Select a Kubernetes context")

        if selected_ctx == "[New...]":
            region = subprocess.run(["aws", "configure", "get", "region"], capture_output=True, text=True)
            if result.returncode != 0:
                click.echo("Error fetching AWS region.")
                return

            region = region.stdout.strip()

            result = subprocess.run(["aws", "eks", "list-clusters", "--query", "clusters", "--region", region, "--output", "text"], capture_output=True, text=True)
            if result.returncode != 0:
                click.echo("Error fetching EKS clusters.")
                return

            clusters = sorted(result.stdout.split())
            if not clusters:
                click.echo("No EKS clusters found.")
                return

            selected_cluster = select_from_list(clusters, "Select an EKS cluster")

            if selected_cluster:
                subprocess.run(["aws", "eks", "update-kubeconfig", "--name", selected_cluster, "--alias", selected_cluster, "--region", region])
                click.echo(f"Updated kubeconfig for {selected_cluster}")
            else:
                click.echo("No cluster selected.")
        elif selected_ctx == "[Del...]":
            delete_contexts = [ctx for ctx in contexts if ctx not in ("[New...]", "[Del...]")]
            delete_contexts.append("[All...]")
            selected_to_delete = select_from_list(delete_contexts, "Select a context to delete")
            if selected_to_delete == "[All...]":
                subprocess.run(["kubectl", "config", "unset", "contexts"])
                click.echo("Deleted all Kubernetes contexts.")
            elif selected_to_delete:
                subprocess.run(["kubectl", "config", "delete-context", selected_to_delete])
                click.echo(f"Deleted Kubernetes context: {selected_to_delete}")
            else:
                click.echo("No context selected for deletion.")
        elif selected_ctx:
            subprocess.run(["kubectl", "config", "use-context", selected_ctx])
            click.echo(f"Switched to Kubernetes context: {selected_ctx}")
        else:
            click.echo("No context selected.")
