"""Example configuration patterns for Python libraries.

This file demonstrates best practices for handling configuration
in production-grade Python libraries.
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


# Pattern 1: Dataclass-based Configuration
# ==========================================

@dataclass
class DatabaseConfig:
    """Database connection configuration.

    Attributes:
        host: Database host address
        port: Database port
        username: Database username
        password: Database password (use env var, never in code)
        database: Database name
        timeout: Connection timeout in seconds
        pool_size: Connection pool size
        ssl: Whether to use SSL for connection
    """

    host: str = "localhost"
    port: int = 5432
    username: str = "user"
    password: str = ""  # Set from environment
    database: str = "mydb"
    timeout: int = 30
    pool_size: int = 10
    ssl: bool = True

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.port < 1 or self.port > 65535:
            raise ValueError(f"Invalid port number: {self.port}")
        if self.timeout <= 0:
            raise ValueError(f"Timeout must be positive, got {self.timeout}")
        if self.pool_size < 1:
            raise ValueError(f"Pool size must be positive, got {self.pool_size}")


@dataclass
class LibraryConfig:
    """Main library configuration.

    Attributes:
        debug: Enable debug mode
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        cache_enabled: Whether to enable caching
        cache_ttl: Cache time-to-live in seconds
        database: Database configuration
        timeout: Default operation timeout in seconds
        max_retries: Maximum number of retries for operations
        retry_backoff: Exponential backoff multiplier for retries
    """

    debug: bool = False
    log_level: str = "INFO"
    cache_enabled: bool = True
    cache_ttl: int = 3600  # 1 hour
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    timeout: int = 30
    max_retries: int = 3
    retry_backoff: float = 2.0

    @classmethod
    def from_env(cls) -> "LibraryConfig":
        """Create configuration from environment variables.

        Environment variables:
            MYLIB_DEBUG: Set to "1", "true", "yes" for debug mode
            MYLIB_LOG_LEVEL: Logging level (default: INFO)
            MYLIB_CACHE_ENABLED: Set to "0", "false", "no" to disable cache
            MYLIB_CACHE_TTL: Cache TTL in seconds (default: 3600)
            MYLIB_DB_HOST: Database host (default: localhost)
            MYLIB_DB_PORT: Database port (default: 5432)
            MYLIB_DB_USER: Database username (default: user)
            MYLIB_DB_PASSWORD: Database password (required if used)
            MYLIB_DB_NAME: Database name (default: mydb)
            MYLIB_TIMEOUT: Operation timeout (default: 30)
            MYLIB_MAX_RETRIES: Max retries (default: 3)
        """
        return cls(
            debug=os.getenv("MYLIB_DEBUG", "").lower() in ("1", "true", "yes"),
            log_level=os.getenv("MYLIB_LOG_LEVEL", "INFO"),
            cache_enabled=os.getenv("MYLIB_CACHE_ENABLED", "1").lower() not in ("0", "false", "no"),
            cache_ttl=int(os.getenv("MYLIB_CACHE_TTL", "3600")),
            database=DatabaseConfig(
                host=os.getenv("MYLIB_DB_HOST", "localhost"),
                port=int(os.getenv("MYLIB_DB_PORT", "5432")),
                username=os.getenv("MYLIB_DB_USER", "user"),
                password=os.getenv("MYLIB_DB_PASSWORD", ""),
                database=os.getenv("MYLIB_DB_NAME", "mydb"),
            ),
            timeout=int(os.getenv("MYLIB_TIMEOUT", "30")),
            max_retries=int(os.getenv("MYLIB_MAX_RETRIES", "3")),
        )

    @classmethod
    def from_file(cls, config_path: str) -> "LibraryConfig":
        """Load configuration from a YAML or JSON file.

        Args:
            config_path: Path to configuration file

        Returns:
            Loaded configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file format is invalid
        """
        import json
        from pathlib import Path

        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        if path.suffix == ".json":
            with open(path) as f:
                data = json.load(f)
        elif path.suffix in (".yaml", ".yml"):
            try:
                import yaml
            except ImportError:
                raise ImportError("PyYAML required for YAML config. Install with: pip install pyyaml")
            with open(path) as f:
                data = yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported config format: {path.suffix}")

        # Convert dict to config object
        return cls(**data)


# Pattern 2: Builder Pattern for Complex Configuration
# ======================================================

class ConfigBuilder:
    """Builder for constructing complex configurations.

    Allows gradual configuration with sensible defaults:

        config = (ConfigBuilder()
            .with_debug(True)
            .with_database("postgresql://localhost/mydb")
            .with_cache_ttl(7200)
            .build())
    """

    def __init__(self):
        """Initialize builder with defaults."""
        self._debug = False
        self._log_level = "INFO"
        self._cache_enabled = True
        self._cache_ttl = 3600
        self._db_config = DatabaseConfig()
        self._timeout = 30
        self._max_retries = 3

    def with_debug(self, debug: bool) -> "ConfigBuilder":
        """Enable/disable debug mode."""
        self._debug = debug
        return self

    def with_log_level(self, level: str) -> "ConfigBuilder":
        """Set logging level."""
        if level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            raise ValueError(f"Invalid log level: {level}")
        self._log_level = level
        return self

    def with_database(self, host: str, port: int = 5432, **kwargs) -> "ConfigBuilder":
        """Configure database connection."""
        self._db_config = DatabaseConfig(
            host=host,
            port=port,
            **kwargs
        )
        return self

    def with_cache(self, enabled: bool = True, ttl: int = 3600) -> "ConfigBuilder":
        """Configure caching."""
        self._cache_enabled = enabled
        self._cache_ttl = ttl
        return self

    def with_timeout(self, timeout: int) -> "ConfigBuilder":
        """Set operation timeout."""
        if timeout <= 0:
            raise ValueError(f"Timeout must be positive, got {timeout}")
        self._timeout = timeout
        return self

    def build(self) -> LibraryConfig:
        """Build the final configuration."""
        return LibraryConfig(
            debug=self._debug,
            log_level=self._log_level,
            cache_enabled=self._cache_enabled,
            cache_ttl=self._cache_ttl,
            database=self._db_config,
            timeout=self._timeout,
        )


# Pattern 3: Configuration with Optional Dependencies
# ====================================================

@dataclass
class OptionalFeaturesConfig:
    """Configuration for optional features.

    Only load dependencies if features are actually used.
    """

    enable_caching: bool = True
    cache_backend: str = "memory"  # "memory", "redis"
    enable_compression: bool = False
    compression_level: int = 6

    def get_cache_backend(self):
        """Lazy-load cache backend only if needed."""
        if not self.enable_caching:
            return None

        if self.cache_backend == "memory":
            return MemoryCache()
        elif self.cache_backend == "redis":
            try:
                import redis
            except ImportError:
                raise ImportError(
                    "Redis cache backend requires 'redis' package. "
                    "Install with: pip install redis"
                )
            return RedisCache()
        else:
            raise ValueError(f"Unknown cache backend: {self.cache_backend}")


class MemoryCache:
    """Simple in-memory cache."""

    pass


class RedisCache:
    """Redis-backed cache."""

    pass


# Pattern 4: Validation and Defaults
# ===================================

@dataclass
class APIConfig:
    """API configuration with validation.

    Demonstrates setting sensible defaults and validating
    configuration values.
    """

    api_key: str
    api_secret: str
    base_url: str = "https://api.example.com"
    timeout: int = 30
    max_connections: int = 100
    verify_ssl: bool = True

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.api_key:
            raise ValueError("api_key is required and cannot be empty")
        if not self.api_secret:
            raise ValueError("api_secret is required and cannot be empty")
        if not self.base_url:
            raise ValueError("base_url is required and cannot be empty")
        if self.timeout <= 0:
            raise ValueError(f"timeout must be positive, got {self.timeout}")
        if self.max_connections < 1:
            raise ValueError(f"max_connections must be at least 1, got {self.max_connections}")

    @classmethod
    def from_env(cls) -> "APIConfig":
        """Load API configuration from environment variables.

        Environment variables:
            MYLIB_API_KEY (required)
            MYLIB_API_SECRET (required)
            MYLIB_API_URL (optional, default: https://api.example.com)
            MYLIB_API_TIMEOUT (optional, default: 30)
            MYLIB_API_VERIFY_SSL (optional, default: true)
        """
        api_key = os.getenv("MYLIB_API_KEY")
        if not api_key:
            raise ValueError(
                "MYLIB_API_KEY environment variable is required. "
                "Set it with: export MYLIB_API_KEY=your_key"
            )

        api_secret = os.getenv("MYLIB_API_SECRET")
        if not api_secret:
            raise ValueError(
                "MYLIB_API_SECRET environment variable is required. "
                "Set it with: export MYLIB_API_SECRET=your_secret"
            )

        return cls(
            api_key=api_key,
            api_secret=api_secret,
            base_url=os.getenv("MYLIB_API_URL", "https://api.example.com"),
            timeout=int(os.getenv("MYLIB_API_TIMEOUT", "30")),
            verify_ssl=os.getenv("MYLIB_API_VERIFY_SSL", "true").lower() in ("1", "true", "yes"),
        )


# Usage Examples
# ==============

def example_dataclass_config():
    """Example: Create configuration with dataclass."""
    config = LibraryConfig(
        debug=True,
        log_level="DEBUG",
        database=DatabaseConfig(
            host="db.example.com",
            username="admin",
            password=os.getenv("DB_PASSWORD"),
        ),
        timeout=60,
    )
    print(f"Config: {config}")


def example_from_env():
    """Example: Load configuration from environment variables."""
    # Set environment variables first:
    # export MYLIB_DEBUG=1
    # export MYLIB_LOG_LEVEL=DEBUG
    # export MYLIB_DB_HOST=db.example.com

    config = LibraryConfig.from_env()
    print(f"Debug mode: {config.debug}")
    print(f"Database host: {config.database.host}")


def example_from_file():
    """Example: Load configuration from file."""
    # config.json:
    # {
    #   "debug": true,
    #   "log_level": "DEBUG",
    #   "database": {
    #     "host": "db.example.com",
    #     "password": "secret"
    #   }
    # }

    config = LibraryConfig.from_file("config.json")
    print(f"Config loaded from file: {config}")


def example_builder():
    """Example: Use builder pattern for fluent configuration."""
    config = (ConfigBuilder()
              .with_debug(True)
              .with_log_level("DEBUG")
              .with_database("db.example.com", port=5432, username="admin")
              .with_cache(enabled=True, ttl=7200)
              .with_timeout(60)
              .build())
    print(f"Config built with builder: {config}")


# Best Practices Summary
# ======================
"""
1. USE DATACLASSES FOR CONFIGURATION
   - Cleaner than writing __init__ manually
   - Type hints provide IDE support
   - Easy serialization/deserialization

2. PROVIDE MULTIPLE LOADING METHODS
   - from_env(): Load from environment variables
   - from_file(): Load from config files
   - Direct instantiation: Simple cases

3. VALIDATE IN __post_init__
   - Check required values
   - Validate ranges and constraints
   - Provide helpful error messages

4. USE SENSIBLE DEFAULTS
   - Default values prevent required arguments
   - Documents expected configuration
   - Simplifies common use cases

5. BUILDER PATTERN FOR COMPLEX CONFIGS
   - Fluent interface for readability
   - Gradual construction
   - Works well with optional features

6. NEVER HARDCODE CREDENTIALS
   - Use environment variables
   - Use config files (not in repo)
   - Document required env variables

7. LAZY LOAD OPTIONAL DEPENDENCIES
   - Only import when feature is used
   - Provide helpful error messages
   - Keep core library lightweight

8. CONSISTENT NAMING
   - Environment variables: MYLIB_FEATURE_SETTING
   - Config file keys: feature.setting
   - Python attributes: feature_setting (snake_case)
"""
