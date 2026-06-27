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


if __name__ == "__main__":
    unittest.main()
