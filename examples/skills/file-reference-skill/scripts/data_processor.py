"""Data processing script for file-reference-skill.

This script demonstrates how supporting files can be used within a skill.
"""

import sys
from pathlib import Path


def process_data(input_file: str, output_file: str) -> None:
    """Process data from input file and write to output file.

    Args:
        input_file: Path to input data file
        output_file: Path to output data file
    """
    print(f"Processing data from {input_file}")
    print(f"Output will be written to {output_file}")

    # Read input file
    try:
        with open(input_file, 'r') as f:
            data = f.read()
        print(f"Read {len(data)} bytes from input file")
    except FileNotFoundError:
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    # Process data (example: uppercase transformation)
    processed_data = data.upper()

    # Write output file
    with open(output_file, 'w') as f:
        f.write(processed_data)
    print(f"Wrote {len(processed_data)} bytes to output file")


def main() -> None:
    """Main entry point."""
    if len(sys.argv) != 3:
        print("Usage: data_processor.py <input_file> <output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    process_data(input_file, output_file)


if __name__ == "__main__":
    main()
