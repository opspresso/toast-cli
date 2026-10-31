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

Pull requests and pushes to `main` do not start CI. A release tag starts it, or
run the `CI` workflow by hand. CI checks the supported minimum and current Python
versions on Linux and macOS.

## Release

Push a `vMAJOR.MINOR.PATCH` tag on `main`:

```bash
git tag v4.2.0 && git push origin v4.2.0
```

`release.yml` runs CI, checks the tag, writes the tag version to `VERSION` for the
build, publishes to PyPI, and creates a GitHub Release. If a step fails, nothing
after it runs. PyPI never accepts the same version twice, so fix the cause and push
the next version.

## Implementation rules

- Search existing helpers and callers before introducing another abstraction.
- Keep plugins focused on their command; shared subprocess, masking, and file
  operations belong in `toast/plugins/utils.py`.
- All terminal output goes through `toast/ui.py`. Do not create a `Console`, set a
  style or call `click.echo` in a plugin. Send a result to stdout with `ui.result`,
  `ui.table` or `ui.json_result`. Send status to stderr with `ui.success`, `ui.warning`,
  `ui.info` or `ui.muted`. Report a cancel with `ui.cancelled` and exit 0. Word a message
  as a past-tense fact, such as `Deleted x`, not `Successfully deleted x`.
- Wrap work that can take more than a moment in `ui.status`, and ask for a destructive
  action with `ui.confirm`, which defaults to no.
- Keep `Picker` free of terminal access so tests can drive it; `tests/test_ui.py`
  covers the real key loop in a PTY.
- Every `clean` target must stay inside the home directory given to `catalog()` or
  come from a tool or environment value. A hardcoded absolute path would let a test
  in a temporary home reach real data.
- Use `run_command()` for subprocesses whose nonzero status is a failure.
  Use `spawn()` when the call site handles a nonzero status itself.
- Raise `click.UsageError` for invalid arguments and `click.ClickException` for
  operational failures. `BasePlugin` converts expected OS, value, and config
  errors at the command boundary. Do not print an error and return success.
- Do not patch Click globals or catch unexpected exceptions to hide defects.
- Preserve `toast git <repo> <command>` and `toast ssm <command> [name] [value]`.
  Click applies dynamically added argument decorators in reverse order.
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
unique `name` and `help`, set `category`, `commands` and `examples` for the help
screen and completion, and
implement `execute()`. Override `get_arguments()`
for Click options or arguments. Discovery registers classes defined in that
module; imported classes are not registered again.

Run the complete checks above after changes to shared behavior. For website
changes, serve `docs/` with `python -m http.server --directory docs`, check local
links, and verify desktop/mobile layout and affected interactions in a browser.
