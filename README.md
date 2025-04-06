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

Python-based CLI utility with plugin architecture for AWS, Kubernetes, and Git operations.

## Features

* **Plugin Architecture**: Modular design with dynamic command discovery
* **AWS Integration**: Identity checking, profile management, region selection, SSM integration
* **Kubernetes**: Context switching, EKS integration
* **Git**: Repository management, branch creation, pull operations
* **Workspace**: Directory navigation, environment file management
* **Interface**: FZF-powered menus, formatted output with Rich

## Architecture

* Commands implemented as plugins extending BasePlugin
* Automatic plugin discovery and loading
* Click integration for CLI behavior
* See [ARCHITECTURE.md](ARCHITECTURE.md) for details

## Installation

### Requirements
* Python 3.6+
* External tools: fzf, aws-cli, kubectl
* Python packages: click, rich

### Install
```bash
# From PyPI
pip install toast-cli

# From GitHub
pip install git+https://github.com/opspresso/toast-cli.git

# Development mode
git clone https://github.com/opspresso/toast-cli.git
cd toast-cli
pip install -e .
```

## Usage

```bash
toast --help         # View available commands
toast am             # Show AWS identity
toast cdw            # Navigate workspace directories
toast ctx            # Manage Kubernetes contexts
toast dot            # Manage .env.local files
toast env            # Manage AWS profiles
toast git            # Manage Git repositories
toast region         # Manage AWS region
toast version        # Display version
```

### Examples

```bash
# AWS
toast am                   # Show identity
toast env                  # Switch profiles
toast region               # Switch regions

# Kubernetes
toast ctx                  # Switch contexts

# Environment Files
toast dot up               # Upload to SSM
toast dot down             # Download from SSM
toast dot ls               # List in SSM

# Git
toast git repo-name clone  # Clone repository
toast git repo-name branch -b branch-name  # Create branch
toast git repo-name pull -r  # Pull with rebase
```

## Creating Plugins

1. Create a file in `toast/plugins/`
2. Extend `BasePlugin`
3. Implement required methods
4. Set name and help variables

```python
from toast.plugins.base_plugin import BasePlugin
import click

class MyPlugin(BasePlugin):
    name = "mycommand"
    help = "Command description"

    @classmethod
    def get_arguments(cls, func):
        func = click.option("--option", "-o", help="Option description")(func)
        return func

    @classmethod
    def execute(cls, **kwargs):
        option = kwargs.get("option")
        click.echo(f"Executing with option: {option}")
```

## Aliases

```bash
alias t='toast'
c() { cd "$(toast cdw)" }
alias m='toast am'      # AWS identity
alias x='toast ctx'     # Kubernetes contexts
alias d='toast dot'     # Environment files
alias e='toast env'     # AWS profiles
alias g='toast git'     # Git repositories
alias r='toast region'  # AWS region
```

## Resources

* **Development**: See [CLAUDE.md](CLAUDE.md) for guidelines
* **License**: [GNU GPL v3.0](LICENSE)
* **Contributing**: Via [GitHub repository](https://github.com/opspresso/toast-cli)
* **Documentation**: [ARCHITECTURE.md](ARCHITECTURE.md) and [toast.sh](https://toast.sh/)
