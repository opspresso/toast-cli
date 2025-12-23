#!/usr/bin/env python3

import subprocess
import click
import json
import hashlib
import difflib


def select_from_list(options, prompt="Select an option"):
    try:
        fzf_proc = subprocess.run(
            ["fzf", "--height=15", "--reverse", "--border", "--prompt", prompt + ": "],
            input="\n".join(options),
            capture_output=True,
            text=True,
        )
        return fzf_proc.stdout.strip()
    except Exception as e:
        click.echo(f"Error selecting from list: {e}")
        return None


def check_aws_cli():
    """Check if AWS CLI is available."""
    result = subprocess.run(["aws", "--version"], capture_output=True, text=True)
    return result.returncode == 0


def get_ssm_parameter(ssm_path):
    """
    Get parameter value from AWS SSM.

    Returns:
        tuple: (value, last_modified, error_message)
        - value: Parameter value or None if not found
        - last_modified: Last modified date string or None
        - error_message: Error message or None if successful
    """
    try:
        result = subprocess.run(
            [
                "aws",
                "ssm",
                "get-parameter",
                "--name",
                ssm_path,
                "--with-decryption",
                "--output",
                "json",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            if "ParameterNotFound" in result.stderr:
                return None, None, None  # Parameter doesn't exist (not an error)
            return None, None, result.stderr

        response = json.loads(result.stdout)
        parameter = response.get("Parameter", {})
        value = parameter.get("Value", "")
        last_modified = parameter.get("LastModifiedDate", "")

        return value, last_modified, None

    except json.JSONDecodeError:
        return None, None, "Error parsing AWS SSM response"
    except Exception as e:
        return None, None, str(e)


def compute_hash(content):
    """Compute SHA256 hash of content."""
    if content is None:
        return None
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]


def show_diff(local_content, remote_content, local_name="LOCAL", remote_name="SSM"):
    """
    Show diff between local and remote content.

    Returns:
        list: Diff lines for display
    """
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


def select_sync_action(status, file_name):
    """
    Present sync action options to user via fzf.

    Args:
        status: Comparison status ('identical', 'different', 'local_only', 'remote_only')
        file_name: Name of the file being synced

    Returns:
        str: Selected action ('upload', 'download', 'cancel', or None)
    """
    if status == "identical":
        click.echo(f"'{file_name}' is identical between local and SSM.")
        return None

    options = []
    descriptions = {}

    if status == "different":
        options = [
            "⬆ Upload (local → SSM)",
            "⬇ Download (SSM → local)",
            "✗ Cancel",
        ]
        descriptions = {
            "⬆ Upload (local → SSM)": "upload",
            "⬇ Download (SSM → local)": "download",
            "✗ Cancel": "cancel",
        }
    elif status == "local_only":
        options = [
            "⬆ Upload (local → SSM)",
            "✗ Cancel",
        ]
        descriptions = {
            "⬆ Upload (local → SSM)": "upload",
            "✗ Cancel": "cancel",
        }
    elif status == "remote_only":
        options = [
            "⬇ Download (SSM → local)",
            "✗ Cancel",
        ]
        descriptions = {
            "⬇ Download (SSM → local)": "download",
            "✗ Cancel": "cancel",
        }

    if not options:
        return None

    selected = select_from_list(options, f"Select action for {file_name}")

    if selected and selected in descriptions:
        return descriptions[selected]

    return "cancel"
