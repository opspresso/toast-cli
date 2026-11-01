#!/usr/bin/env python3

import click

from toast import ui
from toast.plugins.base_plugin import BasePlugin

# A program cannot change the directory of the shell that started it, so a shell
# function runs `cd` in that shell. It acts only on `toast cdw` typed in an
# interactive shell with stdout on a terminal; every other call, and every help
# request, goes to the executable unchanged. The path is data: it is never
# evaluated, and an empty CDPATH keeps `cd` from printing it.
FUNCTION = """\
toast() {
  if [ "${1-}" != cdw ] || [ ! -t 1 ]; then
    command toast "$@"; return
  fi
  case $- in *i*) ;; *) command toast "$@"; return ;; esac
  local arg dir
  for arg in "$@"; do
    case $arg in
      --) break ;;
      -h|--help) command toast "$@"; return ;;
    esac
  done
  dir=$(command toast "$@") || return
  [ -n "$dir" ] || return 0
  CDPATH= builtin cd -- "$dir"
}"""


class ShellInitPlugin(BasePlugin):
    """Plugin for 'shell-init' command - prints the shell function that lets cdw change directory."""

    name = "shell-init"
    help = (
        "Print the shell function that lets 'toast cdw' change directory\n\n"
        "A program cannot change the directory of its shell. Load this function in an "
        "interactive bash or zsh, and 'toast cdw' typed at the terminal changes to the "
        "printed path. Other commands, help, pipes, $(...) and scripts run toast unchanged. "
        "This command only prints the function; it changes no file."
    )
    category = "Workspace"
    examples = (
        ('eval "$(toast shell-init zsh)"', "Add to ~/.zshrc"),
        ('eval "$(toast shell-init bash)"', "Add to ~/.bashrc"),
        ("unset -f toast", "Remove the function from the current shell"),
    )

    @classmethod
    def get_arguments(cls, func):
        return click.argument("shell", metavar="SHELL", type=click.Choice(["bash", "zsh"]))(func)

    @classmethod
    def execute(cls, shell, **kwargs):
        ui.result(FUNCTION)
