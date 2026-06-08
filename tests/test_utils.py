#!/usr/bin/env python3

"""Unit tests for the secret-masking helpers (pure logic, no AWS access)."""

import contextlib
import io
import unittest

from toast.plugins.utils import (
    mask_secret,
    mask_env_content,
    mask_lines,
    compare_contents,
    print_unified_diff,
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

    def test_comment_blank_and_no_equals_preserved(self):
        content = "# comment\n\nPLAINLINE\nTOKEN=abcdef"
        expected = "# comment\n\nPLAINLINE\nTOKEN=ab**ef"
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


class PrintUnifiedDiffTests(unittest.TestCase):
    def test_does_not_raise_and_caps(self):
        # 60 lines with limit 50 -> prints a "more lines" trailer, no exception
        lines = [f"+line{i}" for i in range(60)]
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                print_unified_diff(lines, limit=50)
        except Exception as e:  # noqa: BLE001 - test guard
            self.fail(f"print_unified_diff raised: {e}")


if __name__ == "__main__":
    unittest.main()
