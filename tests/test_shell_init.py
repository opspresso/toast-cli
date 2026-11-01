"""Load the shell-init function into real bash and zsh and check where the shell ends up."""

import fcntl
import json
import os
from pathlib import Path
import select
import shutil
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest

import click
from click.testing import CliRunner

from toast import discover_and_load_plugins

ROOT = Path(__file__).resolve().parent.parent
SHELLS = {"bash": ["--noprofile", "--norc"], "zsh": ["-f"]}
INTERACTIVE = {"bash": ["--noprofile", "--rcfile", "{rc}", "-i"], "zsh": ["--no-globalrcs", "-i"]}

# Records each cdw call, prints TOAST_TEST_TARGET and exits with TOAST_TEST_STATUS.
# Every other command, and cdw with TOAST_TEST_REAL set, runs the real CLI.
FAKE_TOAST = """\
import json, os, sys
args = sys.argv[1:]
if args[:1] == ["cdw"] and not os.environ.get("TOAST_TEST_REAL"):
    with open(os.environ["TOAST_TEST_CALLS"], "a") as calls:
        calls.write(json.dumps({"argv": args, "stdout_tty": sys.stdout.isatty(), "stderr_tty": sys.stderr.isatty()}) + "\\n")
    if os.environ["TOAST_TEST_TARGET"]:
        print(os.environ["TOAST_TEST_TARGET"])
    sys.exit(int(os.environ.get("TOAST_TEST_STATUS", "0")))
os.execv(sys.executable, [sys.executable, "-m", "toast", *args])
"""

SETUP = """\
PS1='READY> '
CDPATH=.:"$TOAST_TEST_ROOT"
eval "$(toast shell-init {shell})"
eval "$(toast shell-init {shell})"
cd -- "$TOAST_TEST_START"
done_() {{ printf '%s\\n%s\\n' "$1" "$PWD" > "$TOAST_TEST_ROOT/result"; printf '@@%s@@\\n' E; exit; }}
"""


def make_cli():
    cli = click.Group()
    for plugin in discover_and_load_plugins():
        plugin.register(cli)
    return cli


class ShellInitCommandTests(unittest.TestCase):
    def test_prints_only_the_function_and_rejects_other_shells(self):
        home = tempfile.TemporaryDirectory()
        self.addCleanup(home.cleanup)
        runner = CliRunner(env={"HOME": home.name, "ZDOTDIR": home.name})
        for shell in ("bash", "zsh"):
            result = runner.invoke(make_cli(), ["shell-init", shell])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertTrue(result.output.startswith("toast() {"), result.output)
            self.assertTrue(result.output.endswith("}\n"), result.output)
        self.assertEqual(os.listdir(home.name), [])
        for arguments in (["shell-init"], ["shell-init", "fish"]):
            self.assertEqual(runner.invoke(make_cli(), arguments).exit_code, 2)


class ShellFunctionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.start = self.root / "start"
        self.target = self.root / """it's "a b" $(touch pwned) ;&|*"""
        for path in (self.start, self.target, self.root / "bin", self.root / "home" / "workspace" / "github.com" / "org" / "proj"):
            path.mkdir(parents=True)
        toast = self.root / "bin" / "toast"
        toast.write_text(f"#!{sys.executable}\n" + FAKE_TOAST)
        toast.chmod(0o700)
        self.env = {
            "PATH": str(self.root / "bin") + os.pathsep + os.environ["PATH"],
            "PYTHONPATH": str(ROOT),
            "HOME": str(self.root / "home"),
            "ZDOTDIR": str(self.root),
            "TERM": "dumb",
            "TOAST_TEST_ROOT": str(self.root),
            "TOAST_TEST_START": str(self.start),
            "TOAST_TEST_CALLS": str(self.root / "calls"),
            "TOAST_TEST_TARGET": str(self.target),
        }

    def require(self, shell):
        if shutil.which(shell, path=self.env["PATH"]) is None:
            if os.environ.get("CI"):
                self.fail(f"{shell} is required in CI")
            self.skipTest(f"{shell} is not installed")

    def calls(self):
        path = self.root / "calls"
        calls = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
        path.unlink(missing_ok=True)
        return calls

    def terminal(self, shell, line, interactive=True, **env):
        """Run LINE in SHELL on a PTY, typed at the prompt or as `-c`; return (status, pwd, terminal output)."""
        rc = self.root / ".zshrc"
        rc.write_text(SETUP.format(shell=shell))
        command = f"printf '@@%s@@\\n' B; {line}; done_ $?"
        if interactive:
            argv = [shell] + [arg.format(rc=rc) for arg in INTERACTIVE[shell]]
        else:
            argv = [shell, *SHELLS[shell], "-c", f'. "{rc}"; {command}']
        master, slave = os.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 500, 0, 0))
        process = subprocess.Popen(
            argv, stdin=slave, stdout=slave, stderr=slave, cwd=self.start, env={**self.env, **env},
            start_new_session=True, preexec_fn=lambda: fcntl.ioctl(0, termios.TIOCSCTTY, 0),
        )
        os.close(slave)
        output, sent, deadline = b"", not interactive, time.monotonic() + 30
        try:
            while time.monotonic() < deadline:
                if not sent and b"READY> " in output:
                    os.write(master, (command + "\n").encode())
                    sent = True
                if select.select([master], [], [], 0.1)[0]:
                    try:
                        chunk = os.read(master, 4096)
                    except OSError:  # Linux reports EIO once the shell exits.
                        break
                    if not chunk:
                        break
                    output += chunk
        finally:
            os.close(master)
            if process.poll() is None:
                process.kill()
            process.wait()
        text = output.decode(errors="replace").replace("\r", "")
        self.assertIn("@@E@@", text, text)
        status, pwd = (self.root / "result").read_text().splitlines()
        return int(status), pwd, text.split("@@B@@\n", 1)[1].split("@@E@@", 1)[0]

    def test_cdw_at_the_terminal_changes_the_shell_directory(self):
        for shell in SHELLS:
            with self.subTest(shell=shell):
                self.require(shell)
                status, pwd, output = self.terminal(shell, "toast cdw 'two words' '*' --flag")
                self.assertEqual((status, pwd, output), (0, str(self.target), ""))
                self.assertEqual(self.calls(), [{"argv": ["cdw", "two words", "*", "--flag"], "stdout_tty": False, "stderr_tty": True}])
                self.assertFalse((self.root / "pwned").exists())
                status, pwd, output = self.terminal(shell, "toast cdw proj", TOAST_TEST_REAL="1")
                self.assertEqual((status, pwd), (0, str(self.root / "home" / "workspace" / "github.com" / "org" / "proj")))
                self.assertIn("Target", output)

    def test_failure_empty_result_and_missing_directory_stay_put(self):
        missing = str(self.root / "gone")
        for shell in SHELLS:
            with self.subTest(shell=shell):
                self.require(shell)
                for env, expected in (({"TOAST_TEST_STATUS": "3"}, 3), ({"TOAST_TEST_TARGET": ""}, 0), ({"TOAST_TEST_TARGET": missing}, 1)):
                    with self.subTest(env=env):
                        status, pwd, _ = self.terminal(shell, "toast cdw q", **env)
                        self.assertEqual((status, pwd), (expected, str(self.start)))

    def test_help_pipes_and_substitution_keep_printing_the_path(self):
        for shell in SHELLS:
            with self.subTest(shell=shell):
                self.require(shell)
                for line in ("toast cdw --help", "toast cdw q | cat", "command toast cdw q"):
                    with self.subTest(line=line):
                        status, pwd, output = self.terminal(shell, line)
                        self.assertEqual((status, pwd), (0, str(self.start)))
                        self.assertIn(str(self.target), output)
                status, pwd, output = self.terminal(shell, 'd=$(toast cdw q); [ "$d" = "$TOAST_TEST_TARGET" ]')
                self.assertEqual((status, pwd, output), (0, str(self.start), ""))
                status, _, output = self.terminal(shell, "toast version")
                self.assertEqual(status, 0)
                self.assertIn("toast-cli", output)

    def test_a_script_keeps_the_directory_and_receives_the_path(self):
        for shell in SHELLS:
            with self.subTest(shell=shell):
                self.require(shell)
                status, pwd, output = self.terminal(shell, "toast cdw q", interactive=False)
                self.assertEqual((status, pwd), (0, str(self.start)))
                self.assertIn(str(self.target), output)
                script = f'eval "$(toast shell-init {shell})"; toast cdw q; pwd'
                result = subprocess.run([shell, *SHELLS[shell], "-c", script], cwd=self.start, env=self.env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, f"{self.target}\n{self.start}\n")


if __name__ == "__main__":
    unittest.main()
