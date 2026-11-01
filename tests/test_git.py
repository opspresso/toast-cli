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
        ), mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
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
            with self.assertRaises(click.ClickException) as raised:
                git_plugin.GitPlugin.execute("clone", "https://gitlab.clush.net/apps/ws.git")
            run.assert_not_called()
        self.assertIn("/home/user/workspace/gitlab.clush.net/apps/ws already exists", raised.exception.message)
        self.assertIn("--target", raised.exception.message)

    def test_clone_shows_the_target_without_url_credentials(self):
        url = "https://user:s3cr3t-token@gitlab.example.com/apps/ws.git"
        cwd = "/home/user/workspace/gitlab.example.com/apps"
        with mock.patch.object(git_plugin.ui, "fields") as fields:
            self.run_clone(url, cwd, url)
        shown = dict(fields.call_args.args[0])
        self.assertEqual(shown["Path"], os.path.join(cwd, "ws"))
        self.assertEqual(shown["Source"], "https://***@gitlab.example.com/apps/ws.git")
        self.assertNotIn("s3cr3t-token", str(fields.call_args))

    def test_clone_hides_query_tokens_but_passes_the_original_url(self):
        cwd = "/home/user/workspace/git.example.com/org"
        for url, source in (
            (
                "https://git.example.com/org/repo.git?access_token=q-tok3n",
                "https://git.example.com/org/repo.git?access_token=***",
            ),
            (
                "https://user:p4ss@git.example.com/org/repo.git?private_token=q-tok3n",
                "https://***@git.example.com/org/repo.git?private_token=***",
            ),
        ):
            with self.subTest(url=url), mock.patch.object(git_plugin.ui, "fields") as fields:
                self.run_clone(url, cwd, url, expected_target="repo")
                shown = dict(fields.call_args.args[0])
                self.assertEqual(shown["Source"], source)
                self.assertEqual(shown["Path"], os.path.join(cwd, "repo"))
                self.assertNotIn("q-tok3n", str(fields.call_args))
                self.assertNotIn("p4ss", str(fields.call_args))

    def test_failed_clone_error_hides_url_secrets_but_git_gets_the_original_url(self):
        url = "https://u5er:p4ss@127.0.0.1:9/org/repo.git?access_token=q-tok3n#fr4g"
        cwd = "/home/user/workspace/127.0.0.1/org"
        # Git 2.39 drops the user name and appends a slash before it prints the URL.
        stderr = (
            "Cloning into 'repo'...\n"
            "fatal: unable to access 'https://127.0.0.1:9/org/repo.git?access_token=q-tok3n#fr4g/': "
            "Failed to connect to 127.0.0.1 port 9 after 0 ms: Couldn't connect to server\n"
        )
        failed = subprocess.CompletedProcess([], 128, "", stderr)
        with mock.patch.object(git_plugin.os, "getcwd", return_value=cwd), mock.patch.object(
            git_plugin.os.path, "lexists", return_value=False
        ), mock.patch("subprocess.run", return_value=failed) as run, mock.patch.object(git_plugin.ui, "success") as success:
            with self.assertRaises(click.ClickException) as raised:
                git_plugin.GitPlugin.execute("clone", url)
        run.assert_called_once_with(
            ["git", "clone", url, os.path.join(cwd, "repo")], capture_output=True, text=True
        )
        success.assert_not_called()
        message = raised.exception.format_message()
        for secret in ("u5er", "p4ss", "q-tok3n", "fr4g"):
            self.assertNotIn(secret, message)
        self.assertIn("'https://127.0.0.1:9/org/repo.git?access_token=***#***'", message)
        self.assertIn("Failed to connect to 127.0.0.1 port 9", message)


class RedactUrlTests(unittest.TestCase):
    def test_credentials_are_hidden(self):
        for url, shown in (
            ("https://user:pass@host.com/org/repo.git", "https://***@host.com/org/repo.git"),
            ("https://ghp_token@github.com/org/repo.git", "https://***@github.com/org/repo.git"),
            ("ssh://git:pass@host.com:2222/org/repo.git", "ssh://git:***@host.com:2222/org/repo.git"),
            ("https://host.com/org/repo.git?access_token=tok", "https://host.com/org/repo.git?access_token=***"),
            ("https://u:p@host.com/org/repo.git?a=1&tok", "https://***@host.com/org/repo.git?a=***&***"),
            ("https://host.com/org/repo.git#tok", "https://host.com/org/repo.git#***"),
        ):
            with self.subTest(url=url):
                self.assertEqual(git_plugin.redact_url(url), shown)

    def test_urls_without_credentials_are_unchanged(self):
        for url in (
            "ssh://git@110.45.156.168:30022/apps/cdp/be/ws.git",
            "https://gitlab.clush.net/apps/cdp/be/ws.git",
            "git@gitlab.clush.net:apps/cdp/be/ws.git",
        ):
            with self.subTest(url=url):
                self.assertEqual(git_plugin.redact_url(url), url)

    def test_every_url_in_text_is_redacted(self):
        text = (
            "From https://ghp_t0k@git.example.com/org/repo?access_token=q-tok3n\n"
            "To ssh://git:p4ss@git.example.com:2222/org/repo.git and "
            "https://mirror.example.com/org/repo.git#fr4g\n"
            "fatal: repository 'http://u:p@host.example.com/org/repo.git/' not found"
        )
        self.assertEqual(
            git_plugin.redact_urls(text),
            "From https://***@git.example.com/org/repo?access_token=***\n"
            "To ssh://git:***@git.example.com:2222/org/repo.git and "
            "https://mirror.example.com/org/repo.git#***\n"
            "fatal: repository 'http://***@host.example.com/org/repo.git/' not found",
        )

    def test_a_quote_inside_a_url_does_not_end_it(self):
        cases = (
            (
                "fatal: unable to access 'http://h.example/r.git?access_token=prefix'SYNTH_Q#SYNTH_F/': refused",
                "fatal: unable to access 'http://h.example/r.git?access_token=***#***': refused",
            ),
            (
                "fatal: repository 'https://us'er:pa'ss@h.example/o'rg/r.git' not found",
                "fatal: repository 'https://***@h.example/o'rg/r.git' not found",
            ),
            (
                'To "ssh://git:pa"ss@h.example:2222/r.git#fr"ag", next',
                'To "ssh://git:***@h.example:2222/r.git#***", next',
            ),
            (
                "From https://h.example/r?access_token=a'SYNTH_Q'b#fr'ag\n * branch main",
                "From https://h.example/r?access_token=***#***\n * branch main",
            ),
            # A URL contains no whitespace, so it ends at the quote before a space.
            (
                "error: 'https://h.example/r?t=a'SYNTH_Q' isn't valid, 'x'",
                "error: 'https://h.example/r?t=***' isn't valid, 'x'",
            ),
        )
        for text, shown in cases:
            with self.subTest(text=text):
                self.assertEqual(git_plugin.redact_urls(text), shown)

    def test_several_quoted_urls_on_one_line_are_redacted_separately(self):
        cases = (
            (
                "warning: remote 'https://first.example/r' redirected to "
                "'https://SYNTH_USER:SYNTH_PASS@second.example/r'",
                "warning: remote 'https://first.example/r' redirected to "
                "'https://***@second.example/r'",
            ),
            (
                'redirect "https://u:SYNTH_A@a.example/r?t=SYNTH_B" -> '
                '"ssh://git:SYNTH_C@b.example:2222/r.git#SYNTH_D".',
                'redirect "https://***@a.example/r?t=***" -> '
                '"ssh://git:***@b.example:2222/r.git#***".',
            ),
            (
                "fatal: 'https://h.example/r?t=a'SYNTH_E' and "
                "'https://us'er:SYNTH_F@i.example/o'rg/r.git': refused",
                "fatal: 'https://h.example/r?t=***' and "
                "'https://***@i.example/o'rg/r.git': refused",
            ),
            # An unmatched quote does not join the next quoted URL to the first one.
            (
                "'https://a.example/x'y 'https://u:SYNTH_G@b.example/r'",
                "'https://a.example/x'y 'https://***@b.example/r'",
            ),
        )
        for text, shown in cases:
            with self.subTest(text=text):
                redacted = git_plugin.redact_urls(text)
                self.assertEqual(redacted, shown)
                self.assertNotIn("SYNTH_", redacted)

    def test_whitespace_inside_a_url_does_not_end_its_secrets(self):
        # Git prints a malformed URL as given, whitespace included.
        cases = (
            (
                "fatal: unable to access 'http://127.0.0.1:9/org/repo.git"
                "?access_token=prefix SYNTH_Q#SYNTH_F/': URL using bad/illegal format",
                "fatal: unable to access 'http://127.0.0.1:9/org/repo.git"
                "?access_token=***#***': URL using bad/illegal format",
            ),
            (
                "fatal: repository 'https://us er:SYNTH_P ass@h.example/r.git/' not found",
                "fatal: repository 'https://***@h.example/r.git/' not found",
            ),
            (
                "From https://SYNTH_U x:SYNTH_P@h.example/r\nTo ssh://git:SYNTH_P x@h.example:2222/r.git",
                "From https://***@h.example/r\nTo ssh://git:***@h.example:2222/r.git",
            ),
            (
                "From https://h.example/r?access_token=a SYNTH_Q#SYNTH_F\n * branch main",
                "From https://h.example/r?access_token=***#***\n * branch main",
            ),
            (
                "warning: redirecting to 'https://h.example/r?t=a SYNTH_A' from "
                "'https://u:SYNTH_B@h.example/r#x SYNTH_C'",
                "warning: redirecting to 'https://h.example/r?t=***' from "
                "'https://***@h.example/r#***'",
            ),
        )
        for text, shown in cases:
            with self.subTest(text=text):
                redacted = git_plugin.redact_urls(text)
                self.assertEqual(redacted, shown)
                self.assertNotIn("SYNTH_", redacted)

    def test_secret_parts_of_known_urls_are_hidden_wherever_they_appear(self):
        url = "https://SYNTH_U ser:SYNTH_P@h.example/r.git?access_token=a SYNTH_Q#SYNTH_F"
        cases = (
            (
                f"From {url}\n",
                "From https://***@h.example/r.git?access_token=***#***\n",
            ),
            (
                "fatal: unable to access 'https://h.example/r.git?access_token=a SYNTH_Q#SYNTH_F/': refused",
                "fatal: unable to access 'https://h.example/r.git?access_token=***#***': refused",
            ),
        )
        for text, shown in cases:
            with self.subTest(text=text):
                redacted = git_plugin.redact_urls(text, ["git", "clone", url, "/tmp/r"])
                self.assertEqual(redacted, shown)
                self.assertNotIn("SYNTH_", redacted)

    def test_known_arguments_without_url_secrets_change_nothing(self):
        text = "Cloning into '/tmp/r'...\ngit@h.example:org/r.git ssh://git@h.example:2222/r.git"
        arguments = ["git", "clone", "git@h.example:org/r.git", "ssh://git@h.example:2222/r.git", "/tmp/r"]
        self.assertEqual(git_plugin.redact_urls(text, arguments), text)

    def test_a_malformed_known_url_is_hidden_after_its_scheme(self):
        url = "https://[SYNTH_T@bad/org/repo.git"
        self.assertEqual(
            git_plugin.redact_urls(f"fatal: bad URL {url}", [url]),
            "fatal: bad URL https://***",
        )

    def test_text_without_url_secrets_is_unchanged(self):
        for text in (
            "",
            "Already up to date.",
            "To git@github.com:org/repo.git\n   abc..def  main -> main",
            "From https://github.com/org/repo\n * branch main -> FETCH_HEAD",
            "ssh: connect to host 127.0.0.1 port 22: Connection refused",
        ):
            with self.subTest(text=text):
                self.assertEqual(git_plugin.redact_urls(text), text)

    def test_a_malformed_url_is_hidden_instead_of_raising(self):
        text = "fatal: unable to access 'https://[t0ken@bad/org/repo.git': bad URL"
        shown = git_plugin.redact_urls(text)
        self.assertEqual(shown, "fatal: unable to access 'https://***': bad URL")


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
                git_plugin.GitPlugin.execute("rm", name, yes=True)
            self.assertTrue(self.repo.exists())

    def test_non_repository_cannot_be_removed(self):
        with self.assertRaisesRegex(click.ClickException, "not a Git repository"):
            git_plugin.GitPlugin.execute("rm", "repo", yes=True)
        self.assertTrue(self.repo.exists())

    def test_symlink_cannot_target_another_repository(self):
        (self.repo / ".git").mkdir()
        (self.namespace / "linked").symlink_to(self.repo, target_is_directory=True)
        with self.assertRaisesRegex(click.ClickException, "symlink"):
            git_plugin.GitPlugin.execute("rm", "linked", yes=True)
        self.assertTrue(self.repo.exists())

    def test_mirror_uses_nested_namespace_without_mutating_remotes(self):
        (self.repo / ".git").mkdir()
        with mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", "")) as run, mock.patch(
            "click.confirm", return_value=True
        ) as confirm:
            git_plugin.GitPlugin.execute("push", "repo", mirror=True)
        run.assert_called_once_with(
            ["git", "push", "--mirror", "git@gitlab.com:org/group/repo.git"],
            cwd=str(self.repo), capture_output=True, text=True,
        )
        prompt = confirm.call_args.args[0]
        self.assertIn("git@gitlab.com:org/group/repo.git", prompt)
        self.assertIn("overwrites remote branches and tags", prompt)
        self.assertIn("deletes remote refs", prompt)
        self.assertIs(confirm.call_args.kwargs["default"], False)

    def test_mirror_destination_follows_github_host(self):
        (self.repo / ".git").mkdir()
        (self.namespace.parent / ".toast-config").write_text("GITHUB_HOST=mirror-host.example\n")
        with mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", "")) as run, mock.patch(
            "click.confirm", return_value=True
        ) as confirm:
            git_plugin.GitPlugin.execute("push", "repo", mirror=True)
        self.assertEqual(run.call_args.args[0], ["git", "push", "--mirror", "git@mirror-host.example:org/group/repo.git"])
        self.assertIn("git@mirror-host.example:org/group/repo.git", confirm.call_args.args[0])

    def test_declined_mirror_does_not_push(self):
        (self.repo / ".git").mkdir()
        with mock.patch("subprocess.run") as run, mock.patch("click.confirm", return_value=False), mock.patch.object(
            git_plugin.ui, "cancelled"
        ) as cancelled:
            git_plugin.GitPlugin.execute("push", "repo", mirror=True)
        run.assert_not_called()
        cancelled.assert_called_once()

    def test_yes_skips_only_the_mirror_confirmation(self):
        (self.repo / ".git").mkdir()
        with mock.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", "")) as run, mock.patch(
            "click.confirm"
        ) as confirm:
            git_plugin.GitPlugin.execute("push", "repo", mirror=True, yes=True)
            git_plugin.GitPlugin.execute("push", "repo")
        confirm.assert_not_called()
        self.assertEqual([call.args[0][:3] for call in run.call_args_list], [["git", "push", "--mirror"], ["git", "push"]])

    def test_yes_is_rejected_outside_rm_and_mirror(self):
        (self.repo / ".git").mkdir()
        for command in ("push", "ps", "pull", "branch", "clone"):
            with self.subTest(command=command), mock.patch("subprocess.run") as run:
                with self.assertRaisesRegex(click.UsageError, "--yes requires rm or push --mirror"):
                    git_plugin.GitPlugin.execute(command, "repo", yes=True)
                run.assert_not_called()

    def test_invalid_github_host_names_the_file_and_does_not_push(self):
        (self.repo / ".git").mkdir()
        config = self.namespace.parent / ".toast-config"
        config.write_text("GITHUB_HOST=bad host\n")
        with mock.patch("subprocess.run") as run, self.assertRaises(click.ClickException) as raised:
            git_plugin.GitPlugin.execute("push", "repo", mirror=True, yes=True)
        run.assert_not_called()
        self.assertIn(str(config), raised.exception.message)
        self.assertIn("remove the line", raised.exception.message)

    def test_missing_repository_names_the_path_and_the_clone_command(self):
        with self.assertRaises(click.ClickException) as raised:
            git_plugin.GitPlugin.execute("pull", "absent")
        self.assertIn(str(self.namespace / "absent"), raised.exception.message)
        self.assertIn("toast git absent clone", raised.exception.message)

    def test_non_repository_names_the_absolute_path(self):
        with self.assertRaises(click.ClickException) as raised:
            git_plugin.GitPlugin.execute("pull", "repo")
        self.assertIn(f"{self.repo} is not a Git repository", raised.exception.message)

    def test_outside_workspace_names_the_directory_and_where_to_go(self):
        with mock.patch.object(git_plugin.os, "getcwd", return_value="/tmp/elsewhere"), mock.patch("subprocess.run") as run:
            with self.assertRaises(click.ClickException) as raised:
                git_plugin.GitPlugin.execute("pull", "repo")
        run.assert_not_called()
        self.assertIn("/tmp/elsewhere", raised.exception.message)
        self.assertIn("cd ~/workspace/", raised.exception.message)

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
        git_plugin.GitPlugin.execute("rm", "repo", yes=True)
        self.assertFalse(self.repo.exists())
        self.assertTrue(remote.exists())

    def test_rm_asks_first_and_names_uncommitted_work(self):
        subprocess.run(["git", "init", str(self.repo)], check=True, capture_output=True)
        (self.repo / "note.txt").write_text("work")
        with mock.patch("click.confirm", return_value=False), mock.patch.object(git_plugin.ui, "warning") as warning:
            git_plugin.GitPlugin.execute("rm", "repo")
        self.assertTrue(self.repo.exists())
        self.assertIn("1 uncommitted changes", warning.call_args_list[0].args[0])
