#!/bin/bash

success() {
    echo -e "$1"
}

warning() {
    echo -e "$1"
}

################################################################################

ORG=

CONFIG="${HOME}/.toast"
if [ -f "${CONFIG}" ]; then
    source "${CONFIG}"
fi

if [ "${ORG}" == "yanolja" ]; then
    REPO="http://toaster.yanolja.com.s3-website.ap-northeast-2.amazonaws.com"
else
    REPO="http://toast.sh"
fi

################################################################################

if [ ! -d ~/toaster ]; then
    mkdir ~/toaster
fi

# version
curl -s -o /tmp/toaster.new ${REPO}/toaster-v3.txt

if [ ! -f /tmp/toaster.new ]; then
    warning "Can not download. [${REPO}]"
    exit 1
fi

if [ -f /tmp/toaster.old ]; then
    NEW="$(cat /tmp/toaster.new)"
    OLD="$(cat /tmp/toaster.old)"

    if [ "${NEW}" == "${OLD}" ]; then
        success "Already have latest version. [${OLD}]"
        exit 0
    fi

    MSG="Latest version updated. [${OLD} -> ${NEW}]"
else
    MSG="Toast.sh installed."
fi

# download
curl -s -o /tmp/toaster.tar.gz ${REPO}/toaster-v3.tar.gz

if [ ! -f /tmp/toaster.tar.gz ]; then
    warning "Can not download. [${REPO}]"
    exit 1
fi

# install
tar -zxf /tmp/toaster.tar.gz -C ~/toaster

# cp version
cp -rf /tmp/toaster.new /tmp/toaster.old

# done
success "${MSG}"
