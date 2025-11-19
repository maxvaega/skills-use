#!/usr/bin/env python3
"""Test script that should be blocked by tool restrictions.

This script will not execute because the skill doesn't have Bash in allowed-tools.
"""
import json
import sys

# Read arguments from stdin
args = json.load(sys.stdin)

# Simple processing
result = {
    "status": "success",
    "message": "This should never be executed due to tool restrictions",
    "input": args
}

print(json.dumps(result))
