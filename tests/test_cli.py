"""Exercise Click entry points and subprocess failures without external writes."""

import configparser
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import click
from click.testing import CliRunner
from rich.console import Console

from toast import discover_and_load_plugins
from toast.plugins import cdw_plugin, env_plugin, utils


def make_cli():
    cli = click.Group()
    for plugin in discover_and_load_plugins():
        plugin.register(cli)
    return cli


class CliTests(unittest.TestCase):
    def setUp(self):
        self.cli = make_cli()
        self.runner = CliRunner()

    def test_import_does_not_modify_click(self):
        result = subprocess.run(
            [sys.executable, "-c", "import click; echo = click.echo; show = click.ClickException.show; import toast; assert click.echo is echo; assert click.ClickException.show is show"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_executable_exits_nonzero(self):
        for command in ("am", "ctx", "region"):
            with self.subTest(command=command), mock.patch(
                "subprocess.run", side_effect=FileNotFoundError("Executable not found")
            ):
                result = self.runner.invoke(self.cli, [command])
                self.assertEqual(result.exit_code, 1)
                self.assertIn("Executable not found", result.output)

    def test_context_mutation_failure_never_reports_success(self):
        for selections in (["dev"], ["[Del...]", "dev"], ["[Del...]", "[All...]"]):
            with self.subTest(selections=selections), mock.patch(
                "subprocess.run", side_effect=[
                    subprocess.CompletedProcess([], 0, "dev\n", ""),
                    subprocess.CompletedProcess([], 1, "", "permission denied"),
                ]
            ), mock.patch("toast.plugins.ctx_plugin.select_from_list", side_effect=selections):
                result = self.runner.invoke(self.cli, ["ctx"])
                self.assertEqual(result.exit_code, 1)
                self.assertIn("permission denied", result.output)
                self.assertNotIn("✓", result.output)

    def test_aws_api_failure_exits_nonzero(self):
        with mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 255, "", "AccessDenied")):
            result = self.runner.invoke(self.cli, ["am"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("AccessDenied", result.output)

    def test_cdw_returns_project_path_without_status_output(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            repo = workspace / "gitlab.com" / "org" / "group" / "repo"
            (repo / ".git" / "objects").mkdir(parents=True)
            (repo / "node_modules").mkdir()
            with mock.patch.object(cdw_plugin.os.path, "expanduser", return_value=str(workspace)), mock.patch.object(
                cdw_plugin, "select_from_list", return_value=str(repo)
            ) as select:
                result = self.runner.invoke(self.cli, ["cdw"])
            self.assertEqual(result.stdout, str(repo) + "\n")
            self.assertIn(str(repo), select.call_args.args[0])
            self.assertNotIn(str(repo / "node_modules"), select.call_args.args[0])

    def test_cdw_initial_setup_only_writes_stderr(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(
            cdw_plugin.os.path, "expanduser", return_value=str(Path(temp) / "workspace")
        ), mock.patch.object(cdw_plugin, "console", Console(file=io.StringIO())):
            result = self.runner.invoke(self.cli, ["cdw"])
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(result.stdout, "")

    def test_invalid_profile_preserves_credentials(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "credentials"
            original = "[default]\naws_access_key_id=old\naws_secret_access_key=oldsecret\n[broken]\naws_access_key_id=new\n"
            path.write_text(original)
            with mock.patch.dict(os.environ, {"AWS_SHARED_CREDENTIALS_FILE": str(path)}), mock.patch.object(
                env_plugin, "select_from_list", return_value="broken"
            ):
                result = self.runner.invoke(self.cli, ["env"])
            self.assertEqual(result.exit_code, 1)
            self.assertEqual(path.read_text(), original)

    def test_profile_switch_handles_percent_and_clears_old_token(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "credentials"
            path.write_text("[default]\naws_session_token=old\n[new]\naws_access_key_id=id\naws_secret_access_key=ab%c\n")
            with mock.patch.dict(os.environ, {"AWS_SHARED_CREDENTIALS_FILE": str(path)}), mock.patch.object(
                env_plugin, "select_from_list", return_value="new"
            ), mock.patch.object(env_plugin, "show_identity") as identity:
                result = self.runner.invoke(self.cli, ["env"])
            self.assertEqual(result.exit_code, 0, result.output)
            config = configparser.ConfigParser(interpolation=None)
            config.read(path)
            self.assertEqual(config["default"]["aws_secret_access_key"], "ab%c")
            self.assertNotIn("aws_session_token", config["default"])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            identity.assert_called_once_with(profile="default")


class SelectionTests(unittest.TestCase):
    def test_cancel_and_no_match_are_not_failures(self):
        for code in (1, 130):
            with mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], code, "", "")):
                self.assertIsNone(utils.select_from_list(["dev"]))

    def test_fzf_failure_is_not_cancellation(self):
        with mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 2, "", "invalid flag")):
            with self.assertRaisesRegex(click.ClickException, "invalid flag"):
                utils.select_from_list(["dev"])

    def test_selection_preserves_spaces(self):
        with mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, " dev \n", "")):
            self.assertEqual(utils.select_from_list([" dev "]), " dev ")
