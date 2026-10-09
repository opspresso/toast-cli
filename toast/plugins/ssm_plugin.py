#!/usr/bin/env python3

import json
import os
import subprocess
import tempfile

import click
from rich.console import Console
from toast.plugins.base_plugin import BasePlugin
from toast.plugins.utils import (
    aws_error_code,
    fetch_ssm_parameter,
    run_command,
    select_from_list,
    mask_secret,
    mask_lines,
    show_diff,
    print_unified_diff,
)

console = Console(markup=False, highlight=False)


class SsmPlugin(BasePlugin):
    """Direct SSM operations; failures stop the command before any dependent write."""

    name = "ssm"
    help = "AWS SSM Parameter Store operations"

    @classmethod
    def get_arguments(cls, func):
        # Click reverses decorators when it constructs the command parameters.
        func = click.argument("value", required=False)(func)
        func = click.argument("name", required=False)(func)
        func = click.argument("command", required=False)(func)
        func = click.option("--region", "-r", help="AWS region")(func)
        func = click.option("--reveal", is_flag=True, help="Show secret values in plaintext")(func)
        return func

    @classmethod
    def execute(cls, command=None, name=None, value=None, region=None, reveal=False, **kwargs):
        def aws_cmd(args):
            return ["aws", "ssm"] + args + (["--region", region] if region else [])

        aliases = {"g": "get", "p": "put", "d": "delete", "rm": "delete"}
        command = aliases.get(command, command)
        if command and command.startswith("/"):
            if name is not None or value is not None:
                raise click.UsageError("A parameter shorthand accepts only its name")
            name, command = command, "get"
        if command not in (None, "get", "put", "diff", "delete", "ls"):
            raise click.UsageError(f"Unknown ssm command: {command}")
        if value is not None and command not in ("put", "diff"):
            raise click.UsageError(f"{command} does not accept a value")
        if command in ("get", "delete", "put", "diff") and not name:
            raise click.UsageError("Parameter name is required")
        if command in ("put", "diff") and not value:
            raise click.UsageError("Parameter value is required")

        if command == "get":
            cls._get_parameter(name, aws_cmd, reveal)
        elif command == "put":
            cls._put_parameter(name, value, aws_cmd)
        elif command == "diff":
            cls._diff_parameter(name, value, aws_cmd)
        elif command == "delete":
            cls._delete_parameter(name, aws_cmd)
        elif command == "ls":
            cls._list_parameters(name, aws_cmd)
        else:
            cls._interactive_mode(aws_cmd, reveal)

    @staticmethod
    def _fetch_parameter(name, aws_cmd):
        return fetch_ssm_parameter(aws_cmd([
            "get-parameter", "--name", name, "--with-decryption", "--output", "json",
        ]))

    @classmethod
    def _require_parameter(cls, name, aws_cmd):
        parameter = cls._fetch_parameter(name, aws_cmd)
        if parameter is None:
            raise click.ClickException(f"Parameter '{name}' not found")
        return parameter

    @staticmethod
    def _display_parameter(name, parameter, reveal=False):
        console.print(f"Name: {name}")
        console.print(f"Type: {parameter.get('Type', '')}")
        if parameter.get("LastModifiedDate"):
            console.print(f"Last Modified: {parameter['LastModifiedDate']}")
        console.print("-" * 40)
        # click.echo preserves markup-like text, whitespace, and long values.
        click.echo(parameter["Value"] if reveal else mask_secret(parameter["Value"]))
        if not reveal:
            console.print("(masked — use --reveal to show full value)", style="yellow")

    @classmethod
    def _get_parameter(cls, name, aws_cmd, reveal=False):
        cls._display_parameter(name, cls._require_parameter(name, aws_cmd), reveal)

    @classmethod
    def _fetch_parameter_value(cls, name, aws_cmd):
        try:
            parameter = cls._fetch_parameter(name, aws_cmd)
            return (parameter["Value"] if parameter is not None else None), None
        except (OSError, ValueError, click.ClickException) as exc:
            return None, str(exc)

    @staticmethod
    def _print_diff(name, value, existing):
        console.print(f"'{name}' differences (masked):")
        console.print("-" * 40)
        print_unified_diff(show_diff(
            mask_lines(value), mask_lines(existing), local_name="NEW", remote_name="CURRENT",
        ))
        console.print("-" * 40)

    @classmethod
    def _put_parameter(cls, name, value, aws_cmd):
        existing, error = cls._fetch_parameter_value(name, aws_cmd)
        if error:
            raise click.ClickException(f"Could not read current value: {error}")
        if existing == value:
            console.print(f"✓ '{name}' already has this value. Nothing to do.", style="bold green")
            return
        if existing is not None:
            cls._print_diff(name, value, existing)
            if not click.confirm(f"Store '{name}' as SecureString (overwrites current value)?"):
                console.print("Operation cancelled.")
                return

        # Keep plaintext out of the child process command line. A private file
        # also preserves literal values beginning with file:// or fileb://.
        fd, path = tempfile.mkstemp(prefix="toast-ssm-", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump({"Name": name, "Value": value, "Type": "SecureString", "Overwrite": existing is not None}, stream)
            result = subprocess.run(
                aws_cmd(["put-parameter", "--cli-input-json", f"file://{path}", "--output", "json"]),
                capture_output=True, text=True,
            )
            if result.returncode:
                # Validation errors may echo the payload, so show only the code.
                code = aws_error_code(result.stderr) or f"exit status {result.returncode}"
                raise click.ClickException(f"Could not store '{name}': {code}")
            version = json.loads(result.stdout)["Version"]
        finally:
            os.unlink(path)
        console.print(f"✓ Successfully stored '{name}' (Version: {version})", style="bold green")

    @classmethod
    def _diff_parameter(cls, name, value, aws_cmd):
        existing, error = cls._fetch_parameter_value(name, aws_cmd)
        if error:
            raise click.ClickException(f"Could not read current value: {error}")
        if existing is None:
            console.print(f"'{name}' does not exist. New value would create it.")
        elif existing == value:
            console.print(f"✓ '{name}' already has this value. No differences.", style="bold green")
        else:
            cls._print_diff(name, value, existing)

    @classmethod
    def _delete_parameter(cls, name, aws_cmd):
        if not click.confirm(f"Delete parameter '{name}'? This cannot be undone."):
            console.print("Operation cancelled.")
            return
        run_command(aws_cmd(["delete-parameter", "--name", name]))
        console.print(f"✓ Successfully deleted '{name}'", style="bold green")

    @classmethod
    def _list_parameters(cls, path, aws_cmd):
        args = (["get-parameters-by-path", "--path", path, "--recursive"] if path else ["describe-parameters"])
        parameters = json.loads(run_command(aws_cmd(args + ["--output", "json"])).stdout)["Parameters"]
        if not parameters:
            console.print("No parameters found.", style="yellow")
            return
        console.print(f"AWS SSM Parameters{' under ' + path if path else ''}:")
        for parameter in parameters:
            console.print(parameter["Name"])
            console.print(f"  Type: {parameter.get('Type', '')}, Modified: {parameter.get('LastModifiedDate', '')}")

    @classmethod
    def _interactive_mode(cls, aws_cmd, reveal=False):
        console.print("Loading parameters from AWS SSM...")
        parameters = json.loads(run_command(aws_cmd(["describe-parameters", "--output", "json"])).stdout)["Parameters"]
        options = ["[New] Create new parameter..."] + sorted(p["Name"] for p in parameters)
        selected = select_from_list(options, "Select parameter")
        if selected == options[0]:
            cls._create_new_parameter(aws_cmd)
        elif selected:
            cls._parameter_actions(selected, aws_cmd, reveal)
        else:
            console.print("No selection made.", style="yellow")

    @classmethod
    def _create_new_parameter(cls, aws_cmd):
        name = click.prompt("Parameter name (e.g., /my/secret)")
        value = click.prompt("Parameter value", hide_input=True)
        cls._put_parameter(name, value, aws_cmd)

    @classmethod
    def _parameter_actions(cls, name, aws_cmd, reveal=False):
        parameter = cls._require_parameter(name, aws_cmd)
        cls._display_parameter(name, parameter, reveal)
        selected = select_from_list(
            ["Copy value (print only)", "Update value", "Delete parameter", "Cancel"], "Select action",
        )
        if selected == "Update value":
            cls._put_parameter(name, click.prompt("New value", hide_input=True), aws_cmd)
        elif selected == "Delete parameter":
            cls._delete_parameter(name, aws_cmd)
        elif selected == "Copy value (print only)":
            click.echo(parameter["Value"])
        else:
            console.print("Operation cancelled.")
