# Implementation Plan: Script Execution Support

**Branch**: `001-script-execution` | **Date**: 2025-01-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-script-execution/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Enable skills to bundle and execute deterministic scripts (Python, Shell, JavaScript, Ruby, Perl) with security controls, timeout enforcement, and LangChain integration. Scripts are detected lazily during skill invocation and exposed as separate StructuredTools (e.g., "pdf-extractor.extract") alongside existing prompt-based tools. Arguments pass via JSON stdin, outputs capture to stdout/stderr, and security validates paths to prevent traversal attacks. Tool restriction enforcement requires "Bash" in allowed-tools.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.10+ (minimum for existing skillkit v0.3.0 compatibility)
**Primary Dependencies**: PyYAML 6.0+ (existing), aiofiles 23.0+ (existing), subprocess (stdlib), pathlib (stdlib)
**Storage**: Filesystem-based (scripts stored in skill directories: `scripts/` or skill root)
**Testing**: pytest 7.0+ with pytest-asyncio 0.21+ for async tests, pytest-cov 4.0+ for coverage
**Target Platform**: Cross-platform (Linux, macOS, Windows with consistent interpreter availability)
**Project Type**: Single library project (extending existing skillkit core)
**Performance Goals**: Script detection <10ms for 50 scripts; execution overhead <50ms for 95% of calls
**Constraints**: 10MB output limit per stream (stdout/stderr); 30s default timeout (max 600s); 5-level nested script directories
**Scale/Scope**: Support skills with up to 50 scripts; handle concurrent executions; maintain backward compatibility with v0.1/v0.2

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: ✅ PASS (Constitution file is template-only, no active principles to validate)

**Note**: Project constitution at `.specify/memory/constitution.md` contains only placeholder template. When constitution is ratified with concrete principles, this section will validate against those requirements.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/skillkit/
├── core/
│   ├── discovery.py          # Existing (will extend with script detection)
│   ├── parser.py              # Existing (no changes)
│   ├── models.py              # Existing (will add ScriptMetadata, ScriptExecutionResult)
│   ├── manager.py             # Existing (will add execute_skill_script method)
│   ├── processors.py          # Existing (no changes)
│   ├── exceptions.py          # Existing (will add script-specific exceptions)
│   ├── script_detector.py     # NEW - Script detection logic
│   └── script_executor.py     # NEW - Script execution with security controls
├── integrations/
│   └── langchain.py           # Existing (will extend with script tool generation)
└── __init__.py                # Existing (export new script classes)

tests/
├── test_script_detector.py    # NEW - Script detection tests
├── test_script_executor.py    # NEW - Script execution tests
├── test_manager.py            # Existing (extend with script execution tests)
├── test_langchain.py          # Existing (extend with script tool tests)
└── fixtures/
    └── skills/
        ├── script-skill/      # NEW - Test skill with various scripts
        │   ├── SKILL.md
        │   └── scripts/
        │       ├── extract.py
        │       ├── convert.sh
        │       └── utils/
        │           └── parser.py
        └── restricted-skill/  # NEW - Test tool restriction enforcement
            ├── SKILL.md (allowed-tools: Read, Write)
            └── scripts/
                └── blocked.py

examples/
├── script_execution.py        # NEW - Demonstrate script execution
└── skills/
    └── pdf-extractor/         # NEW - Real-world example skill
        ├── SKILL.md
        └── scripts/
            ├── extract.py
            ├── convert.sh
            └── parse.py
```

**Structure Decision**: Single library project (Option 1). This feature extends the existing skillkit core library with two new modules (`script_detector.py`, `script_executor.py`) and updates existing modules (`models.py`, `manager.py`, `exceptions.py`, `langchain.py`). Test structure mirrors source with new test files for script components.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**Status**: N/A (No constitution violations - constitution is template-only)
