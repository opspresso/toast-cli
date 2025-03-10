# toast.sh

```
 _                  _         _
| |_ ___   __ _ ___| |_   ___| |__
| __/ _ \ / _' / __| __| / __| '_ \
| || (_) | (_| \__ \ |_ _\__ \ | | |
 \__\___/ \__,_|___/\__(-)___/_| |_|
```

[![build](https://img.shields.io/github/actions/workflow/status/opspresso/toast.sh/push.yml?branch=main&style=for-the-badge&logo=github)](https://github.com/opspresso/toast.sh/actions/workflows/push.yml)
[![release](https://img.shields.io/github/v/release/opspresso/toast.sh?style=for-the-badge&logo=github)](https://github.com/opspresso/toast.sh/releases)

Toast is a Python-based CLI utility with a plugin architecture that simplifies the use of CLI tools for AWS, Kubernetes, Git, and more.

## Key Features

* Plugin-based architecture for easy extensibility
* Dynamic command discovery and loading
* AWS Features
  - AWS Profile Management (`toast env`)
  - AWS Region Management (`toast region`)
  - IAM Identity Checking (`toast am`)
* Kubernetes Features
  - Context Switching (`toast ctx`)
* Workspace Features
  - Directory Navigation (`toast cdw`)
* Other Utilities
  - System Update (`toast update`)
  - AWS SSM Commands (`toast ssm`)

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
* Python-dotenv package
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
pip install git+https://github.com/opspresso/toast.sh.git

# Install in development mode from local clone
git clone https://github.com/opspresso/toast.sh.git
cd toast.sh
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
toast env          # Set environment
toast region       # Set AWS region
toast ssm          # Run AWS SSM commands
toast update       # Update CLI tool
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

# Directory Navigation
c() {
  cd "$(toast cdw)"
}

# Common Command Aliases
alias i='toast am'      # Check AWS IAM info
alias e='toast env'     # Set AWS profile
alias r='toast region'  # Set AWS region
alias x='toast ctx'     # Switch Kubernetes context
```

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).

## Contributing

Bug reports, feature requests, and pull requests are welcome through the GitHub repository.
