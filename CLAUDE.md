# Development guide

Toast-cli is a Click CLI for AWS, Kubernetes, Git, and workspace navigation.
See [README.md](README.md) for commands and configuration, and
[ARCHITECTURE.md](ARCHITECTURE.md) for component boundaries.

## Setup and validation

Use Python 3.9 or later in an isolated environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e . ruff build
ruff check .
python -m unittest discover -s tests
python -m build
python -m toast --help
```

Tests use temporary files, local Git repositories, and mocked AWS process
boundaries. They must not read or modify real AWS resources or credentials.
Exercise commands through Click when changing arguments or exit behavior;
calling `execute()` directly does not test argument order.

CI checks the supported minimum and current Python versions on Linux and macOS.
It builds source and wheel packages on PRs. Pushes to the release branch also
bump the version, publish to PyPI, and create a release.

## Implementation rules

- Search existing helpers and callers before introducing another abstraction.
- Keep plugins focused on their command; shared subprocess, masking, and file
  operations belong in `toast/plugins/utils.py`.
- Use `run_command()` for subprocesses whose nonzero status is a failure.
  Handle documented special exit codes at the call site, such as fzf cancel.
- Raise `click.UsageError` for invalid arguments and `click.ClickException` for
  operational failures. `BasePlugin` converts expected OS, value, and config
  errors at the command boundary. Do not print an error and return success.
- Do not patch Click globals or catch unexpected exceptions to hide defects.
- Preserve `toast git <repo> <command>` and `toast ssm <command> [name] [value]`.
  Click applies dynamically added argument decorators in reverse order.
- Keep `cdw` stdout limited to the selected path; status belongs on stderr.
- Sanitize names only when deriving a new clone directory. Validate existing
  repository names without rewriting them, especially before deletion.
- Compare real values; mask only display output. Treat multiline dotenv
  continuations as secret. Use `--reveal` only for explicit plaintext retrieval.
- Use private temporary files for secret payloads, and `write_private_file()`
  for atomic local replacement. Preserve UTF-8 content and line endings.
- Require successful reads from both env-store backends before comparing or
  writing. Missing objects are distinct from permission, region, and network
  failures. Never choose an arbitrary AWS region to make a read succeed.
- Keep documentation about current contracts. Avoid duplicating the command
  guide in this file.

## Adding a plugin

Create a module under `toast/plugins/`, define a `BasePlugin` subclass with a
unique `name` and `help`, and implement `execute()`. Override `get_arguments()`
for Click options or arguments. Discovery registers classes defined in that
module; imported classes are not registered again.

Run the complete checks above after changes to shared behavior. For website
changes, serve `docs/` with `python -m http.server --directory docs`, check local
links, and verify desktop/mobile layout and affected interactions in a browser.
