#!/usr/bin/env python3

"""Unit tests for the secret-masking helpers (pure logic, no AWS access)."""

import subprocess
import unittest
from unittest import mock

import click

from toast.plugins.utils import (
    run_command,
    mask_secret,
    mask_env_content,
    mask_lines,
    compare_contents,
)


class MaskSecretTests(unittest.TestCase):
    def test_none(self):
        self.assertIsNone(mask_secret(None))

    def test_empty(self):
        self.assertEqual(mask_secret(""), "")

    def test_short_fully_masked(self):
        # length <= visible * 2 -> all stars
        self.assertEqual(mask_secret("ab"), "**")
        self.assertEqual(mask_secret("abcd"), "****")

    def test_normal_partial_reveal(self):
        # "abcdef" (6): first 2 + 2 stars + last 2
        self.assertEqual(mask_secret("abcdef"), "ab**ef")
        # "secret123" (9): first 2 + 5 stars + last 2
        self.assertEqual(mask_secret("secret123"), "se*****23")

    def test_long_middle_capped(self):
        value = "A" + "x" * 30 + "Z"  # length 32
        masked = mask_secret(value)
        self.assertTrue(masked.startswith("A" + value[1]))
        self.assertTrue(masked.endswith(value[-2:]))
        self.assertEqual(masked.count("*"), 12)  # middle capped at 12

    def test_custom_visible(self):
        self.assertEqual(mask_secret("abcdefgh", visible=3), "abc**fgh")


class MaskEnvContentTests(unittest.TestCase):
    def test_none(self):
        self.assertIsNone(mask_env_content(None))

    def test_key_preserved_value_masked(self):
        self.assertEqual(mask_env_content("API_KEY=secret123"), "API_KEY=se*****23")

    def test_comments_and_blanks_preserved_but_unrecognized_lines_masked(self):
        content = "# comment\n\nPLAINLINE\nTOKEN=abcdef"
        expected = "# comment\n\nPL*****NE\nTOKEN=ab**ef"
        self.assertEqual(mask_env_content(content), expected)

    def test_value_with_equals_kept(self):
        # base64 padding: split on the first '=' only, value masked as a whole
        self.assertEqual(mask_env_content("DATA=ab==cd=="), "DATA=ab****==")

    def test_empty_value(self):
        self.assertEqual(mask_env_content("EMPTY="), "EMPTY=")


class MaskLinesTests(unittest.TestCase):
    def test_none(self):
        self.assertIsNone(mask_lines(None))

    def test_single_line(self):
        self.assertEqual(mask_lines("secret123"), "se*****23")

    def test_blank_lines_preserved(self):
        content = "tokenvalue\n\nothertoken"
        masked = mask_lines(content)
        lines = masked.split("\n")
        self.assertEqual(lines[1], "")
        self.assertEqual(lines[0], mask_secret("tokenvalue"))
        self.assertEqual(lines[2], mask_secret("othertoken"))


class CompareContentsTests(unittest.TestCase):
    def test_both_missing(self):
        self.assertEqual(compare_contents(None, None), "both_missing")

    def test_remote_only(self):
        self.assertEqual(compare_contents(None, "x"), "remote_only")

    def test_local_only(self):
        self.assertEqual(compare_contents("x", None), "local_only")

    def test_identical(self):
        self.assertEqual(compare_contents("x", "x"), "identical")

    def test_different(self):
        self.assertEqual(compare_contents("x", "y"), "different")


class MultilineMaskTests(unittest.TestCase):
    def test_quoted_continuations_never_expose_keys_or_comments(self):
        content = 'PRIVATE_KEY="firstsecret\ncontinuation=secretbody\n#not-a-comment\nlastsecret"\n#safe-comment\nNEXT=nextsecret'
        masked = mask_env_content(content)
        for secret in ("firstsecret", "continuation", "secretbody", "#not-a-comment", "lastsecret", "nextsecret"):
            self.assertNotIn(secret, masked)
        self.assertIn("#safe-comment", masked)
        self.assertIn("NEXT=", masked)

    def test_single_quoted_and_exported_values(self):
        masked = mask_env_content("export TOKEN='secret\nsecondline'\nNEXT=othersecret")
        self.assertIn("export TOKEN=", masked)
        self.assertIn("NEXT=", masked)
        self.assertNotIn("secondline", masked)

    def test_zero_visible_does_not_reveal_entire_value(self):
        self.assertEqual(mask_secret("secret", visible=0), "******")

if __name__ == "__main__":
    unittest.main()


class RunCommandTests(unittest.TestCase):
    def test_success_returns_the_result_unchanged(self):
        done = subprocess.CompletedProcess([], 0, "out https://u:p@h/x\n", "err https://u:p@h/x\n")
        for redact in (None, lambda text: "hidden"):
            with self.subTest(redact=redact), mock.patch("subprocess.run", return_value=done) as run:
                result = run_command(["tool", "arg"], redact=redact, cwd="/tmp")
                self.assertIs(result, done)
                run.assert_called_once_with(["tool", "arg"], capture_output=True, text=True, cwd="/tmp")

    def test_failure_names_the_tool_and_its_stderr(self):
        failed = subprocess.CompletedProcess([], 254, "", "An error occurred (AccessDenied)\n")
        with mock.patch("subprocess.run", return_value=failed):
            with self.assertRaises(click.ClickException) as raised:
                run_command(["aws", "ssm", "delete-parameter"])
        self.assertEqual(raised.exception.message, "aws failed: An error occurred (AccessDenied)")

    def test_failure_without_stderr_names_the_exit_status(self):
        for redact in (None, lambda text: "hidden"):
            with self.subTest(redact=redact), mock.patch(
                "subprocess.run", return_value=subprocess.CompletedProcess([], 3, "", " \n")
            ):
                with self.assertRaises(click.ClickException) as raised:
                    run_command(["kubectl", "config"], redact=redact)
                self.assertEqual(raised.exception.message, "kubectl failed: exit status 3")

    def test_redact_rewrites_only_the_failure_message(self):
        failed = subprocess.CompletedProcess([], 1, "", "fatal: secret-value\n")
        with mock.patch("subprocess.run", return_value=failed) as run:
            with self.assertRaises(click.ClickException) as raised:
                run_command(["git", "pull"], redact=lambda text: text.replace("secret-value", "***"))
        self.assertEqual(raised.exception.message, "git failed: fatal: ***")
        self.assertNotIn("redact", run.call_args.kwargs)

    def test_missing_executable_is_reported(self):
        with mock.patch("subprocess.run", side_effect=FileNotFoundError):
            with self.assertRaises(click.ClickException) as raised:
                run_command(["kubectl"], redact=str.upper)
        self.assertEqual(raised.exception.message, "kubectl is not installed")
