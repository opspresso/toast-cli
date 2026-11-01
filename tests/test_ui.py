"""Exercise the picker state, then the real key loop through a pseudo-terminal."""

import fcntl
import io
import os
from pathlib import Path
import pty
import re
import select
import subprocess
import sys
import tempfile
import termios
import time
import unittest

from rich.console import Console
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

SINGLE = """
from toast import ui
print("RESULT", ui.choose(["alpha", "gamma"], "Pick"))
"""


CDW = """
import os, sys
os.chdir(sys.argv[1])
sys.argv = ["toast", "cdw", *sys.argv[2:]]
from toast import main
main()
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

    def test_typing_filters_a_single_choice(self):
        picker = ui.Picker(rows("alpha", "beta", "gamma"), multiple=False)
        for key in ("g", "\n"):
            picker.handle(key)
        self.assertEqual([row.key for row in picker.result()], ["gamma"])

    def test_letters_are_filter_text_in_a_single_choice(self):
        picker = ui.Picker(rows("quit", "jump"), multiple=False)
        for key in ("q", "\x7f", "j", "\n"):
            picker.handle(key)
        self.assertEqual([row.key for row in picker.result()], ["jump"])

    def test_enter_does_nothing_without_a_match(self):
        picker = ui.Picker(rows("a"), multiple=False)
        for key in ("z", "\r"):
            picker.handle(key)
        self.assertFalse(picker.done)

    def test_ctrl_u_clears_the_filter(self):
        picker = ui.Picker(rows("a", "b"), multiple=False)
        for key in ("a", "\x15"):
            picker.handle(key)
        self.assertEqual(len(picker.view), 2)

    def test_clearing_the_filter_restores_order_and_current_value(self):
        picker = ui.Picker(rows("long-name", "b", "c"), multiple=False, current="c")
        for key in ("b", "\x7f"):
            picker.handle(key)
        self.assertEqual(picker.view, [0, 1, 2])
        self.assertEqual(picker.result()[0].key, "c")

    def test_a_single_choice_starts_on_the_current_value(self):
        picker = ui.Picker(rows("a", "b", "c"), multiple=False, current="b")
        self.assertEqual(picker.result()[0].key, "b")

    def test_render_marks_the_current_value_and_the_empty_state(self):
        console = Console(record=True, width=60, file=io.StringIO())
        picker = ui.Picker(rows("a", "b"), multiple=False, current="b")
        console.print(ui.render(picker, "Pick", None, "hint"))
        self.assertIn("b  current", console.export_text())
        picker.handle("z")
        console.print(ui.render(picker, "Pick", None, "hint"))
        self.assertIn("No match", console.export_text())

    def test_fuzzy_prefers_a_word_start_over_scattered_letters(self):
        names = ["t-o-a-s-t", "xtoast", "acme/toast-cli"]
        picker = ui.Picker(rows(*names), multiple=False)
        for key in "toast":
            picker.handle(key)
        self.assertEqual([picker.rows[index].key for index in picker.view], ["acme/toast-cli", "xtoast", "t-o-a-s-t"])

    def test_every_term_must_match(self):
        self.assertIsNotNone(ui.fuzzy("toast cli", "opspresso/toast-cli"))
        self.assertIsNone(ui.fuzzy("toast zzz", "opspresso/toast-cli"))

    def test_read_key_reports_end_of_input(self):
        reader, writer = os.pipe()
        os.close(writer)
        self.addCleanup(os.close, reader)
        self.assertIsNone(ui.read_key(reader))

    def test_format_size(self):
        self.assertEqual(ui.format_size(5 * 1024**3), "5.0 GiB")
        self.assertEqual(ui.format_size(512 * 1024**2), "512 MiB")
        self.assertEqual(ui.format_size(10), "< 1 MiB")


class TerminalTests(unittest.TestCase):
    def drive(self, keys, script=None, args=(), env=None, ready=b"Pick"):
        master, slave = pty.openpty()
        environment = dict(os.environ, PYTHONPATH=str(ROOT), TERM="xterm-256color", COLUMNS="80", LINES="24", **(env or {}))
        process = subprocess.Popen(
            [sys.executable, "-c", script or SCRIPT, *args], stdin=slave, stdout=slave, stderr=slave, env=environment, close_fds=True,
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
            elif pending and ready in output:
                os.write(master, pending.pop(0))
            if process.poll() is not None and not select.select([master], [], [], 0)[0]:
                break
        process.wait(timeout=5)
        return output.decode("utf-8", "ignore")

    def test_arrow_space_enter_selects_past_a_blocked_row(self):
        output = self.drive([b" ", b"\x1b[B", b"\r"])
        self.assertIn("RESULT ['a']", output)

    def test_filter_then_enter_selects_in_a_real_terminal(self):
        output = self.drive([b"g", b"a", b"\r"], SINGLE)
        self.assertIn("RESULT gamma", output)

    def test_q_cancels_and_restores_the_cursor(self):
        output = self.drive([b"q"])
        self.assertIn("RESULT None", output)
        self.assertIn("\x1b[?25h", output)

    def test_ctrl_c_cancels(self):
        output = self.drive([b"\x03"])
        self.assertIn("RESULT None", output)

    def drive_cdw(self, keys, *query):
        """Run `toast cdw` from inside a repository of a temporary workspace."""
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        home = Path(temp.name).resolve()
        workspace = home / "workspace"
        for name in ("github.com/opspresso/toast-cli", "github.com/acme/api", "gitlab.com/b/api"):
            (workspace / name / ".git").mkdir(parents=True)
        inside = workspace / "github.com/opspresso/toast-cli/src"
        inside.mkdir()
        output = self.drive(keys, CDW, (str(inside), *query), {"HOME": str(home)}, b"Select a directory")
        return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", output), workspace

    def test_cdw_starts_on_the_current_repository(self):
        output, workspace = self.drive_cdw([b"\r"])
        self.assertIn("github.com/opspresso/toast-cli  current", output)
        self.assertIn(f"{workspace}/github.com/opspresso/toast-cli\r\n", output)

    def test_cdw_search_opens_a_filtered_picker(self):
        output, workspace = self.drive_cdw([b"\x1b[B", b"\r"], "api")
        self.assertIn("Select a directory matching 'api'", output)
        self.assertNotIn("toast-cli", output.split("Select a directory", 1)[1].split("Workspace", 1)[0])
        self.assertIn(f"{workspace}/gitlab.com/b/api\r\n", output)

    def test_cdw_escape_cancels_without_a_path(self):
        output, workspace = self.drive_cdw([b"\x1b"])
        self.assertIn("Cancelled", output)
        self.assertNotIn(f"{workspace}/", output)
