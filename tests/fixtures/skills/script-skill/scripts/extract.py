#!/usr/bin/env python3
"""Extract data from JSON input.

This script reads JSON from stdin, extracts specified fields,
and outputs the results.
"""
import sys
import json


def main():
    """Read JSON from stdin and extract data."""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        # Extract fields
        result = {
            "status": "success",
            "extracted": input_data.get("field", "default"),
            "count": len(str(input_data))
        }

        # Output JSON result
        print(json.dumps(result, indent=2))
        sys.exit(0)

    except Exception as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
