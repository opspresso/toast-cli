#!/usr/bin/env python3

from setuptools import setup, find_packages

# Get the version from the VERSION file
with open("VERSION", "r") as f:
    version = f.read().strip()

# Get the long description from README.md
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="toast-cli",
    version=version,
    author="nalbam",
    author_email="byforce@gmail.com",
    description="A Python-based CLI utility with a plugin architecture for AWS, Kubernetes, Git, and more",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/opspresso/toast-cli",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "toast_cli": ["VERSION"],
        "toast": ["../VERSION"],
    },
    python_requires=">=3.6",
    install_requires=[
        "click",
        "rich",
    ],
    entry_points={
        "console_scripts": [
            "toast=toast:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: Utilities",
    ],
)
