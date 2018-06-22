#!/bin/bash

alias n="~/toaster/helper/nsh.sh"
alias c="~/toaster/helper/cdw.sh"
alias e="~/toaster/helper/env.sh"
alias s="~/toaster/helper/ssh.sh"

alias t="~/toaster/toast.sh"
alias ta="t auto"
alias tu="t update"
alias td="t deploy"

alias st="/Applications/Sublime\ Text.app/Contents/SharedSupport/bin/subl"

alias tf="terraform"
alias tfp="tf init && tf plan"
alias tfa="tf init && tf apply -auto-approve"
alias tfd="tf init && tf destroy -auto-approve"
alias tfg="tf graph"
alias tfo="tf output"
alias tfc="rm -rf .terraform && tf init"

alias vg="vagrant"
alias vgu="vg up"
alias vgh="vg halt"
alias vgd="vg destroy"

alias p="reveal-md"
