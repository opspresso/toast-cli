# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Build and Package
```bash
# Install in development mode
pip install -e .

# Build distribution packages
python -m build

# Publish to PyPI (requires credentials)
twine upload dist/*
```

### Running the CLI
```bash
# Run directly after installation
toast --help

# Run as module during development
python -m toast --help

# Common commands
toast version
toast am           # AWS identity
toast cdw          # Navigate workspace
toast ctx          # Kubernetes contexts
toast env          # AWS profiles
toast git          # Git operations
```

## Architecture Overview

Toast-cli is a plugin-based CLI tool built with Click. The core architecture consists of:

### Plugin Discovery System
- **Main entry point**: `toast/__init__.py` - Uses `importlib` and `pkgutil` for dynamic plugin discovery
- **Plugin loading**: Scans `toast/plugins/` directory, imports modules, and registers classes extending `BasePlugin`
- **Command registration**: Each plugin registers itself with the main CLI group via `plugin_class.register(toast_cli)`

### Base Plugin Architecture
- **BasePlugin** (`toast/plugins/base_plugin.py`): Abstract base class defining the plugin interface
- **Required attributes**: `name` (command name), `help` (command description)
- **Required methods**: `execute(**kwargs)` for command implementation
- **Optional methods**: `get_arguments(func)` for adding Click decorators/options

### Plugin Implementation Pattern
All plugins follow this structure:
```python
class MyPlugin(BasePlugin):
    name = "mycommand"
    help = "Command description"
    
    @classmethod
    def get_arguments(cls, func):
        # Add Click options/arguments
        return func
    
    @classmethod
    def execute(cls, **kwargs):
        # Command implementation
        pass
```

### Key Components
- **Helpers** (`toast/helpers.py`): Version handling, custom Click classes for UI
- **Plugin Utils** (`toast/plugins/utils.py`): Common utilities for subprocess execution, fzf integration
- **Dynamic Loading**: No hardcoded plugin imports - all plugins discovered at runtime

### Plugin Categories
- **AWS plugins**: `am_plugin.py` (identity), `env_plugin.py` (profiles), `region_plugin.py` (regions)
- **Kubernetes**: `ctx_plugin.py` (context management)
- **Git**: `git_plugin.py` (repository operations)
- **Environment**: `dot_plugin.py` (SSM integration for .env files)
- **Navigation**: `cdw_plugin.py` (workspace directory navigation)

## Adding New Plugins

1. Create `toast/plugins/my_plugin.py`
2. Extend `BasePlugin` class
3. Set `name` and `help` class variables
4. Implement `execute()` method
5. Plugin will be automatically discovered and loaded

## Dependencies

**Core dependencies** (defined in setup.py):
- `click`: CLI framework
- `rich`: Terminal formatting

**External tools** (required at runtime):
- `fzf`: Interactive selection menus
- `aws-cli`: AWS operations
- `kubectl`: Kubernetes operations

## Project Code Guidelines

**Important: Before writing new code, search for similar existing code and maintain consistent logic and style patterns.**

### Core Principles
- **Solve the right problem**: Avoid unnecessary complexity or scope creep
- **Favor standard solutions**: Use well-known libraries and documented patterns before writing custom code
- **Keep code clean and readable**: Use clear naming, logical structure, and avoid deeply nested logic
- **Handle errors thoughtfully**: Consider edge cases and fail gracefully
- **Design for change**: Structure code to be modular and adaptable to future changes
- **Keep dependencies shallow**: Minimize tight coupling between modules. Maintain clear boundaries
- **Fail fast and visibly**: Surface errors early with meaningful messages or logs
