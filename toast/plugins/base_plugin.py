#!/usr/bin/env python3

import click
from toast.helpers import CustomHelpCommand


class BasePlugin:
    """Base class for all plugins."""

    name = None  # Command name
    help = None  # Command help text

    @classmethod
    def register(cls, cli_group):
        """Register the plugin with the CLI group."""
        if not cls.name:
            raise ValueError(f"Plugin {cls.__name__} must define a name")

        # Use CustomHelpCommand for colored error messages
        @cli_group.command(name=cls.name, help=cls.help, cls=CustomHelpCommand)
        @cls.get_arguments
        def command(**kwargs):
            return cls.execute(**kwargs)

    @classmethod
    def get_arguments(cls, func):
        """Define command arguments. Override in subclass."""
        return func

    @classmethod
    def execute(cls, **kwargs):
        """Execute the command. Override in subclass."""
        raise NotImplementedError(
            f"Plugin {cls.__name__} must implement execute method"
        )
