"""Example custom exception hierarchy for a Python library.

This file demonstrates best practices for defining exception hierarchies
in production-grade Python libraries.
"""


class MyLibraryError(Exception):
    """Base exception for all mylib errors.

    All exceptions raised by the library inherit from this class,
    allowing users to catch all library-specific errors with:

        try:
            ...
        except MyLibraryError as e:
            ...
    """

    pass


# Configuration-related errors
class ConfigurationError(MyLibraryError):
    """Raised when configuration is invalid.

    Example:
        raise ConfigurationError(
            f"Missing required config key 'database_url'. "
            f"Provide via config parameter or DATABASE_URL env variable."
        )
    """

    pass


class MissingConfigError(ConfigurationError):
    """Raised when required configuration is missing."""

    pass


class InvalidConfigError(ConfigurationError):
    """Raised when configuration values are invalid."""

    pass


# Validation-related errors
class ValidationError(MyLibraryError):
    """Raised when input validation fails.

    Example:
        if not isinstance(age, int):
            raise ValidationError(
                f"Parameter 'age' must be an integer, got {type(age).__name__}"
            )
    """

    pass


class InputError(ValidationError):
    """Raised when user input is invalid."""

    pass


class DataFormatError(ValidationError):
    """Raised when data format is not as expected."""

    pass


# API/Communication errors
class APIError(MyLibraryError):
    """Raised when API operations fail.

    Example:
        try:
            response = requests.get(url)
            response.raise_for_status()
        except requests.RequestException as e:
            raise APIError(
                f"Failed to fetch from {url}: {str(e)}. "
                f"Check your network connection and URL."
            ) from e
    """

    pass


class NetworkError(APIError):
    """Raised when network operations fail."""

    pass


class TimeoutError(APIError):
    """Raised when operation times out.

    Note: This shadows the built-in TimeoutError. Consider using
    a different name like `OperationTimeout` if needed.
    """

    pass


# Resource-related errors
class ResourceError(MyLibraryError):
    """Raised when resource operations fail."""

    pass


class ResourceNotFoundError(ResourceError):
    """Raised when a required resource is not found.

    Example:
        if not os.path.exists(filepath):
            raise ResourceNotFoundError(
                f"Configuration file not found: {filepath}. "
                f"Create a config file at {default_path} or "
                f"pass 'config_path' parameter."
            )
    """

    pass


class PermissionError(ResourceError):
    """Raised when operation is not permitted.

    Note: This shadows the built-in PermissionError. Consider using
    a different name like `AccessDenied` if needed.
    """

    pass


class InsufficientResourcesError(ResourceError):
    """Raised when insufficient resources are available."""

    pass


# State-related errors
class StateError(MyLibraryError):
    """Raised when operation is invalid for current state.

    Example:
        if not self.is_initialized:
            raise StateError(
                "Client not initialized. Call client.initialize() first."
            )
    """

    pass


class NotInitializedError(StateError):
    """Raised when required initialization hasn't been performed."""

    pass


class AlreadyExistsError(StateError):
    """Raised when trying to create something that already exists."""

    pass


# Implementation errors
class NotImplementedError(MyLibraryError):
    """Raised when feature is not yet implemented."""

    pass


class UnsupportedOperationError(MyLibraryError):
    """Raised when operation is not supported.

    Example:
        if not hasattr(processor, 'process'):
            raise UnsupportedOperationError(
                f"Processor {type(processor).__name__} doesn't support "
                f"process operation. Use a different processor."
            )
    """

    pass


# Usage Examples
# ==============

def example_validation_error():
    """Example of raising a validation error with helpful message."""
    timeout = -5
    if timeout < 0:
        raise ValidationError(
            f"Parameter 'timeout' must be non-negative, got {timeout}. "
            f"Use timeout=30 for a 30-second timeout."
        )


def example_chained_exception():
    """Example of chaining exceptions to preserve context."""
    import requests

    try:
        response = requests.get("https://example.com", timeout=5)
        response.raise_for_status()
    except requests.RequestException as e:
        raise APIError(
            f"Failed to fetch data from API: {str(e)}. "
            f"Check your network connection and API endpoint."
        ) from e


def example_missing_resource():
    """Example of reporting missing resources clearly."""
    import os

    config_path = "/etc/myapp/config.json"
    if not os.path.exists(config_path):
        raise ResourceNotFoundError(
            f"Configuration file not found: {config_path}\n"
            f"Create a config file or set MYAPP_CONFIG_PATH environment variable.\n"
            f"See documentation at: https://docs.example.com/config"
        )


def example_state_error():
    """Example of reporting state-related errors."""

    class Client:
        def __init__(self):
            self._connected = False

        def query(self, sql):
            if not self._connected:
                raise StateError(
                    "Client not connected. Call client.connect() before "
                    "executing queries."
                )
            # Execute query...

    client = Client()
    try:
        client.query("SELECT * FROM users")
    except StateError as e:
        print(f"Connection error: {e}")


# Best Practices Summary
# ======================
"""
1. DEFINE A BASE EXCEPTION
   - All library exceptions inherit from it
   - Users can catch all library errors with: except MyLibraryError

2. CREATE SEMANTIC SUBCLASSES
   - Group related errors (ConfigurationError, ValidationError, etc.)
   - Allows specific error handling

3. WRITE HELPFUL ERROR MESSAGES
   - State what was wrong
   - Explain why it's wrong
   - Show how to fix it
   - Example: f"X must be Y, got {Z}. Use X=default for default behavior."

4. CHAIN EXCEPTIONS WHEN WRAPPING
   - Use `raise ... from e` to preserve context
   - Helps with debugging and tracing

5. DOCUMENT EXCEPTIONS
   - Add docstrings to exception classes
   - Include examples in docstrings
   - Document which operations raise which exceptions

6. AVOID SHADOWING BUILT-INS
   - Consider naming like TimeoutError -> OperationTimeout
   - Be careful with common exception names

7. USE EXCEPTIONS FOR EXCEPTIONAL CASES
   - Not for normal control flow
   - Return None or empty collection for "not found" when appropriate
   - Reserve exceptions for actual errors

8. CONSISTENCY
   - Same error for same condition across codebase
   - Consistent error message format
   - Clear exception hierarchy
"""
