---
name: restricted-skill
description: Test skill with tool restrictions (no Bash permission)
allowed-tools:
  - Read
  - Write
---

# Restricted Skill

This is a test skill used to verify tool restriction enforcement.

The skill has `allowed-tools` defined without 'Bash', so script execution should be blocked.

## Purpose

Verify that `ToolRestrictionError` is raised when attempting to execute scripts from a skill that doesn't have 'Bash' in its allowed-tools list.

## Expected Behavior

- Script detection should work normally (scripts are detected)
- Script execution should raise `ToolRestrictionError` with clear error message
- Error message should list the skill's allowed tools
