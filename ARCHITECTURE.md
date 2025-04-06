# Toast-cli Architecture

[![Website](https://img.shields.io/badge/Website-Visit-blue)](https://toast.sh/)
[![PyPI](https://img.shields.io/pypi/v/toast-cli)](https://pypi.org/project/toast-cli/)
[![Version](https://img.shields.io/badge/Version-v3.2.0.dev0-orange)](https://github.com/opspresso/toast-cli/releases)

## Overview

Toast-cli is a Python-based CLI tool that provides various utility commands for AWS, Kubernetes, and Git operations. The architecture follows a plugin-based design pattern, allowing for easy extension of functionality through the addition of new plugins. This modular approach enables developers to add new commands without modifying existing code, promoting maintainability and extensibility.

## Package Structure

The project is organized as a Python package with the following structure:

```
toast-cli/
  ├── setup.py            # Package setup script
  ├── setup.cfg           # Package configuration
  ├── pyproject.toml      # Build system requirements
  ├── MANIFEST.in         # Additional files to include in the package
  ├── VERSION             # Version information
  ├── README.md           # Project documentation
  ├── ARCHITECTURE.md     # Architecture documentation
  ├── LICENSE             # License information
  ├── docs/               # Documentation website files
  │   ├── CNAME           # Custom domain configuration
  │   ├── favicon.ico     # Website favicon
  │   ├── index.html      # Main documentation page
  │   ├── css/            # Stylesheet files
  │   ├── images/         # Documentation images
  │   └── js/             # JavaScript files
  └── toast/              # Main package
      ├── __init__.py     # Package initialization and CLI entry point
      ├── __main__.py     # Entry point for running as a module
      ├── helpers.py      # Helper functions and custom UI elements
      └── plugins/        # Plugin modules
          ├── __init__.py
          ├── base_plugin.py
          ├── am_plugin.py
          ├── cdw_plugin.py
          ├── ctx_plugin.py
          ├── dot_plugin.py
          ├── env_plugin.py
          ├── git_plugin.py
          ├── region_plugin.py
          └── utils.py
```

## Components

### Main Application Components

#### Main Entry Point (toast/__init__.py)

The main entry point of the application is responsible for:
- Dynamically discovering and loading plugins from the `toast.plugins` package
- Registering plugin commands with the CLI interface using Click
- Running the CLI with all discovered commands
- Providing core commands like `version` to display the current version

Key functions:
- `discover_and_load_plugins()`: Scans the plugins directory and loads all valid plugin classes
- `toast_cli()`: The main Click group that serves as the entry point for all commands
- `main()`: Initializes the application, loads plugins, and runs the CLI

#### Module Entry Point (toast/__main__.py)

Enables the application to be run as a module with `python -m toast`, providing an alternative way to execute the tool.

#### Helper Utilities (toast/helpers.py)

- Contains helper functions and custom UI elements
- `display_logo()`: Renders the ASCII logo with version information
- `get_version()`: Retrieves version information from VERSION file with multiple fallback methods
- `CustomHelpCommand` & `CustomHelpGroup`: Custom Click classes for enhanced help display with the ASCII logo

### Plugin System

The plugin system is based on Python's `importlib` and `pkgutil` modules, which enable dynamic loading of modules at runtime. This allows the application to be extended without modifying the core code.

#### Core Plugin Components

1. **BasePlugin (`plugins/base_plugin.py`)**
   - Abstract base class that all plugins must extend
   - Defines the interface for plugins with required methods:
     - `register()`: Registers the plugin with the CLI
     - `get_arguments()`: Defines command arguments (optional to override)
     - `execute()`: Contains the command implementation (must be overridden)
   - Provides registration mechanism for adding commands to the CLI

2. **Utilities (`plugins/utils.py`)**
   - Common utility functions used by multiple plugins
   - `select_from_list()`: Interactive selection using fzf for better user experience
   - Handles subprocess execution and error handling

### Plugin Structure

Each plugin follows a standard structure:
- Inherits from `BasePlugin`
- Defines a unique `name` and `help` text as class variables
- Implements `execute()` method containing the command logic
- Optionally overrides `get_arguments()` to define custom command arguments using Click decorators

Example plugin structure:
```python
class ExamplePlugin(BasePlugin):
    name = "example"
    help = "Example command description"

    @classmethod
    def get_arguments(cls, func):
        func = click.option("--option", "-o", help="Option description")(func)
        return func

    @classmethod
    def execute(cls, **kwargs):
        # Command implementation
        click.echo("Executing example command")
```

### Plugin Loading Process

1. The application scans the `plugins` directory for Python modules using pkgutil.iter_modules
2. Each module is imported using importlib.import_module
3. The module is examined for classes that extend `BasePlugin` using inspect.getmembers
4. Valid plugin classes are collected and registered with the CLI using their register() method
5. Click handles argument parsing and command execution when the command is invoked

## Core Commands

| Command | Description |
|--------|-------------|
| version | Display the current version of toast-cli |

## Current Plugins

| Plugin | Command | Description |
|--------|---------|-------------|
| AmPlugin | am | Show AWS caller identity |
| CdwPlugin | cdw | Navigate to workspace directories |
| CtxPlugin | ctx | Manage Kubernetes contexts |
| DotPlugin | dot | Manage .env.local files with AWS SSM integration |
| EnvPlugin | env | Manage AWS profiles |
| GitPlugin | git | Manage Git repositories |
| RegionPlugin | region | Set AWS region |

### Plugin Details

#### AmPlugin (am command)

The `am` command shows the current AWS identity:

1. **Identity Retrieval**:
   - Executes `aws sts get-caller-identity` to get the current AWS identity
   - Uses `rich` to format the JSON output for better readability
   - Displays the account ID, user ARN, and user ID

2. **Error Handling**:
   - Captures and displays errors from the AWS CLI
   - Provides clear feedback when identity retrieval fails

#### CdwPlugin (cdw command)

The `cdw` command helps navigate workspace directories:

1. **Directory Discovery**:
   - Searches for directories in the `~/workspace` path
   - Creates the workspace directory if it doesn't exist
   - Finds directories up to 2 levels deep

2. **Directory Selection**:
   - Uses interactive fzf selection for better user experience
   - Outputs the selected directory path for use with shell functions
   - Enables quick navigation to project directories

#### CtxPlugin (ctx command)

The `ctx` command manages Kubernetes contexts:

1. **Context Discovery**:
   - Retrieves available Kubernetes contexts from kubectl configuration
   - Presents sorted list of contexts for selection
   - Adds special options for creating new contexts or deleting existing ones

2. **EKS Integration**:
   - When creating a new context, lists available EKS clusters from the current AWS region
   - Uses `aws eks update-kubeconfig` to add selected cluster to kubectl configuration
   - Automatically sets cluster alias to match cluster name

3. **Context Management**:
   - Switches between contexts using `kubectl config use-context`
   - Provides options to delete individual contexts or all contexts
   - Displays clear feedback after each operation

#### DotPlugin (dot command)

The `dot` command manages .env.local files with AWS SSM integration:

1. **Environment File Management**:
   - Detects .env.local files in the current directory
   - Extracts organization and project information from the workspace path
   - Creates standardized SSM parameter paths based on project structure

2. **AWS SSM Integration**:
   - Uploads .env.local files to AWS SSM Parameter Store as SecureString
   - Downloads environment files from SSM to local .env.local
   - Lists all environment files stored in SSM under the /toast/local/ path
   - Handles secure storage and retrieval of sensitive environment variables

3. **Path Validation**:
   - Validates that the current directory follows the expected workspace structure
   - Extracts organization and project name from the path for SSM parameter naming
   - Ensures consistent parameter paths across projects

#### EnvPlugin (env command)

The `env` command manages AWS profiles:

1. **Profile Discovery**:
   - Reads profiles from the `~/.aws/credentials` file
   - Shows list of available AWS profiles for selection

2. **Profile Selection**:
   - Uses interactive fzf selection for better user experience
   - Allows users to select from all configured AWS profiles

3. **Default Profile Management**:
   - Sets the selected profile as the default AWS profile
   - Preserves authentication information including access key, secret key, and session token
   - Simplifies working with multiple AWS accounts

4. **Identity Verification**:
   - After switching profiles, verifies the new identity using `aws sts get-caller-identity`
   - Displays the new identity information in formatted JSON using `rich`

#### RegionPlugin (region command)

The `region` command manages AWS regions:

1. **Current Region Display**:
   - Shows the currently configured AWS region before selection
   - Provides clear feedback on the active region

2. **Region Discovery**:
   - Fetches available AWS regions using the AWS CLI
   - Presents a sorted list of all available regions

3. **Region Selection**:
   - Uses interactive fzf selection for better user experience
   - Allows users to select from all available AWS regions

4. **Region Configuration**:
   - Sets the selected region as the default AWS region
   - Updates AWS CLI configuration with the selected region
   - Sets JSON as the default output format

#### GitPlugin (git command)

The `git` command handles Git repository operations:

1. **Repository Path Validation**:
   - Validates that the current directory is in the ~/workspace/github.com/{username} format
   - Extracts username from the current path for repository operations

2. **Repository Cloning**:
   - Clones repositories from the user's GitHub account using the username extracted from path
   - Supports cloning to a specified target directory name (optional)
   - Format: `toast git repo_name clone` (default) or `toast git repo_name clone --target target_name` (specify target directory)
   - Shorthand: `toast git repo_name cl -t target_name`

3. **Repository Removal**:
   - Safely removes repository directories with confirmation prompt
   - Format: `toast git repo_name rm`

4. **Branch Creation**:
   - Creates a new git branch in the specified repository
   - Automatically changes to the new branch using git checkout -b
   - Format: `toast git repo_name branch --branch branch_name` (default) or `toast git repo_name b -b branch_name` (shortened command)

5. **Pull Repository Changes**:
   - Pulls the latest changes from the remote repository
   - Synchronizes the local repository with updates from the remote
   - Supports rebase option with `--rebase` or `-r` flag
   - Format: `toast git repo_name pull` (default) or `toast git repo_name p` (shortened command)
   - With rebase: `toast git repo_name pull --rebase` or `toast git repo_name p -r`

6. **Path Management**:
   - Automatically constructs GitHub repository URLs based on extracted username
   - Manages repository paths within the workspace directory structure

## Dependencies

The plugin system has the following external dependencies:
- Click: Command-line interface creation
- pkg_resources: Resource access within Python packages (included in setuptools)
- importlib/pkgutil: Dynamic module discovery and loading
- subprocess: Execution of external commands
- External tools used by various plugins:
  - fzf: Interactive selection in terminal
  - aws-cli: AWS command line interface
  - kubectl: Kubernetes command line tool
- Python packages:
  - rich: Terminal formatting and JSON output

## Adding New Plugins

To add a new plugin:
1. Create a new Python file in the `toast/plugins` directory
2. Define a class that extends `BasePlugin`
3. Implement the required methods (`execute` and optionally `get_arguments`)
4. Set the `name` and `help` class variables

The plugin will be automatically discovered and loaded when the application starts.

Example of a minimal plugin:

```python
from toast.plugins.base_plugin import BasePlugin
import click

class NewPlugin(BasePlugin):
    name = "newcommand"
    help = "Description of the new command"

    @classmethod
    def execute(cls, **kwargs):
        click.echo("Executing new command")
```

Example of a plugin with arguments:

```python
from toast.plugins.base_plugin import BasePlugin
import click

class AdvancedPlugin(BasePlugin):
    name = "advanced"
    help = "Advanced command with arguments"

    @classmethod
    def get_arguments(cls, func):
        func = click.argument("subcommand", required=True)(func)
        func = click.option("--flag", "-f", is_flag=True, help="Boolean flag")(func)
        func = click.option("--value", "-v", help="Value parameter")(func)
        return func

    @classmethod
    def execute(cls, subcommand, flag=False, value=None, **kwargs):
        click.echo(f"Executing {subcommand} with flag={flag}, value={value}")
```

## Benefits of the Plugin Architecture

- **Modularity**: Each command is isolated in its own module
- **Extensibility**: New commands can be added without modifying existing code
- **Maintainability**: Code is organized into logical components
- **Testability**: Plugins can be tested independently
- **Consistency**: Common patterns are enforced through the base class
- **Discoverability**: Commands are automatically found and registered

## Packaging and Distribution

The project is packaged using standard Python packaging tools. The following files enable packaging and distribution:

1. **setup.py**: The main setup script that defines package metadata and dependencies
   - Author: nalbam <byforce@gmail.com>
   - Description: A Python-based CLI utility with a plugin architecture for AWS, Kubernetes, Git, and more
   - Main package requirements: click
   - Entry point: toast=toast:main

2. **setup.cfg**: Configuration file for package metadata and entry points
   - License: GNU General Public License v3.0
   - Python compatibility: 3.6+
   - Classifiers for package categorization

3. **pyproject.toml**: Defines build system requirements
   - Using setuptools (>=42) and wheel

4. **MANIFEST.in**: Specifies additional files to include in the source distribution
   - Includes: README.md, LICENSE, VERSION, ARCHITECTURE.md, CNAME, favicon.ico, .mergify.yml
   - Ensures documentation and configuration files are included in the package

### Installation Methods

The package can be installed using pip:

```bash
# Install from PyPI
pip install toast-cli

# Install from local directory in development mode
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

## Future Development

Potential areas for enhancement:

1. **Testing Framework**: Adding unit tests for core functionality and plugins
2. **Configuration System**: Supporting user-defined configuration files
3. **Plugin Discovery**: Extending plugin discovery to support user-installed plugins
4. **Documentation**: Expanding documentation with examples and tutorials
5. **Additional Plugins**: Developing more plugins for common DevOps tasks
