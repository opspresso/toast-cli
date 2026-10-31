#!/usr/bin/env python3

import click
import importlib
import inspect
import os
import pkgutil
import sys
from typing import List, Type
from toast import ui
from toast.helpers import CustomHelpGroup, get_version


def discover_and_load_plugins(
    plugins_package_name: str = "toast.plugins",
) -> List[Type]:
    """
    Dynamically discover and load all plugin classes from the plugins package.

    Args:
        plugins_package_name: Name of the plugins package to search

    Returns:
        List of plugin classes that extend BasePlugin
    """
    from toast.plugins.base_plugin import BasePlugin

    discovered_plugins = []

    try:
        # Import the plugins package
        plugins_package = importlib.import_module(plugins_package_name)
        plugins_path = os.path.dirname(plugins_package.__file__)

        # Discover all modules in the plugins package
        for _, name, _ in pkgutil.iter_modules([plugins_path]):
            # Skip the base_plugin module and __init__.py
            if name in ("base_plugin", "__init__", "utils"):
                continue

            # Import the module
            module_name = f"{plugins_package_name}.{name}"
            try:
                module = importlib.import_module(module_name)

                # Find all classes in the module that are subclasses of BasePlugin
                for _, item in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(item, BasePlugin)
                        and item is not BasePlugin
                        and item.__module__ == module_name
                    ):
                        discovered_plugins.append(item)
            except ImportError as e:
                raise click.ClickException(f"Error loading plugin module {module_name}: {e}") from e

    except ImportError as e:
        raise click.ClickException(f"Error loading plugins package {plugins_package_name}: {e}") from e

    return discovered_plugins


def show_version(ctx, param, value):
    if value and not ctx.resilient_parsing:
        ui.result(f"toast-cli {get_version()}")
        ctx.exit()


@click.group(cls=CustomHelpGroup, invoke_without_command=True, context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--version", is_flag=True, is_eager=True, expose_value=False, callback=show_version, help="Show the version and exit.")
@click.pass_context
def toast_cli(ctx):
    """
    Daily commands for AWS, Kubernetes, Git and your workspace.
    """
    if ctx.invoked_subcommand is None:
        ui.result(ctx.get_help())


@toast_cli.command()
def version():
    """Show the version."""
    ui.result(f"toast-cli {get_version()}")


def main():
    # Discover and load all plugins
    try:
        plugins = discover_and_load_plugins()
        if not plugins:
            raise click.ClickException("No plugins were discovered")
        for plugin_class in plugins:
            plugin_class.register(toast_cli)
    except (click.ClickException, ValueError) as e:
        ui.error(str(e))
        sys.exit(1)

    # Run the CLI
    toast_cli()


if __name__ == "__main__":
    main()
