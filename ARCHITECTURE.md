# Toast-cli architecture

Toast-cli is a Python 3.9+ CLI built with Click and Rich. Plugins use installed
command-line tools instead of adding Python SDK dependencies.

## Execution flow

1. `toast` calls `toast.main`; `python -m toast` uses `toast/__main__.py`.
2. `toast/__init__.py` discovers modules under `toast/plugins/` and registers
   classes defined in each module that extend `BasePlugin`.
3. Click parses the command. `BasePlugin` invokes `execute()` and converts
   expected OS, value, and configuration errors to nonzero exits on stderr.
4. Plugins call shared helpers or external tools. A failed external command
   stops dependent work; it must not produce a success message.

Plugin import or registration failures stop startup. Click's global functions
are unchanged. `toast/helpers.py` supplies the help logo and version lookup
(installed metadata, with a local `VERSION` fallback when not installed).

## Components

| File | Responsibility |
|------|----------------|
| `toast/plugins/base_plugin.py` | Registration and expected-error boundary |
| `toast/plugins/utils.py` | Checked subprocesses, fzf selection, SSM reads, secret masking, diffs, atomic private files |
| `toast/plugins/storage.py` | Shared dot/prompt configuration and S3/SSM synchronization |
| `toast/plugins/*_plugin.py` | Individual command arguments and behavior |
| `setup.py`, `pyproject.toml`, `MANIFEST.in` | Package metadata, build configuration, source distribution |
| `tests/` | Unit and isolated CLI/Git regression tests |
| `docs/` | Static documentation; HTML architecture diagram with no graphics dependency |

## Command boundaries

| Command | Behavior and external tools |
|---------|-----------------------------|
| `am` | AWS STS identity, explicit JSON output |
| `cdw` | Walk workspace namespaces until repository roots; fzf selection; only the selected path goes to stdout |
| `ctx` | kubectl contexts; AWS EKS discovery and kubeconfig update |
| `dot`, `prompt` | Shared env-store flow described below |
| `env` | Copy a complete static profile to default in the AWS credentials file; atomic mode 0600 write; verify the default identity |
| `git` | Clone, branch, pull, push, mirror push, remove; Git and Python filesystem operations |
| `region` | AWS EC2 region discovery and AWS CLI default configuration |
| `ssm` | Direct get/put/diff/delete/list and interactive browsing through AWS CLI |
| `version` | Installed package version |

`git` uses `toast git <repo> <command>`. Explicit clone URLs preserve SSH users
and ports. Name-based clone and mirror push derive the namespace from all path
segments below `workspace/{git-host}`. `GITHUB_HOST` can override the host.
Existing repository operations validate the exact directory name and reject
symlinks. Mirror push uses a destination URL without modifying remotes.

`ssm` uses `toast ssm <command> [name] [value]`. A read error stops put/diff.
Creation sends `Overwrite=false`; updating requires a successful comparison and
confirmation. Put payloads use a private temporary JSON file, so values are
literal and are not added to the AWS child process arguments. Direct CLI value
arguments can still appear in shell history; interactive creation hides input.

## Env-store contracts

`dot` manages `.env.local`; `prompt` manages `.prompt.md`. Both use the project
root under `workspace/github.com/{org}/{project}`, including when invoked in a
subdirectory. They currently do not map GitLab namespaces to storage keys.
`ls` can run outside a workspace.

| Backend | Path | Operations |
|---------|------|------------|
| S3 | `s3://{bucket}/local/{org}/{project}/{kind}` | Read, list, write with SSE-KMS |
| Legacy SSM | `/toast/local/{org}/{project}/{kind}` | Read and list only |

`kind` is `env-local` or `prompt-md`. Reads and listings query both backends in
parallel. The newer timestamp wins; ties prefer S3. A failed read is never
absence. Conflicting values require valid timestamps before either is called
the newest copy. The CLI stops if a backend fails.

Writes always target S3. `up` compares against the S3 copy for its no-op decision,
so a matching SSM copy still migrates if S3 is missing or stale. Downloads compare
against the newest copy. Existing destinations require confirmation; new
destinations do not. Sync uses the user's selected upload/download action.

Local downloads are atomic UTF-8 writes with mode 0600 and preserve line endings.
Diff masking does not affect stored values or equality. Dotenv assignments,
quoted continuations, and unrecognized lines are masked; prompt markdown is
shown literally. Both empty and missing files have distinct states.

Configuration precedence is environment > `~/.config/toast/config` > defaults.
See [README.md](README.md#env-store-s3-storage-paths) for keys and setup.
All storage calls use the resolved dedicated AWS profile. SSM requires a
resolved region; there is no arbitrary-region fallback.

## Extension and verification

Add a module with a `BasePlugin` subclass, unique `name`, `help`, and `execute()`.
Use `get_arguments()` for Click parameters. No registry edit is required.

See [CLAUDE.md](CLAUDE.md) for setup and validation commands. CI tests supported
Python endpoints on Linux and macOS and builds both distribution formats before
publication. Package build and release configuration is in
[`.github/workflows/push.yml`](.github/workflows/push.yml).
