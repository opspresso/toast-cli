#!/usr/bin/env python3

import os
import sys

import click

from toast import ui


def get_version():
    """Get the version from package metadata."""
    # Imported here because the metadata machinery slows every shell completion.
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("toast-cli")
    except PackageNotFoundError:
        # Fallback to VERSION file for development environment
        version_file = os.path.join(os.path.dirname(__file__), "..", "VERSION")
        if os.path.exists(version_file):
            with open(version_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        return "unknown"


class ToastFormatter(click.HelpFormatter):
    """Click's help layout in the colors of the rest of the interface."""

    def write_usage(self, prog, args="", prefix=None):
        super().write_usage(prog, args, ui.paint("Usage: ", fg=ui.ACCENT, bold=True))

    def write_heading(self, heading):
        self.write(f"{'':>{self.current_indent}}{ui.paint(heading + ':', fg=ui.ACCENT, bold=True)}\n")

    def write_dl(self, rows, col_max=30, col_spacing=2):
        super().write_dl([(ui.paint(term, bold=True), text) for term, text in rows], col_max, col_spacing)


class ToastContext(click.Context):
    formatter_class = ToastFormatter


class CustomHelpCommand(click.Command):
    """Help for one command, with its subcommands and usage examples."""

    context_class = ToastContext

    def __init__(self, *args, examples=(), commands=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.examples = examples
        self.subcommands = commands

    def format_epilog(self, ctx, formatter):
        for title, rows in (("Commands", self.subcommands), ("Examples", self.examples)):
            if rows:
                with formatter.section(title):
                    formatter.write_dl(rows)
        super().format_epilog(ctx, formatter)


class CustomHelpGroup(click.Group):
    """The top level: the logo, commands by topic, and errors in the toast style."""

    context_class = ToastContext
    command_class = CustomHelpCommand

    def main(self, *args, standalone_mode=True, **extra):
        """Report failures through ui. Exit status: 1 failure, 2 usage, 130 cancelled."""
        if not standalone_mode:
            return super().main(*args, standalone_mode=False, **extra)
        try:
            code = super().main(*args, standalone_mode=False, **extra)
        except click.UsageError as exc:
            hints = []
            if exc.ctx is not None:
                hints = [click.unstyle(exc.ctx.get_usage()), f"Run: {exc.ctx.command_path} --help"]
            ui.error(exc.format_message(), *hints)
            sys.exit(exc.exit_code)
        except click.ClickException as exc:
            ui.error(exc.format_message())
            sys.exit(exc.exit_code)
        except click.Abort:
            ui.cancelled()
            sys.exit(130)
        sys.exit(code if isinstance(code, int) else 0)

    def resolve_command(self, ctx, args):
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError as exc:
            import difflib

            close = difflib.get_close_matches(args[0], self.list_commands(ctx), n=1)
            # Newer Click versions add this suggestion themselves.
            if close and "Did you mean" not in exc.format_message():
                raise click.UsageError(f"{exc.format_message()} Did you mean '{close[0]}'?", ctx) from exc
            raise

    def get_help(self, ctx):
        ui.banner(get_version())
        return super().get_help(ctx)

    def format_commands(self, ctx, formatter):
        sections = {}
        for name in self.list_commands(ctx):
            command = self.get_command(ctx, name)
            if command is not None and not command.hidden:
                sections.setdefault(getattr(command, "category", "General"), []).append(
                    (name, command.get_short_help_str(limit=max(40, formatter.width - 14)))
                )
        for title in sorted(sections, key=lambda section: (section == "General", section)):
            with formatter.section(title):
                formatter.write_dl(sections[title])
