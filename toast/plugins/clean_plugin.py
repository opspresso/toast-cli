#!/usr/bin/env python3

import json
import platform
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import click
from rich.console import Console
from rich.table import Table

from toast.plugins.base_plugin import BasePlugin
from toast.plugins.utils import run_command

console = Console()

CACHE = "cache"  # Rebuilt on demand.
DOWNLOAD = "download"  # Fetched again; the first use is slow.
DATA = "data"  # Cannot be restored; "a" never selects these items.

BUILD_PROCESSES = re.compile(r"(^|/)(Runner\.Worker|xcodebuild)$", re.MULTILINE)
CHROME_PROCESS = re.compile(r"/Google Chrome$", re.MULTILINE)
DOCKER_SIZE = re.compile(r"^([0-9.]+)\s*(B|kB|KB|MB|GB|TB)")
DOCKER_UNITS = {"B": 1, "kB": 1024, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
GIB = 1024**3


def list_processes():
    """Return executable names only; full command lines would match shell scripts."""
    return subprocess.run(["ps", "-axo", "comm="], capture_output=True, text=True).stdout


def path_size(path):
    """Return allocated bytes. du handles hard links and unreadable entries."""
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
    guard: Optional[str] = None  # "build" or "chrome"
    systems: Tuple[str, ...] = ("Darwin", "Linux")
    bytes: int = 0

    def available(self):
        return platform.system() in self.systems and not (self.name in ("docker-images", "docker-volumes") and is_dgx())

    def measure(self, home):
        if self.size:
            return self.size()
        return sum(path_size(home / path) for path in self.paths)

    def remove(self, home):
        for command in self.commands:
            run_command(list(command))
        for path in self.paths:
            (remove_contents if self.keep_directory else remove_path)(home / path)


def catalog():
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
        Item("docker-cache", CACHE, "Docker build cache", size=lambda: docker_reclaimable("Build Cache"), commands=[("docker", "builder", "prune", "-af")], guard="build"),
        Item("docker-images", DOWNLOAD, "Docker images no container uses", size=lambda: docker_reclaimable("Images"), commands=[("docker", "image", "prune", "-af")], guard="build"),
        Item("device-support", DOWNLOAD, "iOS device symbols, rebuilt when a device connects", paths=["Library/Developer/Xcode/iOS DeviceSupport"], systems=darwin),
        Item("arduino-staging", DOWNLOAD, "Arduino download archives", paths=["Library/Arduino15/staging"], systems=darwin),
        Item("aerial-videos", DOWNLOAD, "macOS aerial wallpaper videos", paths=["Library/Application Support/com.apple.wallpaper/aerials/videos"], keep_directory=True, systems=darwin),
        Item("runner-work", DOWNLOAD, "GitHub Actions runner workspaces", paths=["actions-runner/_work"], keep_directory=True, guard="build"),
        Item("simulators", DATA, "Apps and data in every iOS simulator", size=lambda: path_size(Path.home() / "Library/Developer/CoreSimulator/Devices"),
             commands=[("xcrun", "simctl", "erase", "all")], guard="build", systems=darwin),
        Item("android-avds", DATA, "Android virtual devices", paths=[".android/avd"], keep_directory=True),
        Item("docker-volumes", DATA, "Stopped Docker containers and unused volumes", size=lambda: docker_reclaimable("Containers", "Local Volumes"),
             commands=[("docker", "container", "prune", "-f"), ("docker", "volume", "prune", "-af")], guard="build"),
    ]


def blocked_reason(item):
    """Return why ITEM must stay, checked again right before removal."""
    if item.guard == "build" and BUILD_PROCESSES.search(list_processes()):
        return "build running"
    if item.guard == "chrome" and CHROME_PROCESS.search(list_processes()):
        return "Chrome running"
    if item.name == "simulators":
        result = subprocess.run(["xcrun", "simctl", "list", "devices"], capture_output=True, text=True)
        if "(Booted)" in result.stdout:
            return "simulator booted"
    return None


def scan(home):
    items = []
    for item in catalog():
        if item.available():
            item.bytes = item.measure(home)
            if item.bytes > 0:
                items.append(item)
    return sorted(items, key=lambda item: item.bytes, reverse=True)


def gib(size):
    return f"{size / GIB:.1f} GiB"


def show(items, home):
    table = Table(box=None, pad_edge=False)
    table.add_column("#", justify="right")
    table.add_column("SIZE", justify="right")
    table.add_column("RISK")
    table.add_column("NAME")
    table.add_column("DESCRIPTION")
    for number, item in enumerate(items, 1):
        reason = blocked_reason(item)
        suffix = f" \\[blocked: {reason}]" if reason else ""
        table.add_row(str(number), gib(item.bytes), item.risk, item.name, item.description + suffix)
    console.print(table)
    total = sum(item.bytes for item in items)
    free = shutil.disk_usage(home).free
    console.print(f"Reclaimable: {gib(total)}. Free now: {gib(free)}, after: {gib(free + total)}.", style="bold cyan")


def select(items, tokens):
    """Resolve numbers, names and "a". Raises UsageError for anything else."""
    chosen = []
    for token in tokens:
        if token.lower() == "a":
            matches = [item for item in items if item.risk != DATA]
        elif token.isdigit() and 1 <= int(token) <= len(items):
            matches = [items[int(token) - 1]]
        else:
            matches = [item for item in items if item.name == token]
        if not matches:
            raise click.UsageError(f"Nothing to clean for: {token}")
        chosen.extend(item for item in matches if item not in chosen)
    return chosen


def confirm(chosen):
    for item in chosen:
        console.print(f"  {item.name} ({gib(item.bytes)})")
    if any(item.risk == DATA for item in chosen):
        console.print("The selection includes data that cannot be restored.", style="bold yellow")
    total = sum(item.bytes for item in chosen)
    return click.confirm(f"Remove {len(chosen)} items ({gib(total)})?", default=False)


def remove(chosen, home):
    before = shutil.disk_usage(home).free
    failed = []
    for item in chosen:
        reason = blocked_reason(item)
        if reason:
            console.print(f"Skipped {item.name}: {reason}", style="yellow")
            continue
        console.print(f"Removing {item.name}", style="cyan")
        try:
            item.remove(home)
        except (OSError, click.ClickException) as exc:
            message = exc.format_message() if isinstance(exc, click.ClickException) else str(exc)
            console.print(f"Could not remove {item.name}: {message}", style="red")
            failed.append(item.name)
    console.print(f"✓ Free space: {gib(before)} -> {gib(shutil.disk_usage(home).free)}", style="bold green")
    if failed:
        raise click.ClickException(f"Could not remove: {', '.join(failed)}")


class CleanPlugin(BasePlugin):
    """Plugin for 'clean' command - shows and removes reclaimable disk data."""

    name = "clean"
    help = "Show reclaimable disk data and remove selected items"

    @classmethod
    def get_arguments(cls, func):
        func = click.option("--yes", "-y", is_flag=True, help="Skip the confirmation; requires item names")(func)
        func = click.option("--list", "list_only", is_flag=True, help="Show the items and exit")(func)
        func = click.argument("names", nargs=-1)(func)
        return func

    @classmethod
    def execute(cls, names=(), list_only=False, yes=False, **kwargs):
        if yes and not names:
            raise click.UsageError("--yes needs item names; see toast clean --list")
        home = Path.home()
        items = scan(home)
        if not items:
            console.print("Nothing to clean.", style="green")
            return
        if names:
            chosen = select(items, names)
        else:
            show(items, home)
            if list_only:
                return
            try:
                answer = click.prompt("Enter numbers or names (1 3 5), a for all except data, q to quit", default="q", show_default=False)
            except click.Abort:
                answer = "q"
            tokens = answer.replace(",", " ").split()
            if any(token.lower() == "q" for token in tokens):
                console.print("Nothing removed.", style="yellow")
                return
            chosen = select(items, tokens)
        if not chosen:
            console.print("Nothing removed.", style="yellow")
            return
        if not yes:
            try:
                approved = confirm(chosen)
            except click.Abort:
                approved = False
            if not approved:
                console.print("Nothing removed.", style="yellow")
                return
        remove(chosen, home)
