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

Toast is a Python-based CLI utility with a plugin architecture that simplifies the use of CLI tools for AWS, Kubernetes, Git, and more.

## Key Features

* Plugin-based architecture for easy extensibility
* Dynamic command discovery and loading
* AWS Features
  - IAM Identity Checking (`toast am`)
  - AWS Profile Management (`toast env`)
  - AWS Region Management (`toast region`)
* Workspace Features
  - Directory Navigation (`toast cdw`)
* Environment Management
  - .env.local file management with AWS SSM integration (`toast dot`)
* Kubernetes Features
  - Context Switching (`toast ctx`)
* Git Features
  - Git Repository Management (`toast git`)

## Plugin Architecture

Toast uses a plugin-based architecture powered by Python's importlib and pkgutil modules:

* Each command is implemented as a separate plugin
* Plugins are automatically discovered and loaded at runtime
* New functionality can be added without modifying existing code

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed information about the design.

## Installation

### Requirements

* Python 3.6+
* Click package
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
pip install toast-cli==3.0.0

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
toast dot          # Manage .env.local files
toast env          # Manage AWS profiles
toast git          # Manage Git repositories
toast region       # Manage AWS region
```

## Extending with Plugins

To add a new plugin:

1. Create a new Python file in the `plugins` directory
2. Define a class that extends `BasePlugin`
3. Implement the required methods (execute and optionally get_arguments)
4. Set the name and help class variables

Example plugin:

```python
from plugins.base_plugin import BasePlugin
import click

class MyPlugin(BasePlugin):
    name = "mycommand"
    help = "Description of my command"

    @classmethod
    def execute(cls, **kwargs):
        click.echo("My custom command execution")
```

## Aliases

```bash
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

Bug reports, feature requests, and pull requests are welcome through the GitHub repository.
