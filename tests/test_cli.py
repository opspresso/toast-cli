"""Exercise Click entry points and subprocess failures without external writes."""

import configparser
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import click
from click.shell_completion import ShellComplete
from click.testing import CliRunner
from rich.console import Console

from toast import discover_and_load_plugins, ui
from toast.helpers import CustomHelpCommand, CustomHelpGroup
from toast.plugins import ctx_plugin, env_plugin, git_plugin

ROOT = Path(__file__).resolve().parent.parent


def separate_streams_runner():
    """Click 8.1 mixes stderr into stdout by default; Click 8.2 removed the option."""
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


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

    def test_top_level_help_groups_commands(self):
        group = CustomHelpGroup()
        for plugin in discover_and_load_plugins():
            plugin.register(group)
        result = self.runner.invoke(group, ["--help"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertLess(result.output.index("AWS:"), result.output.index("Kubernetes:"))

    def test_command_help_shows_examples(self):
        result = self.runner.invoke(self.cli, ["ctx", "--help"])
        self.assertIn("Examples:", result.output)
        self.assertIn("toast ctx prod", result.output)

    def test_positional_shortcuts_skip_the_picker(self):
        for arguments, expected in ((["ctx", "dev"], ["kubectl", "config", "use-context", "dev"]), (["region", "us-east-1"], ["aws", "configure", "set", "default.region", "us-east-1"])):
            with self.subTest(arguments=arguments), mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
                result = self.runner.invoke(self.cli, arguments)
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(run.call_args_list[0].args[0], expected)

    def test_completion_prints_a_script(self):
        result = self.runner.invoke(self.cli, ["completion", "zsh"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("_TOAST_COMPLETE", result.output)

    def test_missing_executable_exits_nonzero(self):
        for command in ("am", "ctx", "region"):
            with self.subTest(command=command), mock.patch(
                "subprocess.run", side_effect=FileNotFoundError("Executable not found")
            ):
                result = self.runner.invoke(self.cli, [command])
                self.assertEqual(result.exit_code, 1)
                self.assertIn("is not installed", result.output)

    def test_context_mutation_failure_never_reports_success(self):
        for selections in (["dev"], [ctx_plugin.DELETE, "dev"], [ctx_plugin.DELETE, ctx_plugin.ALL]):
            with self.subTest(selections=selections), mock.patch(
                "subprocess.run", side_effect=[
                    subprocess.CompletedProcess([], 0, "dev\n", ""),
                    subprocess.CompletedProcess([], 0, "dev\n", ""),
                    subprocess.CompletedProcess([], 1, "", "permission denied"),
                ]
            ), mock.patch("toast.ui.choose", side_effect=selections), mock.patch("click.confirm", return_value=True):
                result = self.runner.invoke(self.cli, ["ctx"])
                self.assertEqual(result.exit_code, 1)
                self.assertIn("permission denied", result.output)
                self.assertNotIn("✓", result.output)

    def test_declined_context_deletion_changes_nothing(self):
        for selections in ([ctx_plugin.DELETE, "dev"], [ctx_plugin.DELETE, ctx_plugin.ALL]):
            with self.subTest(selections=selections), mock.patch(
                "subprocess.run", return_value=subprocess.CompletedProcess([], 0, "dev\n", "")
            ) as run, mock.patch("toast.ui.choose", side_effect=selections), mock.patch("click.confirm", return_value=False):
                result = self.runner.invoke(self.cli, ["ctx"])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Cancelled", result.output)
            self.assertEqual(run.call_count, 2)

    def test_aws_api_failure_exits_nonzero(self):
        with mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 255, "", "AccessDenied")):
            result = self.runner.invoke(self.cli, ["am"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("AccessDenied", result.output)

    def test_invalid_profile_preserves_credentials(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "credentials"
            original = "[default]\naws_access_key_id=old\naws_secret_access_key=oldsecret\n[broken]\naws_access_key_id=new\n"
            path.write_text(original)
            with mock.patch.dict(os.environ, {"AWS_SHARED_CREDENTIALS_FILE": str(path)}), mock.patch.object(
                env_plugin.ui, "choose", return_value="broken"
            ):
                result = self.runner.invoke(self.cli, ["env"])
            self.assertEqual(result.exit_code, 1)
            self.assertEqual(path.read_text(), original)

    def test_profile_switch_handles_percent_and_clears_old_token(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "credentials"
            path.write_text("[default]\naws_session_token=old\n[new]\naws_access_key_id=id\naws_secret_access_key=ab%c\n")
            with mock.patch.dict(os.environ, {"AWS_SHARED_CREDENTIALS_FILE": str(path)}), mock.patch.object(
                env_plugin.ui, "choose", return_value="new"
            ), mock.patch.object(env_plugin, "show_identity") as identity:
                result = self.runner.invoke(self.cli, ["env"])
            self.assertEqual(result.exit_code, 0, result.output)
            config = configparser.ConfigParser(interpolation=None)
            config.read(path)
            self.assertEqual(config["default"]["aws_secret_access_key"], "ab%c")
            self.assertNotIn("aws_session_token", config["default"])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            identity.assert_called_once_with(profile="default")


class GitCliTests(unittest.TestCase):
    """Drive `toast git REPO COMMAND` through Click with Git mocked."""

    def setUp(self):
        self.cli = make_cli()
        self.runner = separate_streams_runner()
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.namespace = Path(temp.name) / "workspace" / "gitlab.com" / "org" / "group"
        self.repo = self.namespace / "repo"
        (self.repo / ".git").mkdir(parents=True)
        cwd = mock.patch.object(git_plugin.os, "getcwd", return_value=str(self.namespace))
        cwd.start()
        self.addCleanup(cwd.stop)

    def invoke(self, *arguments, stdout="", stderr="", **options):
        with mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, stdout, stderr)) as run:
            result = self.runner.invoke(self.cli, ["git", *arguments], **options)
        return result, run

    def test_git_output_goes_to_stdout_and_status_to_stderr(self):
        cases = (
            (["repo", "pull", "-r"], ["git", "pull", "--rebase"], self.repo),
            (["repo", "p"], ["git", "pull"], self.repo),
            (["repo", "push"], ["git", "push"], self.repo),
            (["repo", "ps"], ["git", "push"], self.repo),
            (["repo", "branch", "--branch", "feature"], ["git", "checkout", "-b", "feature"], self.repo),
            (["repo", "b", "-b", "feature"], ["git", "checkout", "-b", "feature"], self.repo),
            (["new", "clone"], ["git", "clone", "git@gitlab.com:org/group/new.git", str(self.namespace / "new")], self.namespace / "new"),
            (["new", "cl", "--target", "other"], ["git", "clone", "git@gitlab.com:org/group/new.git", str(self.namespace / "other")], self.namespace / "other"),
        )
        for arguments, expected, path in cases:
            with self.subTest(arguments=arguments):
                result, run = self.invoke(*arguments, stdout="git result\n", stderr="git diagnostic\n")
                self.assertEqual(result.exit_code, 0, result.stderr)
                self.assertEqual(run.call_args.args[0], expected)
                self.assertEqual(result.stdout, "git result\n")
                for shown in ("gitlab.com", "org/group", str(path), "git diagnostic", "✓"):
                    self.assertIn(shown, result.stderr)
                self.assertIn(" ".join(expected[:2]), result.stderr)

    def test_git_failure_exits_nonzero_without_success(self):
        with mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 1, "", "rejected")):
            result = self.runner.invoke(self.cli, ["git", "repo", "push"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("rejected", result.stderr)
        self.assertNotIn("✓", result.stderr)
        self.assertEqual(result.stdout, "")

    SECRETS = ("u5er", "p4ss", "q-tok3n", "fr4g", "ghp_t0k")

    def assert_hidden(self, result):
        for secret in self.SECRETS:
            self.assertNotIn(secret, result.stdout)
            self.assertNotIn(secret, result.stderr)
            self.assertNotIn(secret, str(result.exception or ""))

    def test_git_failure_hides_url_secrets_and_exits_nonzero(self):
        clone_url = "https://u5er:p4ss@127.0.0.1:9/org/repo.git?access_token=q-tok3n#fr4g"
        # Git prints the remote URL even when it is not an argument, and rewrites it:
        # it drops the user name and appends a slash.
        refused = (
            "fatal: unable to access 'https://127.0.0.1:9/org/repo.git?access_token=q-tok3n#fr4g/': "
            "Failed to connect to 127.0.0.1 port 9 after 0 ms: Couldn't connect to server\n"
        )
        for arguments, expected in (
            ([clone_url, "clone", "-t", "new"], ["git", "clone", clone_url, str(self.namespace / "new")]),
            (["repo", "pull"], ["git", "pull"]),
            (["repo", "push"], ["git", "push"]),
        ):
            with self.subTest(arguments=arguments), mock.patch(
                "subprocess.run", return_value=subprocess.CompletedProcess([], 128, "", refused)
            ) as run:
                result = self.runner.invoke(self.cli, ["git", *arguments])
                self.assertEqual(result.exit_code, 1, result.stderr)
                self.assertEqual(run.call_args.args[0], expected)
                self.assert_hidden(result)
                self.assertEqual(result.stdout, "")
                self.assertNotIn("✓", result.stderr)
                self.assertIn("'https://127.0.0.1:9/org/repo.git?access_token=***#***'", result.stderr)
                self.assertIn("Failed to connect to 127.0.0.1 port 9", result.stderr)

    def test_successful_git_diagnostics_hide_url_secrets(self):
        diagnostic = (
            "From https://ghp_t0k@git.example.com/org/repo?access_token=q-tok3n\n"
            "To ssh://git:p4ss@git.example.com:2222/org/repo.git, "
            "https://u5er@mirror.example.com/org/repo.git#fr4g\n"
        )
        for arguments, expected in (
            (["repo", "pull"], ["git", "pull"]),
            (["repo", "push"], ["git", "push"]),
        ):
            with self.subTest(arguments=arguments):
                result, run = self.invoke(*arguments, stdout="Already up to date.\n", stderr=diagnostic)
                self.assertEqual(result.exit_code, 0, result.stderr)
                self.assertEqual(run.call_args.args[0], expected)
                self.assertEqual(result.stdout, "Already up to date.\n")
                self.assert_hidden(result)
                for shown in (
                    "From https://***@git.example.com/org/repo?access_token=***",
                    "ssh://git:***@git.example.com:2222/org/repo.git",
                    "https://***@mirror.example.com/org/repo.git#***",
                    "✓",
                ):
                    self.assertIn(shown, result.stderr)

    def test_url_secrets_containing_quotes_stay_hidden(self):
        # A quote inside a URL must not be taken for the quote Git puts around it.
        secrets = ("qu0te-us'er", "us'er", "qu0te-pa'ss", "pa'ss", "qu0te-q", "qu0te-f", "fr'ag")
        clone_url = (
            "http://qu0te-us'er:qu0te-pa'ss@127.0.0.1:9/org/repo.git"
            "?access_token=prefix'qu0te-q#qu0te-f'fr'ag"
        )
        refused = (
            "fatal: unable to access 'http://127.0.0.1:9/org/repo.git"
            "?access_token=prefix'qu0te-q#qu0te-f'fr'ag/': "
            "Failed to connect to 127.0.0.1 port 9 after 0 ms: Couldn't connect to server\n"
        )
        with mock.patch(
            "subprocess.run", return_value=subprocess.CompletedProcess([], 128, "", refused)
        ) as run:
            result = self.runner.invoke(self.cli, ["git", clone_url, "clone", "-t", "new"])
        self.assertEqual(result.exit_code, 1, result.stderr)
        self.assertEqual(run.call_args.args[0], ["git", "clone", clone_url, str(self.namespace / "new")])
        self.assertEqual(result.stdout, "")
        self.assertNotIn("✓", result.stderr)
        self.assertIn("'http://127.0.0.1:9/org/repo.git?access_token=***#***': Failed to connect", result.stderr)
        diagnostic = (
            "From 'https://qu0te-us'er:qu0te-pa'ss@git.example.com/org/repo?access_token=a'qu0te-q'\n"
            "To \"https://git.example.com/org/repo.git#qu0te-f'fr'ag\", "
            "https://git.example.com/org/repo.git?access_token=a'qu0te-q#fr'ag\n"
        )
        success, _ = self.invoke("repo", "pull", stderr=diagnostic)
        self.assertEqual(success.exit_code, 0, success.stderr)
        for shown in (
            "From 'https://***@git.example.com/org/repo?access_token=***'",
            'To "https://git.example.com/org/repo.git#***", ',
            "https://git.example.com/org/repo.git?access_token=***#***",
        ):
            self.assertIn(shown, success.stderr)
        for output in (result, success):
            for secret in secrets:
                self.assertNotIn(secret, output.stdout)
                self.assertNotIn(secret, output.stderr)
                self.assertNotIn(secret, str(output.exception or ""))

    def test_mirror_runs_only_after_approval_or_yes(self):
        target = "git@gitlab.com:org/group/repo.git"
        for arguments, answer, pushed in (
            (["repo", "push", "--mirror"], "\n", False),
            (["repo", "push", "-m"], "n\n", False),
            (["repo", "ps", "--mirror"], "y\n", True),
            (["repo", "push", "--mirror", "--yes"], None, True),
            (["repo", "push", "-m", "-y"], None, True),
        ):
            with self.subTest(arguments=arguments, answer=answer):
                result, run = self.invoke(*arguments, input=answer)
                self.assertEqual(result.exit_code, 0, result.stderr)
                self.assertIn(target, result.stderr)
                self.assertEqual(run.called, pushed)
                if pushed:
                    self.assertEqual(run.call_args.args[0], ["git", "push", "--mirror", target])
                else:
                    self.assertIn("Cancelled", result.stderr)
                if answer is None:
                    self.assertNotIn("deletes remote refs", result.stderr)
                else:
                    self.assertIn("deletes remote refs", result.stderr)

    def test_invalid_option_combinations_are_usage_errors(self):
        for arguments in (
            ["repo", "push", "--yes"],
            ["repo", "pull", "-y"],
            ["repo", "clone", "--yes"],
            ["repo", "pull", "--mirror"],
            ["repo", "push", "--rebase"],
            ["repo", "pull", "--target", "x"],
            ["repo", "push", "--branch", "x"],
            ["repo", "fetch"],
        ):
            with self.subTest(arguments=arguments):
                result, run = self.invoke(*arguments)
                self.assertEqual(result.exit_code, 2, result.stderr)
                run.assert_not_called()

    def test_rm_yes_still_removes_without_a_confirmation(self):
        with mock.patch("click.confirm") as confirm:
            result, _ = self.invoke("repo", "rm", "--yes")
        self.assertEqual(result.exit_code, 0, result.stderr)
        confirm.assert_not_called()
        self.assertFalse(self.repo.exists())
        self.assertEqual(result.stdout, "")


class InterfaceTests(unittest.TestCase):
    """The contract shared by every command: streams, exit codes and wording."""

    def setUp(self):
        self.cli = make_cli()
        self.runner = CliRunner()

    def run_cli(self, *arguments, env=None):
        return subprocess.run(
            [sys.executable, "-m", "toast", *arguments], capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": str(ROOT), **(env or {})},
        )

    def test_no_arguments_show_help_and_succeed(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Workspace:", result.stdout)

    def test_a_typo_suggests_the_command(self):
        result = self.run_cli("ctxx")
        self.assertEqual(result.returncode, 2)
        self.assertIn("✗", result.stderr)
        self.assertIn("Did you mean 'ctx'?", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_usage_error_names_the_help_command(self):
        result = self.run_cli("git")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Run: toast git --help", result.stderr.replace("python -m toast", "toast").replace("__main__.py", "toast"))

    def test_version_forms_agree(self):
        self.assertEqual(self.run_cli("--version").stdout, self.run_cli("version").stdout)

    def test_help_has_no_color_in_a_pipe_or_with_no_color(self):
        self.assertNotIn("\x1b", self.run_cli("ctx", "--help").stdout)
        with mock.patch.dict(os.environ, {"NO_COLOR": "1"}):
            self.assertEqual(ui.paint("x", bold=True), "x")

    def test_subcommands_appear_in_help_and_completion(self):
        self.assertIn("Commands:", self.runner.invoke(self.cli, ["dot", "--help"]).output)
        names = [item.value for item in ShellComplete(self.cli, {}, "toast", "_TOAST_COMPLETE").get_completions(["git", "repo"], "p")]
        self.assertEqual(names, ["pull", "push"])

    def test_status_stays_out_of_stdout(self):
        with mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", "")):
            result = separate_streams_runner().invoke(self.cli, ["ctx", "dev"])
        self.assertEqual(result.exit_code, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn("✓ Switched", result.stderr)

    def test_long_messages_do_not_wrap_in_a_pipe(self):
        name = "/" + "x" * 200
        with mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, json.dumps({"Parameters": [{"Name": name, "Type": "String"}]}), "")):
            result = self.runner.invoke(self.cli, ["ssm", "ls"])
        self.assertEqual(result.stdout.split("\t")[-1].strip(), name)

    def test_a_bare_separator_is_a_usage_error(self):
        result = self.run_cli("--", "--bogus")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_a_closed_pipe_ends_quietly(self):
        script = f"{sys.executable} -m toast completion zsh | true"
        result = subprocess.run(["bash", "-c", "set -o pipefail; " + script], capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(ROOT)})
        self.assertNotIn("✗", result.stderr)
        self.assertNotIn("Broken pipe", result.stderr)

    def test_completion_stays_silent_when_its_source_fails(self):
        with mock.patch("subprocess.run", side_effect=FileNotFoundError):
            self.assertEqual(ctx_plugin.complete_contexts(None, None, ""), [])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "credentials"
            path.write_text("not an ini file\n")
            with mock.patch.dict(os.environ, {"AWS_SHARED_CREDENTIALS_FILE": str(path)}):
                self.assertEqual(env_plugin.complete_profiles(None, None, ""), [])

    def test_a_pipe_receives_the_complete_diff(self):
        output = io.StringIO()
        with mock.patch.object(ui, "console", Console(file=output)):
            ui.diff([f"+{number}" for number in range(60)], limit=50)
        self.assertEqual(len(output.getvalue().splitlines()), 60)

    def test_unset_region_names_the_fix(self):
        with mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 1, "", "")):
            with self.assertRaisesRegex(click.ClickException, "toast region"):
                ctx_plugin.CtxPlugin._add_cluster()

    def test_table_cells_are_literal_text(self):
        console = Console(file=io.StringIO(), force_terminal=True, width=60)
        with mock.patch.object(ui, "console", console):
            ui.table(("NAME",), [("a/[/b]",)])
        self.assertIn("a/[/b]", console.file.getvalue())

    def test_abort_exits_130(self):
        @click.command(cls=CustomHelpCommand)
        def stop():
            raise click.Abort()

        group = CustomHelpGroup()
        group.add_command(stop)
        result = self.runner.invoke(group, ["stop"])
        self.assertEqual(result.exit_code, 130)
        self.assertIn("Cancelled", result.output)


class ChoiceTests(unittest.TestCase):
    def test_no_terminal_is_an_error_that_names_the_way_out(self):
        with mock.patch.object(ui, "is_interactive", return_value=False):
            with self.assertRaisesRegex(click.ClickException, "needs a terminal"):
                ui.choose(["a"], "Pick")

    def test_no_options_need_no_terminal(self):
        self.assertIsNone(ui.choose([], "Pick"))

    def test_options_keep_their_exact_text(self):
        def pick(picker, *args, **kwargs):
            return picker.rows
        with mock.patch.object(ui, "is_interactive", return_value=True), mock.patch.object(ui, "run_picker", side_effect=pick):
            self.assertEqual(ui.choose([" dev "], "Pick"), " dev ")
