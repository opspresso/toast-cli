#!/usr/bin/env python3

import click
import os
import shutil
import re
from urllib.parse import quote, unquote, urlsplit
from toast import ui
from toast.plugins.base_plugin import BasePlugin
from toast.plugins.utils import run_command, spawn


def get_github_host():
    """Read GITHUB_HOST from .toast-config file or extract from path."""
    current_path = os.getcwd()

    # First, try to extract host from the workspace path pattern
    # Matches: /Users/user/workspace/{github-host}/{org} or /workspace/{github-host}/{org}
    pattern = r"^(.*)/workspace/([^/]+)/([^/]+)"
    match = re.match(pattern, current_path)

    default_host = "github.com"

    if match:
        default_host = match.group(2)

    config_locations = []

    if match:
        # If in org directory, check org-specific config first
        org_dir = os.path.join(
            match.group(1), "workspace", match.group(2), match.group(3)
        )
        config_locations.append(os.path.join(org_dir, ".toast-config"))

    # Add current directory config
    config_locations.append(os.path.join(current_path, ".toast-config"))

    for config_file in config_locations:
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GITHUB_HOST="):
                            host = line.split("=", 1)[1].strip()
                            if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", host):
                                raise click.ClickException(
                                    f"Invalid GITHUB_HOST in {config_file}. Set it to a host name such as "
                                    "github.com, or remove the line to use the workspace host"
                                )
                            return host
            except OSError as e:
                raise click.ClickException(f"Could not read {config_file}: {e}") from e

    return default_host


def sanitize_repo_name(repo_name):
    """Build a local clone directory name from a remote repository name."""
    return re.sub(r"[^A-Za-z0-9_.-]", "", repo_name or "").strip(".-") or "repo"


def redact_url(url):
    """Hide credentials in a Git URL before it is displayed.

    An HTTP user name is often a token, so it is hidden together with any password.
    An SSH user name such as git stays visible. Query values and the fragment can
    carry a token such as access_token, so their values are hidden too; query keys
    stay visible. Git itself receives the original URL.
    """
    parsed = urlsplit(url)
    if "@" in parsed.netloc:
        userinfo, host = parsed.netloc.rsplit("@", 1)
        user, has_password, _ = userinfo.partition(":")
        if parsed.scheme in ("http", "https"):
            user = "***"
        elif has_password:
            user += ":***"
        parsed = parsed._replace(netloc=f"{user}@{host}")
    if parsed.query:
        params = [part.partition("=") for part in parsed.query.split("&")]
        parsed = parsed._replace(query="&".join(f"{key}=***" if sep else "***" for key, sep, _ in params))
    if parsed.fragment:
        parsed = parsed._replace(fragment="***")
    return parsed.geturl()


# Git may rewrite a URL before printing it, for example by dropping the user name
# or by appending a slash, and it prints a remote URL that is not in its arguments.
# Every URL is therefore found in the text, and the known secret parts of the URLs
# Git uses are then hidden around and inside the URLs found. Git prints a malformed URL as given, so a URL
# can contain quotes and whitespace, and its end cannot always be told from the text.
# A quoted URL runs to the last matching quote on the line that is followed by
# whitespace or the end of the text, optionally after one punctuation mark, as in
# "unable to access 'URL': reason". It never runs into the next URL, so several URLs
# on one line are found separately. An unquoted URL ends at whitespace, except where
# a secret can contain whitespace: user information runs to the last "@" before the
# path on the line, and a query or fragment runs to the end of the line. Hiding too
# much text is safer than showing part of a secret.
_SCHEME = r"[A-Za-z][A-Za-z0-9+.-]*://"
URL_IN_TEXT = re.compile(
    rf"""(?P<quote>['"])(?P<quoted>{_SCHEME}(?:(?!['"]?{_SCHEME})[^\n])*)(?P=quote)(?=\s|$|[:;,.)](?:\s|$))"""
    rf"""|\b{_SCHEME}(?:[^/?#\n]*@)?[^\s?#]*(?:[?#][^\n]*)?"""
)

# A secret value shorter than this is not hidden on its own, outside its URL, so a
# value such as "1" does not hide every digit of the message.
_MIN_BARE_SECRET = 4


def _hide_url(url):
    try:
        return redact_url(url)
    except ValueError:
        # urlsplit rejects some malformed URLs; hide all of it but the scheme.
        return url.split("://", 1)[0] + "://***"


def _secret_parts(url):
    """Pair each secret part of url with what is shown instead, longest first.

    A part with its delimiter, such as "user:pass@" or "?query", is shown as
    redact_url shows it. Each secret value is also hidden on its own, as given and
    percent-encoded or decoded, and each word of a value with whitespace, because
    Git can print it without the rest of the URL.
    """
    try:
        parsed = urlsplit(url)
    except ValueError:
        rest = url.split("://", 1)[1]
        return [(rest, "***")] if rest else []
    shown = urlsplit(_hide_url(url))
    parts, values = [], []
    if "@" in parsed.netloc:
        userinfo = parsed.netloc.rsplit("@", 1)[0]
        parts.append((userinfo + "@", shown.netloc.rsplit("@", 1)[0] + "@"))
        user, _, password = userinfo.partition(":")
        values += [password, user] if parsed.scheme in ("http", "https") else [password]
    if parsed.query:
        parts.append(("?" + parsed.query, "?" + shown.query))
        values += [part.partition("=")[2] or part for part in parsed.query.split("&")]
    if parsed.fragment:
        parts.append(("#" + parsed.fragment, "#***"))
        values.append(parsed.fragment)
    # A malformed URL can hold a value with whitespace; Git may print a word of it.
    values += [word for value in values for word in unquote(value).split() if word != value]
    for value in values:
        for form in {value, unquote(value), quote(value, safe=""), quote(unquote(value), safe="")}:
            if len(form) >= _MIN_BARE_SECRET:
                parts.append((form, "***"))
    parts = [(raw, masked) for raw, masked in parts if raw != masked]
    return sorted(parts, key=lambda part: len(part[0]), reverse=True)


def redact_urls(text, known_urls=()):
    """Hide credentials in every URL inside Git output, as redact_url does.

    known_urls are the URLs Git uses, from its arguments or from the remotes of the
    repository. Their secret parts are hidden wherever they appear, even where Git
    printed a URL whose ends cannot be found in the text.

    URLs are found in the original text first. A known secret can be any text, such
    as the user name "https", so hiding it first could change another URL until it
    is no longer found, and that URL would be shown with its credentials. Known
    secrets are therefore hidden only outside the URLs found and after the scheme
    of each redacted URL.
    """
    parts = sorted(
        {part for url in known_urls if "://" in url for part in _secret_parts(url)},
        key=lambda part: len(part[0]),
        reverse=True,
    )

    def hide_known(segment):
        for raw, masked in parts:
            segment = segment.replace(raw, masked)
        return segment

    def hide(url):
        scheme, sep, rest = _hide_url(url).partition("://")
        return scheme + sep + hide_known(rest)

    shown, end = [], 0
    for match in URL_IN_TEXT.finditer(text):
        shown.append(hide_known(text[end : match.start()]))
        if match.group("quote"):
            shown.append(match.group("quote") + hide(match.group("quoted")) + match.group("quote"))
        else:
            shown.append(hide(match.group(0)))
        end = match.end()
    shown.append(hide_known(text[end:]))
    return "".join(shown)


def remote_urls(repo_path):
    """Return the fetch and push URLs of every remote of the repository.

    Git prints these URLs, after any url.<base>.insteadOf rewrite, although a plain
    pull or push does not name them. They stay in memory to hide their secrets. A
    repository without remotes, or one Git cannot read, has none to hide.
    """
    listed = spawn(["git", "remote", "-v"], cwd=repo_path)
    if listed.returncode:
        return []
    urls = []
    for line in listed.stdout.splitlines():
        _, tab, entry = line.partition("\t")
        for suffix in (" (fetch)", " (push)"):
            if tab and entry.endswith(suffix):
                urls.append(entry[: -len(suffix)])
    return urls


class GitPlugin(BasePlugin):
    """Plugin for 'git' command - handles Git repository operations."""

    name = "git"
    help = (
        "Manage Git repositories\n\n"
        "Run it in ~/workspace/{git-host}/{namespace}. Before it runs Git, it shows the "
        "host, namespace, absolute local path and action on stderr. Git output goes to "
        "stdout; Git progress, diagnostics and status go to stderr.\n\n"
        "push --mirror shows the remote and asks for a confirmation, because it overwrites "
        "remote branches and tags and deletes those that do not exist locally. --yes skips "
        "the confirmation of rm and push --mirror only."
    )
    category = "Workspace"
    commands = (
        ("clone", "Clone into this namespace (alias: cl)"),
        ("pull", "Pull the current branch (alias: p)"),
        ("push", "Push the current branch (alias: ps); --mirror after a confirmation"),
        ("branch", "Create and switch to --branch (alias: b)"),
        ("rm", "Remove the checkout after a confirmation"),
    )
    examples = (
        ("toast git my-repo clone", "Clone into this namespace"),
        ("toast git my-repo pull -r", "Pull with rebase"),
        ("toast git my-repo push -m", "Mirror push after a confirmation"),
        ("toast git my-repo rm", "Remove a checkout after a confirmation"),
    )

    @classmethod
    def get_arguments(cls, func):
        func = click.argument("command", required=True, shell_complete=cls.complete_command)(func)
        func = click.argument("repo_name", required=True)(func)
        func = click.option("--branch", "-b", help="Branch name for branch operation")(
            func
        )
        func = click.option(
            "--target", "-t", help="Target directory name for clone operation"
        )(func)
        func = click.option(
            "--rebase", "-r", is_flag=True, help="Use rebase when pulling"
        )(func)
        func = click.option(
            "--mirror",
            "-m",
            is_flag=True,
            help="Push all refs with --mirror for repository migration, after a confirmation",
        )(func)
        func = click.option(
            "--yes", "-y", is_flag=True, help="Skip the confirmation of rm or push --mirror"
        )(func)
        return func

    @staticmethod
    def _confirm_remove(repo_name, repo_path):
        """Name what would be lost, because the removal cannot be undone."""
        status = spawn(["git", "status", "--short", "--branch"], cwd=repo_path)
        lines = status.stdout.splitlines()
        changed = sum(1 for line in lines if not line.startswith("##"))
        if changed:
            ui.warning(f"{repo_name} has {changed} uncommitted changes")
        if lines and "ahead" in lines[0]:
            ui.warning(f"{repo_name} has commits that are not pushed")
        return ui.confirm(f"Remove {repo_path}? This cannot be undone.")

    @staticmethod
    def _run_git(args, message, remotes=False, **kwargs):
        """Run Git: its stdout is the result, its stderr is about the run.

        Git receives the original arguments. Git can print a remote URL that is not
        in the arguments, so every displayed URL is redacted, on success and failure.
        With remotes, the URLs of the remotes in cwd are hidden like the arguments.
        """
        known = list(args) + (remote_urls(kwargs["cwd"]) if remotes else [])

        def hide(text):
            return redact_urls(text, known)

        with ui.status(message):
            result = run_command(args, redact=hide, **kwargs)
        for line in hide(result.stderr.strip()).splitlines():
            ui.muted(f"  {line}")
        if result.stdout.strip():
            ui.result(hide(result.stdout.rstrip("\n")))

    @classmethod
    def execute(
        cls,
        command,
        repo_name,
        branch=None,
        target=None,
        rebase=False,
        mirror=False,
        yes=False,
        **kwargs,
    ):
        aliases = {"cl": "clone", "b": "branch", "p": "pull", "ps": "push"}
        command = aliases.get(command, command)
        if command not in ("clone", "rm", "branch", "pull", "push"):
            raise click.UsageError(f"Unknown git command: {command}. Use clone, pull, push, branch or rm")
        if target is not None and command != "clone":
            raise click.UsageError("--target requires clone")
        if branch is not None and command != "branch":
            raise click.UsageError("--branch requires branch")
        if rebase and command != "pull":
            raise click.UsageError("--rebase requires pull")
        if mirror and command != "push":
            raise click.UsageError("--mirror requires push")
        if yes and not (command == "rm" or mirror):
            raise click.UsageError("--yes requires rm or push --mirror")

        current_path = os.getcwd()
        match = re.fullmatch(r".*/workspace/([^/]+)/(.+)", current_path)
        if not match:
            raise click.ClickException(
                f"{current_path} is not a workspace namespace directory. "
                "Change to ~/workspace/{git-host}/{namespace} first, for example "
                "cd ~/workspace/github.com/my-org"
            )
        host, namespace = match.groups()
        place = [("Host", host), ("Namespace", namespace)]

        if command == "clone":
            repo_url = None
            if repo_name.startswith(("https://", "http://", "ssh://", "git://")):
                repo_url = repo_name
                parsed = urlsplit(repo_url)
                if not parsed.hostname or not parsed.path.rstrip("/"):
                    raise click.UsageError(
                        "Clone URL must include a host and repository path, "
                        "for example https://github.com/my-org/my-repo.git"
                    )
                repo_name = parsed.path.rstrip("/").rsplit("/", 1)[-1]
            elif re.match(r"^[^/@:]+@[^/:]+:.+", repo_name):
                repo_url = repo_name
                repo_name = repo_url.split(":", 1)[1].rstrip("/").rsplit("/", 1)[-1]
            if repo_name.endswith(".git"):
                repo_name = repo_name[:-4]
            repo_name = sanitize_repo_name(repo_name)
            target_path = os.path.abspath(os.path.join(current_path, target or repo_name))
            if os.path.lexists(target_path):
                raise click.ClickException(
                    f"{target_path} already exists. Choose another directory with --target, "
                    "or use the existing checkout"
                )
            if repo_url is None:
                repo_url = f"git@{get_github_host()}:{namespace}/{repo_name}.git"
            ui.fields(place + [("Path", target_path), ("Source", redact_url(repo_url)), ("Action", "git clone")])
            cls._run_git(["git", "clone", repo_url, target_path], f"Cloning {repo_name}")
            ui.success(f"Cloned {repo_name} to {target_path}")
            return

        # Never rewrite the name of an existing repository: it could select a
        # different directory, especially for destructive operations.
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", repo_name):
            raise click.UsageError(
                f"Repository must be the name of a directory in {current_path}, "
                "without paths or special characters"
            )
        repo_path = os.path.join(current_path, repo_name)
        if os.path.islink(repo_path):
            raise click.ClickException(
                f"{repo_path} is a symlink. Run toast git in the namespace directory that holds the checkout"
            )
        if not os.path.isdir(repo_path):
            raise click.ClickException(
                f"{repo_path} does not exist. Clone it with: toast git {repo_name} clone"
            )
        is_worktree = os.path.exists(os.path.join(repo_path, ".git"))
        is_bare = all(os.path.exists(os.path.join(repo_path, part)) for part in ("HEAD", "objects", "refs"))
        if not (is_worktree or is_bare):
            raise click.ClickException(
                f"{repo_path} is not a Git repository. Check the repository name"
            )

        if command == "rm":
            ui.fields(place + [("Path", repo_path), ("Action", "remove the directory")])
            if not (yes or cls._confirm_remove(repo_name, repo_path)):
                ui.cancelled()
                return
            shutil.rmtree(repo_path)
            ui.success(f"Removed {repo_path}")
            return
        details = [("Path", repo_path)]
        if command == "branch":
            if not branch:
                raise click.UsageError("Branch name is required (--branch)")
            args = ["git", "checkout", "-b", branch]
            action = " ".join(args)
        elif command == "pull":
            args = ["git", "pull"] + (["--rebase"] if rebase else [])
            action = " ".join(args)
        elif mirror:
            # Push directly to the destination, preserving existing remotes.
            repo_url = f"git@{get_github_host()}:{namespace}/{repo_name}.git"
            args = ["git", "push", "--mirror", repo_url]
            action = "git push --mirror"
            details.append(("Remote", repo_url))
        else:
            args = ["git", "push"]
            action = "git push"
        ui.fields(place + details + [("Action", action)])
        if mirror and not (yes or ui.confirm(
            f"Mirror push to {repo_url}? This overwrites remote branches and tags "
            "and deletes remote refs that do not exist locally."
        )):
            ui.cancelled()
            return
        cls._run_git(
            args, f"Running {action} in {repo_name}", remotes=command in ("pull", "push") and not mirror, cwd=repo_path
        )
        ui.success(f"Finished {command} in {repo_name}")
