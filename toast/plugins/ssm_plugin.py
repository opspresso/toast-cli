#!/usr/bin/env python3

import json
import os
import sys
import tempfile

import click
from toast import ui
from toast.plugins.base_plugin import BasePlugin
from toast.plugins.utils import (
    aws_error_code,
    fetch_ssm_parameter,
    run_command,
    spawn,
    mask_secret,
    mask_lines,
    show_diff,
)

NEW = "+ Create a parameter"
PRINT = "Print the value"
UPDATE = "Update the value"
DELETE = "Delete the parameter"


class SsmPlugin(BasePlugin):
    """Direct SSM operations; failures stop the command before any dependent write."""

    name = "ssm"
    help = "AWS SSM Parameter Store operations"
    category = "AWS"
    commands = (
        ("get", "Show a masked value; --reveal prints it (alias: g)"),
        ("put", "Store a SecureString; the value can come from stdin (alias: p)"),
        ("diff", "Compare a value with the stored one"),
        ("delete", "Delete after a confirmation (aliases: d, rm)"),
        ("ls", "List parameters, optionally under a path"),
    )
    examples = (
        ("toast ssm", "Browse parameters"),
        ("toast ssm get /app/key --reveal", "Print a value"),
        ("pbpaste | toast ssm put /app/key --yes", "Store a value without shell history"),
        ("toast ssm ls /app", "List a path"),
    )

    @classmethod
    def get_arguments(cls, func):
        # Click reverses decorators when it constructs the command parameters.
        func = click.argument("value", required=False)(func)
        func = click.argument("name", required=False)(func)
        func = click.argument("command", required=False, shell_complete=cls.complete_command)(func)
        func = click.option("--region", "-r", help="AWS region")(func)
        func = click.option("--reveal", is_flag=True, help="Show secret values in plaintext")(func)
        func = click.option("--yes", "-y", is_flag=True, help="Overwrite with put without a confirmation")(func)
        return func

    @classmethod
    def execute(cls, command=None, name=None, value=None, region=None, reveal=False, yes=False, **kwargs):
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
        if yes and command != "put":
            raise click.UsageError("--yes requires put")
        # A value read from a pipe consumes stdin, so no confirmation can follow.
        can_confirm = bool(value) or sys.stdin.isatty()
        if command in ("put", "diff") and not value:
            value = cls._read_value()

        if command == "get":
            cls._get_parameter(name, aws_cmd, reveal)
        elif command == "put":
            cls._put_parameter(name, value, aws_cmd, yes=yes, can_confirm=can_confirm)
        elif command == "diff":
            cls._diff_parameter(name, value, aws_cmd)
        elif command == "delete":
            cls._delete_parameter(name, aws_cmd)
        elif command == "ls":
            cls._list_parameters(name, aws_cmd)
        else:
            cls._interactive_mode(aws_cmd, reveal)

    @staticmethod
    def _read_value():
        """Read a value without placing it in the command line or shell history."""
        if sys.stdin.isatty():
            return ui.prompt("Parameter value", hide_input=True)
        value = sys.stdin.read().removesuffix("\n")
        if not value:
            raise click.UsageError("Parameter value is required")
        return value

    @staticmethod
    def _fetch_parameter(name, aws_cmd):
        with ui.status(f"Reading {name}"):
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
        details = [("Name", name), ("Type", parameter.get("Type", ""))]
        if parameter.get("LastModifiedDate"):
            details.append(("Modified", str(parameter["LastModifiedDate"])))
        ui.fields(details)
        ui.result(parameter["Value"] if reveal else mask_secret(parameter["Value"]))
        if not reveal:
            ui.muted("Masked. Use --reveal to print the value.")

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
        ui.info(f"{name} differences (masked)")
        ui.rule()
        ui.diff(show_diff(
            mask_lines(value), mask_lines(existing), local_name="NEW", remote_name="CURRENT",
        ))
        ui.rule()

    @classmethod
    def _put_parameter(cls, name, value, aws_cmd, yes=False, can_confirm=True):
        existing, error = cls._fetch_parameter_value(name, aws_cmd)
        if error:
            raise click.ClickException(f"Could not read current value: {error}")
        if existing == value:
            ui.success(f"{name} already has this value")
            return
        if existing is not None:
            cls._print_diff(name, value, existing)
            if not (yes or can_confirm):
                raise click.ClickException(f"{name} already exists. Add --yes to overwrite it.")
            if not (yes or ui.confirm(f"Overwrite {name} as a SecureString?")):
                ui.cancelled()
                return

        # Keep plaintext out of the child process command line. A private file
        # also preserves literal values beginning with file:// or fileb://.
        fd, path = tempfile.mkstemp(prefix="toast-ssm-", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump({"Name": name, "Value": value, "Type": "SecureString", "Overwrite": existing is not None}, stream)
            with ui.status(f"Storing {name}"):
                result = spawn(aws_cmd(["put-parameter", "--cli-input-json", f"file://{path}", "--output", "json"]))
            if result.returncode:
                # Validation errors may echo the payload, so show only the code.
                code = aws_error_code(result.stderr) or f"exit status {result.returncode}"
                raise click.ClickException(f"Could not store '{name}': {code}")
            version = json.loads(result.stdout)["Version"]
        finally:
            os.unlink(path)
        ui.success(f"Stored {name} (version {version})")

    @classmethod
    def _diff_parameter(cls, name, value, aws_cmd):
        existing, error = cls._fetch_parameter_value(name, aws_cmd)
        if error:
            raise click.ClickException(f"Could not read current value: {error}")
        if existing is None:
            ui.info(f"{name} does not exist. This value would create it.")
        elif existing == value:
            ui.success(f"{name} already has this value")
        else:
            cls._print_diff(name, value, existing)

    @classmethod
    def _delete_parameter(cls, name, aws_cmd):
        if not ui.confirm(f"Delete {name}? This cannot be undone."):
            ui.cancelled()
            return
        with ui.status(f"Deleting {name}"):
            run_command(aws_cmd(["delete-parameter", "--name", name]))
        ui.success(f"Deleted {name}")

    @classmethod
    def _list_parameters(cls, path, aws_cmd):
        args = (["get-parameters-by-path", "--path", path, "--recursive"] if path else ["describe-parameters"])
        with ui.status("Listing parameters"):
            parameters = json.loads(run_command(aws_cmd(args + ["--output", "json"])).stdout)["Parameters"]
        if not parameters:
            ui.warning(f"No parameters under {path}" if path else "No parameters")
            return
        ui.table(
            ("TYPE", "MODIFIED", "NAME"),
            [(parameter.get("Type", ""), str(parameter.get("LastModifiedDate", "")), parameter["Name"]) for parameter in parameters],
        )

    @classmethod
    def _interactive_mode(cls, aws_cmd, reveal=False):
        with ui.status("Listing parameters"):
            parameters = json.loads(run_command(aws_cmd(["describe-parameters", "--output", "json"])).stdout)["Parameters"]
        selected = ui.choose(sorted(p["Name"] for p in parameters) + [NEW], "Select a parameter")
        if selected == NEW:
            cls._create_new_parameter(aws_cmd)
        elif selected:
            cls._parameter_actions(selected, aws_cmd, reveal)
        else:
            ui.cancelled()

    @classmethod
    def _create_new_parameter(cls, aws_cmd):
        name = ui.prompt("Parameter name (for example, /my/secret)")
        value = ui.prompt("Parameter value", hide_input=True)
        cls._put_parameter(name, value, aws_cmd)

    @classmethod
    def _parameter_actions(cls, name, aws_cmd, reveal=False):
        parameter = cls._require_parameter(name, aws_cmd)
        cls._display_parameter(name, parameter, reveal)
        selected = ui.choose([PRINT, UPDATE, DELETE], f"Select an action for {name}")
        if selected == UPDATE:
            cls._put_parameter(name, ui.prompt("New value", hide_input=True), aws_cmd)
        elif selected == DELETE:
            cls._delete_parameter(name, aws_cmd)
        elif selected == PRINT:
            ui.result(parameter["Value"])
        else:
            ui.cancelled()
