# Toast CLI Development Guide

## Basic Guidelines
- Focus on solving the specific problem - avoid unnecessary complexity or scope creep.
- Use standard libraries and documented patterns first before creating custom solutions.
- Write clean, well-structured code with meaningful names and clear organization.
- Handle errors and edge cases properly to ensure code robustness.
- Include helpful comments for complex logic while keeping code self-documenting.

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
