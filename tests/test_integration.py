"""Run the real CLI and shell aliases against isolated executable fixtures."""

import os
from pathlib import Path
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
        self.env = {
            **os.environ,
            "PATH": str(self.bin) + os.pathsep + os.environ["PATH"],
            "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
            "TOAST_ENV_STORE_BUCKET": "test-bucket",
            "TOAST_ENV_STORE_PROFILE": "test-profile",
            "TOAST_ENV_STORE_REGION": "eu-west-1",
            "TOAST_ENV_STORE_KMS_KEY": "test-key",
            "TOAST_TEST_REMOTE": str(self.remote),
        }
        self.executable("toast", "from toast import main\nmain()\n")
        self.executable("fzf", "import sys\nprint(sys.stdin.read().splitlines()[0])\n")
        self.executable("aws", textwrap.dedent('''\
            import json, os, shutil, sys
            from pathlib import Path
            args = sys.argv[1:]
            root = Path(os.environ['TOAST_TEST_REMOTE'])
            operation = args[1]
            if os.environ.get('TOAST_TEST_DENIED'):
                print('An error occurred (AccessDenied): fixture denied', file=sys.stderr)
                sys.exit(254)
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
                for command in ("down", "dn", "sync"):
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
