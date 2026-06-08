# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Build and Package
```bash
# Install in development mode
pip install -e .

# Build distribution packages
python -m build

# Publish to PyPI (requires credentials)
twine upload dist/*
```

### Running the CLI
```bash
# Run directly after installation
toast --help

# Run as module during development
python -m toast --help

# Common commands
toast version
toast am           # AWS identity
toast cdw          # Navigate workspace
toast ctx          # Kubernetes contexts
toast dot          # Environment file management (.env.local)
toast env          # AWS profiles
toast git          # Git operations (clone, branch, pull, push, rm)
toast prompt       # Prompt file management (.prompt.md)
toast region       # AWS region
toast ssm          # AWS SSM Parameter Store operations
```

### Testing
```bash
# Run unit tests (env-store backend pure logic, no AWS access)
python -m unittest discover -s tests
```

## Architecture Overview

Toast-cli is a plugin-based CLI tool built with Click. The core architecture consists of:

### Plugin Discovery System
- **Main entry point**: `toast/__init__.py` - Uses `importlib` and `pkgutil` for dynamic plugin discovery
- **Plugin loading**: Scans `toast/plugins/` directory, imports modules, and registers classes extending `BasePlugin`
- **Command registration**: Each plugin registers itself with the main CLI group via `plugin_class.register(toast_cli)`

### Base Plugin Architecture
- **BasePlugin** (`toast/plugins/base_plugin.py`): Abstract base class defining the plugin interface
- **Required attributes**: `name` (command name), `help` (command description)
- **Required methods**: `execute(**kwargs)` for command implementation
- **Optional methods**: `get_arguments(func)` for adding Click decorators/options

### Plugin Implementation Pattern
All plugins follow this structure:
```python
class MyPlugin(BasePlugin):
    name = "mycommand"
    help = "Command description"

    @classmethod
    def get_arguments(cls, func):
        # Add Click options/arguments
        return func

    @classmethod
    def execute(cls, **kwargs):
        # Command implementation
        pass
```

### Key Components
- **Helpers** (`toast/helpers.py`): Version handling, custom Click classes for UI
- **Plugin Utils** (`toast/plugins/utils.py`): Common utilities for subprocess execution, fzf integration
- **Env-store** (`toast/plugins/storage.py`): S3/SSM dual-backend storage for dot/prompt (newest-wins reads, S3 writes)
- **Dynamic Loading**: No hardcoded plugin imports - all plugins discovered at runtime

### Plugin Categories
- **AWS plugins**: `am_plugin.py` (identity), `env_plugin.py` (profiles), `region_plugin.py` (regions), `ssm_plugin.py` (SSM Parameter Store)
- **Kubernetes**: `ctx_plugin.py` (context management)
- **Git**: `git_plugin.py` (repository operations: clone, branch, pull, push, rm)
- **Environment**: `dot_plugin.py` (.env.local files), `prompt_plugin.py` (.prompt.md files), backed by `storage.py` (S3 env-store with SSM transition)
- **Navigation**: `cdw_plugin.py` (workspace directory navigation)

## Adding New Plugins

1. Create `toast/plugins/my_plugin.py`
2. Extend `BasePlugin` class
3. Set `name` and `help` class variables
4. Implement `execute()` method
5. Plugin will be automatically discovered and loaded

## Dependencies

**Core dependencies** (defined in setup.py):
- `click`: CLI framework
- `rich`: Terminal formatting

**External tools** (required at runtime):
- `fzf`: Interactive selection menus
- `aws-cli`: AWS operations
- `kubectl`: Kubernetes operations

## Git Plugin Configuration

### Organization-specific GitHub Hosts

The git plugin supports per-organization GitHub host configuration:

**Configuration file**: `~/workspace/github.com/{org}/.toast-config`
```
GITHUB_HOST=custom-host.com
```

**Key features**:
- Automatic repository name sanitization (removes invalid characters like `/`, `:`, etc.)
- Mirror push support for repository migration
- Works with SSH config for different accounts/keys
- Supports both regular push and mirror push operations

### Development Notes for Git Plugin

When working on git_plugin.py:
- Always use `sanitize_repo_name()` to clean repository names (removes `/`, `:`, and other invalid characters)
- Use `get_github_host()` for host detection with organization support
- Follow the simple pattern used by other commands (clone, pull, etc.)
- Handle subprocess calls properly - avoid mixing `capture_output=True` with explicit `stdout`/`stderr`
- Supported commands: `clone` (cl), `rm`, `branch` (b), `pull` (p), `push` (ps) (with optional flags like `-b`, `-t`, `-r`, `-m`/`--mirror`)

### Env-store Integration (S3 with SSM transition)

The `dot` and `prompt` plugins store secure files in an S3 env-store bucket.
The backend logic lives in `toast/plugins/storage.py`; the plugins themselves
are thin wrappers that call `run_file_sync(kind, filename, command)`.

**Storage structure**:
```
s3://{bucket}/local/{org}/{project}/env-local    # DotPlugin (kind=env-local)
s3://{bucket}/local/{org}/{project}/prompt-md    # PromptPlugin (kind=prompt-md)

/toast/local/{org}/{project}/{kind}              # legacy SSM (read-only fallback)
```

**Transition semantics** (`storage.store_read` / `store_write`):
- Reads check both S3 and SSM and use whichever copy is newest (by
  `LastModified`); ties prefer S3
- Writes always go to S3 (the bucket is the source of truth)
- SSM copies are never written; they go stale and are harvested into S3 on the
  next upload (`up`, or choosing upload in `sync`)

**Configuration** (`storage.resolve_config`) — precedence: environment variable
> config file > built-in default. The config file `~/.config/toast/config`
(`KEY=VALUE`) is created on first run by prompting the user for values
(`prompt_and_create_config`); skipped in non-interactive sessions.

| Env variable | Config key | Default |
|--------------|------------|---------|
| `TOAST_ENV_STORE_PROFILE` | `ENV_STORE_PROFILE` | `{username}-admin` (`default_profile`) |
| `TOAST_ENV_STORE_BUCKET` | `ENV_STORE_BUCKET` | `env-store-{account-id}` of the profile (`default_bucket`, via STS) |
| `TOAST_ENV_STORE_KMS_KEY` | `ENV_STORE_KMS_KEY` | bucket/account default KMS key |
| `TOAST_ENV_STORE_REGION` | `ENV_STORE_REGION` | profile's region (SSM reads fall back to `us-east-1`) |

**Commands**:
| Command | Description |
|---------|-------------|
| (none) | Default: same as `sync` |
| `sync` | Compare local and env-store (newest), then choose action |
| `up` | Upload local file to env-store (S3) |
| `down`/`dn` | Download newest from env-store to local |
| `ls` | List entries across S3 + SSM with current source |

**Sync command features**:
- Compares local file content with the newest env-store copy
- Displays SHA256 hash (first 12 chars) for local, S3, and SSM, plus the
  current (newest) source
- Shows unified diff when contents differ
- Interactive selection via fzf: Upload / Download / Cancel
- Handles cases: identical, different, local_only, remote_only

**Diff on up/down**:
- `up`/`down` also show the masked diff (and a confirm prompt) when local and
  env-store both exist and differ, so you see what changes before overwriting
- Secret masking applies to `.env.local` only (`KEY=VALUE` values become
  `KEY=ab****yz`); `.prompt.md` is regular markdown and shown as-is
- identical/different is decided on the real content; masking is display-only
  (see `mask_secret`/`mask_env_content` in `plugins/utils.py`)

**Common patterns**:
- Validate workspace path: `workspace/github.com/{org}/{project}`
- All AWS calls use the env-store profile via `storage._aws()`
- Write S3 objects with `--server-side-encryption aws:kms`
- Use temporary files for content upload/download
- Include confirmation prompts before overwriting files

### SSM Plugin Secret Handling

The `ssm` plugin masks SecureString values for safe terminal display:
- `put` fetches the current value first; if it exists and differs, a masked diff
  (NEW vs CURRENT) is shown before the overwrite confirm. Identical values are a
  no-op.
- `get` and the interactive preview mask the value by default. Use `--reveal`
  (or the interactive "Copy value" action) to print the full plaintext — these
  are the explicit value-retrieval paths.
- Masking uses `mask_secret`/`mask_lines` from `plugins/utils.py`.

## Project Code Guidelines

**Important: Before writing new code, search for similar existing code and maintain consistent logic and style patterns.**

### Core Principles
- **Solve the right problem**: Avoid unnecessary complexity or scope creep
- **Favor standard solutions**: Use well-known libraries and documented patterns before writing custom code
- **Keep code clean and readable**: Use clear naming, logical structure, and avoid deeply nested logic
- **Handle errors thoughtfully**: Consider edge cases and fail gracefully
- **Design for change**: Structure code to be modular and adaptable to future changes
- **Keep dependencies shallow**: Minimize tight coupling between modules. Maintain clear boundaries
- **Fail fast and visibly**: Surface errors early with meaningful messages or logs
