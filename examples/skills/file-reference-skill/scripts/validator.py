"""Input validation utilities for file-reference-skill."""

from pathlib import Path


def validate_file_path(file_path: str) -> bool:
    """Validate that a file path exists and is readable.

    Args:
        file_path: Path to validate

    Returns:
        True if valid, False otherwise
    """
    path = Path(file_path)

    if not path.exists():
        print(f"Error: File does not exist: {file_path}")
        return False

    if not path.is_file():
        print(f"Error: Path is not a file: {file_path}")
        return False

    try:
        with open(path, 'r') as f:
            f.read(1)
        return True
    except PermissionError:
        print(f"Error: Permission denied reading file: {file_path}")
        return False
    except Exception as e:
        print(f"Error: Cannot read file: {file_path} ({e})")
        return False


def validate_csv_format(file_path: str) -> bool:
    """Validate that a file is in CSV format.

    Args:
        file_path: Path to CSV file

    Returns:
        True if valid CSV, False otherwise
    """
    if not validate_file_path(file_path):
        return False

    # Check file extension
    if not file_path.endswith('.csv'):
        print(f"Warning: File does not have .csv extension: {file_path}")

    # Check for CSV content (basic validation)
    with open(file_path, 'r') as f:
        first_line = f.readline()
        if ',' not in first_line:
            print(f"Warning: File may not be valid CSV (no commas found): {file_path}")
            return False

    return True
