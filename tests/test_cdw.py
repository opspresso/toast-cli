"""Drive `toast cdw` through Click in a temporary home with a fake workspace."""

import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import click
from click.testing import CliRunner

from toast import discover_and_load_plugins

ROOT = Path(__file__).resolve().parent.parent
# The shell function documented in README.md, with toast run from this checkout.
SHELL_FUNCTION = """
toast() { "$PYTHON" -m toast "$@"; }
c() {
  local dir
  dir="$(toast cdw "$@")" || return
  [ -z "$dir" ] || cd -- "$dir"
}
"""


def separate_streams_runner():
    """Click 8.1 mixes stderr into stdout by default; Click 8.2 removed the option."""
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


class CdwTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.home = Path(temp.name).resolve()
        self.workspace = self.home / "workspace"
        home = mock.patch.dict(os.environ, {"HOME": str(self.home)})
        home.start()
        self.addCleanup(home.stop)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.home)
        self.cli = click.Group()
        for plugin in discover_and_load_plugins():
            plugin.register(self.cli)

    def repo(self, relative, git_file=False):
        path = self.workspace / relative
        path.mkdir(parents=True)
        if git_file:
            (path / ".git").write_text("gitdir: /elsewhere/.git/worktrees/x\n")
        else:
            (path / ".git" / "objects").mkdir(parents=True)
        return path

    def standard_workspace(self):
        self.toast = self.repo("github.com/opspresso/toast-cli")
        (self.toast / "src" / "deep").mkdir(parents=True)
        self.github_api = self.repo("github.com/acme/api")
        self.gitlab_api = self.repo("gitlab.com/b/api")
        self.nested = self.repo("gitlab.com/apps/cdp/be/ws", git_file=True)
        (self.nested / "inner").mkdir()
        self.spaced = self.repo("github.com/acme/my repo")
        (self.workspace / "github.com" / ".hidden" / "x").mkdir(parents=True)

    def invoke(self, *arguments, interactive=False, choice=None):
        with mock.patch("toast.ui.is_interactive", return_value=interactive), mock.patch("toast.ui.choose", return_value=choice) as choose:
            result = separate_streams_runner().invoke(self.cli, ["cdw", *arguments])
        return result, choose

    def relative(self, paths):
        return [os.path.relpath(path, self.workspace) for path in paths]

    def assert_printed(self, result, path):
        self.assertEqual(result.exit_code, 0, result.stderr)
        self.assertEqual(result.stdout, f"{path}\n")

    def test_picker_offers_namespaces_and_repositories_and_marks_the_current_one(self):
        self.standard_workspace()
        os.chdir(self.toast / "src" / "deep")
        result, choose = self.invoke(interactive=True, choice=str(self.toast))
        self.assert_printed(result, self.toast)
        options = self.relative(choose.call_args.args[0])
        self.assertEqual(options, [
            "github.com", "github.com/acme", "github.com/acme/api", "github.com/acme/my repo", "github.com/opspresso",
            "github.com/opspresso/toast-cli", "gitlab.com", "gitlab.com/apps", "gitlab.com/apps/cdp", "gitlab.com/apps/cdp/be",
            "gitlab.com/apps/cdp/be/ws", "gitlab.com/b", "gitlab.com/b/api",
        ])
        self.assertEqual(choose.call_args.kwargs["current"], str(self.toast))
        self.assertIn(str(self.workspace), choose.call_args.args[1])
        self.assertEqual(choose.call_args.kwargs["label"](str(self.nested)), "gitlab.com/apps/cdp/be/ws")
        for line in (f"Workspace  {self.workspace}", "Current    github.com/opspresso/toast-cli", "Target     github.com/opspresso/toast-cli"):
            self.assertIn(line, result.stderr)

    def test_no_query_keeps_the_picker_for_a_single_directory(self):
        (self.workspace / "github.com").mkdir(parents=True)
        result, choose = self.invoke(interactive=True, choice=None)
        self.assertEqual(self.relative(choose.call_args.args[0]), ["github.com"])
        self.assertEqual(result.stdout, "")

    def test_current_is_the_nearest_candidate_ancestor(self):
        self.standard_workspace()
        for cwd, expected in ((self.nested / "inner", self.nested), (self.workspace / "github.com" / ".hidden" / "x", self.workspace / "github.com"), (self.workspace, None), (self.home, None)):
            with self.subTest(cwd=cwd):
                os.chdir(cwd)
                _, choose = self.invoke(interactive=True, choice=None)
                self.assertEqual(choose.call_args.kwargs["current"], None if expected is None else str(expected))

    def test_a_query_that_names_one_directory_skips_the_picker(self):
        self.standard_workspace()
        for query, expected in (
            (["github.com/acme/api"], self.github_api),
            (["github.com/acme/api/"], self.github_api),
            (["github.com/acme/my repo"], self.spaced),
            (["my", "repo"], self.spaced),
            (["toast-cli"], self.toast),
            (["opspresso/toast-cli"], self.toast),
            (["cdp"], self.workspace / "gitlab.com/apps/cdp"),
            (["tst", "cli"], self.toast),
        ):
            with self.subTest(query=query):
                result, choose = self.invoke(*query)
                self.assert_printed(result, expected)
                choose.assert_not_called()
                self.assertIn("Target", result.stderr)

    def test_same_named_repositories_open_a_filtered_picker(self):
        self.standard_workspace()
        os.chdir(self.gitlab_api)
        result, choose = self.invoke("api", interactive=True, choice=str(self.gitlab_api))
        self.assert_printed(result, self.gitlab_api)
        self.assertEqual(self.relative(choose.call_args.args[0]), ["github.com/acme/api", "gitlab.com/b/api"])
        self.assertEqual(choose.call_args.kwargs["current"], str(self.gitlab_api))

    def test_fuzzy_matches_are_offered_best_first(self):
        self.standard_workspace()
        _, choose = self.invoke("acme", "a", interactive=True, choice=None)
        self.assertEqual(self.relative(choose.call_args.args[0]), [
            "github.com/acme", "github.com/acme/api", "github.com/acme/my repo", "gitlab.com/apps/cdp/be", "gitlab.com/apps/cdp/be/ws",
        ])

    def test_an_ambiguous_query_without_a_terminal_lists_paths_and_fails(self):
        self.standard_workspace()
        result, choose = self.invoke("api")
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.stdout, "")
        choose.assert_not_called()
        self.assertIn("  github.com/acme/api\n  gitlab.com/b/api\n", result.stderr)
        self.assertIn("toast cdw github.com/acme/api", result.stderr)

    def test_an_ambiguous_example_quotes_a_path_with_spaces(self):
        self.repo("github.com/a/my repo")
        self.repo("github.com/b/my repo")
        result, _ = self.invoke("my repo")
        self.assertIn("toast cdw 'github.com/a/my repo'", result.stderr)

    def test_no_match_fails_with_a_next_step_in_both_modes(self):
        self.standard_workspace()
        for interactive in (False, True):
            with self.subTest(interactive=interactive):
                result, choose = self.invoke("zzzq", interactive=interactive)
                self.assertEqual(result.exit_code, 1)
                self.assertEqual(result.stdout, "")
                choose.assert_not_called()
                self.assertIn("matches 'zzzq'", result.stderr)
                self.assertIn("toast cdw", result.stderr)

    def test_a_query_never_reaches_outside_the_candidates(self):
        self.standard_workspace()
        (self.home / "outside").mkdir()
        for query in ("../outside", str(self.home / "outside"), "github.com/opspresso/toast-cli/src"):
            with self.subTest(query=query):
                result, _ = self.invoke(query)
                self.assertNotEqual(result.exit_code, 0)
                self.assertEqual(result.stdout, "")

    def test_no_query_without_a_terminal_suggests_a_query(self):
        self.standard_workspace()
        result, _ = self.invoke()
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("toast cdw QUERY", result.stderr)

    def test_cancel_prints_nothing_to_stdout(self):
        self.standard_workspace()
        result, _ = self.invoke(interactive=True, choice=None)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("Cancelled", result.stderr)

    def test_initial_setup_only_writes_stderr(self):
        for query in ((), ("toast-cli",)):
            with self.subTest(query=query):
                result, choose = self.invoke(*query)
                self.assertEqual(result.exit_code, 0, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertIn("Created", result.stderr)
                self.assertTrue((self.workspace / "github.com").is_dir())
                choose.assert_not_called()
                (self.workspace / "github.com").rmdir()

    def test_shell_function_changes_directory_only_after_a_result(self):
        environment = dict(os.environ, HOME=str(self.home), PYTHON=sys.executable, PYTHONPATH=str(ROOT))

        def run(query):
            script = f"{SHELL_FUNCTION}\nc {query}; status=$?; pwd; exit $status"
            return subprocess.run(["bash", "-c", script], cwd=self.home, env=environment, capture_output=True, text=True)

        setup = run("")
        self.assertEqual((setup.returncode, setup.stdout), (0, f"{self.home}\n"), setup.stderr)
        self.repo("github.com/opspresso/toast-cli")
        missing = run("zzzq")
        self.assertEqual((missing.returncode, missing.stdout), (1, f"{self.home}\n"), missing.stderr)
        found = run(shlex.quote("toast-cli"))
        self.assertEqual((found.returncode, found.stdout), (0, f"{self.workspace / 'github.com/opspresso/toast-cli'}\n"), found.stderr)


if __name__ == "__main__":
    unittest.main()
