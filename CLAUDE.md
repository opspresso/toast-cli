# Toast CLI Development Guide

## Basic Guidelines
- Focus on the problem. Don't take detours in problem solving.
- Always refer to the documentation, check for and utilize common modules.

## Build and Development Commands
```bash
# Installation
pip install -e .             # Install in development mode
python -m build              # Build distribution packages
twine upload dist/*          # Publish to PyPI

# Running
python -m toast              # Run from source
toast                        # Run installed version
```

## Code Style Guidelines
- **Python Version**: >=3.6
- **Type Hints**: Use Python type annotations from typing module
- **Naming**:
  - snake_case for functions, variables, files
  - CamelCase for classes
  - Plugins should end with `_plugin.py`
- **Imports**: Group by standard library, then third-party
- **Documentation**: Write docstrings for all functions and classes
- **Error Handling**: Use try/except with specific exceptions

## Plugin Development
All plugins should:
- Extend BasePlugin class
- Define name and help class variables
- Implement execute() method
- Be placed in toast/plugins/ directory

## Dependencies
- Core: click
- External tools: fzf, jq, aws-cli, kubectl
