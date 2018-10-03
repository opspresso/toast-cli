#!/bin/bash

# curl -s https://api.github.com/rate_limit
# echo

USERNAME=${1:-nalbam}
REPONAME=${2:-toaster}

rm -rf target
mkdir -p target/dist
mkdir -p target/helper

# uname
OS_NAME="$(uname | awk '{print tolower($0)}')"
echo "OS_NAME=${OS_NAME}"
echo

# previous versions
VERSION=$(curl -s https://api.github.com/repos/${USERNAME}/${REPONAME}/releases/latest | grep tag_name | cut -d'"' -f4 | xargs)

# release version
if [ -z ${VERSION} ]; then
    VERSION=$(cat ./VERSION | xargs)
else
    MAJOR=$(cat ./VERSION | xargs | cut -d'.' -f1)
    MINOR=$(cat ./VERSION | xargs | cut -d'.' -f2)

    LATEST_MAJOR=$(echo ${VERSION} | cut -d'.' -f1)
    LATEST_MINOR=$(echo ${VERSION} | cut -d'.' -f2)

    if [ "${MAJOR}" != "${LATEST_MAJOR}" ] || [ "${MINOR}" != "${LATEST_MINOR}" ]; then
        VERSION=$(cat ./VERSION | xargs)
    fi

    # add
    VERSION=$(echo ${VERSION} | perl -pe 's/^(([v\d]+\.)*)(\d+)(.*)$/$1.($3+1).$4/e')
fi

printf "${VERSION}" > target/VERSION
echo "VERSION=${VERSION}"
echo

# 755
find ./** | grep [.]sh | xargs chmod 755

# target/
cp -rf install.sh target/install
cp -rf slack.sh target/slack
cp -rf tools.sh target/tools

# target/dist/
cp -rf toaster.sh target/dist/toaster

# version
if [ "${OS_NAME}" == "linux" ]; then
    sed -i -e "s/THIS_VERSION=.*/THIS_VERSION=${VERSION}/" target/dist/toaster
elif [ "${OS_NAME}" == "darwin" ]; then
    sed -i "" -e "s/THIS_VERSION=.*/THIS_VERSION=${VERSION}/" target/dist/toaster
fi

# target/dist/helper.tar.gz
pushd helper
tar -czf ../target/dist/helper.tar.gz *
popd
echo

# target/helper/
cp -rf helper/* target/helper/

# target/
cp -rf web/* target/
