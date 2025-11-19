#!/usr/bin/env python3
"""Test script for reading JSON from stdin and writing to stdout.

This script validates JSON input/output handling.
"""
import sys
import json


def main():
    """Read JSON from stdin and write transformed output to stdout."""
    try:
        # Read and parse JSON from stdin
        data = json.load(sys.stdin)

        # Transform data
        output = {
            "status": "received",
            "input_keys": list(data.keys()),
            "message": data.get("message", "No message provided")
        }

        # Write JSON to stdout
        print(json.dumps(output, indent=2))

    except json.JSONDecodeError as e:
        sys.stderr.write(f"Invalid JSON: {e}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
