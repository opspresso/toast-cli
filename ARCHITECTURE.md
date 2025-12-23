# Toast-cli Architecture

[![Website](https://img.shields.io/badge/Website-Visit-blue)](https://toast.sh/)
[![PyPI](https://img.shields.io/pypi/v/toast-cli)](https://pypi.org/project/toast-cli/)
[![Version](https://img.shields.io/badge/Version-v3.6.0.dev0-orange)](https://github.com/opspresso/toast-cli/releases)

## Overview

Toast-cli is a Python-based CLI tool for AWS, Kubernetes, and Git operations. It uses a plugin-based architecture for extensibility, allowing new commands to be added without modifying existing code.

## Package Structure

```
toast-cli/
  ├── setup.py            # Package setup script
  ├── setup.cfg           # Package configuration
  ├── pyproject.toml      # Build system requirements
  ├── MANIFEST.in         # Additional files to include
  ├── VERSION             # Version information
  ├── README.md           # Project documentation
  ├── ARCHITECTURE.md     # Architecture documentation
  ├── CLAUDE.md           # Development guidelines and plugin documentation
  ├── LICENSE             # License information (GNU GPL v3.0)
  ├── docs/               # Documentation website files
  └── toast/              # Main package
      ├── __init__.py     # Package initialization and CLI entry point
      ├── __main__.py     # Entry point for running as a module
      ├── helpers.py      # Helper functions and UI elements
      └── plugins/        # Plugin modules
          ├── __init__.py
          ├── base_plugin.py
          ├── am_plugin.py
          ├── cdw_plugin.py
          ├── ctx_plugin.py
          ├── dot_plugin.py
          ├── env_plugin.py
          ├── git_plugin.py
          ├── prompt_plugin.py
          ├── region_plugin.py
          └── utils.py
```

## Components

### Main Application Components

#### Main Entry Point (toast/__init__.py)
- Dynamically discovers and loads plugins
- Registers plugin commands with Click
- Runs the CLI with all discovered commands
- Provides core commands like `version`

#### Module Entry Point (toast/__main__.py)
- Enables running as a module with `python -m toast`

#### Helper Utilities (toast/helpers.py)
- Contains helper functions and UI elements
- Handles version information retrieval
- Provides custom Click classes for enhanced help display

### Plugin System

The plugin system uses Python's `importlib` and `pkgutil` modules for dynamic loading at runtime.

#### Core Plugin Components

1. **BasePlugin (`plugins/base_plugin.py`)**
   - Abstract base class for all plugins
   - Defines interface with required methods:
     - `register()`: Registers with the CLI
     - `get_arguments()`: Defines command arguments
     - `execute()`: Contains command implementation

2. **Utilities (`plugins/utils.py`)**
   - Common utility functions for plugins
   - Interactive selection using fzf
   - Subprocess execution and error handling

### Plugin Structure

Each plugin:
- Inherits from `BasePlugin`
- Defines unique `name` and `help` text
- Implements `execute()` method
- Optionally overrides `get_arguments()`

### Plugin Loading Process

1. Scan plugins directory for Python modules
2. Import each module
3. Find classes extending `BasePlugin`
4. Register valid plugins with the CLI
5. Handle command execution via Click

## Commands

| Command | Description |
|--------|-------------|
| version | Display the current version |
| am | Show AWS caller identity |
| cdw | Navigate to workspace directories |
| ctx | Manage Kubernetes contexts (switch, add EKS clusters, delete) |
| dot | Manage .env.local files with AWS SSM integration |
| env | Manage AWS profiles |
| git | Manage Git repositories (clone, branch, pull, push, mirror) |
| prompt | Manage .prompt.md files with AWS SSM integration |
| region | Set AWS region |

### Plugin Functionality

#### AmPlugin (am)
- Shows current AWS identity using `aws sts get-caller-identity`
- Formats JSON output with `rich`

#### CdwPlugin (cdw)
- Searches directories in `~/workspace`
- Uses fzf for interactive selection
- Outputs selected path for shell navigation

#### CtxPlugin (ctx)
- Manages Kubernetes contexts
- Integrates with EKS for cluster discovery and automatic kubeconfig update
- Handles context switching and deletion (individual or all contexts)
- Interactive selection of contexts and clusters

#### DotPlugin (dot)
- Manages .env.local files with AWS SSM Parameter Store
- Commands: `ls` (list), `up` (upload), `down`/`dn` (download), `sync` (compare and choose)
- Uploads/downloads environment variables as SecureString
- SSM path: `/toast/local/{org}/{project}/env-local`
- Validates workspace path structure (`workspace/github.com/{org}/{project}`)
- Sync command: compares local/remote content, shows diff, offers upload/download choice

#### PromptPlugin (prompt)
- Manages .prompt.md files with AWS SSM Parameter Store
- Commands: `ls` (list), `up` (upload), `down`/`dn` (download), `sync` (compare and choose)
- Uploads/downloads prompt files as SecureString
- SSM path: `/toast/local/{org}/{project}/prompt-md`
- Validates workspace path structure (`workspace/github.com/{org}/{project}`)
- Sync command: compares local/remote content, shows diff, offers upload/download choice

#### EnvPlugin (env)
- Manages AWS profiles from `~/.aws/credentials`
- Interactive selection of profiles
- Sets selected profile as default by updating credentials file
- Handles session tokens when present
- Verifies identity after switching using `aws sts get-caller-identity`

#### RegionPlugin (region)
- Displays current AWS region
- Lists available AWS regions using `aws ec2 describe-regions`
- Interactive selection using fzf
- Updates AWS CLI configuration with selected region

#### GitPlugin (git)
- Handles Git repository operations
- Supports cloning, branch creation, pulling, pushing
- Repository name sanitization (removes invalid characters)
- Mirror push for repository migration
- Organization-specific GitHub host configuration via `.toast-config`
- Validates repository paths and workspace structure

## Configuration

### GitHub Host Configuration

Toast-cli supports organization-specific GitHub host configuration through `.toast-config` files:

**File Location**: `~/workspace/github.com/{org}/.toast-config`

**Format**:
```
GITHUB_HOST=custom-host.com
```

**Search Priority**:
1. Organization directory: `~/workspace/github.com/{org}/.toast-config`
2. Current directory: `.toast-config`
3. Default: `github.com`

This enables:
- Different GitHub Enterprise hosts per organization
- Different SSH configurations and keys per organization
- Seamless switching between GitHub accounts

## Dependencies

- Click: Command-line interface creation
- importlib/pkgutil: Dynamic module discovery
- External tools:
  - fzf: Interactive selection
  - aws-cli: AWS operations
  - kubectl: Kubernetes operations
- Python packages:
  - rich: Terminal formatting

## Adding New Plugins

1. Create a Python file in `toast/plugins/`
2. Define a class extending `BasePlugin`
3. Implement `execute()` method
4. Set `name` and `help` class variables

The plugin will be automatically discovered and loaded.

## Benefits of Plugin Architecture

- Modularity: Isolated command implementations
- Extensibility: Add commands without modifying core code
- Maintainability: Organized, logical components
- Consistency: Common patterns through base class

## Installation

```bash
# Install from PyPI
pip install toast-cli

# Install in development mode
pip install -e .

# Install from GitHub
pip install git+https://github.com/opspresso/toast-cli.git
```

The package is available on PyPI at https://pypi.org/project/toast-cli/

### Building Distribution Packages

To build distribution packages:

```bash
# Install build requirements
pip install build

# Build source and wheel distributions
python -m build

# This will create:
# - dist/toast-cli-X.Y.Z.tar.gz (source distribution)
# - dist/toast_cli-X.Y.Z-py3-none-any.whl (wheel distribution)
```

### Publishing to PyPI

To publish the package to PyPI:

```bash
# Install twine
pip install twine

# Upload to PyPI
twine upload dist/*
```
