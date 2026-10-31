"""Exercise the picker state, then the real key loop through a pseudo-terminal."""

import fcntl
import os
from pathlib import Path
import pty
import select
import subprocess
import sys
import termios
import time
import unittest

from rich.text import Text

from toast import ui

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = """
from rich.text import Text
from toast import ui
rows = [ui.Row(n, [Text(n)], blocked="busy" if n == "b" else None) for n in "abc"]
chosen = ui.multi_select(rows, "Pick", shortcuts={"a": lambda row: True})
print("RESULT", None if chosen is None else [row.key for row in chosen])
"""


def rows(*names, blocked=()):
    return [ui.Row(name, [Text(name)], blocked="busy" if name in blocked else None) for name in names]


class PickerTests(unittest.TestCase):
    def test_space_selects_and_moves_down(self):
        picker = ui.Picker(rows("a", "b", "c"))
        for key in (" ", " ", "\r"):
            picker.handle(key)
        self.assertEqual([row.key for row in picker.result()], ["a", "b"])

    def test_space_again_clears_the_row(self):
        picker = ui.Picker(rows("a", "b"))
        for key in (" ", "up", " "):
            picker.handle(key)
        self.assertEqual(picker.selected, set())

    def test_cursor_skips_blocked_rows(self):
        picker = ui.Picker(rows("a", "b", "c", blocked=("b",)))
        picker.handle("down")
        self.assertEqual(picker.cursor, 2)
        picker.handle("up")
        self.assertEqual(picker.cursor, 0)

    def test_first_row_blocked_starts_on_next(self):
        self.assertEqual(ui.Picker(rows("a", "b", blocked=("a",))).cursor, 1)

    def test_blocked_row_cannot_be_selected_when_all_are_blocked(self):
        picker = ui.Picker(rows("a", blocked=("a",)))
        picker.handle(" ")
        self.assertEqual(picker.selected, set())

    def test_shortcut_skips_blocked_rows_and_toggles(self):
        picker = ui.Picker(rows("a", "b", "c", blocked=("b",)), shortcuts={"a": lambda row: True})
        picker.handle("a")
        self.assertEqual(picker.selected, {0, 2})
        picker.handle("a")
        self.assertEqual(picker.selected, set())

    def test_hangul_layout_keys_work(self):
        picker = ui.Picker(rows("a", "b"))
        picker.handle("ㅓ")
        self.assertEqual(picker.cursor, 1)
        picker.handle("ㅂ")
        self.assertIsNone(picker.result())

    def test_viewport_follows_the_cursor(self):
        picker = ui.Picker(rows(*"abcdefgh"), height=3)
        for _ in range(5):
            picker.handle("down")
        self.assertEqual((picker.cursor, picker.offset), (5, 3))
        picker.handle("home")
        self.assertEqual((picker.cursor, picker.offset), (0, 0))

    def test_single_choice_ignores_space(self):
        picker = ui.Picker(rows("a", "b"), multiple=False)
        for key in ("down", " ", "\n"):
            picker.handle(key)
        self.assertEqual([row.key for row in picker.result()], ["b"])

    def test_format_size(self):
        self.assertEqual(ui.format_size(5 * 1024**3), "5.0 GiB")
        self.assertEqual(ui.format_size(512 * 1024**2), "512 MB")
        self.assertEqual(ui.format_size(10), "< 1 MB")


class TerminalTests(unittest.TestCase):
    def drive(self, keys):
        master, slave = pty.openpty()
        environment = dict(os.environ, PYTHONPATH=str(ROOT), TERM="xterm-256color", COLUMNS="80", LINES="24")
        process = subprocess.Popen(
            [sys.executable, "-c", SCRIPT], stdin=slave, stdout=slave, stderr=slave, env=environment, close_fds=True,
            start_new_session=True, preexec_fn=lambda: fcntl.ioctl(0, termios.TIOCSCTTY, 0),
        )
        os.close(slave)
        self.addCleanup(os.close, master)
        output = b""
        pending = list(keys)
        deadline = time.time() + 10
        while time.time() < deadline:
            if select.select([master], [], [], 0.1)[0]:
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                output += chunk
            elif pending and b"Pick" in output:
                os.write(master, pending.pop(0))
            if process.poll() is not None and not select.select([master], [], [], 0)[0]:
                break
        process.wait(timeout=5)
        return output.decode("utf-8", "ignore")

    def test_arrow_space_enter_selects_past_a_blocked_row(self):
        output = self.drive([b" ", b"\x1b[B", b"\r"])
        self.assertIn("RESULT ['a']", output)

    def test_q_cancels_and_restores_the_cursor(self):
        output = self.drive([b"q"])
        self.assertIn("RESULT None", output)
        self.assertIn("\x1b[?25h", output)

    def test_ctrl_c_cancels(self):
        output = self.drive([b"\x03"])
        self.assertIn("RESULT None", output)
