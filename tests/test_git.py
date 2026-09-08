#!/usr/bin/env python3

"""Unit tests for git_plugin (no network or real subprocesses)."""

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


class CloneTests(unittest.TestCase):
    def run_clone(self, source, cwd, expected_url, expected_target="ws", command="clone", **kwargs):
        with mock.patch.object(git_plugin.os, "getcwd", return_value=cwd), mock.patch.object(
            git_plugin.os.path, "exists", return_value=False
        ), mock.patch.object(git_plugin.subprocess, "run") as run:
            run.return_value.returncode = 0
            git_plugin.GitPlugin.execute(command, source, **kwargs)
            run.assert_called_once_with(
                ["git", "clone", expected_url, os.path.join(cwd, expected_target)],
                capture_output=True,
                text=True,
            )

    def test_gitlab_explicit_urls(self):
        cwd = "/home/nalbam/workspace/gitlab.clush.net/apps/cdp/be"
        for url in (
            "ssh://git@110.45.156.168:30022/apps/cdp/be/ws.git",
            "https://gitlab.clush.net/apps/cdp/be/ws.git",
            "git@gitlab.clush.net:apps/cdp/be/ws.git",
        ):
            with self.subTest(url=url):
                self.run_clone(url, cwd, url)

    def test_gitlab_name_uses_host_and_nested_namespace(self):
        self.run_clone(
            "ws", "/home/nalbam/workspace/gitlab.clush.net/apps/cdp/be",
            "git@gitlab.clush.net:apps/cdp/be/ws.git",
        )

    def test_github_name(self):
        self.run_clone("ws", "/home/user/workspace/github.com/org", "git@github.com:org/ws.git")

    def test_alias_and_custom_target(self):
        url = "https://gitlab.clush.net/apps/cdp/be/ws.git"
        self.run_clone(
            url, "/home/user/workspace/gitlab.clush.net/apps/cdp/be", url,
            expected_target="custom", command="cl", target="custom",
        )

    def test_existing_target_is_not_cloned(self):
        with mock.patch.object(git_plugin.os, "getcwd", return_value="/home/user/workspace/gitlab.clush.net/apps"), mock.patch.object(
            git_plugin.os.path, "exists", return_value=True
        ), mock.patch.object(git_plugin.subprocess, "run") as run:
            git_plugin.GitPlugin.execute("clone", "https://gitlab.clush.net/apps/ws.git")
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
