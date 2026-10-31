#!/usr/bin/env python3

import subprocess
import click
import json
import re
import os
import tempfile


# hashlib, difflib and concurrent.futures load inside the functions that need them.
# Every command and every shell completion would pay for them otherwise.


def spawn(args, **kwargs):
    """Run a command and return its result, whatever its exit status."""
    try:
        return subprocess.run(args, capture_output=True, text=True, **kwargs)
    except FileNotFoundError as exc:
        raise click.ClickException(f"{args[0]} is not installed") from exc


def run_command(args, **kwargs):
    """Run a command and report failures without including its arguments."""
    result = spawn(args, **kwargs)
    if result.returncode:
        detail = result.stderr.strip() or f"exit status {result.returncode}"
        raise click.ClickException(f"{args[0]} failed: {detail}")
    return result


def write_private_file(path, content):
    """Atomically replace a UTF-8 file with a private, complete copy."""
    fd, temporary = tempfile.mkstemp(prefix=".toast-", dir=os.path.dirname(os.path.abspath(path)))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def aws_error_code(stderr):
    """Extract the service error code, without mistaking message text for a code."""
    match = re.search(r"An error occurred \(([^)]+)\)", stderr or "")
    return match.group(1) if match else None


def fetch_ssm_parameter(args):
    """Return a decrypted Parameter object, or None only for ParameterNotFound."""
    result = spawn(args)
    if result.returncode:
        if aws_error_code(result.stderr) == "ParameterNotFound":
            return None
        raise click.ClickException(result.stderr.strip() or f"AWS exited with {result.returncode}")
    parameter = json.loads(result.stdout).get("Parameter")
    if not isinstance(parameter, dict) or not isinstance(parameter.get("Value"), str):
        raise click.ClickException("Invalid AWS SSM response: Parameter.Value is missing")
    return parameter


def get_ssm_parameter(ssm_path, profile=None, region=None):
    """Return (value, LastModifiedDate, error); only a missing parameter is absent."""
    args = ["aws", "ssm", "get-parameter", "--name", ssm_path, "--with-decryption", "--output", "json"]
    if profile:
        args += ["--profile", profile]
    if region:
        args += ["--region", region]
    try:
        parameter = fetch_ssm_parameter(args)
        if parameter is None:
            return None, None, None
        return parameter["Value"], parameter.get("LastModifiedDate"), None
    except (OSError, ValueError, click.ClickException) as exc:
        return None, None, str(exc)


def compute_hash(content):
    """Compute SHA256 hash of content."""
    if content is None:
        return None
    import hashlib

    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]


def mask_secret(value, visible=2):
    """Partially mask a secret string, revealing only the first/last chars.

    Values no longer than 2*visible are fully masked. Longer values reveal the
    first and last `visible` characters; the middle is replaced with stars
    capped at 12 so very long secrets do not leak their exact length.
    """
    if value is None:
        return None
    if visible <= 0:
        return "*" * min(len(value), 12)
    n = len(value)
    if n == 0:
        return value
    if n <= visible * 2:
        return "*" * n
    middle = n - visible * 2
    return value[:visible] + "*" * min(middle, 12) + value[-visible:]


def mask_env_content(content, visible=2):
    """Mask dotenv values, including quoted continuations and malformed lines.

    Only assignment keys and comments outside values are safe to show verbatim.
    """
    if content is None:
        return None

    def quote_remains_open(value, quote):
        escaped = False
        for char in value:
            if char == quote and not escaped:
                return False
            escaped = char == "\\" and not escaped
        return True

    out = []
    quote = None
    for line in content.splitlines():
        stripped = line.strip()
        if quote:
            out.append(mask_secret(line, visible))
            if not quote_remains_open(line, quote):
                quote = None
        elif not stripped or stripped.startswith("#"):
            out.append(line)
        else:
            assignment = re.match(r"([ \t]*(?:export[ \t]+)?[A-Za-z_][A-Za-z0-9_]*[ \t]*=)(.*)", line)
            if assignment:
                key, value = assignment.groups()
                out.append(key + mask_secret(value, visible))
                value = value.lstrip()
                if value[:1] in ("'", '\"') and quote_remains_open(value[1:], value[0]):
                    quote = value[0]
            else:
                out.append(mask_secret(line, visible))
    return "\n".join(out)


def mask_lines(content, visible=2):
    """Mask each non-blank line of content via mask_secret (blank lines kept)."""
    if content is None:
        return None
    return "\n".join(
        mask_secret(line, visible) if line.strip() else line
        for line in content.splitlines()
    )


def show_diff(local_content, remote_content, local_name="LOCAL", remote_name="REMOTE"):
    """
    Show diff between local and remote content.

    Returns:
        list: Diff lines for display
    """
    import difflib

    local_lines = (local_content or "").splitlines(keepends=True)
    remote_lines = (remote_content or "").splitlines(keepends=True)

    diff = list(
        difflib.unified_diff(
            remote_lines,
            local_lines,
            fromfile=f"{remote_name}",
            tofile=f"{local_name}",
            lineterm="",
        )
    )

    return diff


def compare_contents(local_content, remote_content):
    """
    Compare local and remote contents.

    Returns:
        str: One of 'identical', 'different', 'local_only', 'remote_only', 'both_missing'
    """
    if local_content is None and remote_content is None:
        return "both_missing"
    elif local_content is None:
        return "remote_only"
    elif remote_content is None:
        return "local_only"
    elif local_content == remote_content:
        return "identical"
    else:
        return "different"
