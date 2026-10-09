#!/usr/bin/env python3

"""Unit tests for git_plugin (no network or real subprocesses)."""

import os
import click
import subprocess
from pathlib import Path
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
        ), mock.patch("subprocess.run") as run:
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
            git_plugin.os.path, "lexists", return_value=True
        ), mock.patch("subprocess.run") as run:
            with self.assertRaises(click.ClickException):
                git_plugin.GitPlugin.execute("clone", "https://gitlab.clush.net/apps/ws.git")
            run.assert_not_called()


class RepositoryOperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.namespace = Path(self.temp.name) / "workspace" / "gitlab.com" / "org" / "group"
        self.namespace.mkdir(parents=True)
        self.repo = self.namespace / "repo"
        self.repo.mkdir()
        self.cwd = mock.patch.object(git_plugin.os, "getcwd", return_value=str(self.namespace))
        self.cwd.start()
        self.addCleanup(self.cwd.stop)

    def test_destructive_names_are_rejected_without_rewriting(self):
        for name in ("../repo", "re/po", "repo ", "..", "", "-repo"):
            with self.subTest(name=name), self.assertRaises(click.UsageError):
                git_plugin.GitPlugin.execute("rm", name)
            self.assertTrue(self.repo.exists())

    def test_non_repository_cannot_be_removed(self):
        with self.assertRaisesRegex(click.ClickException, "not a Git repository"):
            git_plugin.GitPlugin.execute("rm", "repo")
        self.assertTrue(self.repo.exists())

    def test_symlink_cannot_target_another_repository(self):
        (self.repo / ".git").mkdir()
        (self.namespace / "linked").symlink_to(self.repo, target_is_directory=True)
        with self.assertRaisesRegex(click.ClickException, "symlink"):
            git_plugin.GitPlugin.execute("rm", "linked")
        self.assertTrue(self.repo.exists())

    def test_mirror_uses_nested_namespace_without_mutating_remotes(self):
        (self.repo / ".git").mkdir()
        with mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
            git_plugin.GitPlugin.execute("push", "repo", mirror=True)
        run.assert_called_once_with(
            ["git", "push", "--mirror", "git@gitlab.com:org/group/repo.git"],
            cwd=str(self.repo), capture_output=True, text=True,
        )

    def test_real_local_branch_pull_push_and_remove(self):
        def git(*args, cwd=None):
            return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
        remote = Path(self.temp.name) / "remote.git"
        git("init", "--bare", "--initial-branch=trunk", str(remote))
        git("init", "--initial-branch=trunk", str(self.repo))
        git("-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "--allow-empty", "-m", "fixture", cwd=self.repo)
        git("remote", "add", "origin", str(remote), cwd=self.repo)
        git("push", "-u", "origin", "trunk", cwd=self.repo)
        git_plugin.GitPlugin.execute("pull", "repo", rebase=True)
        git_plugin.GitPlugin.execute("push", "repo")
        git_plugin.GitPlugin.execute("branch", "repo", branch="feature")
        self.assertEqual(git("branch", "--show-current", cwd=self.repo).stdout.strip(), "feature")
        git_plugin.GitPlugin.execute("rm", "repo")
        self.assertFalse(self.repo.exists())
        self.assertTrue(remote.exists())
