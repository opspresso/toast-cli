#!/usr/bin/env python3

"""Unit tests for git_plugin pure helpers (no network/subprocess)."""

import os
import tempfile
import unittest
from unittest import mock

from toast.plugins import git_plugin


class SanitizeRepoNameTests(unittest.TestCase):
    def test_plain_name_unchanged(self):
        self.assertEqual(git_plugin.sanitize_repo_name("my-repo"), "my-repo")

    def test_internal_dot_preserved(self):
        self.assertEqual(git_plugin.sanitize_repo_name("my.repo"), "my.repo")

    def test_invalid_chars_removed(self):
        self.assertEqual(git_plugin.sanitize_repo_name("my/repo:x"), "myrepox")
        self.assertEqual(git_plugin.sanitize_repo_name("a b@c#d"), "abcd")

    def test_leading_trailing_dots_hyphens_stripped(self):
        self.assertEqual(git_plugin.sanitize_repo_name("-lead-"), "lead")
        self.assertEqual(git_plugin.sanitize_repo_name(".dotted."), "dotted")

    def test_empty_or_all_invalid_falls_back(self):
        self.assertEqual(git_plugin.sanitize_repo_name(""), "repo")
        self.assertEqual(git_plugin.sanitize_repo_name("..."), "repo")
        self.assertEqual(git_plugin.sanitize_repo_name("///"), "repo")


class GetGithubHostTests(unittest.TestCase):
    def _run_in(self, cwd):
        """Patch git_plugin's cwd lookup to the given path."""
        return mock.patch.object(git_plugin.os, "getcwd", return_value=cwd)

    def test_default_when_path_not_workspace(self):
        with tempfile.TemporaryDirectory() as d:
            # No /workspace/ segment and no local .toast-config in this dir
            with self._run_in(d), mock.patch.object(
                git_plugin.os.path, "exists", return_value=False
            ):
                self.assertEqual(git_plugin.get_github_host(), "github.com")

    def test_extracts_host_from_workspace_path(self):
        with tempfile.TemporaryDirectory() as base:
            cwd = os.path.join(base, "workspace", "github.enterprise.com", "org", "proj")
            os.makedirs(cwd)
            with self._run_in(cwd):
                self.assertEqual(
                    git_plugin.get_github_host(), "github.enterprise.com"
                )

    def test_org_config_takes_precedence(self):
        with tempfile.TemporaryDirectory() as base:
            org_dir = os.path.join(base, "workspace", "github.enterprise.com", "org")
            cwd = os.path.join(org_dir, "proj")
            os.makedirs(cwd)
            with open(os.path.join(org_dir, ".toast-config"), "w") as f:
                f.write("GITHUB_HOST=custom-host.com\n")
            with self._run_in(cwd):
                self.assertEqual(git_plugin.get_github_host(), "custom-host.com")


if __name__ == "__main__":
    unittest.main()
