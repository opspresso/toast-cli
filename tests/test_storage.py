#!/usr/bin/env python3

"""Unit tests for the env-store backend pure logic (no AWS access)."""

import os
import tempfile
import unittest
from datetime import timezone
from unittest import mock

from toast.plugins import storage


class ParseTimestampTests(unittest.TestCase):
    def test_iso_with_offset(self):
        dt = storage.parse_timestamp("2024-01-02T03:04:05+00:00")
        self.assertEqual(dt.year, 2024)
        self.assertEqual(dt.tzinfo, timezone.utc)

    def test_iso_with_z(self):
        dt = storage.parse_timestamp("2024-01-02T03:04:05Z")
        self.assertEqual(dt.hour, 3)
        self.assertEqual(dt.tzinfo, timezone.utc)

    def test_iso_fractional(self):
        dt = storage.parse_timestamp("2024-01-02T03:04:05.123456+00:00")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.microsecond, 123456)

    def test_epoch_float(self):
        dt = storage.parse_timestamp(0)
        self.assertEqual(dt.year, 1970)

    def test_none(self):
        self.assertIsNone(storage.parse_timestamp(None))

    def test_blank(self):
        self.assertIsNone(storage.parse_timestamp("   "))

    def test_ordering(self):
        older = storage.parse_timestamp("2024-01-01T00:00:00Z")
        newer = storage.parse_timestamp("2024-02-01T00:00:00+00:00")
        self.assertLess(older, newer)


class DefaultsTests(unittest.TestCase):
    def test_default_profile(self):
        with mock.patch.object(storage, "_current_username", return_value="alice"):
            self.assertEqual(storage.default_profile(), "alice-admin")

    def test_get_account_id_success(self):
        fake = mock.Mock(returncode=0, stdout="123456789012\n", stderr="")
        with mock.patch.object(storage.subprocess, "run", return_value=fake):
            self.assertEqual(storage.get_account_id("p"), "123456789012")

    def test_get_account_id_failure(self):
        fake = mock.Mock(returncode=255, stdout="", stderr="error")
        with mock.patch.object(storage.subprocess, "run", return_value=fake):
            self.assertIsNone(storage.get_account_id("p"))

    def test_default_bucket(self):
        with mock.patch.object(storage, "get_account_id", return_value="123456789012"):
            self.assertEqual(storage.default_bucket("p"), "env-store-123456789012")

    def test_default_bucket_none(self):
        with mock.patch.object(storage, "get_account_id", return_value=None):
            self.assertIsNone(storage.default_bucket("p"))


class ConfigTests(unittest.TestCase):
    def setUp(self):
        # Isolate the `aws configure get region` lookup from the environment.
        p = mock.patch.object(storage, "_profile_region", return_value=None)
        p.start()
        self.addCleanup(p.stop)

    def test_defaults_no_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "config")
            with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(
                storage, "_current_username", return_value="bob"
            ), mock.patch.object(storage, "get_account_id", return_value="111122223333"):
                c = storage.resolve_config(config_path=path, create=False)
            self.assertEqual(c.profile, "bob-admin")
            self.assertEqual(c.bucket, "env-store-111122223333")
            self.assertIsNone(c.kms_key)
            self.assertIsNone(c.region)

    def test_region_from_profile(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "config")
            with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(
                storage, "_profile_region", return_value="ap-northeast-2"
            ), mock.patch.object(storage, "get_account_id", return_value="111122223333"):
                c = storage.resolve_config(config_path=path, create=False)
            self.assertEqual(c.region, "ap-northeast-2")

    def test_bucket_none_on_sts_failure(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "config")
            with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(
                storage, "get_account_id", return_value=None
            ):
                c = storage.resolve_config(config_path=path, create=False)
            self.assertIsNone(c.bucket)

    def test_env_overrides(self):
        env = {
            "TOAST_ENV_STORE_BUCKET": "my-bucket",
            "TOAST_ENV_STORE_PROFILE": "my-profile",
            "TOAST_ENV_STORE_KMS_KEY": "key-123",
            "TOAST_ENV_STORE_REGION": "us-west-2",
        }
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "config")
            with mock.patch.dict(os.environ, env, clear=True):
                c = storage.resolve_config(config_path=path, create=False)
            self.assertEqual(c.bucket, "my-bucket")
            self.assertEqual(c.profile, "my-profile")
            self.assertEqual(c.kms_key, "key-123")
            self.assertEqual(c.region, "us-west-2")

    def test_file_values_used(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "config")
            with open(path, "w") as f:
                f.write("ENV_STORE_BUCKET=file-bucket\nENV_STORE_PROFILE=file-profile\n")
            with mock.patch.dict(os.environ, {}, clear=True):
                c = storage.resolve_config(config_path=path, create=False)
            self.assertEqual(c.bucket, "file-bucket")
            self.assertEqual(c.profile, "file-profile")

    def test_env_beats_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "config")
            with open(path, "w") as f:
                f.write("ENV_STORE_BUCKET=file-bucket\n")
            with mock.patch.dict(
                os.environ, {"TOAST_ENV_STORE_BUCKET": "env-bucket"}, clear=True
            ):
                c = storage.resolve_config(config_path=path, create=False)
            self.assertEqual(c.bucket, "env-bucket")

    def test_prompt_creates_file(self):
        # Prompt order: profile, region, bucket, kms
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "toast", "config")
            self.assertFalse(os.path.exists(path))
            with mock.patch.dict(os.environ, {}, clear=True), mock.patch(
                "sys.stdin.isatty", return_value=True
            ), mock.patch.object(
                storage, "get_account_id", return_value="999988887777"
            ), mock.patch.object(
                storage.click, "confirm", return_value=True
            ), mock.patch.object(
                storage.click, "prompt", side_effect=["p1", "", "b1", ""]
            ):
                c = storage.resolve_config(config_path=path, create=True)
            self.assertTrue(os.path.exists(path))
            self.assertEqual(c.profile, "p1")
            self.assertEqual(c.bucket, "b1")
            self.assertIsNone(c.kms_key)

    def test_decline_does_not_create(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "toast", "config")
            with mock.patch.dict(os.environ, {}, clear=True), mock.patch(
                "sys.stdin.isatty", return_value=True
            ), mock.patch.object(
                storage, "get_account_id", return_value="111122223333"
            ), mock.patch.object(storage.click, "confirm", return_value=False):
                c = storage.resolve_config(config_path=path, create=True)
            self.assertFalse(os.path.exists(path))
            self.assertEqual(c.bucket, "env-store-111122223333")

    def test_no_prompt_when_not_tty(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "toast", "config")
            with mock.patch.dict(os.environ, {}, clear=True), mock.patch(
                "sys.stdin.isatty", return_value=False
            ), mock.patch.object(
                storage, "get_account_id", return_value="111122223333"
            ):
                c = storage.resolve_config(config_path=path, create=True)
            self.assertFalse(os.path.exists(path))
            self.assertEqual(c.bucket, "env-store-111122223333")

    def test_render_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "config")
            with open(path, "w") as f:
                f.write(storage.render_config("b", "p", "k", "r"))
            cfg = storage.read_config_file(path)
            self.assertEqual(cfg["ENV_STORE_BUCKET"], "b")
            self.assertEqual(cfg["ENV_STORE_PROFILE"], "p")
            self.assertEqual(cfg["ENV_STORE_REGION"], "r")

    def test_read_skips_comments(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "config")
            with open(path, "w") as f:
                f.write("# comment\n\n#ENV_STORE_BUCKET=x\nENV_STORE_PROFILE=p\n")
            self.assertEqual(storage.read_config_file(path), {"ENV_STORE_PROFILE": "p"})


class PathTests(unittest.TestCase):
    def test_ssm_path(self):
        self.assertEqual(
            storage.ssm_path("org", "proj", "env-local"),
            "/toast/local/org/proj/env-local",
        )

    def test_s3_key(self):
        self.assertEqual(
            storage.s3_key("org", "proj", "prompt-md"),
            "local/org/proj/prompt-md",
        )

    def test_parse_s3_key(self):
        self.assertEqual(
            storage._parse_s3_key("local/org/proj/env-local"),
            ("org", "proj", "env-local"),
        )
        self.assertIsNone(storage._parse_s3_key("bad/key"))
        self.assertIsNone(storage._parse_s3_key("other/org/proj/env-local"))

    def test_parse_ssm_name(self):
        self.assertEqual(
            storage._parse_ssm_name("/toast/local/org/proj/prompt-md"),
            ("org", "proj", "prompt-md"),
        )
        self.assertIsNone(storage._parse_ssm_name("/foo/bar"))


class AwsCommandTests(unittest.TestCase):
    def test_profile_injected(self):
        cfg = storage.StoreConfig("b", "myprofile", None, None)
        cmd = storage._aws(cfg, ["s3api", "list-objects-v2"])
        self.assertIn("--profile", cmd)
        self.assertEqual(cmd[cmd.index("--profile") + 1], "myprofile")
        self.assertNotIn("--region", cmd)

    def test_region_injected(self):
        cfg = storage.StoreConfig("b", "p", None, "us-west-2")
        cmd = storage._aws(cfg, ["ssm", "get-parameter"])
        self.assertEqual(cmd[cmd.index("--region") + 1], "us-west-2")

    def test_region_override_takes_precedence(self):
        cfg = storage.StoreConfig("b", "p", None, None)
        cmd = storage._aws(cfg, ["ssm", "x"], region="ap-northeast-2")
        self.assertEqual(cmd[cmd.index("--region") + 1], "ap-northeast-2")

    def test_s3_put_uses_kms_server_side_encryption(self):
        cfg = storage.StoreConfig("b", "p", None, None)
        captured = {}

        def fake_run(cmd, **kw):
            captured["cmd"] = cmd
            return mock.Mock(returncode=0, stdout="{}", stderr="")

        with mock.patch.object(storage.subprocess, "run", side_effect=fake_run):
            ok, err = storage.s3_put(cfg, "local/o/p/env-local", "data")

        self.assertTrue(ok)
        cmd = captured["cmd"]
        self.assertIn("--server-side-encryption", cmd)
        self.assertEqual(cmd[cmd.index("--server-side-encryption") + 1], "aws:kms")
        # '--sse' is not a valid s3api option (it is the high-level `aws s3` shorthand)
        self.assertNotIn("--sse", cmd)

    def test_ssm_get_passes_profile_and_region(self):
        cfg = storage.StoreConfig("b", "myprofile", None, "eu-west-1")
        with mock.patch.object(
            storage, "get_ssm_parameter", return_value=("v", "t", None)
        ) as m:
            storage.ssm_get(cfg, "/toast/local/o/p/env-local")
        m.assert_called_once_with(
            "/toast/local/o/p/env-local", profile="myprofile", region="eu-west-1"
        )

    def test_ssm_get_falls_back_to_default_region(self):
        cfg = storage.StoreConfig("b", "myprofile", None, None)
        with mock.patch.object(
            storage, "get_ssm_parameter", return_value=("v", "t", None)
        ) as m:
            storage.ssm_get(cfg, "/toast/local/o/p/env-local")
        m.assert_called_once_with(
            "/toast/local/o/p/env-local",
            profile="myprofile",
            region=storage.DEFAULT_REGION,
        )

    def test_profile_region_lookup(self):
        ok = mock.Mock(returncode=0, stdout="ap-northeast-2\n", stderr="")
        with mock.patch.object(storage.subprocess, "run", return_value=ok):
            self.assertEqual(storage._profile_region("p"), "ap-northeast-2")
        empty = mock.Mock(returncode=0, stdout="\n", stderr="")
        with mock.patch.object(storage.subprocess, "run", return_value=empty):
            self.assertIsNone(storage._profile_region("p"))


class StoreReadTests(unittest.TestCase):
    def _cfg(self):
        return storage.StoreConfig("b", "p", None, None)

    def test_both_s3_newer(self):
        with mock.patch.object(
            storage, "s3_get", return_value=("s3val", "2024-02-01T00:00:00Z", None)
        ), mock.patch.object(
            storage, "ssm_get", return_value=("ssmval", "2024-01-01T00:00:00Z", None)
        ):
            r = storage.store_read(self._cfg(), "o", "p", "env-local")
            self.assertEqual(r.source, "s3")
            self.assertEqual(r.value, "s3val")
            self.assertEqual(r.status, "both")

    def test_both_ssm_newer(self):
        with mock.patch.object(
            storage, "s3_get", return_value=("s3val", "2024-01-01T00:00:00Z", None)
        ), mock.patch.object(
            storage, "ssm_get", return_value=("ssmval", "2024-02-01T00:00:00Z", None)
        ):
            r = storage.store_read(self._cfg(), "o", "p", "env-local")
            self.assertEqual(r.source, "ssm")
            self.assertEqual(r.value, "ssmval")

    def test_tie_prefers_s3(self):
        ts = "2024-01-01T00:00:00Z"
        with mock.patch.object(
            storage, "s3_get", return_value=("s3val", ts, None)
        ), mock.patch.object(storage, "ssm_get", return_value=("ssmval", ts, None)):
            r = storage.store_read(self._cfg(), "o", "p", "env-local")
            self.assertEqual(r.source, "s3")

    def test_s3_only(self):
        with mock.patch.object(
            storage, "s3_get", return_value=("s3val", "2024-01-01T00:00:00Z", None)
        ), mock.patch.object(storage, "ssm_get", return_value=(None, None, None)):
            r = storage.store_read(self._cfg(), "o", "p", "env-local")
            self.assertEqual(r.source, "s3")
            self.assertEqual(r.status, "s3_only")

    def test_ssm_only(self):
        with mock.patch.object(
            storage, "s3_get", return_value=(None, None, None)
        ), mock.patch.object(
            storage, "ssm_get", return_value=("ssmval", "2024-01-01T00:00:00Z", None)
        ):
            r = storage.store_read(self._cfg(), "o", "p", "env-local")
            self.assertEqual(r.source, "ssm")
            self.assertEqual(r.status, "ssm_only")

    def test_none(self):
        with mock.patch.object(
            storage, "s3_get", return_value=(None, None, None)
        ), mock.patch.object(storage, "ssm_get", return_value=(None, None, None)):
            r = storage.store_read(self._cfg(), "o", "p", "env-local")
            self.assertEqual(r.status, "none")
            self.assertIsNone(r.value)
            self.assertIsNone(r.source)

    def test_s3_error_falls_back_to_ssm(self):
        with mock.patch.object(
            storage, "s3_get", return_value=(None, None, "AccessDenied")
        ), mock.patch.object(
            storage, "ssm_get", return_value=("ssmval", "2024-01-01T00:00:00Z", None)
        ):
            r = storage.store_read(self._cfg(), "o", "p", "env-local")
            self.assertEqual(r.source, "ssm")
            self.assertTrue(any(src == "s3" for src, _ in r.errors))


class CmdUpTests(unittest.TestCase):
    """Regression tests for _cmd_up's S3-based no-op decision."""

    def _cfg(self):
        return storage.StoreConfig("b", "p", None, None)

    def _read_result(self, value, source, s3_value, ssm_value, status):
        return storage.ReadResult(
            value, source, s3_value, "ts", ssm_value, "ts", status, []
        )

    def _run_up(self, content, read_result):
        """Call _cmd_up with a real local file and mocked store I/O.

        Returns (write_mock, confirm_mock) so callers can assert whether the
        upload happened and whether a confirm prompt was shown.
        """
        with tempfile.TemporaryDirectory() as d:
            local_path = os.path.join(d, ".env.local")
            with open(local_path, "w") as f:
                f.write(content)
            with mock.patch.object(
                storage, "store_read", return_value=read_result
            ), mock.patch.object(
                storage, "store_write", return_value=(True, None)
            ) as write_mock, mock.patch.object(
                storage.click, "confirm", return_value=True
            ) as confirm_mock:
                storage._cmd_up(
                    self._cfg(), "o", "p", "env-local", ".env.local", local_path
                )
            return write_mock, confirm_mock

    def test_s3_identical_is_noop(self):
        # S3 already has the same content -> no upload, even though SSM also matches
        rr = self._read_result("abc", "s3", "abc", "abc", "both")
        write_mock, _ = self._run_up("abc", rr)
        write_mock.assert_not_called()

    def test_ssm_only_identical_migrates_to_s3(self):
        # Newest (SSM) matches local but S3 is missing -> upload to migrate
        rr = self._read_result("abc", "ssm", None, "abc", "ssm_only")
        write_mock, _ = self._run_up("abc", rr)
        write_mock.assert_called_once()

    def test_s3_different_uploads(self):
        rr = self._read_result("xyz", "s3", "xyz", None, "s3_only")
        write_mock, _ = self._run_up("abc", rr)
        write_mock.assert_called_once()

    def test_s3_absent_uploads_without_confirm(self):
        # Destination (S3) has no copy -> upload immediately, no confirm prompt.
        rr = self._read_result(None, None, None, None, "none")
        write_mock, confirm_mock = self._run_up("abc", rr)
        write_mock.assert_called_once()
        confirm_mock.assert_not_called()

    def test_s3_present_requires_confirm(self):
        rr = self._read_result("xyz", "s3", "xyz", None, "s3_only")
        _, confirm_mock = self._run_up("abc", rr)
        confirm_mock.assert_called_once()


class CmdDownTests(unittest.TestCase):
    """Tests for _cmd_down's confirm-only-on-overwrite behavior."""

    def _cfg(self):
        return storage.StoreConfig("b", "p", None, None)

    def _read_result(self, value, source):
        return storage.ReadResult(
            value,
            source,
            value if source == "s3" else None,
            "ts",
            value if source == "ssm" else None,
            "ts",
            f"{source}_only",
            [],
        )

    def _run_down(self, local_content, read_result):
        """Call _cmd_down; returns (confirm_mock, final local file content)."""
        with tempfile.TemporaryDirectory() as d:
            local_path = os.path.join(d, ".env.local")
            if local_content is not None:
                with open(local_path, "w") as f:
                    f.write(local_content)
            with mock.patch.object(
                storage, "store_read", return_value=read_result
            ), mock.patch.object(
                storage.click, "confirm", return_value=True
            ) as confirm_mock:
                storage._cmd_down(
                    self._cfg(), "o", "p", "env-local", ".env.local", local_path
                )
            written = None
            if os.path.exists(local_path):
                with open(local_path, "r") as f:
                    written = f.read()
            return confirm_mock, written

    def test_local_absent_downloads_without_confirm(self):
        # Destination (local file) does not exist -> download immediately.
        rr = self._read_result("abc", "s3")
        confirm_mock, written = self._run_down(None, rr)
        confirm_mock.assert_not_called()
        self.assertEqual(written, "abc")

    def test_local_present_requires_confirm(self):
        rr = self._read_result("xyz", "s3")
        confirm_mock, written = self._run_down("abc", rr)
        confirm_mock.assert_called_once()
        self.assertEqual(written, "xyz")


class CmdDiffTests(unittest.TestCase):
    def _cfg(self):
        return storage.StoreConfig("b", "p", None, None)

    def _read_result(self, value, source, status):
        return storage.ReadResult(
            value,
            source,
            value if source == "s3" else None,
            "ts",
            value if source == "ssm" else None,
            "ts",
            status,
            [],
        )

    def _run_diff(self, local_content, read_result):
        with tempfile.TemporaryDirectory() as d:
            local_path = os.path.join(d, ".env.local")
            if local_content is not None:
                with open(local_path, "w") as f:
                    f.write(local_content)
            with mock.patch.object(
                storage, "store_read", return_value=read_result
            ), mock.patch.object(storage, "_print_masked_diff") as diff_mock:
                storage._cmd_diff(
                    self._cfg(), "o", "p", "env-local", ".env.local", local_path
                )
            return diff_mock

    def test_identical_does_not_print_diff(self):
        rr = self._read_result("abc", "s3", "s3_only")
        diff_mock = self._run_diff("abc", rr)
        diff_mock.assert_not_called()

    def test_different_prints_diff(self):
        rr = self._read_result("xyz", "s3", "s3_only")
        diff_mock = self._run_diff("abc", rr)
        diff_mock.assert_called_once_with("abc", "xyz", "env-local")

    def test_local_only_does_not_print_diff(self):
        rr = self._read_result(None, None, "none")
        diff_mock = self._run_diff("abc", rr)
        diff_mock.assert_not_called()

    def test_remote_only_does_not_print_diff(self):
        rr = self._read_result("xyz", "ssm", "ssm_only")
        diff_mock = self._run_diff(None, rr)
        diff_mock.assert_not_called()


class StoreListTests(unittest.TestCase):
    def _cfg(self):
        return storage.StoreConfig("b", "p", None, None)

    def test_merge_and_newest(self):
        s3_entries = [
            {"key": "local/org/proj/env-local", "last_modified": "2024-02-01T00:00:00Z"}
        ]
        ssm_entries = [
            {
                "name": "/toast/local/org/proj/env-local",
                "last_modified": "2024-01-01T00:00:00Z",
            },
            {
                "name": "/toast/local/org/other/env-local",
                "last_modified": "2024-01-01T00:00:00Z",
            },
        ]
        with mock.patch.object(
            storage, "s3_list", return_value=(s3_entries, None)
        ), mock.patch.object(storage, "ssm_list", return_value=(ssm_entries, None)):
            rows, errors = storage.store_list(self._cfg(), "env-local")

        self.assertEqual(errors, [])
        self.assertEqual([r["path"] for r in rows], ["org/other", "org/proj"])
        by_path = {r["path"]: r for r in rows}
        # org/proj exists in both; S3 is newer -> current S3, in both backends
        self.assertEqual(by_path["org/proj"]["source"], "s3")
        self.assertTrue(by_path["org/proj"]["in_s3"])
        self.assertTrue(by_path["org/proj"]["in_ssm"])
        # org/other only in SSM
        self.assertEqual(by_path["org/other"]["source"], "ssm")
        self.assertFalse(by_path["org/other"]["in_s3"])

    def test_kind_filter(self):
        s3_entries = [
            {"key": "local/org/proj/prompt-md", "last_modified": "2024-02-01T00:00:00Z"}
        ]
        with mock.patch.object(
            storage, "s3_list", return_value=(s3_entries, None)
        ), mock.patch.object(storage, "ssm_list", return_value=([], None)):
            rows, _ = storage.store_list(self._cfg(), "env-local")
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
