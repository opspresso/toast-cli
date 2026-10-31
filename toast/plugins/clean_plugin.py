#!/usr/bin/env python3

import json
import shutil
from pathlib import Path

import click
from rich.table import Table
from rich.text import Text

from toast import ui
from toast.plugins.base_plugin import BasePlugin
from toast.plugins.clean_catalog import CACHE, DATA, DOWNLOAD, blocked_reason, catalog, list_processes, readable, scan

RISK_STYLES = {CACHE: "green", DOWNLOAD: "yellow", DATA: "bold red"}


def total_size(items):
    return sum(item.bytes for item in items)


def space_summary(selected_size, free):
    return f"Free now {ui.format_size(free)} · after {ui.format_size(free + selected_size)}"


def show_table(items, home):
    processes = list_processes()
    table = Table(box=None, pad_edge=False, header_style="bold")
    table.add_column("#", justify="right", style="dim", no_wrap=True, min_width=2)
    table.add_column("SIZE", justify="right", no_wrap=True, min_width=9)
    table.add_column("RISK", no_wrap=True, min_width=8)
    table.add_column("NAME", no_wrap=True, min_width=18)
    table.add_column("DESCRIPTION", overflow="ellipsis", no_wrap=True)
    for number, item in enumerate(items, 1):
        reason = blocked_reason(item, processes)
        # The reason goes first: a narrow terminal cuts the end of this column.
        description = Text.assemble((f"blocked: {reason} · ", "yellow") if reason else "", item.description)
        table.add_row(str(number), ui.format_size(item.bytes), Text(item.risk, style=RISK_STYLES[item.risk]), item.name, description)
    ui.console.print(table)
    free = shutil.disk_usage(home).free
    ui.info(f"Reclaimable {ui.format_size(total_size(items))} · {space_summary(total_size(items), free)}")
    show_access_notice(home)


def show_access_notice(home):
    if not readable(home / ".Trash"):
        ui.warning("macOS hides the Trash, Mail and OrbStack data from this terminal. Grant it Full Disk Access to include them.")


def choose_with_picker(items, home):
    """Return the chosen items, or None after a cancel."""
    processes = list_processes()
    free = shutil.disk_usage(home).free
    rows = []
    for item in items:
        cells = [
            Text(ui.format_size(item.bytes).rjust(9)),
            Text(item.risk.ljust(8), style=RISK_STYLES[item.risk]),
            Text(item.name.ljust(19)),
            Text(item.description, style="dim"),
        ]
        rows.append(ui.Row(item.name, cells, blocked=blocked_reason(item, processes), value=item))

    def footer(chosen):
        size = sum(row.value.bytes for row in chosen)
        return f"Selected {len(chosen)} · {ui.format_size(size)} · {space_summary(size, free)}"

    chosen = ui.multi_select(
        rows,
        f"Reclaimable {ui.format_size(total_size(items))}",
        footer=footer,
        shortcuts={"a": lambda row: row.value.risk != DATA},
        hint="↑↓ move · space select · a all except data · n clear · enter confirm · q quit",
    )
    return None if chosen is None else [row.value for row in chosen]


def choose_with_prompt(items, home):
    """Serve pipes and terminals without a key-by-key input mode."""
    show_table(items, home)
    try:
        answer = click.prompt("Enter numbers or names (1 3 5), a for all except data, q to quit", default="q", show_default=False)
    except click.Abort:
        return None
    tokens = answer.replace(",", " ").split()
    if not tokens or any(token.lower() == "q" for token in tokens):
        return None
    return select(items, tokens)


def select(items, tokens):
    """Resolve numbers, names and "a". Raises UsageError for anything else."""
    chosen = []
    for token in tokens:
        if token.lower() == "a":
            matches = [item for item in items if item.risk != DATA]
        elif token.isdigit() and 1 <= int(token) <= len(items):
            matches = [items[int(token) - 1]]
        else:
            matches = [item for item in items if item.name == token]
        if not matches:
            raise click.UsageError(f"Nothing to clean for: {token}")
        chosen.extend(item for item in matches if item not in chosen)
    return chosen


def confirm(chosen):
    for item in chosen:
        ui.console.print(Text.assemble("  ", (ui.format_size(item.bytes).rjust(9)), "  ", item.name))
    if any(item.risk == DATA for item in chosen):
        ui.warning("The selection includes data that cannot be restored.")
    try:
        return click.confirm(f"Remove {len(chosen)} items ({ui.format_size(total_size(chosen))})?", default=False)
    except click.Abort:
        return False


def remove(chosen, home):
    before = shutil.disk_usage(home).free
    failed = []
    for item in chosen:
        reason = blocked_reason(item)
        if reason:
            ui.warning(f"Skipped {item.name}: {reason}")
            continue
        try:
            with ui.console.status(f"Removing {item.name}"):
                item.remove(home)
        except (OSError, click.ClickException) as exc:
            message = exc.format_message() if isinstance(exc, click.ClickException) else str(exc)
            ui.console.print(Text(f"✗ {item.name}: {message}", style="bold red"))
            failed.append(item.name)
        else:
            ui.success(f"{item.name} ({ui.format_size(item.bytes)})")
    after = shutil.disk_usage(home).free
    ui.info(f"Free space {ui.format_size(before)} → {ui.format_size(after)}")
    if failed:
        raise click.ClickException(f"Could not remove: {', '.join(failed)}")


def complete_names(ctx, param, incomplete):
    return sorted({item.name for item in catalog(Path.home()) if item.name.startswith(incomplete)})


class CleanPlugin(BasePlugin):
    """Plugin for 'clean' command - shows and removes reclaimable disk data."""

    name = "clean"
    help = "Show reclaimable disk data and remove selected items"
    category = "Workspace"
    examples = (
        ("toast clean", "Pick items with the space bar"),
        ("toast clean --list", "Show the items and exit"),
        ("toast clean go-cache npm-cache --yes", "Remove named items without a question"),
    )

    @classmethod
    def get_arguments(cls, func):
        func = click.option("--yes", "-y", is_flag=True, help="Skip the confirmation; requires item names")(func)
        func = click.option("--json", "as_json", is_flag=True, help="Print the items as JSON and exit")(func)
        func = click.option("--list", "list_only", is_flag=True, help="Show the items and exit")(func)
        func = click.argument("names", nargs=-1, shell_complete=complete_names)(func)
        return func

    @classmethod
    def execute(cls, names=(), list_only=False, as_json=False, yes=False, **kwargs):
        if yes and not names:
            raise click.UsageError("--yes needs item names; see toast clean --list")
        home = Path.home()
        if ui.is_interactive() and not as_json:
            with ui.error_console.status("Measuring disk usage"):
                items = scan(home)
        else:
            items = scan(home)
        if as_json:
            processes = list_processes()
            click.echo(json.dumps([
                {"name": item.name, "bytes": item.bytes, "risk": item.risk, "description": item.description, "blocked": blocked_reason(item, processes)}
                for item in items
            ], indent=2))
            return
        if not items:
            ui.success("Nothing to clean")
            return
        if list_only:
            show_table(items, home)
            return
        if names:
            chosen = select(items, names)
        elif ui.is_interactive():
            chosen = choose_with_picker(items, home)
            show_access_notice(home)
        else:
            chosen = choose_with_prompt(items, home)
        if not chosen or not (yes or confirm(chosen)):
            ui.muted("Nothing removed")
            return
        remove(chosen, home)
