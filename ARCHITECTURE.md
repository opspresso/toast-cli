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
are unchanged. `toast/helpers.py` supplies the help layout, error reporting and version lookup
(installed metadata, with a local `VERSION` fallback when not installed).

## Components

| File | Responsibility |
|------|----------------|
| `toast/ui.py` | The only module that writes to the terminal: palette, messages, tables, diffs, spinners, prompts and pickers. Results go to stdout and everything else to stderr. `Picker` holds state only; `run_picker` owns the terminal and always restores it |
| `toast/plugins/base_plugin.py` | Registration, help metadata (`category`, `commands`, `examples`) and expected-error boundary |
| `toast/plugins/clean_catalog.py` | `clean` item catalog, parallel size scan and activity guards |
| `toast/plugins/utils.py` | Checked subprocesses, SSM reads, secret masking, diffs, atomic private files |
| `toast/plugins/storage.py` | Shared dot/prompt configuration and S3/SSM synchronization |
| `toast/plugins/*_plugin.py` | Individual command arguments and behavior |
| `setup.py`, `pyproject.toml`, `MANIFEST.in` | Package metadata, build configuration, source distribution |
| `tests/` | Unit and isolated CLI/Git regression tests |
| `docs/` | Static documentation; HTML architecture diagram with no graphics dependency |

## Command boundaries

| Command | Behavior and external tools |
|---------|-----------------------------|
| `am` | AWS STS identity, explicit JSON output |
| `cdw` | Walk workspace namespaces until repository roots; filtering picker; only the selected path goes to stdout |
| `ctx` | kubectl contexts; AWS EKS discovery and kubeconfig update |
| `dot`, `prompt` | Shared env-store flow described below |
| `env` | Copy a complete static profile to default in the AWS credentials file; atomic mode 0600 write; verify the default identity |
| `git` | Clone, branch, pull, push, mirror push, remove; Git and Python filesystem operations |
| `clean` | Picker, prompt fallback, confirmation and removal; the catalog is in `clean_catalog.py` |
| `completion` | Prints the Click completion script for bash, zsh or fish |
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
literal and are not added to the AWS child process arguments. A value given as an
argument can appear in shell history; stdin and the hidden prompt avoid that.

## Env-store contracts

`dot` manages `.env.local`; `prompt` manages `.prompt.md`. Both use the project
root under `workspace/{host}/{org}/{project}`, including when invoked in a
subdirectory. The storage namespace is `{org}` for `github.com` and
`{host}/{org}` for other hosts. GitHub org names cannot contain dots, so a
dotted first key segment identifies a host. Subgroups are not mapped.
`ls` can run outside a workspace.

| Backend | Path | Operations |
|---------|------|------------|
| S3 | `s3://{bucket}/local/{namespace}/{project}/{kind}` | Read, list, write with SSE-KMS |
| Legacy SSM | `/toast/local/{namespace}/{project}/{kind}` | Read and list only |

`kind` is `env-local` or `prompt-md`. Reads and listings query both backends in
parallel. The newer timestamp wins; ties prefer S3. A failed read is never
absence. Conflicting values require valid timestamps before either is called
the newest copy. The CLI stops if a backend fails.

Writes always target S3. An upload (`up`, or the sync upload action) compares
local with the S3 copy for its no-op decision and preview, so a matching SSM copy
still migrates if S3 is missing or stale. A download (`down`, or the sync download
action) compares local with the newest copy and writes that copy. Sync uses the
user's selected action and the values it already read; it does not read again.
An existing destination that differs, including an empty one, requires a
confirmation that defaults to no and names the S3 URI or the absolute local path
and its source. A new destination does not. A declined confirmation writes nothing
and exits 0.

The preview before a change goes to stderr, so `up`, `down` and `sync` leave stdout
empty. The `diff` command prints its diff to stdout as the result. `ui.diff`
shortens a diff only on a terminal of the stream it writes to.

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

See [CLAUDE.md](CLAUDE.md) for setup and validation commands. CI tests the
supported minimum and current Python versions on Linux and macOS. The release
workflow, [`.github/workflows/release.yml`](.github/workflows/release.yml), runs
CI and then builds both distribution formats before publication.
