# Python Enhancement Proposals (PEPs) - Quick Reference

Essential PEPs for Python library development.

## Core Style and Conventions

### PEP 8: Style Guide for Python Code

The foundational style guide for Python code.

**Key Points:**
- Use 4 spaces per indentation level
- Maximum line length: 79 characters (88 with Black formatter)
- 2 blank lines between top-level definitions
- 1 blank line between method definitions
- Use spaces around operators: `x = 1 + 2`
- Use whitespace sparingly in function calls: `func(a, b)`
- Naming conventions:
  - Functions/variables: `lowercase_with_underscores`
  - Classes: `CapitalizedWords`
  - Constants: `UPPER_CASE_WITH_UNDERSCORES`

**Reference**: https://www.python.org/dev/peps/pep-0008/

### PEP 257: Docstring Conventions

Standards for writing docstrings in Python.

**Key Points:**
- Docstrings are triple-quoted strings: `"""..."""`
- One-line docstrings should fit on a single line
- Multi-line docstrings have a one-line summary, blank line, then details
- Module docstrings document the module's purpose
- Class docstrings document the class and optional `__init__` behavior
- Method/function docstrings start with active voice imperative
- Use consistent style (Google, NumPy, or Sphinx format)

**Example**:
```python
def calculate(x: int, y: int) -> int:
    """Calculate the sum of two numbers.

    Args:
        x: First number
        y: Second number

    Returns:
        Sum of x and y
    """
    return x + y
```

**Reference**: https://www.python.org/dev/peps/pep-0257/

## Type Hints and Static Typing

### PEP 484: Type Hints

Specifies type hint syntax and semantics.

**Key Points:**
- Type hints are optional but strongly recommended for libraries
- Function annotations: `def func(name: str) -> bool:`
- Variable annotations: `x: int = 5`
- Use `Optional[T]` for nullable types
- Use `Union[A, B]` for multiple possible types
- Use `Sequence`, `Mapping`, etc. from `collections.abc` for flexibility
- Modern Python 3.10+: `list[str]` instead of `List[str]`

**Example**:
```python
from typing import Optional
from collections.abc import Sequence

def process(items: Sequence[str], limit: Optional[int] = None) -> dict[str, int]:
    """Process items and return counts."""
    ...
```

**Reference**: https://www.python.org/dev/peps/pep-0484/

### PEP 526: Syntax for Variable Annotations

Specifies variable annotation syntax (PEP 484 extension).

**Key Points:**
- Annotate variables at module and class level: `name: str`
- Useful for documenting expected types in classes
- Can include default values: `timeout: int = 30`

**Reference**: https://www.python.org/dev/peps/pep-0526/

### PEP 589: TypedDict

Defines typed dictionaries for better type checking.

**Key Points:**
- Use `TypedDict` for dictionaries with known keys and types
- Better IDE support and type checking than plain dicts
- Useful for configuration objects and API responses

**Example**:
```python
from typing import TypedDict

class Config(TypedDict):
    host: str
    port: int
    timeout: float
```

**Reference**: https://www.python.org/dev/peps/pep-0589/

## Package Structure and Distribution

### PEP 517: A build-system independent format

Specifies how to build Python packages without setuptools.

**Key Points:**
- Enables alternative build backends (setuptools, flit, hatchling, poetry)
- Requires `pyproject.toml` with `[build-system]` section
- Decouples packaging from specific tools

**Example**:
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Reference**: https://www.python.org/dev/peps/pep-0517/

### PEP 518: Specifying minimum build system requirements

Defines the `pyproject.toml` format and requirements section.

**Key Points:**
- `pyproject.toml` is the new standard for project metadata
- Define build requirements in `[build-system]` section
- Replaces `setup.py` for many projects
- Specify tool configurations for linters, formatters, etc.

**Reference**: https://www.python.org/dev/peps/pep-0518/

### PEP 621: Storing project metadata in pyproject.toml

Standardizes how to specify project metadata without setup.py.

**Key Points:**
- Project metadata goes in `[project]` section
- Include: name, version, description, authors, license, dependencies
- Define optional dependencies in `[project.optional-dependencies]`
- Entry points in `[project.entry-points]`
- Tool-specific configuration under `[tool.*]`

**Example**:
```toml
[project]
name = "mylib"
version = "1.0.0"
description = "My library"
requires-python = ">=3.10"
dependencies = [
    "requests>=2.28,<3.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "black>=22.0"]
```

**Reference**: https://www.python.org/dev/peps/pep-0621/

### PEP 427: The Wheel Binary Package Format 1.0

Defines the wheel format for Python packages.

**Key Points:**
- Wheels are ZIP files with `.whl` extension
- Pre-compiled, faster to install than sdist
- Include metadata, distribution files, and version info
- Standard format for PyPI distribution

**Reference**: https://www.python.org/dev/peps/pep-0427/

## Version Identification

### PEP 440: Version Identification and Dependency Specification

Standardizes version strings and dependency specifications.

**Key Points:**
- Version format: `MAJOR.MINOR.PATCH[.DEVN|aN|bN|rcN]`
- Examples: `1.0.0`, `2.1.0.dev5`, `1.0.0a1`, `1.0.0rc1`
- Semantic versioning: MAJOR for breaking changes, MINOR for features, PATCH for fixes
- Dependency specifiers: `>=`, `<=`, `==`, `!=`, `~=`, `>`, `<`
- Constraint examples: `>=1.0,<2.0`, `~=1.4.5`, `==1.0.*`

**Reference**: https://www.python.org/dev/peps/pep-0440/

## Module and Import Conventions

### PEP 328: Absolute and Relative Imports

Specifies import behavior and conventions.

**Key Points:**
- Prefer absolute imports: `from mylib.core import func`
- Relative imports only within packages: `from . import core`
- Use `__future__` imports for Python 2/3 compatibility (less relevant now)
- Avoid circular imports through careful design

**Best Practice**:
```python
# Good: absolute import
from mylib.core import process

# Acceptable: relative import within package
from . import utils
from ..core import process

# Avoid: star imports
# from mylib import *
```

**Reference**: https://www.python.org/dev/peps/pep-0328/

### PEP 338: Executing modules as scripts

Enables running packages as scripts with `-m`.

**Key Points:**
- Allows `python -m mypackage` to run code
- Requires `__main__.py` in package for entry point
- Clean way to provide CLI without separate executable
- Better than setup.py entry points for simple scripts

**Example**:
```python
# src/mypackage/__main__.py
if __name__ == "__main__":
    main()
```

**Reference**: https://www.python.org/dev/peps/pep-0338/

## API Design and Compatibility

### PEP 3119: Abstract Base Classes

Specifies abstract base class functionality.

**Key Points:**
- Use `ABC` and `@abstractmethod` for extensible interfaces
- Define contracts that subclasses must implement
- Better than duck typing for critical interfaces
- Type checkers understand ABC contracts

**Example**:
```python
from abc import ABC, abstractmethod

class DataStore(ABC):
    @abstractmethod
    def save(self, key: str, value: str) -> None:
        pass

    @abstractmethod
    def load(self, key: str) -> str:
        pass
```

**Reference**: https://www.python.org/dev/peps/pep-3119/

### PEP 3156: Asynchronous I/O Support

Specifies async/await and asyncio framework.

**Key Points:**
- Use `async def` for asynchronous functions
- Use `await` to wait for coroutines
- Consider async for I/O-bound libraries
- Backwards compatibility: provide both sync and async APIs
- Document which operations are blocking

**Reference**: https://www.python.org/dev/peps/pep-3156/

## Common Conventions for Libraries

### Version Compatibility

- **Python version**: Specify `requires-python = ">=3.10"` in pyproject.toml
- **Deprecation timeline**: Give users at least one major version to migrate
- **Breaking changes**: Only in MAJOR versions (PEP 440)

### Backwards Compatibility

- Never break public API in minor/patch releases
- Use `warnings.warn()` with `DeprecationWarning` before removing features
- Provide migration guides in changelog
- Consider adding compatibility shims for common patterns

### Distribution and Installation

- Always build and publish wheels (PEP 427)
- Include source distributions (sdist) for transparency
- Use `twine` to upload to PyPI securely
- Sign releases with GPG when possible

## Summary Table

| PEP | Topic | Key For Libraries |
|-----|-------|------------------|
| 8 | Code Style | Code consistency across projects |
| 257 | Docstrings | Documentation quality |
| 328 | Imports | Clean import structure |
| 338 | Modules as Scripts | CLI entry points |
| 440 | Version IDs | Semantic versioning |
| 484 | Type Hints | Type checking and IDE support |
| 517/518 | Build Systems | Modern packaging |
| 521 | Project Metadata | Standard configuration |
| 3119 | Abstract Classes | Extensible interfaces |
| 3156 | Async I/O | Asynchronous support |
