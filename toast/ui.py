#!/usr/bin/env python3

"""Terminal presentation shared by all commands: messages, sizes and pickers.

Interactive screens draw on stderr, so a command can keep stdout for its result.
"""

import os
import select
import sys
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence

from rich.console import Console, Group
from rich.live import Live
from rich.text import Text

console = Console(highlight=False)
error_console = Console(stderr=True, highlight=False)

# Hangul layout keys, so a Korean input method does not disable the shortcuts.
KEY_ALIASES = {"ㅓ": "j", "ㅏ": "k", "ㅁ": "a", "ㅜ": "n", "ㅂ": "q"}
ESCAPE_KEYS = {"\x1b[A": "up", "\x1b[B": "down", "\x1bOA": "up", "\x1bOB": "down", "\x1b[5~": "pageup", "\x1b[6~": "pagedown", "\x1b[H": "home", "\x1b[F": "end"}
GIB = 1024**3
MIB = 1024**2


def format_size(size):
    """Show the unit a person expects: 734 MB rather than 0.7 GiB."""
    if size >= GIB:
        return f"{size / GIB:.1f} GiB"
    if size >= MIB:
        return f"{size / MIB:.0f} MB"
    return "< 1 MB"


def success(message):
    console.print(Text(f"✓ {message}", style="bold green"))


def warning(message):
    console.print(Text(f"! {message}", style="bold yellow"))


def info(message):
    console.print(Text(message, style="cyan"))


def muted(message, stderr=False):
    (error_console if stderr else console).print(Text(message, style="dim"))


def is_interactive():
    return sys.stdin.isatty() and sys.stderr.isatty()


@dataclass
class Row:
    """One line of a picker. A row with a blocked reason cannot be selected."""

    key: str
    cells: Sequence[Text]
    blocked: Optional[str] = None
    value: object = None


class Picker:
    """Selection state. It reads no keys and draws nothing, so tests can drive it."""

    def __init__(self, rows: List[Row], multiple=True, shortcuts: Optional[Dict[str, Callable[[Row], bool]]] = None, height=20):
        self.rows = rows
        self.multiple = multiple
        self.shortcuts = shortcuts or {}
        self.height = height
        self.cursor = 0
        self.offset = 0
        self.selected = set()
        self.done = False
        self.cancelled = False
        self._move_to(0, 1)

    def _selectable(self, index):
        return not self.multiple or not self.rows[index].blocked

    def _move_to(self, index, step):
        """Stop on the nearest row that can be selected."""
        count = len(self.rows)
        index = max(0, min(index, count - 1))
        while 0 <= index < count and not self._selectable(index):
            index += step
        if 0 <= index < count:
            self.cursor = index
        self.offset = min(self.offset, self.cursor)
        self.offset = max(self.offset, self.cursor - self.height + 1)

    def _toggle(self):
        if not self._selectable(self.cursor):
            return
        if self.cursor in self.selected:
            self.selected.discard(self.cursor)
        else:
            self.selected.add(self.cursor)

    def handle(self, key):
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
            self._move_to(len(self.rows) - 1, -1)
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
            self.done = True
        elif key in ("q", "\x1b", "\x03"):
            self.cancelled = True

    def result(self):
        if self.cancelled:
            return None
        if self.multiple:
            return [self.rows[index] for index in sorted(self.selected)]
        return [self.rows[self.cursor]]

    def chosen_rows(self):
        return [self.rows[index] for index in sorted(self.selected)]


def render(picker: Picker, title, footer, hint):
    lines = [Text(title, style="bold")]
    if picker.offset > 0:
        lines.append(Text(f"    ↑ {picker.offset} more", style="dim"))
    visible = picker.rows[picker.offset:picker.offset + picker.height]
    for position, row in enumerate(visible, picker.offset):
        current = position == picker.cursor
        line = Text("❯ " if current else "  ", style="bold cyan")
        if picker.multiple:
            line.append("◉ " if position in picker.selected else "○ ", style="bold green" if position in picker.selected else "dim")
        for cell in row.cells[:-1]:
            line.append_text(cell)
            line.append("  ")
        if row.blocked:
            line.stylize("dim")
            # The reason precedes the last cell: a narrow terminal cuts the line end.
            line.append(f"blocked: {row.blocked} · ", style="yellow")
        line.append_text(row.cells[-1])
        if current and not row.blocked:
            line.stylize("bold")
        line.no_wrap = True
        line.overflow = "ellipsis"
        lines.append(line)
    hidden = len(picker.rows) - picker.offset - len(visible)
    if hidden > 0:
        lines.append(Text(f"    ↓ {hidden} more", style="dim"))
    lines.append(Text(""))
    summary = footer(picker.chosen_rows()) if footer else ""
    if summary:
        lines.append(Text(summary, style="bold cyan"))
    lines.append(Text(hint, style="dim"))
    return Group(*lines)


def read_key(fd):
    """Return one key press, joining an escape sequence and multibyte text."""
    data = os.read(fd, 1)
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

    picker.height = max(3, min(len(picker.rows), error_console.size.height - 8))
    picker.offset = 0
    picker._move_to(picker.cursor, 1)
    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        with Live(render(picker, title, footer, hint), console=error_console, auto_refresh=False, transient=True) as live:
            while not (picker.done or picker.cancelled):
                picker.handle(read_key(fd))
                live.update(render(picker, title, footer, hint), refresh=True)
    except KeyboardInterrupt:
        picker.cancelled = True
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)
    return picker.result()


MULTI_HINT = "↑↓ move · space select · n clear · enter confirm · q quit"


def multi_select(rows, title, footer=None, shortcuts=None, hint=MULTI_HINT):
    """Return the chosen rows, or None when the user cancels."""
    return run_picker(Picker(rows, shortcuts=shortcuts), title, footer, hint)


def select_one(options, title):
    """Return the chosen option, or None when the user cancels."""
    rows = [Row(option, [Text(option)]) for option in options]
    chosen = run_picker(Picker(rows, multiple=False), title, hint="↑↓ move · enter select · q quit")
    return chosen[0].key if chosen else None
