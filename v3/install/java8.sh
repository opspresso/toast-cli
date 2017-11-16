#!/bin/bash

echo_() {
    echo -e "$1"
    echo "$1" >> /tmp/toast.log
}

success() {
    echo -e "$(tput setaf 2)$1$(tput sgr0)"
    echo "$1" >> /tmp/toast.log
}

error() {
    echo -e "$(tput setaf 1)$1$(tput sgr0)"
    echo "$1" >> /tmp/toast.log
    exit 1
}

################################################################################

OS_NAME="$(uname)"
OS_FULL="$(uname -a)"
if [ "${OS_NAME}" == "Linux" ]; then
    if [ $(echo "${OS_FULL}" | grep -c "Ubuntu") -gt 0 ]; then
        OS_TYPE="Ubuntu"
    else
        OS_TYPE="generic"
    fi
elif [ "${OS_NAME}" == "Darwin" ]; then
    OS_TYPE="${OS_NAME}"
fi

SUDO=""
if [ "${HOME}" != "/root" ]; then
    SUDO="sudo"
fi

################################################################################

download() {
    _FILE="$1"
    _PATH="$2"

    if [ "${REPO}" != "" ]; then
        URL="s3://${REPO}/${_PATH}/${_FILE}"

        echo_ "download... [${URL}]"

        aws s3 cp ${URL} ./
    fi

    if [ ! -f ${_FILE} ]; then
        URL="http://repo.toast.sh/${_PATH}/${_FILE}"

        echo_ "download... [${URL}]"

        curl -O ${URL}
    fi
}

remove() {
    if [ "${OS_TYPE}" == "Ubuntu" ]; then
        sudo apt-get remove -y $1
    else
        sudo yum remove -y $1
    fi
}

################################################################################

# s3://repo.toast.sh/java/server-jre-8u152-linux-x64.tar.gz

NAME="java"

VERSION="8u152"

FILE="server-jre-${VERSION}-linux-x64"

EXT="tar.gz"

################################################################################

REPO="$1"

download "${FILE}.${EXT}" "${NAME}"

if [ ! -f ${FILE}.${EXT} ]; then
    error "Can not download : ${FILE}.${EXT}"
fi

################################################################################

remove "java-1.7.0-openjdk java-1.7.0-openjdk-headless"
remove "java-1.8.0-openjdk java-1.8.0-openjdk-headless java-1.8.0-openjdk-devel"

################################################################################

tar xzf ${FILE}.${EXT}

VS1=$(echo ${FILE} | cut -d "-" -f 3)
VS2="${VS1/u/.0_}"

JAVA_PATH="jdk1.${VS2}"
JAVA_HOME="/usr/local/${JAVA_PATH}"

if [ ! -d ${JAVA_PATH} ]; then
    error "Can not found : ${JAVA_PATH}"
fi

${SUDO} rm -rf ${JAVA_HOME}
${SUDO} rm -rf /usr/local/java

${SUDO} mv ${JAVA_PATH} /usr/local/
${SUDO} ln -s ${JAVA_HOME} /usr/local/java

rm -rf ${FILE}.${EXT}

echo_ "JAVA_HOME=${JAVA_HOME}"

################################################################################

FILE="local_policy.jar.bin"
download "${FILE}" "${NAME}"

if [ -f ${FILE} ]; then
    ${SUDO} mv ${FILE} ${JAVA_HOME}/jre/lib/security/local_policy.jar
fi

################################################################################

FILE="US_export_policy.jar.bin"
download "${FILE}" "${NAME}"

if [ -f ${FILE} ]; then
    ${SUDO} mv ${FILE} ${JAVA_HOME}/jre/lib/security/US_export_policy.jar
fi

################################################################################
