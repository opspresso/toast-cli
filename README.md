# toast-cli

```
 _                  _           _ _
| |_ ___   __ _ ___| |_     ___| (_)
| __/ _ \ / _` / __| __|__ / __| | |
| || (_) | (_| \__ \ ||___| (__| | |
 \__\___/ \__,_|___/\__|   \___|_|_|
```

[![build](https://img.shields.io/github/actions/workflow/status/opspresso/toast-cli/push.yml?branch=main&style=for-the-badge&logo=github)](https://github.com/opspresso/toast-cli/actions/workflows/push.yml)
[![release](https://img.shields.io/github/v/release/opspresso/toast-cli?style=for-the-badge&logo=github)](https://github.com/opspresso/toast-cli/releases)
[![PyPI](https://img.shields.io/pypi/v/toast-cli?style=for-the-badge&logo=pypi&logoColor=white)](https://pypi.org/project/toast-cli/)
[![website](https://img.shields.io/badge/website-toast--cli-blue?style=for-the-badge&logo=github)](https://toast.sh/)

Toast is a Python-based CLI utility with a plugin architecture that simplifies the use of CLI tools for AWS, Kubernetes, Git, and more. It provides a unified interface for common DevOps tasks and enhances productivity through interactive selection and streamlined workflows.

## Key Features

* **Plugin-based Architecture**
  - Modular design for easy extensibility
  - Dynamic command discovery and loading
  - Simple plugin development model

* **AWS Integration**
  - IAM Identity Checking (`toast am`)
  - AWS Profile Management (`toast env`)
  - AWS Region Selection (`toast region`)
  - AWS SSM Parameter Store Integration (`toast dot`)

* **Kubernetes Management**
  - Context Switching (`toast ctx`)
  - EKS Cluster Integration

* **Git Workflow**
  - Repository Cloning and Management
  - Branch Creation
  - Pull Operations with Rebase Support

* **Workspace Organization**
  - Directory Navigation (`toast cdw`)
  - Environment File Management (`toast dot`)

* **Interactive Interface**
  - FZF-powered selection menus
  - Formatted JSON output with JQ

## Plugin Architecture

Toast uses a plugin-based architecture powered by Python's importlib and pkgutil modules:

* Each command is implemented as a separate plugin that extends the BasePlugin class
* Plugins are automatically discovered and loaded at runtime
* Commands are registered with Click for consistent CLI behavior
* New functionality can be added without modifying existing code

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed information about the design and implementation.

## Installation

### Requirements

* Python 3.6+
* Click package for CLI interface
* External tools used by various plugins:
  - fzf: Interactive selection in terminal
  - jq: JSON processing for formatted output
  - aws-cli: AWS command line interface
  - kubectl: Kubernetes command line tool

### Installation Methods

```bash
# Install from PyPI
pip install toast-cli

# Update to latest version
pip install --upgrade toast-cli

# Install specific version
pip install toast-cli==3.2.0

# Install development version from GitHub
pip install git+https://github.com/opspresso/toast-cli.git

# Install in development mode from local clone
git clone https://github.com/opspresso/toast-cli.git
cd toast-cli
pip install -e .
```

### Creating Symbolic Link (Optional)

If toast command is not available in your PATH after installation:

```bash
# Create a symbolic link to make it available system-wide
sudo ln -sf $(which toast) /usr/local/bin/toast
```

## Usage

```bash
# View available commands
toast --help

# Run a specific command
toast am           # Show AWS identity
toast cdw          # Navigate workspace directories
toast ctx          # Manage Kubernetes contexts
toast dot          # Manage .env.local files with AWS SSM integration
toast env          # Manage AWS profiles
toast git          # Manage Git repositories
toast region       # Manage AWS region
toast version      # Display the current version
```

### Command Examples

```bash
# AWS Identity Management
toast am                   # Show current AWS identity

# Workspace Navigation
toast cdw                  # Interactive selection of workspace directories

# Kubernetes Context Management
toast ctx                  # Switch between Kubernetes contexts
                          # Select [New...] to add EKS clusters
                          # Select [Del...] to remove contexts

# Environment File Management
toast dot                  # Show .env.local status
toast dot up               # Upload .env.local to AWS SSM Parameter Store
toast dot down             # Download .env.local from AWS SSM Parameter Store
toast dot ls               # List all .env.local files in AWS SSM

# AWS Profile Management
toast env                  # Switch between AWS profiles

# Git Repository Management
toast git repo-name clone  # Clone a repository
toast git repo-name rm     # Remove a repository
toast git repo-name branch -b branch-name  # Create a new branch
toast git repo-name pull   # Pull latest changes
toast git repo-name pull -r  # Pull with rebase

# AWS Region Management
toast region               # Switch between AWS regions
```

## Extending with Plugins

To add a new plugin:

1. Create a new Python file in the `toast/plugins` directory
2. Define a class that extends `BasePlugin`
3. Implement the required methods (execute and optionally get_arguments)
4. Set the name and help class variables

Example plugin:

```python
from toast.plugins.base_plugin import BasePlugin
import click

class MyPlugin(BasePlugin):
    name = "mycommand"
    help = "Description of my command"

    @classmethod
    def get_arguments(cls, func):
        # Optional: Define command arguments
        func = click.option("--option", "-o", help="An option for my command")(func)
        return func

    @classmethod
    def execute(cls, **kwargs):
        # Command implementation
        option = kwargs.get("option")
        if option:
            click.echo(f"Executing with option: {option}")
        else:
            click.echo("My custom command execution")
```

The plugin will be automatically discovered and loaded when toast is run.

## Recommended Aliases

Add these to your shell configuration file (e.g., .bashrc, .zshrc):

```bash
# Main alias
alias t='toast'

# Navigate workspace directories
c() {
  cd "$(toast cdw)"
}

# Common Command Aliases
alias m='toast am'      # Show AWS identity
alias x='toast ctx'     # Manage Kubernetes contexts
alias d='toast dot'     # Manage .env.local files
alias e='toast env'     # Manage AWS profiles
alias g='toast git'     # Manage Git repositories
alias r='toast region'  # Manage AWS region
```

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).

## Contributing

Bug reports, feature requests, and pull requests are welcome through the [GitHub repository](https://github.com/opspresso/toast-cli).

## Documentation

For more detailed information about the architecture and implementation, see [ARCHITECTURE.md](ARCHITECTURE.md).

Visit the project website at [toast.sh](https://toast.sh/) for additional resources.
