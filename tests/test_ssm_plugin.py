#!/usr/bin/env python3

"""Unit tests for SSM plugin pure command helpers (no AWS access)."""

import unittest
from unittest import mock

from toast.plugins.ssm_plugin import SsmPlugin


class SsmDiffTests(unittest.TestCase):
    def test_missing_parameter_does_not_print_diff(self):
        with mock.patch.object(
            SsmPlugin, "_fetch_parameter_value", return_value=(None, None)
        ), mock.patch("toast.plugins.ssm_plugin.print_unified_diff") as print_diff:
            SsmPlugin._diff_parameter("/x", "new", lambda args: args)
        print_diff.assert_not_called()

    def test_identical_parameter_does_not_print_diff(self):
        with mock.patch.object(
            SsmPlugin, "_fetch_parameter_value", return_value=("same", None)
        ), mock.patch("toast.plugins.ssm_plugin.print_unified_diff") as print_diff:
            SsmPlugin._diff_parameter("/x", "same", lambda args: args)
        print_diff.assert_not_called()

    def test_different_parameter_prints_masked_diff(self):
        with mock.patch.object(
            SsmPlugin, "_fetch_parameter_value", return_value=("oldsecret", None)
        ), mock.patch("toast.plugins.ssm_plugin.show_diff") as show_diff, mock.patch(
            "toast.plugins.ssm_plugin.print_unified_diff"
        ) as print_diff:
            show_diff.return_value = ["diff"]
            SsmPlugin._diff_parameter("/x", "newsecret", lambda args: args)
        show_diff.assert_called_once_with(
            "ne*****et",
            "ol*****et",
            local_name="NEW",
            remote_name="CURRENT",
        )
        print_diff.assert_called_once_with(["diff"])


class SsmPutTests(unittest.TestCase):
    def _fake_put_run(self):
        result = mock.Mock()
        result.returncode = 0
        result.stdout = '{"Version": 1}'
        result.stderr = ""
        return result

    def test_new_parameter_skips_confirm(self):
        # Destination has no existing value -> store immediately without asking.
        with mock.patch.object(
            SsmPlugin, "_fetch_parameter_value", return_value=(None, None)
        ), mock.patch(
            "toast.plugins.ssm_plugin.subprocess.run",
            return_value=self._fake_put_run(),
        ) as run_mock, mock.patch(
            "toast.plugins.ssm_plugin.click.confirm"
        ) as confirm:
            SsmPlugin._put_parameter("/x", "new", lambda args: args)
        confirm.assert_not_called()
        run_mock.assert_called_once()

    def test_existing_parameter_requires_confirm(self):
        with mock.patch.object(
            SsmPlugin, "_fetch_parameter_value", return_value=("old", None)
        ), mock.patch(
            "toast.plugins.ssm_plugin.subprocess.run",
            return_value=self._fake_put_run(),
        ) as run_mock, mock.patch(
            "toast.plugins.ssm_plugin.click.confirm", return_value=False
        ) as confirm:
            SsmPlugin._put_parameter("/x", "new", lambda args: args)
        confirm.assert_called_once()
        run_mock.assert_not_called()


class SsmCliTests(unittest.TestCase):
    def setUp(self):
        import click
        from click.testing import CliRunner
        self.cli = click.Group()
        SsmPlugin.register(self.cli)
        self.runner = CliRunner()

    def test_documented_get_order_and_aliases(self):
        import subprocess
        value = '[bold]literal[/bold]' + 'x' * 100
        import json
        for args in (["get", "/x"], ["g", "/x"], ["/x"]):
            with self.subTest(args=args), mock.patch("subprocess.run", return_value=subprocess.CompletedProcess(
                [], 0, json.dumps({"Parameter": {"Value": value, "Type": "SecureString"}}), ""
            )) as run:
                result = self.runner.invoke(self.cli, ["ssm", *args, "--region", "eu-west-1", "--reveal"])
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertIn(value + "\n", result.stdout)
                self.assertEqual(run.call_args.args[0], ["aws", "ssm", "get-parameter", "--name", "/x", "--with-decryption", "--output", "json", "--region", "eu-west-1"])

    def test_invalid_arguments_do_not_invoke_aws(self):
        for args in (["get"], ["put", "/x"], ["delete"], ["unknown"], ["get", "/x", "extra"]):
            with self.subTest(args=args), mock.patch("subprocess.run") as run:
                result = self.runner.invoke(self.cli, ["ssm", *args])
                self.assertEqual(result.exit_code, 2, result.output)
                run.assert_not_called()

    def test_denied_read_never_becomes_blind_overwrite(self):
        import subprocess
        with mock.patch("subprocess.run", return_value=subprocess.CompletedProcess(
            [], 255, "", "An error occurred (AccessDeniedException): denied"
        )) as run:
            result = self.runner.invoke(self.cli, ["ssm", "put", "/x", "newsecret"])
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(run.call_count, 1)
        self.assertNotIn("Successfully", result.output)

    def test_new_value_is_private_literal_and_creation_cannot_overwrite(self):
        import json
        import os
        from pathlib import Path
        import subprocess
        paths = []
        secret = "file://literal-secret"

        def aws(args, **kwargs):
            if args[2] == "get-parameter":
                return subprocess.CompletedProcess(args, 254, "", "An error occurred (ParameterNotFound): missing")
            self.assertNotIn(secret, args)
            path = Path(args[args.index("--cli-input-json") + 1].removeprefix("file://"))
            paths.append(path)
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(path.read_text()), {"Name": "/x", "Value": secret, "Type": "SecureString", "Overwrite": False})
            return subprocess.CompletedProcess(args, 0, '{"Version": 1}', "")

        with mock.patch("subprocess.run", side_effect=aws):
            result = self.runner.invoke(self.cli, ["ssm", "put", "/x", secret])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(len(paths), 1)
        self.assertFalse(paths[0].exists())

    def test_failed_write_does_not_echo_secret_payload(self):
        import subprocess
        with mock.patch.object(SsmPlugin, "_fetch_parameter_value", return_value=(None, None)), mock.patch(
            "subprocess.run", return_value=subprocess.CompletedProcess([], 255, "", "Invalid input: supersecret")
        ):
            result = self.runner.invoke(self.cli, ["ssm", "p", "/x", "supersecret"])
        self.assertEqual(result.exit_code, 1)
        self.assertNotIn("supersecret", result.output)

    def test_empty_account_can_create_first_parameter(self):
        import subprocess
        with mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, '{"Parameters": []}', "")), mock.patch(
            "toast.plugins.ssm_plugin.select_from_list", return_value="[New] Create new parameter..."
        ), mock.patch.object(SsmPlugin, "_create_new_parameter") as create:
            result = self.runner.invoke(self.cli, ["ssm"])
        self.assertEqual(result.exit_code, 0)
        create.assert_called_once()

    def test_get_rejects_malformed_success_response(self):
        import subprocess
        with mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, '{}', "")):
            result = self.runner.invoke(self.cli, ["ssm", "get", "/x"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Parameter.Value is missing", result.output)

if __name__ == "__main__":
    unittest.main()
