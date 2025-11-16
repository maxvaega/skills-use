"""Secure file path resolution for skill supporting files.

This module provides the FilePathResolver class for resolving relative file paths
within skill directories while preventing directory traversal attacks.
"""

import logging
from pathlib import Path

from .exceptions import PathSecurityError

logger = logging.getLogger(__name__)


class FilePathResolver:
    """Secure path resolution for skill supporting files.

    This class provides static methods to resolve relative file paths within
    a skill's base directory while preventing security vulnerabilities like
    directory traversal, symlink escape, and absolute path injection.

    Security Features:
    - Path traversal prevention using Path.resolve() + is_relative_to()
    - Symlink resolution and escape detection
    - Absolute path rejection
    - Detailed error logging for security violations

    Example:
        >>> base_dir = Path("/skills/my-skill")
        >>> # Valid path
        >>> path = FilePathResolver.resolve_path(base_dir, "scripts/helper.py")
        >>> print(path)
        /skills/my-skill/scripts/helper.py

        >>> # Invalid path traversal (blocked)
        >>> path = FilePathResolver.resolve_path(base_dir, "../../etc/passwd")
        Traceback (most recent call last):
            ...
        PathSecurityError: Path traversal attempt detected
    """

    @staticmethod
    def resolve_path(base_directory: Path, relative_path: str) -> Path:
        """Resolve relative path from skill base directory with security validation.

        This method resolves a relative file path within the skill's base directory
        while enforcing security constraints to prevent directory traversal and
        other path-based attacks.

        Security Validation:
        1. Base directory is resolved to canonical absolute path
        2. Relative path is joined to base directory
        3. Combined path is resolved (collapses .., resolves symlinks)
        4. Resolved path is validated to be within base directory tree
        5. Security violations raise PathSecurityError with ERROR logging

        Args:
            base_directory: Skill's base directory (must be absolute)
            relative_path: Path relative to base directory (e.g., "scripts/helper.py")

        Returns:
            Absolute Path object guaranteed to be within base_directory

        Raises:
            PathSecurityError: If path attempts directory traversal, uses absolute
                paths, or escapes base directory via symlinks

        Example:
            >>> base = Path("/skills/data-processor")
            >>> # Valid subdirectory access
            >>> FilePathResolver.resolve_path(base, "scripts/helper.py")
            PosixPath('/skills/data-processor/scripts/helper.py')

            >>> # Invalid traversal (blocked)
            >>> FilePathResolver.resolve_path(base, "../../../etc/passwd")
            Traceback (most recent call last):
                ...
            PathSecurityError: Path traversal attempt detected: '../../../etc/passwd'
                               resolves outside skill directory /skills/data-processor
        """
        # Normalize base directory to canonical absolute path
        base_dir_resolved = base_directory.resolve()

        # Join relative path to base and resolve to canonical path
        # This collapses .. sequences, resolves symlinks, and normalizes separators
        try:
            requested_path = (base_dir_resolved / relative_path).resolve()
        except (OSError, RuntimeError) as e:
            # Handle errors from resolve() (e.g., circular symlinks, permission errors)
            error_msg = (
                f"Failed to resolve path '{relative_path}' from base directory "
                f"{base_dir_resolved}: {e}"
            )
            logger.error(
                "Path resolution failed",
                extra={
                    "base_directory": str(base_dir_resolved),
                    "requested_path": relative_path,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise PathSecurityError(error_msg) from e

        # SECURITY: Validate resolved path is within base directory
        if not requested_path.is_relative_to(base_dir_resolved):
            error_msg = (
                f"Path traversal attempt detected: '{relative_path}' resolves "
                f"outside skill directory {base_dir_resolved}"
            )
            logger.error(
                "SECURITY VIOLATION: Path traversal attempt detected",
                extra={
                    "base_directory": str(base_dir_resolved),
                    "requested_path": relative_path,
                    "resolved_path": str(requested_path),
                    "violation_type": "path_traversal",
                },
            )
            raise PathSecurityError(error_msg)

        # Log successful resolution (debug level)
        logger.debug(
            "Path resolved successfully",
            extra={
                "base_directory": str(base_dir_resolved),
                "requested_path": relative_path,
                "resolved_path": str(requested_path),
            },
        )

        return requested_path
