"""Run the real CLI and shell aliases against isolated executable fixtures."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest


class FileSyncIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "workspace" / "github.com" / "org" / "project"
        self.cwd = self.project / "src"
        self.cwd.mkdir(parents=True)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.remote = self.root / "remote"
        self.remote.mkdir()
        # Ambient AWS and env-store settings would change how the CLI resolves
        # its region and bucket, so the fixture sets every value it relies on.
        inherited = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("AWS_", "TOAST_ENV_STORE_"))
        }
        self.env = {
            **inherited,
            "PATH": str(self.bin) + os.pathsep + os.environ["PATH"],
            "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
            "TOAST_ENV_STORE_BUCKET": "test-bucket",
            "TOAST_ENV_STORE_PROFILE": "test-profile",
            "TOAST_ENV_STORE_REGION": "eu-west-1",
            "TOAST_ENV_STORE_KMS_KEY": "test-key",
            "TOAST_TEST_REMOTE": str(self.remote),
            "TOAST_TEST_LOG": str(self.root / "aws.log"),
            # A temporary home keeps the real ~/.config/toast/config out of the run.
            "HOME": str(self.root),
        }
        self.executable("toast", "from toast import main\nmain()\n")
        self.executable("kubectl", "import sys\nprint('fixture denied', file=sys.stderr)\nsys.exit(1)\n")
        self.executable("aws", textwrap.dedent('''\
            import json, os, shutil, sys
            from pathlib import Path
            args = sys.argv[1:]
            root = Path(os.environ['TOAST_TEST_REMOTE'])
            operation = args[1]
            with open(os.environ['TOAST_TEST_LOG'], 'a') as log:
                log.write(json.dumps(args) + '\\n')
            if os.environ.get('TOAST_TEST_DENIED'):
                print('An error occurred (AccessDenied): fixture denied', file=sys.stderr)
                sys.exit(254)
            if operation in ('get', 'get-caller-identity'):
                sys.exit(255)
            if operation == 'get-parameter':
                print('An error occurred (ParameterNotFound): absent', file=sys.stderr)
                sys.exit(254)
            if operation == 'get-parameters-by-path':
                print(json.dumps({'Parameters': []}))
            elif operation == 'list-objects-v2':
                print(json.dumps({'Contents': [{'Key': 'local/org/project/' + p.name, 'LastModified': '2024-01-01T00:00:00Z'} for p in root.iterdir()]}))
            elif operation in ('get-object', 'put-object'):
                key = args[args.index('--key') + 1]
                path = root / key.rsplit('/', 1)[-1]
                assert key.startswith('local/org/project/')
                if operation == 'put-object':
                    source = args[args.index('--body') + 1]
                    assert os.stat(source).st_mode & 0o777 == 0o600
                    shutil.copyfile(source, path)
                    print('{}')
                elif path.exists():
                    shutil.copyfile(path, args[args.index('--output') + 2])
                    print(json.dumps({'LastModified': '2024-01-01T00:00:00Z'}))
                else:
                    print('An error occurred (NoSuchKey): absent', file=sys.stderr)
                    sys.exit(254)
            else:
                raise RuntimeError('Unexpected fixture operation: ' + operation)
        '''))

    def executable(self, name, body):
        path = self.bin / name
        path.write_text(f"#!{sys.executable}\n" + body)
        path.chmod(0o700)

    def command(self, alias, args="", input=""):
        aliases = "alias d='toast dot'\nalias p='toast prompt'\nalias t='toast'\nalias g='toast git'\nalias ssm='toast ssm'\n"
        return subprocess.run(
            ["bash", "--noprofile", "--norc", "-O", "expand_aliases", "-c", aliases + f"{alias} {args}"],
            cwd=self.cwd, env=self.env, input=input, text=True, capture_output=True,
        )

    def test_both_file_kinds_roundtrip_through_shell_aliases(self):
        for alias, filename, kind in (("d", ".env.local", "env-local"), ("p", ".prompt.md", "prompt-md")):
            with self.subTest(kind=kind):
                local = self.project / filename
                content = "KEY=original-secret\r\nNOTE=한글\r\n"
                local.write_bytes(content.encode())
                uploaded = self.command(alias, "up")
                self.assertEqual(uploaded.returncode, 0, uploaded.stderr)
                self.assertEqual((self.remote / kind).read_bytes(), content.encode())
                for command in ("down", "dn"):
                    local.unlink()
                    downloaded = self.command(alias, command)
                    self.assertEqual(downloaded.returncode, 0, downloaded.stderr)
                    self.assertEqual(local.read_bytes(), content.encode())
                    self.assertEqual(local.stat().st_mode & 0o777, 0o600)
                local.write_text("KEY=replacement-secret\n")
                compared = self.command(alias, "diff")
                self.assertEqual(compared.returncode, 0, compared.stderr)
                if alias == "d":
                    self.assertNotIn("original-secret", compared.stdout)
                    self.assertNotIn("replacement-secret", compared.stdout)
                else:
                    self.assertIn("replacement-secret", compared.stdout)
                listed = self.command(alias, "ls")
                self.assertEqual(listed.returncode, 0, listed.stderr)
                self.assertIn("org/project", listed.stdout)

    def aws_calls(self):
        log = self.root / "aws.log"
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    def test_sync_without_a_terminal_changes_nothing(self):
        (self.remote / "env-local").write_text("KEY=remote")
        result = self.command("d", "sync")
        self.assertEqual(result.returncode, 1)
        self.assertIn("needs a terminal", result.stderr)
        # Only the direction that exists is offered, and it overwrites nothing.
        self.assertIn("Run `toast dot down` to download it", result.stderr)
        self.assertNotIn("toast dot up", result.stderr)
        self.assertFalse((self.project / ".env.local").exists())

    def test_overwrite_preview_and_prompt_keep_stdout_empty(self):
        local, remote = self.project / ".env.local", self.remote / "env-local"
        for command, answer, target, kept in (
            ("up", "n\n", "s3://test-bucket/local/org/project/env-local", "KEY=local-secret\n"),
            ("down", "y\n", str(local.resolve()), "KEY=remote-secret\n"),
        ):
            with self.subTest(command=command):
                local.write_text("KEY=local-secret\n")
                remote.write_text("KEY=remote-secret\n")
                result = self.command("d", command, input=answer)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertIn(f"Overwrite {target}", result.stderr)
                self.assertRegex(result.stderr, r"(?m)^-KEY=")
                self.assertNotIn("-secret", result.stderr)
                self.assertEqual(local.read_text(), kept)
                self.assertEqual(remote.read_text(), "KEY=remote-secret\n")

    def sync(self, alias, action, input=""):
        """Run sync as if on a terminal that picks ACTION; answers come from INPUT."""
        # The picker's key loop needs a PTY and has its own tests in test_ui.py.
        self.executable("toast", textwrap.dedent('''\
            import os
            from toast import main, ui
            ui.is_interactive = lambda: True
            ui.choose = lambda options, title, **_: next(o for o in options if os.environ["TOAST_TEST_ACTION"] in o)
            main()
        '''))
        self.env["TOAST_TEST_ACTION"] = action
        log = self.root / "aws.log"
        if log.exists():
            log.unlink()
        return self.command(alias, "sync", input=input)

    def test_sync_confirms_before_replacing_a_changed_copy(self):
        cases = (
            ("d", ".env.local", "env-local", 'KEY=local-secret\nMULTI="first\nhidden-continuation"\n', "KEY=remote-secret\r\nNOTE=한글\r\n"),
            ("p", ".prompt.md", "prompt-md", "# Local\n**local** [link](x)\n", "# Remote\r\n**remote** 한글\r\n"),
        )
        for alias, filename, kind, local_text, remote_text in cases:
            local, remote = self.project / filename, self.remote / kind
            s3 = f"s3://test-bucket/local/org/project/{kind}"
            for action, question in (("Upload", f"Overwrite {s3}? [y/N]"), ("Download", f"Overwrite {local.resolve()} with {s3}? [y/N]")):
                for answer, code in (("y\n", 0), ("n\n", 0), ("", 130)):
                    with self.subTest(kind=kind, action=action, answer=answer):
                        local.write_bytes(local_text.encode())
                        local.chmod(0o644)
                        remote.write_bytes(remote_text.encode())
                        result = self.sync(alias, action, answer)
                        self.assertEqual(result.returncode, code, result.stderr)
                        self.assertEqual(result.stdout, "")
                        self.assertIn(question, result.stderr)
                        if alias == "d":
                            for secret in ("local-secret", "remote-secret", "hidden-continuation"):
                                self.assertNotIn(secret, result.stderr)
                        else:
                            self.assertIn("**local** [link](x)", result.stderr)
                        approved = answer == "y\n"
                        if not approved:
                            self.assertIn("Cancelled", result.stderr)
                        uploaded = approved and action == "Upload"
                        downloaded = approved and action == "Download"
                        self.assertEqual(remote.read_bytes(), (local_text if uploaded else remote_text).encode())
                        self.assertEqual(local.read_bytes(), (remote_text if downloaded else local_text).encode())
                        self.assertEqual(local.stat().st_mode & 0o777, 0o600 if downloaded else 0o644)
                        # Sync reuses its single read of each backend.
                        operations = sorted(call[1] for call in self.aws_calls())
                        self.assertEqual(operations, sorted(["get-object", "get-parameter"] + ["put-object"] * uploaded))

    def test_sync_creates_a_new_copy_without_a_question(self):
        local, remote = self.project / ".prompt.md", self.remote / "prompt-md"
        remote.write_bytes(b"# Remote\r\n")
        result = self.sync("p", "Download")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("Overwrite", result.stderr)
        self.assertIn(f"Downloaded .prompt.md from s3://test-bucket/local/org/project/prompt-md to {local.resolve()}", result.stderr)
        self.assertEqual(local.read_bytes(), b"# Remote\r\n")
        self.assertEqual(local.stat().st_mode & 0o777, 0o600)

        remote.unlink()
        result = self.sync("p", "Upload")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("Overwrite", result.stderr)
        self.assertEqual(remote.read_bytes(), b"# Remote\r\n")

    def test_target_is_shown_on_stderr_from_a_subdirectory(self):
        for alias, program, filename, kind in (("d", "toast dot", ".env.local", "env-local"), ("p", "toast prompt", ".prompt.md", "prompt-md")):
            with self.subTest(kind=kind):
                (self.project / filename).write_text("KEY=local-secret\n")
                (self.remote / kind).write_text("KEY=remote-secret\n")
                calls_before = len(self.aws_calls())
                result = self.command(alias, "diff")
                self.assertEqual(result.returncode, 0, result.stderr)
                expected = {
                    "Command": f"{program} diff",
                    "Project": str(self.project),
                    "Local": str(self.project / filename),
                    "Profile": "test-profile",
                    "Region": "eu-west-1",
                    "S3": f"s3://test-bucket/local/org/project/{kind}",
                    "SSM": f"/toast/local/org/project/{kind} (legacy, read-only)",
                }
                for label, value in expected.items():
                    self.assertRegex(result.stderr, rf"(?m)^{label}\s+{re.escape(value)}$")
                    self.assertNotIn(value, result.stdout)
                self.assertIn(f"Run `{program} up` to keep local, or `{program} down`", result.stderr)
                self.assertNotIn("local-secret", result.stderr)
                self.assertNotIn("remote-secret", result.stderr)
                # The target block adds no AWS call: one S3 read and one SSM read.
                operations = [call[1] for call in self.aws_calls()[calls_before:]]
                self.assertEqual(sorted(operations), ["get-object", "get-parameter"])

    def test_ls_runs_outside_a_workspace_and_keeps_the_target_off_stdout(self):
        (self.remote / "prompt-md").write_text("notes")
        self.cwd = self.root
        result = self.command("p", "ls")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "S3\tS3\t2024-01-01T00:00:00Z\torg/project\n")
        for label, value in (("Command", "toast prompt ls"), ("Scope", ".prompt.md of all projects"), ("Profile", "test-profile"), ("Region", "eu-west-1"), ("S3", "s3://test-bucket/local/")):
            self.assertRegex(result.stderr, rf"(?m)^{label}\s+{re.escape(value)}$")
        self.assertEqual(sorted(call[1] for call in self.aws_calls()), ["get-parameters-by-path", "list-objects-v2"])

    def test_outside_a_workspace_fails_before_aws_with_next_steps(self):
        self.cwd = self.root
        result = self.command("p", "up")
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"Not inside a workspace project: {self.root}", result.stderr)
        self.assertIn("Run `toast prompt up` in ~/workspace/{host}/{org}/{project}", result.stderr)
        self.assertIn("`toast prompt ls` runs anywhere", result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(self.aws_calls(), [])

    def test_missing_copies_name_the_target_and_a_safe_next_step(self):
        local = self.project / ".env.local"
        result = self.command("d", "up")
        self.assertEqual(result.returncode, 1)
        self.assertIn(f".env.local not found: {local}", result.stderr)
        self.assertIn("check it with `toast dot diff`, then run `toast dot down`", result.stderr)
        self.assertEqual(self.aws_calls(), [])

        result = self.command("d", "down")
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"Create {local}, then run `toast dot up`", result.stderr)
        self.assertIn("`toast dot ls` lists the stored projects", result.stderr)

        for command in ("diff", "sync"):
            result = self.command("d", command)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Neither local nor the env-store has .env.local", result.stderr)
            self.assertIn(f"Create {local}, then run `toast dot up`", result.stderr)
            self.assertEqual(result.stdout, "")

        local.write_text("KEY=only-local")
        result = self.command("d", "down")
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"Run `toast dot up` to upload {local}", result.stderr)
        self.assertEqual(local.read_text(), "KEY=only-local")

        result = self.command("d", "sync")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Run `toast dot up` to upload it. The env-store has no copy to overwrite", result.stderr)
        self.assertNotIn("toast dot down", result.stderr)
        self.assertFalse((self.remote / "env-local").exists())

    def test_sync_without_a_terminal_explains_both_directions_and_confirmation(self):
        local = self.project / ".prompt.md"
        local.write_text("local")
        (self.remote / "prompt-md").write_text("remote")
        result = self.command("p", "sync")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Choosing a sync direction for .prompt.md needs a terminal", result.stderr)
        self.assertIn("Run `toast prompt up` to replace the env-store copy, or `toast prompt down` to replace the local file", result.stderr)
        self.assertIn("ask for confirmation before they overwrite an existing copy", result.stderr)
        self.assertEqual(local.read_text(), "local")
        self.assertEqual((self.remote / "prompt-md").read_text(), "remote")

    def test_identical_sync_needs_no_terminal(self):
        for alias, filename, kind in (("d", ".env.local", "env-local"), ("p", ".prompt.md", "prompt-md")):
            with self.subTest(kind=kind):
                (self.project / filename).write_text("same")
                (self.remote / kind).write_text("same")
                result = self.command(alias, "sync")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("Local matches the env-store", result.stderr)
                self.assertEqual(result.stdout, "")

    def test_store_failures_keep_the_cause_and_suggest_the_fix(self):
        self.env["TOAST_TEST_DENIED"] = "1"
        result = self.command("p", "diff")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Cannot compare env-store copies: S3: An error occurred (AccessDenied)", result.stderr)
        self.assertIn("aws sts get-caller-identity --profile test-profile", result.stderr)
        self.assertIn("Nothing was changed", result.stderr)

        del self.env["TOAST_TEST_DENIED"]
        del self.env["TOAST_ENV_STORE_REGION"]
        calls_before = len(self.aws_calls())
        result = self.command("d", "diff")
        self.assertEqual(result.returncode, 1)
        self.assertRegex(result.stderr, r"(?m)^Region\s+not set")
        self.assertIn(f"ENV_STORE_REGION in {self.root}/.config/toast/config", result.stderr)
        # No region is invented for the display or the reads.
        self.assertFalse(any("--region" in call for call in self.aws_calls()[calls_before:]))

        del self.env["TOAST_ENV_STORE_BUCKET"]
        calls_before = len(self.aws_calls())
        result = self.command("d", "diff")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Could not determine the env-store bucket for profile 'test-profile'", result.stderr)
        self.assertIn("Set TOAST_ENV_STORE_BUCKET, or ENV_STORE_BUCKET in", result.stderr)
        # Only the existing lookups run: the profile region and the account id.
        self.assertEqual([call[1] for call in self.aws_calls()[calls_before:]], ["get", "get-caller-identity"])

    def test_denied_store_read_preserves_local_and_remote_through_alias(self):
        local = self.project / ".env.local"
        local.write_text("KEY=keep-local")
        remote = self.remote / "env-local"
        remote.write_text("KEY=keep-remote")
        self.env["TOAST_TEST_DENIED"] = "1"
        result = self.command("d", "up")
        self.assertEqual(result.returncode, 1)
        self.assertIn("AccessDenied", result.stderr)
        self.assertEqual(local.read_text(), "KEY=keep-local")
        self.assertEqual(remote.read_text(), "KEY=keep-remote")

    def test_aliases_retain_documented_argument_order(self):
        for alias, expected in (("g", "REPO_NAME COMMAND"), ("ssm", "[COMMAND] [NAME] [VALUE]")):
            result = self.command(alias, "--help")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(expected, result.stdout)
        self.assertEqual(self.command("t", "version").returncode, 0)


    def test_operational_errors_are_on_stderr_in_real_processes(self):
        # Exercise real streams independently of Click's changing test capture API.
        self.env["TOAST_TEST_DENIED"] = "1"
        for alias, args in (("t", "am"), ("t", "ctx"), ("t", "region"), ("ssm", "get /x")):
            with self.subTest(command=f"{alias} {args}"):
                result = self.command(alias, args)
                self.assertEqual(result.returncode, 1)
                self.assertIn("fixture denied", result.stderr)
                self.assertNotIn("fixture denied", result.stdout)
                self.assertNotIn("✓", result.stdout)
