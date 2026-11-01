# Changelog

All notable changes to toast-cli will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> Note: a `vMAJOR.MINOR.PATCH` tag on `main` publishes a release. Versions up to
> 4.1.16 were published per push, so not every patch version has a section here.

## [Unreleased]

### Changed
- **`toast git REPO push --mirror` now asks first.** It names the remote and warns that remote refs can be overwritten or deleted. Use `--yes` in scripts
- `toast git` shows the host, namespace, absolute local path and Git action on stderr before it runs Git. Git stdout goes to stdout; Git stderr stays on stderr
- `toast git` errors name the absolute path or config file and the next step

## [5.0.0] - 2026-10-31

### Changed
- **Breaking: stdout now holds only the result.** Status, warnings, prompts and pickers go to stderr. A script that parsed a status line must read stderr or use the exit status
- **Breaking: `fzf` is gone.** One built-in picker serves every command, with type-to-filter, match highlighting, and the cursor on the current value. A picker needs a terminal; a script names the value, or uses `dot up` and `dot down` instead of `dot sync`
- **Breaking: exit status 130** for Ctrl-C or end of input at a prompt. A declined `git rm` now exits 0
- `ssm get` prints only the value to stdout, and the details to stderr
- Tables are tab-separated in a pipe; `ssm ls` and `dot ls` use the same table as `clean --list`
- `toast` without arguments shows help and exits 0; `--version` and `version` print the same line
- Sizes below 1 GiB use MiB
- Clearer picker entries: `+ Add an EKS cluster`, `- Delete a context`, `+ Create a parameter`, `Print the value`

### Added
- One look across commands: shared palette, symbols (`✓ ! ✗`), messages, colored help and errors; `NO_COLOR` is honored
- `ctx` asks before it deletes one or all contexts
- `ssm put` and `ssm diff` read the value from stdin or a hidden prompt; `ssm put --yes` overwrites without a confirmation
- A spinner during AWS, Git and env-store calls; `git pull` and `push` show Git's result
- Every usage error shows the usage line and the help command; a typo suggests the command
- `Commands` section in help, and completion for subcommands, contexts and profiles

### Fixed
- A picker stops at end of input instead of looping forever
- A long name no longer wraps at 80 columns in a pipe
- A missing tool reports `aws is not installed` instead of an OS error

## [4.2.0] - 2026-10-31

### Changed
- **`toast git REPO rm` now asks first** and names uncommitted changes and unpushed commits; use `--yes` in scripts
- `toast clean` measures items in parallel and shows sizes in MB below 1 GiB
- Pickers show the current context, region or profile as a header

### Added
- **Space-bar picker** for `toast clean` with a live size and free-space footer, blocked rows, Hangul-layout shortcuts and terminal restore on every exit path
- **`toast completion`** for bash, zsh and fish, including `clean` item names
- **`toast clean --json`**, `toast --version`, `-h`, and grouped help with per-command examples
- **Name arguments**: `toast ctx NAME`, `toast env PROFILE`, `toast region NAME`
- **Built-in picker fallback** when `fzf` is not installed
- **`toast clean`** — lists reclaimable disk data with sizes and removes the selected items; running builds, Chrome and booted simulators block the affected items
- **GitLab clone support** — explicit HTTPS/SSH URLs (including custom SSH ports), workspace domain detection, and nested group paths for name-based clones
- **Secret masking** for `dot`/`prompt`/`ssm`
  - `.env.local` values masked in diffs (`KEY=ab****yz`); `.prompt.md` shown as-is
  - `ssm get` and the interactive preview mask values by default; `--reveal` prints plaintext
  - `ssm put` shows a masked NEW-vs-CURRENT diff before overwriting an existing value (identical = no-op)
- **`up`/`down` diff + sync** for `dot`/`prompt`
  - Fetch the env-store copy first and compare against local: identical → no-op, different → masked diff + confirm before overwriting
  - `up` no-op is decided against the S3 copy, so a stale SSM-only parameter still migrates into the bucket
- **Unit tests** for masking, `compare_contents`, git helpers (`sanitize_repo_name`, `get_github_host`), and the `up` no-op decision
- **CI quality gate** — `ruff` lint + `unittest` run on release tags and manual dispatch, before publishing
- **`ruff`** linter configuration (`pyproject.toml`)

### Fixed
- SSM argument order now matches `toast ssm <command> [name] [value]` and aliases.
- CLI failures return nonzero status; Click globals are no longer patched.
- Git validates existing repository names, preserves nested mirror namespaces, and leaves remotes unchanged.
- Env-store operations stop on incomplete reads and use the project root file from subdirectories.
- Dotenv masking covers multiline values; downloads are atomic mode 0600 files with preserved line endings.
- Workspace navigation returns only the selected path on stdout and prunes repository contents.
- Documentation copy buttons use the displayed code, report copy failures, and preserve keyboard focus.
- `ctx` add-context flow checked the wrong subprocess result when reading the AWS region
- Logo string used invalid escape sequences (Python 3.12+ `SyntaxWarning`)
- Stale `SSM` labels in env-store sync UI corrected to `env-store`

### Security
- Decrypted S3 objects are staged in a private (0700) temp dir with unique names instead of a fixed world-readable file
- `~/.aws/credentials` is written atomically (temp file + `os.replace`, mode 0600)

### Changed
- Env-store reads/listings run in parallel and require a configured SSM region instead of assuming `us-east-1`.
- SSM writes require a successful read and use private JSON payload files.
- Architecture documentation uses a responsive HTML diagram; removed duplicate renderers and Three.js dependencies.
- Removed the stale, contradictory `setup.cfg` (build metadata now lives solely in `setup.py`)
- `git` branch/pull/push no longer mutate the process working directory (`subprocess(cwd=...)`)

## [4.1.0] - 2026-06-06

### Added
- **`ssm` command** — AWS SSM Parameter Store operations
  - Interactive mode (browse/select parameters via fzf) plus `ls`, `get`/`g`, `put`/`p`, `delete`/`rm`/`d`
  - `--region`/`-r` option for cross-region operations
  - Values stored as `SecureString`
- **S3 env-store backend for `dot` and `prompt`**
  - Sensitive files (`.env.local`, `.prompt.md`) stored in an S3 bucket with SSE-KMS
  - Dual-backend transition from SSM: reads use whichever copy is newest (ties prefer S3), writes always go to S3
  - Shared `storage.py` layer; `sync` (default), `up`, `down`/`dn`, `ls` commands
  - Configurable via `TOAST_ENV_STORE_PROFILE`/`_BUCKET`/`_KMS_KEY`/`_REGION` env vars or `~/.config/toast/config` (env var > config file > default)
- **Git `rm` command** — remove a local repository
- **Git clone `--target`/`-t`** — clone into a custom directory name
- **Unit tests for the env-store backend** (`tests/test_storage.py`)

### Fixed
- S3 `put-object` server-side encryption flag (`--server-side-encryption aws:kms`)
- SSM reads fall back to `us-east-1` when no region is configured, so a missing parameter is reported as absent instead of failing

## [4.0.0] - 2026-01-07

### Breaking Changes
- **Minimum Python version raised to 3.9+** (previously 3.6+)
  - Python 3.6, 3.7, and 3.8 are no longer supported as they have reached EOL
  - Enables use of modern Python standard library features

### Changed
- **Replaced deprecated `pkg_resources` with `importlib.metadata`**
  - Version retrieval now uses `importlib.metadata.version()`
  - Removed dependency on setuptools' pkg_resources (deprecated, to be removed in Nov 2025)
  - Cleaner, more maintainable code with standard library support
- **Removed VERSION file from package data**
  - Version information now sourced directly from package metadata
  - Simplified package distribution configuration
- **Updated Python version classifiers**
  - Added: Python 3.9, 3.10, 3.11, 3.12
  - Removed: Python 3.6, 3.7, 3.8

### Added
- **Colored logo in help output**
  - Logo displayed in bold yellow using Rich Console
  - Version number shown in bold cyan
  - Improved visual appeal and readability
- **Enhanced terminal output with Rich Console colors**
  - Success messages: Green with ✓ checkmark (e.g., "✓ Created workspace directory")
  - Error messages: Red with ✗ cross mark (e.g., "✗ Error fetching AWS caller identity")
  - Info messages: Cyan for headers and current status
  - Warning messages: Yellow for informational warnings
  - Examples and paths: Dimmed or yellow for emphasis
  - Applied to ALL plugins: cdw, am, env, region, ctx, git, dot, prompt, ssm
  - Consistent color scheme across all commands and operations
- **Automatic workspace directory initialization**
  - `toast cdw` now automatically creates `~/workspace` and `~/workspace/github.com` directories
  - Displays helpful instructions for first-time users with colored formatting
  - Eliminates manual directory setup for new installations

### Fixed
- Version display now properly aligned on the same line as logo

### Improved
- Simplified version retrieval logic with cleaner fallback mechanism
- Better error handling for version detection in development environments
- Reduced package complexity by removing unnecessary package_data configuration

## [3.6.0] - Previous Release

- SSM Parameter Store integration for .env.local and .prompt.md files
- Sync command for comparing local and remote files
- Git operations with organization-specific GitHub host support
- Multiple plugin enhancements and bug fixes

---

**Note**: For releases prior to 4.0.0, please refer to git commit history.
