#!/usr/bin/env python3

import click
import importlib
import inspect
import os
import pkgutil
import sys
from typing import List, Type
from toast.helpers import CustomHelpGroup


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
        for _, name, is_pkg in pkgutil.iter_modules([plugins_path]):
            # Skip the base_plugin module and __init__.py
            if name == "base_plugin" or name == "__init__" or name == "utils":
                continue

            # Import the module
            module_name = f"{plugins_package_name}.{name}"
            try:
                module = importlib.import_module(module_name)

                # Find all classes in the module that are subclasses of BasePlugin
                for item_name, item in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(item, BasePlugin)
                        and item is not BasePlugin
                        and item.__module__ == module_name
                    ):
                        discovered_plugins.append(item)
            except ImportError as e:
                click.echo(f"Error loading plugin module {module_name}: {e}", err=True)

    except ImportError as e:
        click.echo(
            f"Error loading plugins package {plugins_package_name}: {e}", err=True
        )

    return discovered_plugins


@click.group(cls=CustomHelpGroup)
def toast_cli():
    """
    Toast command-line tool with dynamically loaded plugins.
    """
    pass


@toast_cli.command()
def version():
    """Display the current version of toast-cli."""
    from toast.helpers import get_version

    click.echo(f"toast-cli version: {get_version()}")


def main():
    # Discover and load all plugins
    plugins = discover_and_load_plugins()

    if not plugins:
        click.echo("No plugins were discovered", err=True)
        sys.exit(1)

    # Register each plugin with the CLI
    for plugin_class in plugins:
        try:
            plugin_class.register(toast_cli)
        except Exception as e:
            click.echo(
                f"Error registering plugin {plugin_class.__name__}: {e}", err=True
            )

    # Run the CLI
    toast_cli()


if __name__ == "__main__":
    main()
