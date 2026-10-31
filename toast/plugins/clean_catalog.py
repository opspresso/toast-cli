#!/usr/bin/env python3

"""What `toast clean` can remove: the catalog, its sizes and activity guards."""

import json
import os
import platform
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Callable, List, Optional, Tuple


from toast.plugins.utils import run_command

CACHE = "cache"  # Rebuilt on demand.
DOWNLOAD = "download"  # Fetched again; the first use is slow.
DATA = "data"  # Cannot be restored; "a" never selects these items.

BUILD_PROCESSES = re.compile(r"(^|/)(Runner\.Worker|xcodebuild)$", re.MULTILINE)
CHROME_PROCESS = re.compile(r"/Google Chrome$", re.MULTILINE)
VSCODE_PROCESS = re.compile(r"Visual Studio Code\.app/|(^|/)code$", re.MULTILINE)
VERSIONED_NAME = re.compile(r"^(.+?)-(\d+(?:\.\d+)+)(-.*)?$")
PROJECT_DEPENDENCIES = {"node_modules"}
PROJECT_TERRAFORM = {".terraform"}
PROJECT_DERIVED = {"DerivedData"}
PROJECT_BUILDS = {".build", ".next", ".next-e2e", "build", "dist", "out", "target"}
STALE_SECONDS = 86400
DOCKER_SIZE = re.compile(r"^([0-9.]+)\s*(B|kB|KB|MB|GB|TB)")
DOCKER_UNITS = {"B": 1, "kB": 1024, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}


def list_processes():
    """Return executable names only; full command lines would match shell scripts."""
    return subprocess.run(["ps", "-axo", "comm="], capture_output=True, text=True).stdout


def path_size(path):
    """Return allocated bytes, or 0 when macOS blocks the folder."""
    if not path.exists():
        return 0
    result = subprocess.run(["du", "-sk", str(path)], capture_output=True, text=True)
    fields = result.stdout.split()
    return int(fields[0]) * 1024 if fields else 0


def tool_path_size(*command):
    """Return the size of the directory a tool reports, or 0 without the tool."""
    if not shutil.which(command[0]):
        return 0
    result = subprocess.run(command, capture_output=True, text=True)
    location = result.stdout.strip()
    return path_size(Path(location)) if result.returncode == 0 and location else 0


def docker_reclaimable(*types):
    """Return reclaimable bytes for `docker system df` types, or 0 when Docker is down."""
    if not shutil.which("docker"):
        return 0
    result = subprocess.run(["docker", "system", "df", "--format", "{{json .}}"], capture_output=True, text=True)
    if result.returncode:
        return 0
    total = 0
    for line in result.stdout.splitlines():
        entry = json.loads(line)
        match = DOCKER_SIZE.match(entry.get("Reclaimable", ""))
        if entry.get("Type") in types and match:
            total += int(float(match.group(1)) * DOCKER_UNITS[match.group(2)])
    return total


def version_key(name):
    return tuple(int(part) for part in re.findall(r"\d+", name))


def old_versions(directory, group=lambda name: "", keep=()):
    """Return entries of DIRECTORY except the newest of each group and the KEEP names."""
    if not directory.is_dir():
        return []
    groups = {}
    for entry in directory.iterdir():
        if not entry.name.startswith(".") and entry.is_dir():
            groups.setdefault(group(entry.name), []).append(entry)
    old = []
    for entries in groups.values():
        entries.sort(key=lambda entry: version_key(entry.name))
        old.extend(entry for entry in entries[:-1] if entry.name not in keep)
    return old


def old_claude_versions(home):
    current = (home / ".local/bin/claude").resolve().name
    return old_versions(home / ".local/share/claude/versions", keep=(current,))


def old_nvm_versions(home):
    default = home / ".nvm/alias/default"
    pinned = default.read_text().strip() if default.is_file() else ""
    return old_versions(home / ".nvm/versions/node", group=lambda name: name.split(".")[0], keep=(pinned,))


def old_terraform_versions(home):
    return old_versions(home / ".tenv/Terraform")


def old_vscode_extensions(home):
    def extension_id(name):
        match = VERSIONED_NAME.match(name)
        return match.group(1) if match else name
    return old_versions(home / ".vscode/extensions", group=extension_id)


def stale_codex_installs(home):
    """Return interrupted Codex installs; a recent one can still be running."""
    limit = time.time() - STALE_SECONDS
    return [path for path in (home / ".cache/codex-runtimes").glob("codex-runtime-install-*") if path.stat().st_mtime < limit]


def android_system_images(home):
    """Return emulator images of the SDKs on this machine."""
    roots = [home / "Library/Android/sdk"]
    if os.environ.get("ANDROID_HOME"):
        roots.append(Path(os.environ["ANDROID_HOME"]))
    if shutil.which("brew"):
        prefix = subprocess.run(["brew", "--prefix"], capture_output=True, text=True).stdout.strip()
        if prefix:
            roots.append(Path(prefix) / "share/android-commandlinetools")
    return [root / "system-images" for root in roots if (root / "system-images").is_dir()]


def git_ignored(path):
    """Tracked or unversioned directories are source, whatever their name."""
    result = subprocess.run(["git", "-C", str(path.parent), "check-ignore", "-q", path.name], capture_output=True, text=True)
    return result.returncode == 0


@lru_cache(maxsize=1)
def project_directories(home):
    """Return git-ignored project output under ~/workspace by directory name."""
    found = {}
    for root, directories, _ in os.walk(home / "workspace"):
        for name in list(directories):
            path = Path(root) / name
            if name == ".git":
                directories.remove(name)
            elif name in PROJECT_DEPENDENCIES | PROJECT_TERRAFORM | PROJECT_DERIVED | PROJECT_BUILDS and git_ignored(path):
                found.setdefault(name, []).append(path)
                # DerivedData often sits inside a build folder and is its own item.
                if name not in PROJECT_BUILDS:
                    directories.remove(name)
    return found


def project_paths(home, names):
    return [path for name in sorted(names) for path in project_directories(home).get(name, [])]


def project_builds_size(home):
    """Exclude DerivedData here so the list does not count it twice."""
    builds = project_paths(home, PROJECT_BUILDS)
    nested = [path for path in project_paths(home, PROJECT_DERIVED) if any(build in path.parents for build in builds)]
    return sum(path_size(path) for path in builds) - sum(path_size(path) for path in nested)


def simulator_runtimes():
    """Return all runtimes except the most recently used one of each platform."""
    if not shutil.which("xcrun"):
        return []
    result = subprocess.run(["xcrun", "simctl", "runtime", "list", "-j"], capture_output=True, text=True)
    if result.returncode:
        return []
    groups = {}
    for identifier, runtime in json.loads(result.stdout).items():
        groups.setdefault(runtime.get("platformIdentifier"), []).append(dict(runtime, identifier=identifier))
    unused = []
    for runtimes in groups.values():
        runtimes.sort(key=lambda runtime: runtime.get("lastUsedAt", ""))
        unused.extend(runtimes[:-1])
    return unused


def is_dgx():
    return Path("/etc/dgx-release").exists()


def remove_path(path):
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def remove_contents(path):
    """Remove the entries of a directory that a service expects to exist."""
    if path.is_dir():
        for entry in path.iterdir():
            remove_path(entry)


@dataclass
class Item:
    name: str
    risk: str
    description: str
    paths: List[str] = field(default_factory=list)  # Relative to the home directory.
    keep_directory: bool = False
    size: Optional[Callable[[], int]] = None
    commands: List[Tuple[str, ...]] = field(default_factory=list)
    resolve: Optional[Callable[[Path], List[Path]]] = None  # Paths found at run time.
    resolve_commands: Optional[Callable[[], List[Tuple[str, ...]]]] = None
    guard: Optional[str] = None  # "build", "chrome" or "vscode"
    systems: Tuple[str, ...] = ("Darwin", "Linux")
    bytes: int = 0

    def available(self):
        return platform.system() in self.systems and not (self.name in ("docker-images", "docker-volumes") and is_dgx())

    def targets(self, home):
        return self.resolve(home) if self.resolve else [home / path for path in self.paths]

    def measure(self, home):
        if self.size:
            return self.size()
        return sum(path_size(path) for path in self.targets(home))

    def remove(self, home):
        for command in self.resolve_commands() if self.resolve_commands else self.commands:
            run_command(list(command))
        for path in self.targets(home):
            (remove_contents if self.keep_directory else remove_path)(path)


def catalog(home):
    """Only regenerable data, or data the owner can choose to lose, belongs here."""
    darwin = ("Darwin",)
    linux = ("Linux",)
    # DGX OS owns Docker, and a stopped model stack still needs its images and volumes.
    return [
        Item("go-cache", CACHE, "Go build cache", size=lambda: tool_path_size("go", "env", "GOCACHE"), commands=[("go", "clean", "-cache")]),
        Item("brew-cache", CACHE, "Homebrew downloads and old versions", size=lambda: tool_path_size("brew", "--cache"), commands=[("brew", "cleanup", "-s", "--prune=all")]),
        Item("npm-cache", CACHE, "npm cache", size=lambda: tool_path_size("npm", "config", "get", "cache"), commands=[("npm", "cache", "clean", "--force")]),
        Item("pnpm-store", CACHE, "pnpm packages no project uses", size=lambda: tool_path_size("pnpm", "store", "path"), commands=[("pnpm", "store", "prune")]),
        Item("pip-cache", CACHE, "pip cache", size=lambda: tool_path_size("pip3", "cache", "dir"), commands=[("pip3", "cache", "purge")]),
        Item("dev-caches", CACHE, "Electron, node-gyp, pnpm and staticcheck caches", systems=darwin,
             paths=[f"Library/Caches/{name}" for name in ("electron", "electron-builder", "node-gyp", "pnpm", "staticcheck")]),
        Item("dev-caches", CACHE, "Electron, node-gyp, pnpm and staticcheck caches", systems=linux,
             paths=[f".cache/{name}" for name in ("electron", "electron-builder", "node-gyp", "pnpm", "staticcheck")]),
        Item("chrome-cache", CACHE, "Chrome disk cache", paths=["Library/Caches/Google/Chrome/Default"], guard="chrome", systems=darwin),
        Item("xcode-derived", CACHE, "Xcode DerivedData", paths=["Library/Developer/Xcode/DerivedData"], guard="build", systems=darwin),
        Item("vscode-cache", CACHE, "VS Code logs and cached extensions", guard="vscode", systems=darwin,
             paths=[f"Library/Application Support/Code/{name}" for name in ("logs", "CachedExtensionVSIXs", "CachedData")]),
        Item("vscode-cache", CACHE, "VS Code logs and cached extensions", guard="vscode", systems=linux,
             paths=[f".config/Code/{name}" for name in ("logs", "CachedExtensionVSIXs", "CachedData")]),
        Item("updater-cache", CACHE, "Google updater downloads", paths=["Library/Application Support/Google/GoogleUpdater/crx_cache"], systems=darwin),
        Item("codex-installs", CACHE, "Interrupted Codex runtime installs", resolve=stale_codex_installs),
        Item("project-derived", CACHE, "Git-ignored DerivedData in ~/workspace", resolve=lambda home: project_paths(home, PROJECT_DERIVED), guard="build"),
        Item("old-claude", CACHE, "Claude Code versions except the newest and current", resolve=old_claude_versions),
        Item("old-extensions", CACHE, "Older copies of VS Code extensions", resolve=old_vscode_extensions, guard="vscode"),
        Item("docker-cache", CACHE, "Docker build cache", size=lambda: docker_reclaimable("Build Cache"), commands=[("docker", "builder", "prune", "-af")], guard="build"),
        Item("docker-images", DOWNLOAD, "Docker images no container uses", size=lambda: docker_reclaimable("Images"), commands=[("docker", "image", "prune", "-af")], guard="build"),
        Item("device-support", DOWNLOAD, "iOS device symbols, rebuilt when a device connects", paths=["Library/Developer/Xcode/iOS DeviceSupport"], systems=darwin),
        Item("arduino-staging", DOWNLOAD, "Arduino download archives", paths=["Library/Arduino15/staging"], systems=darwin),
        Item("aerial-videos", DOWNLOAD, "macOS aerial wallpaper videos", paths=["Library/Application Support/com.apple.wallpaper/aerials/videos"], keep_directory=True, systems=darwin),
        Item("gradle-cache", DOWNLOAD, "Gradle caches and daemon logs", paths=[".gradle/caches", ".gradle/daemon"], guard="build"),
        Item("test-browsers", DOWNLOAD, "Playwright and agent-browser browsers", systems=darwin, paths=["Library/Caches/ms-playwright", ".agent-browser/browsers"]),
        Item("test-browsers", DOWNLOAD, "Playwright and agent-browser browsers", systems=linux, paths=[".cache/ms-playwright", ".agent-browser/browsers"]),
        Item("old-node", DOWNLOAD, "nvm versions except the newest of each major and the default", resolve=old_nvm_versions),
        Item("old-terraform", DOWNLOAD, "tenv Terraform versions except the newest", resolve=old_terraform_versions),
        Item("project-deps", DOWNLOAD, "Git-ignored node_modules in ~/workspace", resolve=lambda home: project_paths(home, PROJECT_DEPENDENCIES), guard="build"),
        Item("project-terraform", DOWNLOAD, "Git-ignored .terraform in ~/workspace; run terraform init again", resolve=lambda home: project_paths(home, PROJECT_TERRAFORM)),
        Item("simulator-runtimes", DOWNLOAD, "Simulator runtimes except the latest used per platform", size=lambda: sum(runtime.get("sizeBytes", 0) for runtime in simulator_runtimes()),
             resolve_commands=lambda: [("xcrun", "simctl", "runtime", "delete", runtime["identifier"]) for runtime in simulator_runtimes()], guard="build", systems=darwin),
        Item("android-images", DOWNLOAD, "Android emulator system images", resolve=android_system_images),
        Item("arduino-packages", DOWNLOAD, "Arduino board toolchains", paths=["Library/Arduino15/packages"], systems=darwin),
        Item("runner-work", DOWNLOAD, "GitHub Actions runner workspaces", paths=["actions-runner/_work"], keep_directory=True, guard="build"),
        Item("simulators", DATA, "Apps and data in every iOS simulator", size=lambda: path_size(Path.home() / "Library/Developer/CoreSimulator/Devices"),
             commands=[("xcrun", "simctl", "erase", "all")], guard="build", systems=darwin),
        Item("android-avds", DATA, "Android virtual devices", paths=[".android/avd"], keep_directory=True),
        Item("project-builds", DATA, "Git-ignored build output in ~/workspace, including release files", size=lambda: project_builds_size(home),
             resolve=lambda home: project_paths(home, PROJECT_BUILDS), guard="build"),
        Item("trash", DATA, "Files in the Trash", paths=[".Trash"], keep_directory=True, systems=darwin),
        Item("docker-volumes", DATA, "Stopped Docker containers and unused volumes", size=lambda: docker_reclaimable("Containers", "Local Volumes"),
             commands=[("docker", "container", "prune", "-f"), ("docker", "volume", "prune", "-af")], guard="build"),
    ]


def blocked_reason(item, processes=None):
    """Return why ITEM must stay. Pass PROCESSES to reuse one snapshot for a whole list."""
    if item.guard:
        processes = list_processes() if processes is None else processes
        patterns = {"build": (BUILD_PROCESSES, "build running"), "chrome": (CHROME_PROCESS, "Chrome running"), "vscode": (VSCODE_PROCESS, "VS Code running")}
        pattern, reason = patterns[item.guard]
        if pattern.search(processes):
            return reason
    if item.name == "simulators":
        result = subprocess.run(["xcrun", "simctl", "list", "devices"], capture_output=True, text=True)
        if "(Booted)" in result.stdout:
            return "simulator booted"
    return None


def readable(path):
    try:
        os.listdir(path)
    except FileNotFoundError:
        return True
    except PermissionError:
        return False
    return True


def scan(home):
    """Measure every item in parallel: each one waits on du or a tool, not the CPU."""
    project_directories.cache_clear()
    project_directories(home)
    from concurrent.futures import ThreadPoolExecutor

    items = [item for item in catalog(home) if item.available()]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for item, size in zip(items, pool.map(lambda item: item.measure(home), items)):
            item.bytes = size
    return sorted((item for item in items if item.bytes > 0), key=lambda item: item.bytes, reverse=True)
