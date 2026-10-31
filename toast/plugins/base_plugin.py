#!/usr/bin/env python3

import configparser

import click

from toast.helpers import CustomHelpCommand


class BasePlugin:
    """Base class for all plugins."""

    name = None  # Command name
    help = None  # Command help text
    category = "General"  # Help section
    examples = ()  # (command, meaning) pairs for the help screen
    commands = ()  # (subcommand, meaning) pairs for the help screen and completion

    @classmethod
    def register(cls, cli_group):
        """Register the plugin with the CLI group."""
        if not cls.name:
            raise ValueError(f"Plugin {cls.__name__} must define a name")

        @cli_group.command(name=cls.name, help=cls.help, cls=CustomHelpCommand, examples=cls.examples, commands=cls.commands)
        @cls.get_arguments
        def command(**kwargs):
            try:
                return cls.execute(**kwargs)
            except (OSError, ValueError, configparser.Error) as exc:
                raise click.ClickException(str(exc)) from exc

        cli_group.commands[cls.name].category = cls.category

    @classmethod
    def complete_command(cls, ctx, param, incomplete):
        return [name for name, _ in cls.commands if name.startswith(incomplete)]

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
