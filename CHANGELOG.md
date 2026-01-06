# Changelog

All notable changes to toast-cli will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [4.0.0] - Unreleased

### Breaking Changes
- **Minimum Python version raised to 3.9+** (previously 3.6+)
  - Python 3.6, 3.7, and 3.8 are no longer supported as they have reached EOL
  - Enables use of modern Python standard library features

### Changed
- **Replaced deprecated `pkg_resources` with `importlib.metadata`**
  - Version retrieval now uses `importlib.metadata.version()`
  - Removed dependency on setuptools' pkg_resources (deprecated, to be removed in Nov 2025)
  - Cleaner, more maintainable code with standard library support
- **Removed VERSION file from package data**
  - Version information now sourced directly from package metadata
  - Simplified package distribution configuration
- **Updated Python version classifiers**
  - Added: Python 3.9, 3.10, 3.11, 3.12
  - Removed: Python 3.6, 3.7, 3.8

### Added
- **Colored logo in help output**
  - Logo displayed in bold yellow using Rich Console
  - Version number shown in bold cyan
  - Improved visual appeal and readability
- **Enhanced terminal output**
  - Leveraged Rich library for syntax highlighting disabled where needed
  - Consistent color scheme across help displays

### Fixed
- Version display now properly aligned on the same line as logo

### Improved
- Simplified version retrieval logic with cleaner fallback mechanism
- Better error handling for version detection in development environments
- Reduced package complexity by removing unnecessary package_data configuration

## [3.6.0] - Previous Release

- SSM Parameter Store integration for .env.local and .prompt.md files
- Sync command for comparing local and remote files
- Git operations with organization-specific GitHub host support
- Multiple plugin enhancements and bug fixes

---

**Note**: For releases prior to 4.0.0, please refer to git commit history.
