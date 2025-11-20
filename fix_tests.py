#!/usr/bin/env python3
"""Fix test_script_executor.py to use correct parameter names."""

import re

# Read the original test file
with open('tests/test_script_executor.py', 'r') as f:
    lines = f.readlines()

# Track which test methods need fixing
in_test_method = False
test_method_name = ""
fixed_lines = []
skip_until_blank = False

for i, line in enumerate(lines):
    # Skip malformed lines from previous fixes
    if skip_until_blank:
        if line.strip() == '' or line.startswith('    def ') or line.startswith('if __name__'):
            skip_until_blank = False
        else:
            continue

    # Detect test method starts
    if line.strip().startswith('def test_'):
        in_test_method = True
        test_method_name = line.split('def ')[1].split('(')[0]
        fixed_lines.append(line)
        continue

    # Skip malformed SkillMetadata creations
    if '),\n' in line and 'SkillMetadata(' in fixed_lines[-5:]:
        skip_until_blank = True
        # Remove the problematic SkillMetadata line
        while fixed_lines and 'SkillMetadata(' not in fixed_lines[-1]:
            fixed_lines.pop()
        if fixed_lines and 'SkillMetadata(' in fixed_lines[-1]:
            fixed_lines.pop()
        if fixed_lines and 'from skillkit.core.models import SkillMetadata' in fixed_lines[-1]:
            fixed_lines.pop()
        if fixed_lines and '# Create minimal skill metadata' in fixed_lines[-1]:
            fixed_lines.pop()
        continue

    fixed_lines.append(line)

# Write the fixed content
with open('tests/test_script_executor.py', 'w') as f:
    f.writelines(fixed_lines)

print(f"Fixed {len(fixed_lines)} lines")
