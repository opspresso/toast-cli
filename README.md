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
* **AWS Integration**: Identity checking, profile management, region selection, SSM Parameter Store integration
* **Kubernetes**: Context switching, EKS cluster discovery and integration, context deletion
* **Git**: Repository management (clone, branch, pull, push, mirror), organization-specific GitHub hosts
* **Workspace**: Directory navigation, environment file management (.env.local, .prompt.md)
* **Interface**: FZF-powered interactive menus, formatted output with Rich
* **Security**: AWS SSM SecureString storage for sensitive files

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
toast prompt         # Manage .prompt.md files
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
# Select [New...] to add EKS clusters from current region
# Select [Del...] to delete contexts (individual or all)

# Environment Files (.env.local)
toast dot                  # Check current directory for .env.local
toast dot up               # Upload .env.local to SSM
toast dot down             # Download .env.local from SSM (alias: dn)
toast dot sync             # Compare local and SSM, choose action
toast dot ls               # List all .env.local files in SSM

# Prompt Files (.prompt.md)
toast prompt               # Check current directory for .prompt.md
toast prompt up            # Upload .prompt.md to SSM
toast prompt down          # Download .prompt.md from SSM (alias: dn)
toast prompt sync          # Compare local and SSM, choose action
toast prompt ls            # List all .prompt.md files in SSM

# Git Operations
toast git repo-name clone                    # Clone repository
toast git repo-name branch -b branch-name    # Create branch
toast git repo-name pull                     # Pull changes
toast git repo-name pull -r                  # Pull with rebase
toast git repo-name push                     # Push to remote
toast git repo-name push -f                  # Force push
toast git repo-name push --mirror            # Mirror push for migration
```

## Configuration

### GitHub Host Configuration

Configure custom GitHub hosts for different organizations by creating `.toast-config` files:

**File location**: `~/workspace/github.com/{org}/.toast-config`

```bash
# For organization-specific hosts
echo "GITHUB_HOST=github.enterprise.com" > ~/workspace/github.com/myorg/.toast-config

# For custom SSH hosts (useful for different accounts)
echo "GITHUB_HOST=myorg-github.com" > ~/workspace/github.com/myorg/.toast-config
```

**Example SSH config** (`~/.ssh/config`):
```
Host myorg-github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_rsa_myorg
```

**Benefits**:
- Different GitHub Enterprise hosts per organization
- Different SSH keys and accounts per organization
- Automatic host detection based on workspace location
- Seamless switching between GitHub accounts

### AWS SSM Storage Paths

Toast-cli stores files in AWS SSM Parameter Store with the following structure:

```
/toast/local/{org}/{project}/env-local     # .env.local files
/toast/local/{org}/{project}/prompt-md     # .prompt.md files
```

Files are stored as SecureString type for encryption at rest.

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
c() { cd "$(toast cdw)" }    # Navigate to workspace
alias m='toast am'           # AWS identity
alias x='toast ctx'          # Kubernetes contexts
alias d='toast dot'          # .env.local files
alias p='toast prompt'       # .prompt.md files
alias e='toast env'          # AWS profiles
alias g='toast git'          # Git repositories
alias r='toast region'       # AWS region
```

## Resources

* **Development**: See [CLAUDE.md](CLAUDE.md) for guidelines
* **License**: [GNU GPL v3.0](LICENSE)
* **Contributing**: Via [GitHub repository](https://github.com/opspresso/toast-cli)
* **Documentation**: [ARCHITECTURE.md](ARCHITECTURE.md) and [toast.sh](https://toast.sh/)
