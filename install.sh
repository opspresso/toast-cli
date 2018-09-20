#!/bin/bash

# curl -sL toast.sh/install | bash

OS_NAME="$(uname | awk '{print tolower($0)}')"

################################################################################

command -v tput > /dev/null || TPUT=false

_echo() {
    if [ -z ${TPUT} ] && [ ! -z $2 ]; then
        echo -e "$(tput setaf $2)$1$(tput sgr0)"
    else
        echo -e "$1"
    fi
}

_result() {
    _echo "# $@" 4
}

_command() {
    _echo "$ $@" 3
}

_success() {
    _echo "+ $@" 2
    exit 0
}

_error() {
    _echo "- $@" 1
    exit 1
}

################################################################################

VERSION=$(curl -s https://api.github.com/repos/nalbam/toaster/releases/latest | grep tag_name | cut -d'"' -f4)

_result "toaster version: ${VERSION}"

if [ -z ${VERSION} ]; then
    _error
fi

DIST=/tmp/toaster
rm -rf ${DIST}

# download
curl -sL -o ${DIST} https://github.com/nalbam/toaster/releases/download/${VERSION}/toaster
chmod +x ${DIST}

if [ ! -z $HOME ]; then
    $HAS_PATH=$(echo "$PATH" | grep "$HOME/bin")
    if [ -z ${HAS_PATH} ]; then
        echo "PATH=$HOME/bin:$PATH" >> $HOME/.bash_profile
    fi

    mkdir -p $HOME/bin
    mv -f ${DIST} $HOME/bin/valve
else
    mv -f ${DIST} /usr/local/bin/valve
fi

# if [ -d ~/bin ]; then
#     mv -f ${DIST} ~/bin/valve
# elif [ -d ~/.local/bin ]; then
#     mv -f ${DIST} ~/.local/bin/valve
# else
#     mv -f ${DIST} /usr/local/bin/valve
# fi

# done
_success "done."
