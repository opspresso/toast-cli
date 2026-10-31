# toast-cli

```
 _                  _           _ _
| |_ ___   __ _ ___| |_     ___| (_)
| __/ _ \ / _` / __| __|__ / __| | |
| || (_) | (_| \__ \ ||___| (__| | |
 \__\___/ \__,_|___/\__|   \___|_|_|

```

[![build](https://img.shields.io/github/actions/workflow/status/opspresso/toast-cli/release.yml?style=for-the-badge&logo=github)](https://github.com/opspresso/toast-cli/actions/workflows/release.yml)
[![release](https://img.shields.io/github/v/release/opspresso/toast-cli?style=for-the-badge&logo=github)](https://github.com/opspresso/toast-cli/releases)
[![PyPI](https://img.shields.io/pypi/v/toast-cli?style=for-the-badge&logo=pypi&logoColor=white)](https://pypi.org/project/toast-cli/)
[![website](https://img.shields.io/badge/website-toast--cli-blue?style=for-the-badge&logo=github)](https://cli.toast.sh/)

Python-based CLI utility with plugin architecture for AWS, Kubernetes, and Git operations.

## Features

* **Plugin Architecture**: Modular design with dynamic command discovery
* **AWS Integration**: Identity checking, profile management, region selection, SSM Parameter Store integration
* **Kubernetes**: Context switching, EKS cluster discovery and integration, context deletion
* **Git**: Repository management (clone, branch, pull, push, rm, mirror), GitHub and GitLab clone URLs and nested groups
* **Workspace**: Directory navigation, environment file management (.env.local, .prompt.md)
* **Interface**: One look across all commands: filtering pickers, colored help, and clean stdout for scripts
* **Security**: S3 env-store with SSE-KMS for sensitive files (SSM fallback during transition); secret values masked in diffs and SSM previews

## Architecture

* Commands implemented as plugins extending BasePlugin
* Automatic plugin discovery and loading
* Click integration for CLI behavior
* See [ARCHITECTURE.md](ARCHITECTURE.md) for details

## Installation

### Requirements
* Python 3.9+
* External tools: git, aws-cli, kubectl (install those required by your commands)
* Python packages: click, rich

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
toast clean          # Show reclaimable disk data and remove selected items
toast completion     # Print the shell completion script
toast ssm            # AWS SSM Parameter Store operations
toast version        # Display version
```

### Disk cleanup

`toast clean` measures removable data and opens a picker, largest item first. The
footer shows the selected size and the free space after removal.

```text
Reclaimable 84.1 GiB
  ◉   6.2 GiB  download  arduino-packages     Arduino board toolchains
❯ ○   2.6 GiB  cache     go-cache             Go build cache
  ○   2.3 GiB  cache     vscode-cache         blocked: VS Code running · VS Code logs

Selected 1 · 6.2 GiB · Free now 166.3 GiB · after 172.5 GiB
↑↓ move · space select · a all except data · n clear · enter confirm · q quit
```

| Key | Action |
| --- | --- |
| `↑` `↓` or `j` `k` | Move. Blocked rows are skipped. |
| `Space` | Select or clear the row, then move down. |
| `a` | Select everything except `data` items. Press again to clear. |
| `n` | Clear the selection. |
| `Enter` | Review the selection and confirm it. |
| `q` or `Esc` | Quit without removing anything. |

| Command | Action |
| --- | --- |
| `toast clean` | Open the picker. Without a terminal, ask for numbers or names. |
| `toast clean --list` | Show the items and exit. |
| `toast clean --json` | Print the items as JSON and exit. |
| `toast clean NAME...` | Remove the named items after a confirmation. |
| `toast clean NAME... --yes` | Remove the named items without a confirmation. |

| RISK | Meaning |
| --- | --- |
| `cache` | Rebuilt on demand. |
| `download` | Fetched again, so the first use is slow. |
| `data` | Cannot be restored: iOS simulator data, Android virtual devices, the Trash, project build output, stopped Docker containers and unused volumes. `a` does not select these items. |

Project items cover `~/workspace` and only directories that Git ignores.
`project-builds` can hold release files, so it is a `data` item. `old-*` items keep
the newest version; `old-claude` also keeps the current one, and `old-node` keeps the
newest of each major version and the nvm default. `simulator-runtimes` keeps the most
recently used runtime of each platform. Installed apps and photos are not listed.
If macOS blocks a protected folder, the command says so; grant the terminal Full Disk
Access to include it.

A blocked item stays. A running GitHub Actions job or `xcodebuild` blocks Docker,
simulator, DerivedData, Gradle, project and runner items. A running Chrome or VS Code
blocks its own items, and a booted simulator blocks `simulators`. The check runs again
right before removal. On DGX Spark, Docker images and volumes are not listed. If one
item fails, the others continue and the command exits nonzero. Docker runtimes can
return freed space late, so the free-space figure may not rise at once.

### Examples

```bash
# AWS
toast am                   # Show identity
toast env                  # Switch profiles
toast region               # Switch regions

# Kubernetes
toast ctx                  # Switch contexts
# Select "+ Add an EKS cluster" to add clusters from the current region
# Select "- Delete a context" to delete one or all contexts, after a confirmation

# Environment Files (.env.local)
toast dot                  # Compare local and env-store, choose action (default: sync)
toast dot up               # Upload .env.local to env-store (S3)
toast dot down             # Download .env.local from env-store (alias: dn)
toast dot diff             # Show local vs env-store diff without changing files
toast dot ls               # List all .env.local files in env-store (S3 + SSM)
# up/down show a masked diff and confirm when local and env-store differ;
# down is a no-op when local matches the newest copy; up compares against S3.
# Secret values are masked, including multiline dotenv values (KEY=ab****yz).

# Prompt Files (.prompt.md)
toast prompt               # Compare local and env-store, choose action (default: sync)
toast prompt up            # Upload .prompt.md to env-store (S3)
toast prompt down          # Download .prompt.md from env-store (alias: dn)
toast prompt diff          # Show local vs env-store diff without changing files
toast prompt ls            # List all .prompt.md files in env-store (S3 + SSM)

# SSM Parameter Store
toast ssm                  # Interactive mode: browse and select parameters
toast ssm ls               # List all parameters
toast ssm ls /toast/       # List parameters under path
toast ssm get /my/param    # Get parameter value, masked by default (alias: g)
toast ssm get /my/param --reveal  # Get parameter value in plaintext
toast ssm put /my/param 'value'  # Store as SecureString; shows masked diff if it exists (alias: p)
toast ssm diff /my/param 'value' # Show masked diff without writing
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

Clone accepts HTTPS, SSH (including custom ports), and SCP-style Git URLs.
The repository is cloned into the current directory using its name, or `-t` for a custom name:

```bash
cd ~/workspace/gitlab.clush.net/apps/cdp/be
toast git ssh://git@110.45.156.168:30022/apps/cdp/be/ws.git clone
# Alternatively, use HTTPS:
toast git https://gitlab.clush.net/apps/cdp/be/ws.git clone
```

With only a repository name, `toast git ws clone` in this directory uses
`git@gitlab.clush.net:apps/cdp/be/ws.git`. All groups below the host directory
form the namespace. Use an explicit URL when the SSH host or port differs.
The existing `GITHUB_HOST` configuration also overrides the host for name-based clones.

## Workspace Structure

Toast-cli uses a standardized workspace directory structure for organizing projects:

```
~/workspace/{git-host}/{namespace}/{project}
```

**Examples**:
- `~/workspace/github.com/opspresso/toast-cli`
- `~/workspace/github.enterprise.com/myorg/myproject`
- `~/workspace/gitlab.clush.net/apps/cdp/be/ws`

The host directory is the Git server domain. The namespace can contain nested groups.

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
- Automatic detection of the Git host from the workspace path
- Git operations across hosts; dot/prompt currently use GitHub project paths

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
s3://env-store-{account-id}/local/{namespace}/{project}/env-local   # .env.local files
s3://env-store-{account-id}/local/{namespace}/{project}/prompt-md   # .prompt.md files

/toast/local/{namespace}/{project}/env-local     # legacy SSM (read-only fallback)
/toast/local/{namespace}/{project}/prompt-md     # legacy SSM (read-only fallback)
```

Run `dot` and `prompt` under `~/workspace/{host}/{org}/{project}`. A call
from a subdirectory still uses the project root's file. `ls` works anywhere.
The namespace is `{org}` for `github.com` and `{host}/{org}` for other hosts:

| Project directory | S3 key |
|-------------------|--------|
| `~/workspace/github.com/opspresso/toast-cli` | `local/opspresso/toast-cli/env-local` |
| `~/workspace/gitlab.example.com/group/project` | `local/gitlab.example.com/group/project/env-local` |

The host must contain a dot. GitLab subgroups are not supported: the directory
after `{org}` is always the project root.

Both S3 and SSM reads must succeed before comparison or transfer. On an access,
network, or region error, fix the reported cause and run the command again.
Downloads replace the local file atomically with mode 0600, preserving UTF-8
content and line endings. Empty files count as existing files.

S3 objects are written with SSE-KMS encryption. All env-store access uses a
dedicated AWS profile so it is decoupled from your current default profile.

**Configuration** — precedence: environment variable > config file > default.

Environment variables:

```bash
TOAST_ENV_STORE_PROFILE   # default: {username}-admin
TOAST_ENV_STORE_BUCKET    # default: env-store-{account-id of the profile}
TOAST_ENV_STORE_KMS_KEY   # default: bucket/account default KMS key
TOAST_ENV_STORE_REGION    # profile region, then AWS_REGION / AWS_DEFAULT_REGION; required for SSM
```

The profile defaults to your OS username + `-admin`, and the bucket defaults to
`env-store-` + the AWS account id of that profile (looked up via
`aws sts get-caller-identity`). The region resolves to the configured value, then
the profile's region, then `AWS_REGION` / `AWS_DEFAULT_REGION`. If none is set,
SSM reads fail. Set `TOAST_ENV_STORE_REGION` to the region holding your legacy
parameters; toast never assumes a different region to report them as absent.

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
c() {
  local dir
  dir="$(toast cdw "$@")" || return
  [ -n "$dir" ] && cd "$dir"
}                          # Navigate only after a selection
alias m='toast am'           # AWS identity
alias x='toast ctx'          # Kubernetes contexts
alias d='toast dot'          # .env.local files
alias p='toast prompt'       # .prompt.md files
alias e='toast env'          # AWS profiles
alias g='toast git'          # Git repositories
alias r='toast region'       # AWS region
alias ssm='toast ssm'        # SSM Parameter Store
```

## Shell completion

Add one line to your shell startup file:

```bash
eval "$(toast completion zsh)"    # ~/.zshrc
eval "$(toast completion bash)"   # ~/.bashrc
toast completion fish | source    # ~/.config/fish/config.fish
```

## Output and exit status

A command writes its result to stdout: a path, a value, a table or JSON. It writes
status, warnings, errors, prompts and pickers to stderr. A pipe or `$(...)` therefore
receives only the result:

```bash
cd "$(toast cdw)"
token="$(toast ssm get /app/token --reveal)"
toast env prod | jq -r .Arn
```

In a pipe, tables are tab-separated and never cut at the terminal width. Set
`NO_COLOR` to turn off colors.

| Exit status | Meaning |
|-------------|---------|
| 0 | Success. A cancelled picker or a declined confirmation also returns 0 and changes nothing |
| 1 | The operation failed |
| 2 | The command line is invalid |
| 130 | Ctrl-C or end of input at a prompt |

## Pickers

Type to filter a list. Letters can be scattered, and spaces separate terms that must
all match. Use `↑`/`↓` to move, `Enter` to select, `Ctrl-U` to clear the filter and
`Esc` to quit. `clean` uses `Space` to select several rows.

A picker needs a terminal. In a script, name the value: `toast ctx prod`, `toast env
prod` or `toast region ap-northeast-2`. `toast dot sync` has no such form, so use
`toast dot up` or `toast dot down`.

`ssm put` and `ssm diff` take a value from stdin or a hidden prompt, which keeps it
out of shell history: `pbpaste | toast ssm put /app/key`. A pipe cannot answer a
confirmation, so add `--yes` to overwrite an existing parameter.

`git REPO rm` asks for a confirmation and names uncommitted changes and unpushed
commits. Use `--yes` in scripts.

`env` manages static profiles in `AWS_SHARED_CREDENTIALS_FILE` (default
`~/.aws/credentials`). It requires both access key fields before replacing the
default credentials, removes a stale session token, and verifies the explicit
`default` profile. SSO/role configuration in `~/.aws/config` is not copied.

`ssm put` requires permission to read the current parameter. A failed read stops
the write. To keep input out of shell history, use `toast ssm` and choose the
interactive create/update action; the value prompt hides input. `--reveal`
prints values literally, including markup-like text.

Git branch/pull/push/rm require an existing repository directory name. Invalid
names and symlinks are rejected without rewriting the target. Mirror push uses
the full workspace namespace and leaves existing remotes unchanged.

## Resources

* **Development**: See [CLAUDE.md](CLAUDE.md) for guidelines
* **License**: [GNU GPL v3.0](LICENSE)
* **Contributing**: Via [GitHub repository](https://github.com/opspresso/toast-cli)
* **Documentation**: [ARCHITECTURE.md](ARCHITECTURE.md) and [toast.sh](https://cli.toast.sh/)
