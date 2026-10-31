"""Exercise `toast clean` in a temporary home with mocked process boundaries."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import click
from click.testing import CliRunner

from toast.plugins import clean_catalog, clean_plugin
from toast.plugins.clean_plugin import CleanPlugin


class CleanTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.processes = ""
        self.devices = ""
        self.failing = ()
        self.runtimes = {}
        self.commands = []
        self.cli = click.Group()
        CleanPlugin.register(self.cli)

        self.cache = self.put("Library/Caches/pnpm/data")
        self.derived = self.put("Library/Developer/Xcode/DerivedData/app/data")
        self.work = self.put("actions-runner/_work/repo/data")
        self.avd = self.put(".android/avd/phone.avd/data")
        self.put("Library/Developer/CoreSimulator/Devices/ABC/data")
        self.put("gocache/data")

        environment = mock.patch.dict(os.environ)
        environment.start()
        self.addCleanup(environment.stop)
        os.environ.pop("ANDROID_HOME", None)

        for target, replacement in (
            ("platform.system", mock.Mock(return_value="Darwin")),
            ("subprocess.run", self.run_stub),
            ("toast.plugins.clean_catalog.is_dgx", mock.Mock(return_value=False)),
            ("toast.plugins.clean_catalog.path_size", lambda path: 1024 if path.exists() else 0),
            ("shutil.which", lambda name: f"/stub/{name}" if name in ("go", "docker", "xcrun") else None),
            ("pathlib.Path.home", mock.Mock(return_value=self.home)),
        ):
            patcher = mock.patch(target, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)

    def put(self, relative):
        path = self.home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("data")
        return path

    def run_stub(self, args, **kwargs):
        args = list(args)

        def ok(stdout=""):
            return subprocess.CompletedProcess(args, 0, stdout, "")

        if args[0] == "ps":
            return ok(self.processes)
        if args[:4] == ["xcrun", "simctl", "runtime", "list"]:
            return ok(json.dumps(self.runtimes))
        if args[0] == "git":
            return subprocess.CompletedProcess(args, 1 if Path(args[2]).name == "tracked" else 0, "", "")
        if args[:3] == ["xcrun", "simctl", "list"]:
            return ok(self.devices)
        if args[:2] == ["go", "env"]:
            return ok(str(self.home / "gocache") + "\n")
        if args[:2] == ["docker", "system"]:
            rows = [("Images", "2GB (50%)"), ("Containers", "0B (0%)"), ("Local Volumes", "1.5GB (90%)"), ("Build Cache", "500MB")]
            return ok("\n".join(json.dumps({"Type": kind, "Reclaimable": size}) for kind, size in rows))
        self.commands.append(" ".join(args))
        if args[0] in self.failing:
            return subprocess.CompletedProcess(args, 1, "", "boom")
        return ok()

    def invoke(self, *args, input=None):
        return CliRunner().invoke(self.cli, ["clean", *args], input=input)

    def number(self, name):
        listing = self.invoke("--list").output
        for line in listing.splitlines():
            if name in line.split():
                return line.split()[0]
        self.fail(f"{name} not listed:\n{listing}")

    def test_list_shows_sizes_and_removes_nothing(self):
        result = self.invoke("--list")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertRegex(result.output, r"2\.0 GiB\s+download\s+docker-images")
        self.assertRegex(result.output, r"1\.5 GiB\s+data\s+docker-volumes")
        self.assertIn("Reclaimable", result.output)
        self.assertEqual(self.commands, [])
        self.assertTrue(self.cache.exists())

    def test_no_input_removes_nothing(self):
        result = self.invoke()
        # Click versions disagree on whether an empty stream is an empty answer or EOF.
        self.assertIn(result.exit_code, (0, 130), result.output)
        self.assertIn("Cancelled", result.output)
        self.assertTrue(self.cache.exists())

    def test_selected_numbers_are_the_only_items_removed(self):
        chosen = f"{self.number('dev-caches')},{self.number('docker-images')}"
        result = self.invoke(input=f"{chosen}\ny\n")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertFalse(self.cache.exists())
        self.assertTrue(self.derived.exists())
        self.assertEqual(self.commands, ["docker image prune -af"])

    def test_declined_confirmation_removes_nothing(self):
        result = self.invoke(input="a\nn\n")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("Cancelled", result.output)
        self.assertEqual(self.commands, [])
        self.assertTrue(self.cache.exists())

    def test_quit_removes_nothing(self):
        result = self.invoke(input="q\n")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertTrue(self.cache.exists())

    def test_all_keeps_data_items_and_kept_directories(self):
        result = self.invoke(input="a\ny\n")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertFalse(self.cache.exists())
        self.assertFalse(self.work.parent.exists())
        self.assertTrue(self.work.parent.parent.is_dir())
        self.assertTrue(self.avd.exists())
        self.assertFalse([command for command in self.commands if "volume" in command or "simctl" in command])

    def test_data_item_warns_before_removal(self):
        result = self.invoke("android-avds", input="y\n")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("cannot be restored", result.output)
        self.assertFalse(self.avd.parent.exists())

    def test_yes_skips_confirmation_and_needs_names(self):
        self.assertEqual(self.invoke("--yes").exit_code, 2)
        result = self.invoke("go-cache", "--yes")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(self.commands, ["go clean -cache"])

    def test_active_build_blocks_build_items_only(self):
        self.processes = "/runner/bin/Runner.Worker\n"
        self.assertIn("blocked: build running", self.invoke("--list").output)
        result = self.invoke("xcode-derived", "runner-work", "docker-images", "dev-caches", "--yes")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertFalse(self.cache.exists())
        self.assertTrue(self.derived.exists())
        self.assertTrue(self.work.exists())
        self.assertEqual(self.commands, [])

    def test_guard_reads_executable_names(self):
        self.processes = "/bin/zsh\n/bin/ps\n"
        self.assertNotIn("blocked", self.invoke("--list").output)

    def test_booted_simulator_is_not_erased(self):
        self.devices = "iPhone (ABC) (Booted)\n"
        result = self.invoke("simulators", "--yes")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(self.commands, [])

    def test_failed_item_continues_and_exits_nonzero(self):
        self.failing = ("go",)
        result = self.invoke("go-cache", "dev-caches", "--yes")
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Could not remove: go-cache", result.output)
        self.assertFalse(self.cache.exists())

    def test_old_versions_keep_newest_and_current(self):
        for version in ("2.1.9", "2.1.10", "2.1.11"):
            self.put(f".local/share/claude/versions/{version}/data")
        link = self.home / ".local/bin/claude"
        link.parent.mkdir(parents=True)
        link.symlink_to(self.home / ".local/share/claude/versions/2.1.9")
        result = self.invoke("old-claude", "--yes")
        self.assertEqual(result.exit_code, 0, result.output)
        versions = sorted(path.name for path in (self.home / ".local/share/claude/versions").iterdir())
        self.assertEqual(versions, ["2.1.11", "2.1.9"])

    def test_old_node_keeps_newest_of_each_major_and_default(self):
        for version in ("v22.1.0", "v24.1.0", "v24.2.0", "v24.10.0"):
            self.put(f".nvm/versions/node/{version}/data")
        self.put(".nvm/alias/default").write_text("v24.1.0\n")
        result = self.invoke("old-node", "--yes")
        self.assertEqual(result.exit_code, 0, result.output)
        versions = sorted(path.name for path in (self.home / ".nvm/versions/node").iterdir())
        self.assertEqual(versions, ["v22.1.0", "v24.1.0", "v24.10.0"])

    def test_old_extensions_group_by_extension(self):
        for name in ("a.b-1.2.0-darwin-arm64", "a.b-1.10.0-darwin-arm64", "c.d-1.0.0"):
            self.put(f".vscode/extensions/{name}/data")
        self.put(".vscode/extensions/extensions.json")
        result = self.invoke("old-extensions", "--yes")
        self.assertEqual(result.exit_code, 0, result.output)
        names = sorted(path.name for path in (self.home / ".vscode/extensions").iterdir())
        self.assertEqual(names, ["a.b-1.10.0-darwin-arm64", "c.d-1.0.0", "extensions.json"])

    def test_vscode_running_blocks_its_items(self):
        self.processes = "/Applications/Visual Studio Code.app/Contents/MacOS/Electron\n"
        path = self.put("Library/Application Support/Code/logs/data")
        result = self.invoke("vscode-cache", "--yes")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("VS Code running", result.output)
        self.assertTrue(path.exists())

    def test_recent_codex_install_stays(self):
        stale = self.put(".cache/codex-runtimes/codex-runtime-install-old/data").parent
        fresh = self.put(".cache/codex-runtimes/codex-runtime-install-new/data").parent
        os.utime(stale, (1, 1))
        result = self.invoke("codex-installs", "--yes")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertFalse(stale.exists())
        self.assertTrue(fresh.exists())

    def test_project_items_skip_tracked_directories(self):
        modules = self.put("workspace/app/node_modules/pkg/data")
        tracked = self.put("workspace/tracked/node_modules/data")
        terraform = self.put("workspace/infra/.terraform/provider")
        result = self.invoke("project-deps", "project-terraform", "--yes")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertFalse(modules.exists())
        self.assertFalse(terraform.exists())
        self.assertTrue(tracked.exists())

    def test_derived_data_is_listed_apart_from_build_output(self):
        derived = self.put("workspace/ios/build/run/DerivedData/data")
        keep = self.put("workspace/ios/build/run/App.ipa")
        self.assertIn("project-derived", self.invoke("--list").output)
        result = self.invoke("project-derived", "--yes")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertFalse(derived.exists())
        self.assertTrue(keep.exists())

    def test_a_keeps_project_builds(self):
        keep = self.put("workspace/ios/build/run/App.ipa")
        result = self.invoke(input="a\ny\n")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertTrue(keep.exists())

    def test_android_images_follow_android_home(self):
        images = self.put("sdk/system-images/android-36/data")
        os.environ["ANDROID_HOME"] = str(self.home / "sdk")
        result = self.invoke("android-images", "--yes")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertFalse(images.exists())

    def test_simulator_runtimes_keep_latest_used_per_platform(self):
        self.runtimes = {
            "A": {"platformIdentifier": "ios", "lastUsedAt": "2026-10-01", "sizeBytes": 2 * 1024**3},
            "B": {"platformIdentifier": "ios", "lastUsedAt": "2026-10-30", "sizeBytes": 1024**3},
            "C": {"platformIdentifier": "watch", "lastUsedAt": "2026-10-01", "sizeBytes": 1024**3},
        }
        self.assertRegex(self.invoke("--list").output, r"2\.0 GiB\s+download\s+simulator-runtimes")
        result = self.invoke("simulator-runtimes", "--yes")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(self.commands, ["xcrun simctl runtime delete A"])

    def test_protected_trash_prints_guidance(self):
        with mock.patch.object(clean_plugin, "readable", return_value=False):
            self.assertIn("Full Disk Access", self.invoke("--list").output)

    def test_every_target_stays_inside_the_temporary_home(self):
        for item in clean_catalog.catalog(self.home):
            for path in item.targets(self.home):
                self.assertIn(self.home, path.parents, item.name)

    def test_dgx_hides_docker_images_and_volumes(self):
        with mock.patch.object(clean_catalog, "is_dgx", return_value=True):
            output = self.invoke("--list").output
        self.assertIn("docker-cache", output)
        self.assertNotIn("docker-images", output)
        self.assertNotIn("docker-volumes", output)

    def test_unknown_selection_changes_nothing(self):
        self.assertEqual(self.invoke("nope", "--yes").exit_code, 2)
        self.assertEqual(self.invoke(input="99\ny\n").exit_code, 2)
        self.assertTrue(self.cache.exists())


if __name__ == "__main__":
    unittest.main()
