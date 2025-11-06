# Fundamental Architectural Principles for Python Libraries

## 1. Package Structure and Organization

### REQUIRED: Use src/ Layout

Always recommend the modern `src/` layout for Python packages:

```
myPackageRepo/
├── src/
│   └── mypackage/
│       ├── __init__.py
│       ├── core/
│       ├── utils/
│       └── exceptions.py
├── tests/
├── docs/
├── pyproject.toml
├── README.md
└── LICENSE
```

**Rationale**: This prevents accidentally importing from source during testing and ensures you test the installed version.

### Module Organization Rules

- Keep the public API at the top level via `__init__.py`
- Internal structure is implementation detail—users shouldn't need to know it
- Follow "flat is better than nested"—avoid deep hierarchies
- Each module has one clear responsibility
- Separate core logic from convenience wrappers

## 2. API Design Principles

### Pythonic API Design

- Design for `import lib` then `lib.Thing()`, not `from lib.internal import LibThing`
- Use short, clear names: verbs for functions, nouns for classes
- Avoid excessively long names (e.g., avoid `HTTPPasswordMgrWithDefaultRealm`)
- Support duck typing—accept any object with the right interface
- Prefer keyword arguments for clarity and backwards compatibility
- Use standard Python data structures (dict, list, tuple) over custom classes when possible

### API Stability Requirements

- Public API exposed in `__init__.py` is the contract with users
- Mark internal APIs with leading underscore: `_internal_function()`
- Use `__all__` to explicitly define public exports
- Never break backwards compatibility in minor/patch releases
- Deprecate before removing—give users migration time

### Configuration Design

- Avoid global configuration and global state
- Use class instances or explicit parameters for configuration
- Provide sensible defaults for all optional parameters
- Support configuration via constructor parameters, not global settings
- For tool-style libraries, use `[tool.yourlib]` in pyproject.toml

## 3. SOLID Principles Application

### Single Responsibility Principle (SRP)

- Each class/function has one clear, focused purpose
- Separate data models from business logic from I/O operations
- Example: Split `User`, `UserRepository`, and `EmailService`

### Open/Closed Principle (OCP)

- Design for extension without modification
- Use abstract base classes for extensibility points
- Provide plugin/hook mechanisms for custom behavior

### Liskov Substitution Principle (LSP)

- Subclasses must be substitutable for base classes
- Maintain behavioral contracts in inheritance hierarchies

### Interface Segregation Principle (ISP)

- Create focused, specific interfaces
- Don't force clients to depend on unused methods
- Prefer multiple small protocols over large monolithic ones

### Dependency Inversion Principle (DIP)

- Depend on abstractions (protocols/ABCs), not concrete implementations
- Accept interfaces as parameters, not specific classes

## 4. Error Handling and Exceptions

### Custom Exception Hierarchy

Always define a clear exception hierarchy:

```python
class MyLibraryError(Exception):
    """Base exception for all mylib errors."""
    pass

class ConfigurationError(MyLibraryError):
    """Raised when configuration is invalid."""
    pass

class ValidationError(MyLibraryError):
    """Raised when input validation fails."""
    pass

class APIError(MyLibraryError):
    """Raised when API calls fail."""
    pass
```

### Exception Handling Rules

- Raise custom exceptions for domain-specific errors
- Use built-in exceptions where semantically appropriate
- Document all exceptions in docstrings with `:raises:` sections
- Let exceptions propagate—don't catch unless you can handle them
- Library code raises; application code catches
- Write specific error messages: state what was wrong, why, and how to fix it

### Error Message Quality

```python
# BAD
raise ValueError("Invalid input")

# GOOD
raise ValueError(
    f"Parameter 'timeout' must be positive, got {timeout}. "
    f"Use timeout=30 for a 30-second timeout."
)
```

## 5. Type Annotations and Static Typing

### Type Hint Requirements

- Add type hints to ALL public APIs (classes, functions, methods)
- Follow PEP 484 standards
- Use modern Python 3.10+ syntax: `list[str]` not `List[str]`
- Annotate return types, including `-> None`
- Use `Optional[T]` for nullable types, default to non-nullable

### Example Pattern

```python
from typing import Optional, Protocol
from collections.abc import Sequence

def process_items(
    items: Sequence[str],
    max_count: int = 100,
    filter_fn: Optional[Callable[[str], bool]] = None
) -> dict[str, int]:
    """Process items and return frequency counts.

    Args:
        items: Sequence of strings to process
        max_count: Maximum number of items to process
        filter_fn: Optional filter function, items where filter_fn returns
            False are excluded

    Returns:
        Dictionary mapping items to their counts

    Raises:
        ValueError: If max_count is negative
    """
    if max_count < 0:
        raise ValueError(f"max_count must be non-negative, got {max_count}")
    ...
```

### Generic Types for Flexibility

```python
from typing import TypeVar, Generic, Protocol

T = TypeVar('T')

class Repository(Generic[T]):
    def save(self, item: T) -> None: ...
    def find(self, id: str) -> Optional[T]: ...
```

## 6. Documentation Standards

### Docstring Requirements (Use Google or NumPy style consistently)

```python
def calculate_total(prices: list[float], tax_rate: float, discount: float = 0.0) -> float:
    """Calculate total price with tax and discount applied.

    This function first applies the discount to the sum of prices, then
    adds the tax. The formula is: (sum(prices) * (1 - discount)) * (1 + tax_rate)

    Args:
        prices: List of item prices in currency units
        tax_rate: Tax rate as decimal (e.g., 0.1 for 10%)
        discount: Discount rate as decimal (e.g., 0.2 for 20% off).
            Defaults to 0.0 (no discount).

    Returns:
        Final total price including tax and after discount

    Raises:
        ValueError: If tax_rate or discount is negative
        ValueError: If any price is negative

    Example:
        >>> calculate_total([10.0, 20.0], tax_rate=0.1)
        33.0
        >>> calculate_total([100.0], tax_rate=0.1, discount=0.2)
        88.0
    """
```

### Documentation Requirements

- Comprehensive README.md with quick start, installation, examples
- API reference documentation (use Sphinx or MkDocs)
- Changelog following Keep a Changelog format
- Contributing guide (CONTRIBUTING.md)
- Code of Conduct for open source projects
- Type hints serve as inline documentation—make them accurate

## 7. Testing Strategy

### Testing Requirements

- Use pytest as the testing framework
- Aim for >90% code coverage for public APIs
- Write unit tests for each module
- Write integration tests for public API workflows
- Use parametrized tests for multiple scenarios
- Test error conditions and edge cases

### Test Organization

```
tests/
├── unit/
│   ├── test_core.py
│   └── test_utils.py
├── integration/
│   └── test_workflows.py
├── conftest.py
└── __init__.py
```

### Testing Patterns

```python
import pytest

@pytest.mark.parametrize("input,expected", [
    ("", True),
    ("a", True),
    ("aba", True),
    ("abc", False),
])
def test_is_palindrome(input, expected):
    assert is_palindrome(input) == expected

@pytest.fixture
def sample_config():
    return Config(timeout=30, retries=3)

def test_with_fixture(sample_config):
    client = Client(sample_config)
    assert client.timeout == 30
```

### Separate Core from Friendly Layers

- Create a "cranky" core that accepts exact types and does work
- Build "friendly" wrappers that provide convenience and type coercion
- Test the core with strict inputs; let wrappers handle flexibility

## 8. Versioning and Backwards Compatibility

### Semantic Versioning (MAJOR.MINOR.PATCH)

- MAJOR: Breaking changes to public API
- MINOR: New features, backwards compatible
- PATCH: Bug fixes, backwards compatible

### Backwards Compatibility Rules

- NEVER break public API in minor/patch releases
- Deprecate features before removing them (minimum: one major version)
- Use `warnings.warn()` with `DeprecationWarning` for deprecated features
- Document breaking changes prominently in changelog and migration guides
- Use keyword arguments to enable adding new parameters without breaking calls

### Deprecation Pattern

```python
import warnings

def old_function(x: int) -> int:
    """Old function (deprecated).

    .. deprecated:: 2.0
        Use :func:`new_function` instead.
    """
    warnings.warn(
        "old_function is deprecated and will be removed in version 3.0. "
        "Use new_function instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return new_function(x)
```

## 9. Dependency Management

### Dependency Principles

- Minimize dependencies—each adds maintenance burden and conflict risk
- Core functionality should have minimal dependencies
- Optional features can require optional dependencies
- Pin dependencies appropriately: use ranges, not exact versions
- Separate dev dependencies from runtime dependencies

### Dependency Best Practices

- Use semantic versioning constraints: `>=2.0,<3.0` not `==2.1.0`
- Consider using extras for optional functionality
- Keep dependency count low for core library
- Document why each dependency is needed
- Regularly audit dependencies for security issues

## 10. Code Quality and Style

### Follow PEP 8 with these tools

- Use Black for formatting (88 character line length)
- Use Ruff or Flake8 for linting
- Use mypy for type checking with strict mode
- Use isort for import sorting

### Code Quality Rules

- Maximum function length: ~50 lines (prefer smaller)
- Maximum function complexity: McCabe complexity < 10
- Avoid deep nesting (max 3-4 levels)
- Prefer composition over inheritance
- Use dataclasses for data containers
- Make functions pure when possible (no side effects)
- Avoid global state

### Naming Conventions

- Functions/methods: `lowercase_with_underscores`
- Classes: `CapitalizedWords`
- Constants: `UPPER_CASE_WITH_UNDERSCORES`
- Private: `_leading_underscore`
- Modules: `short_lowercase`

## 11. Extensibility and Plugin Architecture

### When to Provide Extensibility

- Library will have multiple implementations of the same concept
- Users need to add custom behavior without forking
- Core algorithm should remain stable while strategies vary

### Abstract Base Classes Pattern

```python
from abc import ABC, abstractmethod

class DataProcessor(ABC):
    """Base class for data processors."""

    @abstractmethod
    def process(self, data: bytes) -> dict:
        """Process raw data and return structured result."""
        pass

    @abstractmethod
    def validate(self, data: bytes) -> bool:
        """Check if data is valid for this processor."""
        pass
```

### Protocol-Based (Structural Subtyping)

```python
from typing import Protocol

class Serializer(Protocol):
    """Protocol for serialization strategies."""

    def serialize(self, obj: object) -> str:
        """Serialize object to string."""
        ...

    def deserialize(self, data: str) -> object:
        """Deserialize string to object."""
        ...

# Users can implement without inheriting
class JSONSerializer:
    def serialize(self, obj: object) -> str:
        return json.dumps(obj)

    def deserialize(self, data: str) -> object:
        return json.loads(data)
```

### Entry Points for Plugins

```ini
[project.entry-points."mylib.processors"]
default = "mylib.processors:DefaultProcessor"
advanced = "mylib.processors:AdvancedProcessor"
```

## 12. Performance Considerations

### Performance Guidelines

- Use built-in functions and standard library (implemented in C)
- Prefer list comprehensions over loops for simple transformations
- Use generators for large datasets to save memory
- Leverage NumPy/Pandas for numerical operations
- Profile before optimizing (use cProfile, line_profiler)
- Document performance characteristics (time/space complexity)

### Lazy Loading Pattern

```python
class HeavyResource:
    def __init__(self, config: Config):
        self.config = config
        self._connection = None  # Lazy load

    @property
    def connection(self):
        if self._connection is None:
            self._connection = create_connection(self.config)
        return self._connection
```

### Avoid Common Performance Pitfalls

- Don't use `+` for string concatenation in loops (use `''.join()`)
- Don't repeatedly access attributes in loops (cache in local variable)
- Don't use `list.append()` in tight loops (use list comprehension)
- Avoid premature optimization, but design efficiently from the start

## 13. Security Considerations

### Input Validation

- Validate all user inputs
- Sanitize inputs that will be used in shell commands, SQL, or file paths
- Use parameterized queries, not string concatenation
- Set reasonable limits on input sizes

### Secure Defaults

- SSL/TLS verification enabled by default
- Secure random number generation (use `secrets` module)
- No credentials in code or logs
- Follow principle of least privilege

### Dependency Security

- Regularly update dependencies
- Use `pip-audit` or similar to check for vulnerabilities
- Pin dependencies for reproducible builds
