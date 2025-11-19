#!/bin/bash
# Convert PDF files to different formats
#
# This script demonstrates shell script support in skillkit.
# It reads JSON from stdin and performs format conversion.
#
# Environment variables available:
# - SKILL_NAME
# - SKILL_BASE_DIR
# - SKILL_VERSION
# - SKILLKIT_VERSION

# Read JSON input from stdin
read -r json_input

# Parse JSON using Python (for simplicity)
input_file=$(echo "$json_input" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('input_file', ''))")
output_format=$(echo "$json_input" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('output_format', 'txt'))")

# Validate input
if [ -z "$input_file" ]; then
    echo '{"error": "Missing required argument: input_file"}' >&2
    exit 1
fi

# Mock conversion (in real implementation, would use tools like pdftotext, pandoc, etc.)
output_file="${input_file%.pdf}.${output_format}"

# Output result
cat <<EOF
{
  "status": "success",
  "input_file": "$input_file",
  "output_file": "$output_file",
  "output_format": "$output_format",
  "message": "Converted $input_file to $output_format format",
  "environment": {
    "skill_name": "$SKILL_NAME",
    "skill_base_dir": "$SKILL_BASE_DIR",
    "skill_version": "$SKILL_VERSION",
    "skillkit_version": "$SKILLKIT_VERSION"
  }
}
EOF

exit 0
