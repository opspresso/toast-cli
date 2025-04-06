# Toast CLI Development Guide

## Basic Guidelines
- Focus on specific problems, avoid complexity
- Prefer standard libraries and documented patterns
- Use meaningful names and clear organization
- Handle errors and edge cases properly
- Comment complex logic, keep code self-documenting

## Commands
```bash
# Installation
pip install -e .             # Development mode
python -m build              # Build packages
twine upload dist/*          # Publish to PyPI

# Running
python -m toast              # Run from source
toast                        # Run installed version
```

## Code Style
- **Python**: >=3.6
- **Type Hints**: Use typing module annotations
- **Naming**:
  - snake_case for functions, variables, files
  - CamelCase for classes
  - Plugins end with `_plugin.py`
- **Imports**: Group by standard library, then third-party
- **Documentation**: Docstrings for all functions and classes
- **Error Handling**: Specific exceptions in try/except

## Plugin Development
- Extend BasePlugin class
- Define name and help class variables
- Implement execute() method
- Place in toast/plugins/ directory
