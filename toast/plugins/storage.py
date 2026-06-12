#!/usr/bin/env python3

"""Env-store backend for the dot/prompt plugins.

During the SSM -> S3 transition, reads check both AWS SSM Parameter Store and
the S3 env-store bucket and use whichever copy is newest. Writes always go to
S3 (the bucket is the source of truth); SSM copies become stale over time and
are harvested into S3 on the next upload.

All store access uses a dedicated AWS profile (default: {username}-admin) so it
is decoupled from whatever profile is currently the user's default.
"""

import os
import re
import sys
import json
import shutil
import getpass
import tempfile
import subprocess
from datetime import datetime, timezone

import click
from rich.console import Console

from toast.plugins.utils import (
    check_aws_cli,
    get_ssm_parameter,
    compute_hash,
    show_diff,
    compare_contents,
    select_sync_action,
    mask_env_content,
    print_unified_diff,
)

console = Console()

# Defaults (overridable via environment variables or the config file).
# - profile defaults to {username}-admin (see default_profile())
# - bucket defaults to env-store-{account-id} of the resolved profile
#   (see default_bucket())
PROFILE_SUFFIX = "-admin"
BUCKET_PREFIX = "env-store-"

# SSM get-parameter requires a region. When none is configured (env/file/profile)
# this fallback keeps SSM reads from failing with NoRegion; a missing parameter
# then returns ParameterNotFound (treated as absent) instead of an error.
DEFAULT_REGION = "us-east-1"


class StoreConfig:
    """Resolved env-store configuration."""

    def __init__(self, bucket, profile, kms_key, region):
        self.bucket = bucket
        self.profile = profile
        self.kms_key = kms_key
        self.region = region


def config_file_path():
    """Path to the toast config file (~/.config/toast/config)."""
    return os.path.expanduser(os.path.join("~", ".config", "toast", "config"))


def render_config(bucket, profile, kms_key, region):
    """Render the config file body for the given env-store values."""
    return "\n".join(
        [
            "# toast configuration",
            "# Format: KEY=VALUE",
            "# Precedence: environment variable > this file > built-in default",
            "",
            "# env-store backend for the dot/prompt plugins",
            f"ENV_STORE_BUCKET={bucket}",
            f"ENV_STORE_PROFILE={profile}",
            f"ENV_STORE_KMS_KEY={kms_key}",
            f"ENV_STORE_REGION={region}",
            "",
        ]
    )


def prompt_and_create_config(path=None):
    """Prompt the user for env-store config and save it.

    Returns True if the file was written. Does nothing (returns False) in a
    non-interactive session or if the user declines.
    """
    path = path or config_file_path()
    console.print(f"Config file not found: {path}", style="yellow")

    if not sys.stdin.isatty():
        return False

    if not click.confirm("Create it now?", default=True):
        return False

    profile = click.prompt(
        "ENV_STORE_PROFILE",
        default=os.environ.get("TOAST_ENV_STORE_PROFILE") or default_profile(),
    )
    region = click.prompt(
        "ENV_STORE_REGION (blank for default)",
        default=os.environ.get("TOAST_ENV_STORE_REGION", ""),
        show_default=False,
    )
    bucket = click.prompt(
        "ENV_STORE_BUCKET",
        default=os.environ.get("TOAST_ENV_STORE_BUCKET")
        or default_bucket(profile, region or None)
        or "",
    )
    kms_key = click.prompt(
        "ENV_STORE_KMS_KEY (blank for default)",
        default=os.environ.get("TOAST_ENV_STORE_KMS_KEY", ""),
        show_default=False,
    )

    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(render_config(bucket, profile, kms_key, region))
        console.print(f"✓ Saved config file: {path}", style="bold green")
        return True
    except Exception as e:
        console.print(f"Warning: Could not write {path}: {e}", style="yellow")
        return False


def read_config_file(path=None):
    """Read KEY=VALUE pairs from the config file. Missing file -> {}."""
    path = path or config_file_path()
    values = {}
    if not os.path.exists(path):
        return values
    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    values[key.strip()] = value.strip()
    except Exception as e:
        console.print(f"Warning: Could not read {path}: {e}", style="yellow")
    return values


def _current_username():
    """Best-effort current OS username."""
    try:
        return getpass.getuser()
    except Exception:
        return os.environ.get("USER") or os.environ.get("USERNAME") or "user"


def default_profile():
    """Default AWS profile: {username}-admin."""
    return f"{_current_username()}{PROFILE_SUFFIX}"


def _profile_region(profile):
    """Region configured for a profile via `aws configure get region`, or None."""
    try:
        result = subprocess.run(
            ["aws", "configure", "get", "region", "--profile", profile],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip() or None
    except Exception:
        return None


def get_account_id(profile, region=None):
    """Return the AWS account id for a profile via STS, or None on failure."""
    cmd = [
        "aws",
        "sts",
        "get-caller-identity",
        "--query",
        "Account",
        "--output",
        "text",
        "--profile",
        profile,
    ]
    if region:
        cmd += ["--region", region]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return None
        account = result.stdout.strip()
        return account or None
    except Exception:
        return None


def default_bucket(profile, region=None):
    """Default bucket name: env-store-{account-id} of the profile, or None."""
    account_id = get_account_id(profile, region)
    if not account_id:
        return None
    return f"{BUCKET_PREFIX}{account_id}"


def resolve_config(config_path=None, create=True):
    """Resolve env-store configuration.

    Precedence: environment variable > config file > built-in default.
    Prompts to create the config file on first run if missing.

    Default profile is {username}-admin; default bucket is env-store-{account-id}
    of the resolved profile.
    """
    path = config_path or config_file_path()
    if create and not os.path.exists(path):
        prompt_and_create_config(path)
    file_cfg = read_config_file(path)

    def pick(env_key, file_key, default):
        return os.environ.get(env_key) or file_cfg.get(file_key) or default

    profile = pick("TOAST_ENV_STORE_PROFILE", "ENV_STORE_PROFILE", default_profile())
    region = (
        pick("TOAST_ENV_STORE_REGION", "ENV_STORE_REGION", "")
        or _profile_region(profile)
        or None
    )
    kms_key = pick("TOAST_ENV_STORE_KMS_KEY", "ENV_STORE_KMS_KEY", "") or None
    bucket = (
        os.environ.get("TOAST_ENV_STORE_BUCKET")
        or file_cfg.get("ENV_STORE_BUCKET")
        or default_bucket(profile, region)
    )

    return StoreConfig(bucket=bucket, profile=profile, kms_key=kms_key, region=region)


def ssm_path(org, project, kind):
    """SSM parameter path for a stored file."""
    return f"/toast/local/{org}/{project}/{kind}"


def s3_key(org, project, kind):
    """S3 object key for a stored file."""
    return f"local/{org}/{project}/{kind}"


def _parse_s3_key(key):
    """Parse 'local/{org}/{project}/{kind}' -> (org, project, kind) or None."""
    parts = key.split("/")
    if len(parts) == 4 and parts[0] == "local":
        return parts[1], parts[2], parts[3]
    return None


def _parse_ssm_name(name):
    """Parse '/toast/local/{org}/{project}/{kind}' -> (org, project, kind) or None."""
    parts = name.strip("/").split("/")
    if len(parts) == 5 and parts[0] == "toast" and parts[1] == "local":
        return parts[2], parts[3], parts[4]
    return None


def parse_timestamp(value):
    """Parse an AWS timestamp (SSM/S3) into an aware UTC datetime, or None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if not isinstance(value, str) or not value.strip():
        return None

    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    dt = None
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
        ):
            try:
                dt = datetime.strptime(s, fmt)
                break
            except ValueError:
                continue

    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _aws(config, service_args, region=None):
    """Build an aws CLI command with the env-store profile (and region) applied.

    A `region` override takes precedence over config.region (used for SSM, which
    requires a region even when none is configured).
    """
    cmd = ["aws"] + service_args + ["--profile", config.profile]
    resolved = region or config.region
    if resolved:
        cmd += ["--region", resolved]
    return cmd


def _ssm_region(config):
    """Region for SSM calls: configured region, else a safe default."""
    return config.region or DEFAULT_REGION


def s3_get(config, key):
    """Get an object's content and LastModified.

    Returns (value, last_modified, error). A missing object returns
    (None, None, None); a hard failure returns (None, None, error).
    """
    # Write the (decrypted) object into a private 0700 temp dir so the plaintext
    # is never world-readable and concurrent invocations never collide.
    tmp_dir = tempfile.mkdtemp(prefix="toast-")
    tmp = os.path.join(tmp_dir, "object")
    try:
        result = subprocess.run(
            _aws(
                config,
                [
                    "s3api",
                    "get-object",
                    "--bucket",
                    config.bucket,
                    "--key",
                    key,
                    "--output",
                    "json",
                    tmp,
                ],
            ),
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            stderr = result.stderr or ""
            if "NoSuchKey" in stderr or "Not Found" in stderr or "404" in stderr:
                return None, None, None
            return None, None, stderr.strip()

        meta = json.loads(result.stdout) if result.stdout.strip() else {}
        last_modified = meta.get("LastModified")
        with open(tmp, "r") as f:
            value = f.read()
        return value, last_modified, None

    except json.JSONDecodeError:
        return None, None, "Error parsing S3 get-object response"
    except Exception as e:
        return None, None, str(e)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def s3_put(config, key, content):
    """Upload content to S3 as a SecureString equivalent (SSE-KMS).

    Returns (ok, error).
    """
    # mkstemp creates the file with 0600 perms and a unique name, so the
    # plaintext body is not world-readable and concurrent puts never collide.
    fd, tmp = tempfile.mkstemp(prefix="toast-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)

        args = [
            "s3api",
            "put-object",
            "--bucket",
            config.bucket,
            "--key",
            key,
            "--body",
            tmp,
            "--server-side-encryption",
            "aws:kms",
            "--output",
            "json",
        ]
        if config.kms_key:
            args += ["--ssekms-key-id", config.kms_key]

        result = subprocess.run(_aws(config, args), capture_output=True, text=True)
        if result.returncode != 0:
            return False, (result.stderr or "").strip()
        return True, None

    except Exception as e:
        return False, str(e)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def s3_list(config, prefix="local/"):
    """List env-store objects under prefix.

    Returns (entries, error) where entries = [{key, last_modified}].
    """
    try:
        result = subprocess.run(
            _aws(
                config,
                [
                    "s3api",
                    "list-objects-v2",
                    "--bucket",
                    config.bucket,
                    "--prefix",
                    prefix,
                    "--output",
                    "json",
                ],
            ),
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return [], (result.stderr or "").strip()
        if not result.stdout.strip():
            return [], None

        data = json.loads(result.stdout)
        entries = [
            {"key": c.get("Key", ""), "last_modified": c.get("LastModified")}
            for c in data.get("Contents", [])
        ]
        return entries, None

    except json.JSONDecodeError:
        return [], "Error parsing S3 list-objects-v2 response"
    except Exception as e:
        return [], str(e)


def ssm_get(config, path):
    """Get an SSM parameter value and LastModified using the env-store profile."""
    return get_ssm_parameter(path, profile=config.profile, region=_ssm_region(config))


def ssm_list(config, prefix="/toast/local/"):
    """List SSM parameters under prefix.

    Returns (entries, error) where entries = [{name, last_modified}].
    """
    try:
        result = subprocess.run(
            _aws(
                config,
                [
                    "ssm",
                    "get-parameters-by-path",
                    "--path",
                    prefix,
                    "--recursive",
                    "--output",
                    "json",
                ],
                region=_ssm_region(config),
            ),
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return [], (result.stderr or "").strip()

        data = json.loads(result.stdout)
        entries = [
            {"name": p.get("Name", ""), "last_modified": p.get("LastModifiedDate")}
            for p in data.get("Parameters", [])
        ]
        return entries, None

    except json.JSONDecodeError:
        return [], "Error parsing SSM response"
    except Exception as e:
        return [], str(e)


class ReadResult:
    """Result of a dual-backend read."""

    def __init__(
        self, value, source, s3_value, s3_last, ssm_value, ssm_last, status, errors
    ):
        self.value = value          # newest content, or None
        self.source = source        # 's3' | 'ssm' | None
        self.s3_value = s3_value
        self.s3_last = s3_last      # raw timestamp
        self.ssm_value = ssm_value
        self.ssm_last = ssm_last    # raw timestamp
        self.status = status        # 'both' | 's3_only' | 'ssm_only' | 'none'
        self.errors = errors        # [(source, message)]


def store_read(config, org, project, kind):
    """Read from both backends and return whichever copy is newest."""
    s3_value, s3_last, s3_err = s3_get(config, s3_key(org, project, kind))
    ssm_value, ssm_last, ssm_err = ssm_get(config, ssm_path(org, project, kind))

    errors = []
    if s3_err:
        errors.append(("s3", s3_err))
    if ssm_err:
        errors.append(("ssm", ssm_err))

    has_s3 = s3_value is not None
    has_ssm = ssm_value is not None
    s3_dt = parse_timestamp(s3_last) if has_s3 else None
    ssm_dt = parse_timestamp(ssm_last) if has_ssm else None

    if has_s3 and has_ssm:
        status = "both"
        if s3_dt and ssm_dt:
            # Newest wins; ties prefer S3 (the source of truth).
            source = "s3" if s3_dt >= ssm_dt else "ssm"
        elif ssm_dt and not s3_dt:
            source = "ssm"
        else:
            source = "s3"
    elif has_s3:
        status, source = "s3_only", "s3"
    elif has_ssm:
        status, source = "ssm_only", "ssm"
    else:
        status, source = "none", None

    value = s3_value if source == "s3" else (ssm_value if source == "ssm" else None)

    return ReadResult(
        value, source, s3_value, s3_last, ssm_value, ssm_last, status, errors
    )


def store_write(config, org, project, kind, content):
    """Write content to the S3 env-store (bucket is the source of truth)."""
    return s3_put(config, s3_key(org, project, kind), content)


def store_list(config, kind):
    """Merge S3 and SSM listings for a kind.

    Returns (rows, errors) where rows = [{path, source, last_modified,
    in_s3, in_ssm}] sorted by path.
    """
    errors = []
    merged = {}

    s3_entries, s3_err = s3_list(config)
    if s3_err:
        errors.append(("s3", s3_err))
    for e in s3_entries:
        parsed = _parse_s3_key(e["key"])
        if not parsed:
            continue
        org, project, k = parsed
        if k != kind:
            continue
        slot = merged.setdefault(f"{org}/{project}", {"s3": None, "ssm": None})
        slot["s3"] = e["last_modified"]

    ssm_entries, ssm_err = ssm_list(config)
    if ssm_err:
        errors.append(("ssm", ssm_err))
    for e in ssm_entries:
        parsed = _parse_ssm_name(e["name"])
        if not parsed:
            continue
        org, project, k = parsed
        if k != kind:
            continue
        slot = merged.setdefault(f"{org}/{project}", {"s3": None, "ssm": None})
        slot["ssm"] = e["last_modified"]

    rows = []
    for path, slot in merged.items():
        s3_dt = parse_timestamp(slot["s3"])
        ssm_dt = parse_timestamp(slot["ssm"])
        if s3_dt and ssm_dt:
            source = "s3" if s3_dt >= ssm_dt else "ssm"
        elif s3_dt:
            source = "s3"
        elif ssm_dt:
            source = "ssm"
        else:
            source = "?"
        latest = slot["s3"] if source == "s3" else (
            slot["ssm"] if source == "ssm" else None
        )
        rows.append(
            {
                "path": path,
                "source": source,
                "last_modified": latest,
                "in_s3": slot["s3"] is not None,
                "in_ssm": slot["ssm"] is not None,
            }
        )

    rows.sort(key=lambda r: r["path"])
    return rows, errors


# ---------------------------------------------------------------------------
# Command handlers shared by the dot and prompt plugins
# ---------------------------------------------------------------------------


def _mask_for_display(content, kind):
    """Mask secret values for on-screen diffs. Only env-local is masked;
    prompt-md is regular markdown and shown as-is."""
    if kind == "env-local":
        return mask_env_content(content)
    return content


def _print_masked_diff(local_content, remote_content, kind):
    """Print a colored unified diff of local vs remote with secrets masked.

    The identical/different decision is made by the caller on the real
    content; only this display is masked.
    """
    console.print("Differences found:")
    console.print("-" * 40)
    diff_lines = show_diff(
        _mask_for_display(local_content, kind),
        _mask_for_display(remote_content, kind),
        local_name="LOCAL",
        remote_name="ENV-STORE",
    )
    print_unified_diff(diff_lines)
    console.print("-" * 40)


def run_file_sync(kind, filename, command):
    """Shared entry point for the dot/prompt plugins.

    kind: store segment, e.g. 'env-local' or 'prompt-md'
    filename: local file name, e.g. '.env.local' or '.prompt.md'
    command: subcommand string or None (None defaults to 'sync')
    """
    if not check_aws_cli():
        console.print(
            "Error: AWS CLI not found. Please install it to use this feature."
        )
        return

    config = resolve_config()
    if not config.bucket:
        console.print(
            "✗ Error: could not determine the env-store bucket. Set "
            "TOAST_ENV_STORE_BUCKET, or check the AWS profile/credentials "
            f"('{config.profile}').",
            style="bold red",
        )
        return

    current_path = os.getcwd()
    local_path = os.path.join(current_path, filename)

    if command == "ls":
        _cmd_ls(config, kind, filename)
        return

    pattern = r"^(.*/workspace/github.com/[^/]+/[^/]+).*$"
    match = re.match(pattern, current_path)
    if not match:
        console.print(
            "Error: Current directory is not in a recognized workspace structure."
        )
        return

    project_root = match.group(1)
    project_name = os.path.basename(project_root)
    org_name = os.path.basename(os.path.dirname(project_root))

    if command == "up":
        _cmd_up(config, org_name, project_name, kind, filename, local_path)
    elif command in ("down", "dn"):
        _cmd_down(config, org_name, project_name, kind, filename, local_path)
    elif command == "diff":
        _cmd_diff(config, org_name, project_name, kind, filename, local_path)
    elif command in (None, "sync"):
        _cmd_sync(config, org_name, project_name, kind, filename, local_path)
    else:
        console.print(f"Unknown command: {command}", style="yellow")
        console.print(f"Usage: toast {filename_to_cmd(filename)} [sync|up|down|dn|diff|ls]")


def filename_to_cmd(filename):
    """Map a managed file name back to its command name (for usage hints)."""
    return "dot" if filename == ".env.local" else "prompt"


def _cmd_up(config, org, project, kind, filename, local_path):
    if not os.path.exists(local_path):
        console.print(
            f"✗ Error: {filename} not found in current directory.", style="bold red"
        )
        return

    key = s3_key(org, project, kind)
    target = f"s3://{config.bucket}/{key}"

    with open(local_path, "r") as f:
        content = f.read()

    result = store_read(config, org, project, kind)
    for src, e in result.errors:
        console.print(f"⚠ Warning: {src.upper()} read error: {e}", style="yellow")

    # The upload target is S3, so the no-op decision is made against the S3 copy
    # (not the newest copy): when the newest copy is a stale SSM parameter, an
    # `up` still needs to migrate the content into the bucket.
    if result.s3_value is not None and content == result.s3_value:
        console.print(
            "✓ S3 already matches local. No upload needed.", style="bold green"
        )
        return

    overwrite_msg = ""
    if result.value is not None:
        if compare_contents(content, result.value) == "different":
            console.print(
                f"env-store newest ({result.source.upper()}) differs from local."
            )
            _print_masked_diff(content, result.value, kind)
            overwrite_msg = " (overwrites env-store)"
        else:
            # Local matches the newest copy (SSM) but S3 is stale/missing.
            console.print(
                "ℹ Local matches SSM (newest); uploading to migrate it into S3."
            )
            overwrite_msg = " (migrate to S3)"

    if not click.confirm(f"Upload {filename} to {target}{overwrite_msg}?"):
        console.print("Operation cancelled.")
        return

    console.print(f"Uploading {filename} to {target}...")
    ok, err = store_write(config, org, project, kind, content)
    if ok:
        console.print(
            f"✓ Successfully uploaded {filename} to {target}", style="bold green"
        )
    else:
        console.print(f"✗ Error uploading to S3: {err}", style="bold red")


def _cmd_down(config, org, project, kind, filename, local_path):
    result = store_read(config, org, project, kind)

    if result.value is None:
        if result.errors:
            for src, e in result.errors:
                console.print(f"✗ Error reading {src.upper()}: {e}", style="bold red")
        else:
            console.print(
                f"✗ Error: {filename} not found in env-store (S3 or SSM).",
                style="bold red",
            )
        return

    for src, e in result.errors:
        console.print(f"⚠ Warning: {src.upper()} read error: {e}", style="yellow")

    overwrite_msg = ""
    if os.path.exists(local_path):
        with open(local_path, "r") as f:
            local_content = f.read()
        status = compare_contents(local_content, result.value)
        if status == "identical":
            console.print(
                "✓ Local already matches env-store (newest). No download needed.",
                style="bold green",
            )
            return
        console.print("Local file differs from env-store (newest).")
        _print_masked_diff(local_content, result.value, kind)
        overwrite_msg = " (will overwrite existing file)"

    src_label = result.source.upper()
    if not click.confirm(
        f"Download {filename} from {src_label} (newest){overwrite_msg}?"
    ):
        console.print("Operation cancelled.")
        return

    with open(local_path, "w") as f:
        f.write(result.value)
    console.print(
        f"✓ Successfully downloaded {filename} from {src_label} to {local_path}",
        style="bold green",
    )


def _cmd_diff(config, org, project, kind, filename, local_path):
    local_content = None
    if os.path.exists(local_path):
        with open(local_path, "r") as f:
            local_content = f.read()

    result = store_read(config, org, project, kind)
    for src, e in result.errors:
        console.print(f"⚠ Warning: {src.upper()} read error: {e}", style="yellow")

    remote_content = result.value
    status = compare_contents(local_content, remote_content)

    if status == "both_missing":
        console.print("Neither local file nor env-store has this file.")
        return

    if status == "identical":
        console.print(
            "✓ Local matches env-store (newest). No differences.",
            style="bold green",
        )
        return

    if status == "different":
        console.print(
            f"Local {filename} differs from env-store (newest: {result.source.upper()})."
        )
        _print_masked_diff(local_content, remote_content, kind)
    elif status == "local_only":
        console.print("Local file exists, but env-store does not.")
    elif status == "remote_only":
        console.print(
            f"env-store has this file (newest: {result.source.upper()}), but local does not."
        )


def _cmd_sync(config, org, project, kind, filename, local_path):
    key = s3_key(org, project, kind)
    console.print(f"Comparing {filename} with env-store: s3://{config.bucket}/{key}")
    console.print("=" * 60)

    local_content = None
    if os.path.exists(local_path):
        with open(local_path, "r") as f:
            local_content = f.read()

    result = store_read(config, org, project, kind)
    for src, e in result.errors:
        console.print(f"⚠ Warning: {src.upper()} read error: {e}", style="yellow")

    remote_content = result.value

    local_hash = compute_hash(local_content) if local_content else "-"
    s3_hash = compute_hash(result.s3_value) if result.s3_value else "-"
    ssm_hash = compute_hash(result.ssm_value) if result.ssm_value else "-"

    console.print(f"Local: {local_hash if local_content else '(not found)'}")
    console.print(
        f"S3:    {s3_hash if result.s3_value else '(not found)'}"
        + (f"  {result.s3_last}" if result.s3_last else "")
    )
    console.print(
        f"SSM:   {ssm_hash if result.ssm_value else '(not found)'}"
        + (f"  {result.ssm_last}" if result.ssm_last else "")
    )
    if result.source:
        console.print(f"→ current (newest): {result.source.upper()}", style="bold cyan")
    console.print("")

    status = compare_contents(local_content, remote_content)

    if status == "both_missing":
        console.print("Neither local file nor env-store has this file.")
        return

    if status == "identical":
        console.print(
            "✓ Local matches env-store (newest). No action needed.", style="bold green"
        )
        if result.status == "both" and result.source == "ssm":
            console.print(
                "ℹ SSM is newer than S3; run `up` to migrate to the bucket.",
                style="yellow",
            )
        elif result.status == "ssm_only":
            console.print(
                "ℹ This file exists only in SSM; run `up` to migrate to the bucket.",
                style="yellow",
            )
        return

    if status == "different":
        _print_masked_diff(local_content, remote_content, kind)
    elif status == "local_only":
        console.print("Local file exists, but env-store does not.")
    elif status == "remote_only":
        console.print("env-store has this file, but local does not.")

    console.print("")

    action = select_sync_action(status, filename)

    if action == "upload":
        console.print(f"Uploading {filename} to S3...")
        ok, err = store_write(config, org, project, kind, local_content)
        if ok:
            console.print(
                f"✓ Successfully uploaded to s3://{config.bucket}/{key}",
                style="bold green",
            )
        else:
            console.print(f"✗ Error uploading: {err}", style="bold red")
    elif action == "download":
        console.print(f"Downloading from {result.source.upper()} to {filename}...")
        with open(local_path, "w") as f:
            f.write(remote_content)
        console.print(f"✓ Successfully downloaded to {local_path}", style="bold green")
    else:
        console.print("Operation cancelled.")


def _cmd_ls(config, kind, filename):
    console.print(f"Listing {filename} entries in env-store (S3 + SSM)...")
    rows, errors = store_list(config, kind)
    for src, e in errors:
        console.print(f"⚠ Warning: {src.upper()} list error: {e}", style="yellow")

    if not rows:
        console.print("No entries found.", style="yellow")
        return

    console.print("")
    console.print(f"env-store entries ({filename}):")
    console.print("=" * 60)
    for r in rows:
        backends = []
        if r["in_s3"]:
            backends.append("S3")
        if r["in_ssm"]:
            backends.append("SSM")
        backends_str = "+".join(backends)
        console.print(
            f"{r['path']}  [current: {r['source'].upper()}, in: {backends_str}]"
            + (f"  {r['last_modified']}" if r["last_modified"] else ""),
            markup=False,
        )
