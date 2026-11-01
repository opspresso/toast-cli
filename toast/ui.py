#!/usr/bin/env python3

"""Terminal presentation shared by all commands. Every plugin writes through here.

Stream contract: a command's result goes to stdout, and everything about the run
(status, warnings, errors, prompts, pickers) goes to stderr. A pipe or `$(...)`
therefore receives only the result.
"""

import os
import select
import sys
from contextlib import contextmanager, redirect_stdout
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence

import click
from rich.console import Console, Group
from rich.text import Text

console = Console(highlight=False)
error_console = Console(stderr=True, highlight=False)

ACCENT = "cyan"
BRAND = "yellow"
GOOD = "green"
WARN = "yellow"
BAD = "red"
MUTED = "dim"

# Hangul layout keys, so a Korean input method does not disable the shortcuts.
KEY_ALIASES = {"ㅓ": "j", "ㅏ": "k", "ㅁ": "a", "ㅜ": "n", "ㅂ": "q"}
ESCAPE_KEYS = {"\x1b[A": "up", "\x1b[B": "down", "\x1bOA": "up", "\x1bOB": "down", "\x1b[5~": "pageup", "\x1b[6~": "pagedown", "\x1b[H": "home", "\x1b[F": "end"}
GIB = 1024**3
MIB = 1024**2
LOGO = (
    r" _                  _           _ _",
    r"| |_ ___   __ _ ___| |_     ___| (_)",
    r"| __/ _ \ / _` / __| __|__ / __| | |",
    r"| || (_) | (_| \__ \ ||___| (__| | |",
    r" \__\___/ \__,_|___/\__|   \___|_|_|",
)


def format_size(size):
    """Show the unit a person expects: 734 MiB rather than 0.7 GiB."""
    if size >= GIB:
        return f"{size / GIB:.1f} GiB"
    if size >= MIB:
        return f"{size / MIB:.0f} MiB"
    return "< 1 MiB"


def _say(text):
    # soft_wrap keeps a long path or name on one line in a pipe, which has no width.
    error_console.print(text, soft_wrap=True)


def success(message):
    _say(Text(f"✓ {message}", style=f"bold {GOOD}"))


def warning(message):
    _say(Text(f"! {message}", style=f"bold {WARN}"))


class Failure(click.ClickException):
    """An operational failure with the next steps a person can take.

    The command boundary prints each hint below the error, muted.
    """

    def __init__(self, message, *hints):
        super().__init__(message)
        self.hints = hints


def error(message, *hints):
    _say(Text(f"✗ {message}", style=f"bold {BAD}"))
    for hint in hints:
        _say(Text(f"  {hint}", style=MUTED))


def info(message):
    _say(Text(message, style=ACCENT))


def muted(message):
    _say(Text(message, style=MUTED))


def cancelled():
    muted("Cancelled")


def rule():
    error_console.print(Text("─" * min(error_console.width, 80), style=MUTED))


def fields(pairs):
    """Print (label, value) pairs in aligned columns."""
    width = max(len(label) for label, _ in pairs)
    for label, value in pairs:
        _say(Text.assemble((label.ljust(width), MUTED), "  ", value))


def result(text):
    """Print a result line exactly as given, without markup or wrapping."""
    click.echo(text)


def json_result(data):
    console.print_json(data=data)


def table(headers, rows, min_widths=()):
    """Print rows of cells: aligned for a person, tab-separated for a pipe."""
    if not console.is_terminal:
        for row in rows:
            click.echo("\t".join(cell.plain if isinstance(cell, Text) else cell for cell in row))
        return
    from rich.table import Table

    view = Table(box=None, pad_edge=False, header_style="bold")
    for index, header in enumerate(headers):
        wide = index == len(headers) - 1
        view.add_column(header, no_wrap=True, overflow="ellipsis" if wide else None, min_width=min_widths[index] if index < len(min_widths) else None)
    for row in rows:
        view.add_row(*(cell if isinstance(cell, Text) else Text(cell) for cell in row))
    console.print(view)


def diff(lines, limit=50, stderr=False):
    """Print unified-diff lines with additions and removals colored.

    A diff is a result on stdout. Pass stderr=True for a preview that precedes a
    change, so the command's stdout stays empty. A terminal shows the first LIMIT
    lines; a pipe or file receives the complete diff.
    """
    out = error_console if stderr else console
    if not out.is_terminal:
        limit = len(lines)
    for line in lines[:limit]:
        line = line.rstrip()
        if line.startswith("+") and not line.startswith("+++"):
            style = GOOD
        elif line.startswith("-") and not line.startswith("---"):
            style = BAD
        else:
            style = MUTED
        out.print(Text(line, style=style), soft_wrap=True)
    if len(lines) > limit:
        muted(f"… {len(lines) - limit} more lines")


@contextmanager
def status(message):
    """Show a spinner on a terminal while slow work runs; show nothing in a pipe."""
    if not error_console.is_terminal:
        yield
        return
    with error_console.status(Text(message), spinner="dots", spinner_style=ACCENT):
        yield


def paint(text, **style):
    """Style text that Click writes itself. Click does not honor NO_COLOR."""
    return text if os.environ.get("NO_COLOR") else click.style(text, **style)


def confirm(message, default=False):
    # Click before 8.4 writes the space after a prompt to stdout even with err=True.
    with redirect_stdout(sys.stderr):
        return click.confirm(paint("? ", fg=ACCENT, bold=True) + message, default=default, err=True)


def prompt(message, **options):
    with redirect_stdout(sys.stderr):
        return click.prompt(paint("? ", fg=ACCENT, bold=True) + message, err=True, **options)


def banner(version):
    console.print()
    for line in LOGO[:-1]:
        console.print(Text(line, style=f"bold {BRAND}"))
    console.print(Text.assemble((LOGO[-1], f"bold {BRAND}"), (f"   {version}", f"bold {ACCENT}")))
    console.print(Text("─" * min(console.width, 80), style=MUTED))


def is_interactive():
    return sys.stdin.isatty() and sys.stderr.isatty()


def fuzzy(query, text):
    """Rank TEXT against QUERY. Return (rank, matched positions), or None for no match.

    Every space-separated term must match. A lower rank is better: a substring beats
    scattered letters, and a match at a word start beats one inside a word.
    """
    lowered = text.lower()
    rank = 0
    positions = set()
    for term in query.lower().split():
        start = lowered.find(term)
        if start >= 0:
            positions.update(range(start, start + len(term)))
            rank += 0 if start == 0 or not lowered[start - 1].isalnum() else 1
            continue
        found = []
        index = -1
        for char in term:
            index = lowered.find(char, index + 1)
            if index < 0:
                return None
            found.append(index)
        positions.update(found)
        rank += 2 + found[-1] - found[0]
    return rank, positions


@dataclass
class Row:
    """One line of a picker. A row with a blocked reason cannot be selected."""

    key: str
    cells: Sequence[Text]
    blocked: Optional[str] = None
    value: object = None

    @property
    def plain(self):
        return "".join(cell.plain for cell in self.cells)


class Picker:
    """Selection state. It reads no keys and draws nothing, so tests can drive it.

    A multiple picker uses letter shortcuts. A single picker sends letters to its
    filter instead, because a long list is searched rather than scrolled.
    """

    def __init__(self, rows: List[Row], multiple=True, shortcuts: Optional[Dict[str, Callable[[Row], bool]]] = None, height=20, current=None):
        self.rows = rows
        self.multiple = multiple
        self.shortcuts = shortcuts or {}
        self.height = height
        self.current = current
        self.query = ""
        self.view = list(range(len(rows)))
        self.matches = {}
        self.cursor = 0
        self.offset = 0
        self.selected = set()
        self.done = False
        self.cancelled = False
        start = next((index for index, row in enumerate(rows) if row.key == current), 0)
        self._move_to(start, 1)

    def _selectable(self, position):
        return not self.multiple or not self.rows[self.view[position]].blocked

    def _move_to(self, position, step):
        """Stop on the nearest row that can be selected."""
        count = len(self.view)
        position = max(0, min(position, count - 1))
        while 0 <= position < count and not self._selectable(position):
            position += step
        if 0 <= position < count:
            self.cursor = position
        self.offset = min(self.offset, self.cursor)
        self.offset = max(self.offset, self.cursor - self.height + 1)

    def _toggle(self):
        if not self._selectable(self.cursor):
            return
        if self.cursor in self.selected:
            self.selected.discard(self.cursor)
        else:
            self.selected.add(self.cursor)

    def _apply_filter(self):
        self.matches = {}
        if not self.query.strip():
            self.view = list(range(len(self.rows)))
            self.cursor = self.offset = 0
            self._move_to(next((index for index, row in enumerate(self.rows) if row.key == self.current), 0), 1)
            return
        ranked = []
        for index, row in enumerate(self.rows):
            match = fuzzy(self.query, row.plain)
            if match:
                self.matches[index] = match[1]
                ranked.append((match[0], len(row.plain), index))
        self.view = [index for _, _, index in sorted(ranked)]
        self.cursor = self.offset = 0

    def _edit_filter(self, key):
        """Apply KEY to the filter. Return False when it is not a text edit."""
        if key in ("\x7f", "\x08"):
            self.query = self.query[:-1]
        elif key == "\x15":  # Ctrl-U
            self.query = ""
        elif len(key) == 1 and key.isprintable():
            self.query += key
        else:
            return False
        self._apply_filter()
        return True

    def handle(self, key):
        if not self.multiple:
            key = {"\x0e": "down", "\x10": "up"}.get(key, key)  # Ctrl-N, Ctrl-P
            if self._edit_filter(key):
                return
        else:
            key = KEY_ALIASES.get(key, key)
        if key in ("up", "k"):
            self._move_to(self.cursor - 1, -1)
        elif key in ("down", "j"):
            self._move_to(self.cursor + 1, 1)
        elif key == "pageup":
            self._move_to(self.cursor - self.height, -1)
        elif key == "pagedown":
            self._move_to(self.cursor + self.height, 1)
        elif key in ("home", "g"):
            self._move_to(0, 1)
        elif key in ("end", "G"):
            self._move_to(len(self.view) - 1, -1)
        elif key == " " and self.multiple:
            self._toggle()
            self._move_to(self.cursor + 1, 1)
        elif key == "n" and self.multiple:
            self.selected.clear()
        elif key in self.shortcuts and self.multiple:
            chosen = {index for index, row in enumerate(self.rows) if not row.blocked and self.shortcuts[key](row)}
            # The same key clears its selection, so a mistake takes one press to undo.
            self.selected = set() if self.selected == chosen else chosen
        elif key in ("\r", "\n"):
            self.done = bool(self.view)
        elif key in ("q", "\x1b", "\x03"):
            self.cancelled = True

    def result(self):
        if self.cancelled:
            return None
        if self.multiple:
            return self.chosen_rows()
        return [self.rows[self.view[self.cursor]]]

    def chosen_rows(self):
        return [self.rows[index] for index in sorted(self.selected)]


def render(picker: Picker, title, footer, hint):
    header = Text(title, style="bold")
    if picker.query:
        header.append(f"  {len(picker.view)}/{len(picker.rows)}", style=MUTED)
    lines = [header]
    if not picker.multiple:
        lines.append(Text.assemble(("› ", ACCENT), picker.query, ("▏", ACCENT)))
    if picker.offset > 0:
        lines.append(Text(f"    ↑ {picker.offset} more", style=MUTED))
    visible = picker.view[picker.offset:picker.offset + picker.height]
    for position, index in enumerate(visible, picker.offset):
        row = picker.rows[index]
        current = position == picker.cursor
        line = Text("❯ " if current else "  ", style=f"bold {ACCENT}")
        if picker.multiple:
            chosen = position in picker.selected
            line.append("◉ " if chosen else "○ ", style=f"bold {GOOD}" if chosen else MUTED)
        for cell in row.cells[:-1]:
            line.append_text(cell)
            line.append("  ")
        if row.blocked:
            line.stylize(MUTED)
            # The reason precedes the last cell: a narrow terminal cuts the line end.
            line.append(f"blocked: {row.blocked} · ", style=WARN)
        start = len(line)
        line.append_text(row.cells[-1])
        for match in picker.matches.get(index, ()):
            line.stylize(f"bold {BRAND}", start + match, start + match + 1)
        if row.key == picker.current:
            line.append("  current", style=MUTED)
        if current and not row.blocked:
            line.stylize("bold")
        line.no_wrap = True
        line.overflow = "ellipsis"
        lines.append(line)
    if not picker.view:
        lines.append(Text("  No match", style=MUTED))
    hidden = len(picker.view) - picker.offset - len(visible)
    if hidden > 0:
        lines.append(Text(f"    ↓ {hidden} more", style=MUTED))
    lines.append(Text(""))
    summary = footer(picker.chosen_rows()) if footer else ""
    if summary:
        lines.append(Text(summary, style=f"bold {ACCENT}"))
    lines.append(Text(hint, style=MUTED))
    return Group(*lines)


def read_key(fd):
    """Return one key press, joining an escape sequence and multibyte text.

    Return None at end of input, which means no further key can arrive.
    """
    data = os.read(fd, 1)
    if not data:
        return None
    if data == b"\x1b":
        while select.select([fd], [], [], 0.03)[0]:
            data += os.read(fd, 1)
            if len(data) >= 3 and data[-1:].isalpha() or data[-1:] == b"~":
                break
        text = data.decode("ascii", "ignore")
        return ESCAPE_KEYS.get(text, "\x1b" if text == "\x1b" else "")
    if data and data[0] >= 0xC0:
        length = 2 if data[0] < 0xE0 else 3 if data[0] < 0xF0 else 4
        data += os.read(fd, length - 1)
    return data.decode("utf-8", "ignore")


def run_picker(picker: Picker, title, footer=None, hint=""):
    """Draw PICKER until the user confirms or cancels. Ctrl-C counts as a cancel."""
    import termios  # POSIX only; importing here keeps the other commands portable.
    import tty

    from rich.live import Live

    picker.height = max(3, min(len(picker.rows), error_console.size.height - 8))
    picker.offset = 0
    picker._move_to(picker.cursor, 1)
    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        with Live(render(picker, title, footer, hint), console=error_console, auto_refresh=False, transient=True) as live:
            while not (picker.done or picker.cancelled):
                key = read_key(fd)
                if key is None:
                    picker.cancelled = True
                    break
                picker.handle(key)
                live.update(render(picker, title, footer, hint), refresh=True)
    except KeyboardInterrupt:
        picker.cancelled = True
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)
    return picker.result()


MULTI_HINT = "↑↓ move · space select · n clear · enter confirm · q quit"
SINGLE_HINT = "type to filter · ↑↓ move · enter select · esc quit"


def multi_select(rows, title, footer=None, shortcuts=None, hint=MULTI_HINT):
    """Return the chosen rows, or None when the user cancels."""
    return run_picker(Picker(rows, shortcuts=shortcuts), title, footer, hint)


def choose(options, title, current=None, label=None):
    """Return the chosen option, or None when the user cancels.

    LABEL turns an option into its display text. A session without a terminal
    cannot answer, so it gets an error rather than a guess.
    """
    if not options:
        return None
    if not is_interactive():
        raise click.ClickException(f"{title} needs a terminal")
    rows = [Row(option, [Text(label(option) if label else option)]) for option in options]
    chosen = run_picker(Picker(rows, multiple=False, current=current), title, hint=SINGLE_HINT)
    return chosen[0].key if chosen else None
