# Changelog

All notable changes to toast-cli will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
