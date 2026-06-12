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


if __name__ == "__main__":
    unittest.main()
