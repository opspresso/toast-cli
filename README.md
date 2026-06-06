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
[![website](https://img.shields.io/badge/website-toast--cli-blue?style=for-the-badge&logo=github)](https://cli.toast.sh/)

Python-based CLI utility with plugin architecture for AWS, Kubernetes, and Git operations.

## Features

* **Plugin Architecture**: Modular design with dynamic command discovery
* **AWS Integration**: Identity checking, profile management, region selection, SSM Parameter Store integration
* **Kubernetes**: Context switching, EKS cluster discovery and integration, context deletion
* **Git**: Repository management (clone, branch, pull, push, rm, mirror), organization-specific GitHub hosts
* **Workspace**: Directory navigation, environment file management (.env.local, .prompt.md)
* **Interface**: FZF-powered interactive menus, formatted output with Rich
* **Security**: S3 env-store with SSE-KMS for sensitive files (SSM fallback during transition)

## Architecture

* Commands implemented as plugins extending BasePlugin
* Automatic plugin discovery and loading
* Click integration for CLI behavior
* See [ARCHITECTURE.md](ARCHITECTURE.md) for details

## Installation

### Requirements
* Python 3.9+
* External tools: fzf, aws-cli, kubectl
* Python packages: click, rich

```bash
pyenv install 3.12
pyenv global 3.12.12
pyenv versions
```

### Install

### From PyPI
```bash
pip install toast-cli
```

### Or...
```bash
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
toast ssm            # AWS SSM Parameter Store operations
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
toast dot                  # Compare local and env-store, choose action (default: sync)
toast dot up               # Upload .env.local to env-store (S3)
toast dot down             # Download .env.local from env-store (alias: dn)
toast dot ls               # List all .env.local files in env-store (S3 + SSM)

# Prompt Files (.prompt.md)
toast prompt               # Compare local and env-store, choose action (default: sync)
toast prompt up            # Upload .prompt.md to env-store (S3)
toast prompt down          # Download .prompt.md from env-store (alias: dn)
toast prompt ls            # List all .prompt.md files in env-store (S3 + SSM)

# SSM Parameter Store
toast ssm                  # Interactive mode: browse and select parameters
toast ssm ls               # List all parameters
toast ssm ls /toast/       # List parameters under path
toast ssm get /my/param    # Get parameter value (alias: g)
toast ssm put /my/param 'value'  # Store as SecureString (alias: p)
toast ssm rm /my/param     # Delete parameter (alias: d, delete)

# Git Operations
toast git repo-name clone                    # Clone repository (alias: cl)
toast git repo-name clone -t target-dir      # Clone into a custom directory
toast git repo-name branch -b branch-name    # Create branch (alias: b)
toast git repo-name pull                     # Pull changes (alias: p)
toast git repo-name pull -r                  # Pull with rebase
toast git repo-name push                     # Push to remote (alias: ps)
toast git repo-name push --mirror            # Mirror push for migration
toast git repo-name rm                       # Remove local repository
```

## Workspace Structure

Toast-cli uses a standardized workspace directory structure for organizing projects:

```
~/workspace/{github-host}/{org}/{project}
```

**Examples**:
- `~/workspace/github.com/opspresso/toast-cli`
- `~/workspace/github.enterprise.com/myorg/myproject`

**First-time Setup**:

When you run `toast cdw` for the first time, it will automatically:
1. Create `~/workspace` directory if it doesn't exist
2. Create `~/workspace/github.com` as the default structure
3. Display instructions for creating organization and project directories

You can then create your project directories:
```bash
mkdir -p ~/workspace/github.com/{org}/{project}
```

**Benefits**:
- Consistent project organization across all Git hosts
- Automatic detection of GitHub host per organization
- Seamless integration with other toast-cli commands (git, dot, prompt)

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

### Env-store (S3) Storage Paths

The `dot` and `prompt` plugins store files in the S3 env-store bucket. During
the transition from AWS SSM Parameter Store, reads check both backends and use
whichever copy is newest; writes always go to S3 (the bucket is the source of
truth), and SSM copies become stale and are harvested into S3 on the next
upload.

```
s3://env-store-{account-id}/local/{org}/{project}/env-local   # .env.local files
s3://env-store-{account-id}/local/{org}/{project}/prompt-md   # .prompt.md files

/toast/local/{org}/{project}/env-local     # legacy SSM (read-only fallback)
/toast/local/{org}/{project}/prompt-md     # legacy SSM (read-only fallback)
```

S3 objects are written with SSE-KMS encryption. All env-store access uses a
dedicated AWS profile so it is decoupled from your current default profile.

**Configuration** — precedence: environment variable > config file > default.

Environment variables:

```bash
TOAST_ENV_STORE_PROFILE   # default: {username}-admin
TOAST_ENV_STORE_BUCKET    # default: env-store-{account-id of the profile}
TOAST_ENV_STORE_KMS_KEY   # default: bucket/account default KMS key
TOAST_ENV_STORE_REGION    # default: profile's region
```

The profile defaults to your OS username + `-admin`, and the bucket defaults to
`env-store-` + the AWS account id of that profile (looked up via
`aws sts get-caller-identity`).

Config file `~/.config/toast/config` (`KEY=VALUE` format). On first run, if it
is missing, toast prompts for the values and saves them (interactive sessions
only):

```
ENV_STORE_BUCKET=env-store-{account-id}
ENV_STORE_PROFILE={username}-admin
ENV_STORE_KMS_KEY=
ENV_STORE_REGION=
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
c() { cd "$(toast cdw)" }    # Navigate to workspace
alias m='toast am'           # AWS identity
alias x='toast ctx'          # Kubernetes contexts
alias d='toast dot'          # .env.local files
alias p='toast prompt'       # .prompt.md files
alias e='toast env'          # AWS profiles
alias g='toast git'          # Git repositories
alias r='toast region'       # AWS region
alias s='toast ssm'          # SSM Parameter Store
```

## Resources

* **Development**: See [CLAUDE.md](CLAUDE.md) for guidelines
* **License**: [GNU GPL v3.0](LICENSE)
* **Contributing**: Via [GitHub repository](https://github.com/opspresso/toast-cli)
* **Documentation**: [ARCHITECTURE.md](ARCHITECTURE.md) and [toast.sh](https://cli.toast.sh/)
