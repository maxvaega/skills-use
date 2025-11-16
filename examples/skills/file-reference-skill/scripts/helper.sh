#!/bin/bash
# Helper script for file-reference-skill

echo "File Reference Skill Helper Script"
echo "==================================="
echo ""
echo "This script demonstrates shell scripting support in skills."
echo ""
echo "Usage: ./helper.sh <command> [args...]"
echo ""

case "${1:-help}" in
    check)
        echo "Checking environment..."
        echo "Python version: $(python3 --version)"
        echo "Current directory: $(pwd)"
        echo "Script directory: $(dirname "$0")"
        ;;
    validate)
        if [ -z "$2" ]; then
            echo "Error: No file specified"
            exit 1
        fi
        echo "Validating file: $2"
        if [ -f "$2" ]; then
            echo "File exists: $2"
            echo "File size: $(wc -c < "$2") bytes"
        else
            echo "File not found: $2"
            exit 1
        fi
        ;;
    help|*)
        echo "Available commands:"
        echo "  check    - Check environment"
        echo "  validate <file> - Validate file exists"
        echo "  help     - Show this help message"
        ;;
esac
