# Skills-use: Product Requirements Document

**Version:** 1.2

**Date:** October 28, 2025

**Status:** Draft

**Owner:** Massimo Olivieri

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Goals & Non-Negotiables](#goals--non-negotiables)
3. [Core Concepts](#core-concepts)
4. [Requirements Summary & Prioritization](#requirements-summary--prioritization)
5. [Open Points](#open-points)
6. [Functional Requirements](#functional-requirements)
7. [Technical Specifications](#technical-specifications)
8. [Integration Requirements](#integration-requirements)
9. [Distribution & Deployment Requirements](#distribution--deployment-requirements)
10. [Error Handling](#error-handling)
11. [Testing Requirements](#testing-requirements)
12. [Success Criteria](#success-criteria)
13. [Out of Scope](#out-of-scope)
14. [References](#references)
15. [Appendix A: Example Skill](#appendix-a-example-skill)
16. [Appendix B: Example Plugin](#appendix-b-example-plugin)
17. [Appendix C: Implementation Phases](#appendix-c-implementation-phases)

---

## Executive Summary

### Purpose

This document specifies the requirements for **a Python library that implements Anthropic's Agent Skills functionality**, enabling LLM-powered agents to autonomously discover and utilize packaged expertise stored in structured directories. The library must:

- **be model-agnostic** usable with any LLM
- **be 100% compatible with existing Anthropic SKILL.md files** 
- integrate seamlessly with major agent frameworks (LangChain, Haystack, Google ADK)
- be usable without any agent framework

### What are Agent Skills?

Agent Skills are **self-contained directories containing instructions, scripts, and resources** that extend an agent's capabilities. Unlike traditional function calling where all tools are presented upfront, Skills implement **progressive disclosure**:

1. **Metadata Level**: Skill names and descriptions are available to the agent at startup
2. **Content Level**: Full instructions loaded only when the agent determines relevance
3. **Resource Level**: Supporting files accessed on-demand via file operations

Skills are **model-invoked** (the agent autonomously decides when to use them) rather than user-invoked (explicit commands).

### Key Insight: Why the Skill Tool Abstraction

While the conceptual model describes Claude "reading SKILL.md files via Bash tools," the actual implementation uses a **Skill tool abstraction** because:

- **Efficiency**: Avoids repeated file I/O operations
- **Metadata Pre-loading**: Enables Claude to evaluate all skills without loading full content
- **Clean Interface**: Provides structured skill invocation rather than manual file reading
- **Tool Restriction Enforcement**: Centralized control of allowed tools per skill

Both approaches achieve the same goal: **progressive disclosure** of skill information.

---

## Goals & Non-Negotiables

### Primary Goals

1. **Full Anthropic Compatibility**: Support all existing SKILL.md files without modification
2. **Framework Agnostic Core**: Pure Python implementation independent of any agent framework
3. **Multi-Framework Integration**: Provide adapters for LangChain, Haystack, Google ADK
4. **Progressive Disclosure**: Minimize context window usage through lazy loading
5. **Tool Restriction Enforcement**: Honor `allowed-tools` frontmatter for security

### Non-Negotiables

1. ✅ **MUST be 100% compatible with Anthropic SKILL.md format**
2. ✅ **MUST support all Anthropic-compatible skills without modification**
3. ✅ **MUST integrate with LangChain, Haystack, and Google ADK**
4. ✅ **MUST implement progressive disclosure (metadata → content → files)**
5. ✅ **MUST enforce tool restrictions specified in frontmatter**
6. ✅ **MUST support plugin directory structure**
7. ✅ **MUST provide both sync and async APIs**

### Non-Goals (Out of Scope)

- Marketplace/distribution infrastructure
- Usage analytics and telemetry
- Security auditing tools
- Cross-platform synchronization
- Skill dependency resolution
- Skill composition/chaining
- Visual skill editors
- Technical analysis (detailed in a separated document)

---

## Core Concepts

### 1. Skill Structure

A Skill is a directory containing:

```
skill-name/
├── SKILL.md              # Required: Core skill definition
├── reference.md          # Optional: Additional documentation
├── scripts/              # Optional: Executable scripts
│   └── helper.py
└── templates/            # Optional: Template files
    └── template.txt
```

### 2. SKILL.md Format

```markdown
---
name: lowercase-with-hyphens
description: Brief description of capability and when to use. Max 1024 chars.
allowed-tools: Read, Write, Grep, Glob, Bash
version: 1.0.0
model: inherit
disable-model-invocation: false
---

# Skill Instructions

Step-by-step instructions for the agent...

## Examples

Concrete examples of usage...
```

### 3. Discovery Sources

Skills are discovered from four configurable sources in priority order. See **FR-1.1** for complete specification.

**Quick Reference:**
1. **Project skills** (`./skills/` - primary default)
2. **Anthropic skills** (`./.claude/skills/` - optional, project-scoped)
3. **Plugin skills** (automatic via plugin discovery)
4. **Additional custom paths** (optional, user-specified)

### 4. Progressive Disclosure Pattern

```
┌─────────────────────────────────────────────────────────────┐
│ Level 1: Metadata (loaded at startup)                      │
│ - name: "pdf-extractor"                                    │
│ - description: "Extract text from PDFs..."                 │
│ - allowed-tools: ["Read", "Bash", "Write"]                 │
└─────────────────────────────────────────────────────────────┘
                          ↓ (agent determines relevance)
┌─────────────────────────────────────────────────────────────┐
│ Level 2: Full Content (loaded on invocation)               │
│ - Complete SKILL.md markdown content                       │
│ - Base directory context injected                          │
│ - $ARGUMENTS substitution performed                        │
└─────────────────────────────────────────────────────────────┘
                          ↓ (skill references files)
┌─────────────────────────────────────────────────────────────┐
│ Level 3: Referenced Files (loaded on demand)               │
│ - Agent uses Read tool to access supporting files          │
│ - Relative paths resolved from skill base directory        │
└─────────────────────────────────────────────────────────────┘
```

### 5. Tool Restriction Enforcement

When a skill specifies `allowed-tools`:

```yaml
allowed-tools: Read, Grep, Write
```

The agent framework MUST:

1. Parse the comma-separated tool list
2. Restrict the agent to ONLY those tools during skill execution
3. Block any attempts to use non-allowed tools
4. Restore previous tool access after skill completion

---

## MVP Strategy & Implementation Roadmap

### Phased Approach to Launch

This document defines a **phased implementation roadmap** designed to deliver a production-ready MVP in 8-12 weeks, followed by progressive feature expansion post-launch.

**Core Philosophy:**
- **Phase 1 (MVP)**: Implement progressive loading of skill metadata and content—the foundational concept of Agent Skills
- **Phase 2 (Complete)**: Add advanced features deferred from MVP (script execution, plugin support, tool restrictions)
- **Phase 3 (LangChain)**: Deep integration with the primary framework (LangChain) for production use
- **🚀 Launch v1.0**: Solid, focused release with one production-ready framework integration
- **Phase 4+ (Post-Launch)**: Additional framework integrations (LlamaIndex, CrewAI, Haystack, Google ADK) driven by user demand

**Prioritization Criteria:**
1. **Phase 1 Focus**: Core skill discovery, parsing, metadata management, and progressive loading
2. **Phase 2 Enhancement**: Features that broaden capability but aren't essential for basic functionality
3. **Phase 3 Production**: Deep integration with LangChain to ensure enterprise-grade quality
4. **Phase 4+ Expansion**: Additional frameworks selected based on real user demand and usage patterns

**Timeline to Launch:**
- Phase 1: 4-6 weeks
- Phase 2: 2-3 weeks
- Phase 3: 2-3 weeks
- **Total: 8-12 weeks to production v1.0**

---

## Requirements Summary & Prioritization

### Requirements Overview

This section provides a comprehensive overview of all requirements with brief descriptions and priority assignments.

#### Functional Requirements

- **FR-1: Skill Discovery** - Discover skills from personal, project, and plugin directories with robust error handling
- **FR-2: SKILL.md Parsing** - Parse SKILL.md files extracting YAML frontmatter and markdown content with validation
- **FR-3: Skill Metadata Management** - Manage lightweight skill metadata for efficient agent consumption
- **FR-4: Skill Invocation** - Load and prepare skill content with base directory context and argument substitution (MVP: simple string arguments)
- **FR-5: File Reference Resolution** - Enable agents to access supporting files within skill directories using relative paths
- **FR-6: Script Execution Support** - Support bundled executable scripts within skills for deterministic operations
- **FR-7: Plugin Integration** - Support Anthropic plugin structure with manifest parsing and multi-plugin management
- **FR-8: Error Handling & Logging** - Robust error handling with categorized errors and informative logging
- **FR-9: Advanced Argument Validation & Schemas** - (Future, v1.1+) Support typed argument schemas with validation and framework-specific schema generation (deferred per OP-2)

#### Technical Specifications

- **TS-1: File Format Specification** - Define SKILL.md structure, frontmatter fields, and validation rules
- **TS-2: Directory Structure Specifications** - Define flat, nested, and plugin directory structures
- **TS-3: Data Models** - Define core data models (SkillMetadata, SkillContent, SkillError, PluginManifest, etc.)
- **TS-4: Core Library Architecture** - Define framework-agnostic library architecture and module organization

#### Integration Requirements

- **IR-1: Framework-Agnostic Core** - Pure Python core with zero framework dependencies
- **IR-2: LangChain Integration** - Provide LangChain-compatible tools with restriction enforcement
- **IR-3: Haystack Integration** - Provide Haystack-compatible components for skill invocation
- **IR-4: Google ADK Integration** - Provide Google ADK-compatible function tools for skills
- **IR-5: LlamaIndex Integration** - Provide LlamaIndex-compatible FunctionTool instances for skill invocation
- **IR-6: CrewAI Integration** - Provide CrewAI-compatible BaseTool implementations for skill invocation

#### Distribution & Deployment Requirements

- **DR-1: Packaging Configuration** - Configure pyproject.toml with package metadata, dependencies, and build system
- **DR-2: PyPI Distribution** - Publish to PyPI with wheel and source distributions
- **DR-3: Documentation Infrastructure** - Sphinx-based documentation with ReadTheDocs hosting
- **DR-4: API Documentation** - Auto-generated API reference with comprehensive docstrings
- **DR-5: User Documentation** - Installation guides, tutorials, and framework-specific examples
- **DR-6: Versioning Strategy** - Semantic versioning with PEP 440 compliance
- **DR-7: Changelog Management** - Maintain detailed changelog following Keep a Changelog format
- **DR-8: CI/CD Pipeline** - Automated testing, linting, type checking, and publishing
- **DR-9: Python Version Support** - Support Python 3.8+ with multi-version testing
- **DR-10: Code Quality Standards** - Type hints, linting, formatting, and pre-commit hooks
- **DR-11: Security Requirements** - Path validation, sandboxing guidelines, and vulnerability management
- **DR-12: License & Legal** - Open-source license selection and compliance

#### Testing Requirements

- **TR-1: Unit Tests** - Comprehensive unit tests with 90%+ coverage
- **TR-2: Integration Tests** - Test framework integrations (LangChain, Haystack, Google ADK)
- **TR-3: Compatibility Tests** - Verify compatibility with official Anthropic skills and community plugins
- **TR-4: Performance Tests** - Ensure fast discovery (<100ms for 100 skills) and low invocation overhead (<10ms)

#### Error Handling Requirements

- **EH-1: Error Categories** - Define discovery, parsing, validation, and invocation error categories
- **EH-2: Error Messages** - Provide informative error messages with file paths and context
- **EH-3: Exception Hierarchy** - Define structured exception hierarchy for programmatic handling

### Priority Matrix

| Requirement ID | Requirement Name | Priority | Dependencies |
|----------------|------------------|----------|--------------|
| **FR-1** | Skill Discovery | P0 (Phase 1) | None |
| **FR-2** | SKILL.md Parsing | P0 (Phase 1) | None |
| **FR-3** | Skill Metadata Management | P0 (Phase 1) | FR-1, FR-2 |
| **FR-4** | Skill Invocation | P0 (Phase 1) | FR-2, FR-3 |
| **FR-5** | File Reference Resolution | P0 (Phase 1) | FR-4 |
| **FR-6** | Script Execution Support | P2 (Phase 2) | FR-4 |
| **FR-7** | Plugin Integration | P2 (Phase 2) | FR-1, FR-2 |
| **FR-8** | Error Handling & Logging | P0 (Phase 1) | All FR |
| **FR-9** | Advanced Argument Validation & Schemas | P3 (Future, v1.1+) | FR-4 |
| **TS-1** | File Format Specification | P0 (Phase 1) | None |
| **TS-2** | Directory Structure Specifications | P0 (Phase 1) | None |
| **TS-3** | Data Models | P0 (Phase 1) | TS-1, TS-2 |
| **TS-4** | Core Library Architecture | P0 (Phase 1) | None |
| **IR-1** | Framework-Agnostic Core | P0 (Phase 1) | All TS |
| **IR-2** | LangChain Integration | P3 (Phase 3) | IR-1 |
| **IR-3** | Haystack Integration | P4 (Phase 4+) | IR-1 |
| **IR-4** | Google ADK Integration | P4 (Phase 4+) | IR-1 |
| **IR-5** | LlamaIndex Integration | P4 (Phase 4+) | IR-1 |
| **IR-6** | CrewAI Integration | P4 (Phase 4+) | IR-1 |
| **DR-1** | Packaging Configuration | P0 (Phase 1) | None |
| **DR-2** | PyPI Distribution | P3 (Phase 3) | DR-1 |
| **DR-3** | Documentation Infrastructure | P0 (Phase 1) | None |
| **DR-4** | API Documentation | P0 (Phase 1) | DR-3, DR-10 |
| **DR-5** | User Documentation | P0 (Phase 1) | DR-3 |
| **DR-6** | Versioning Strategy | P0 (Phase 1) | DR-1 |
| **DR-7** | Changelog Management | P3 (Phase 3) | DR-6 |
| **DR-8** | CI/CD Pipeline | P0 (Phase 1) | All TR, DR-10 |
| **DR-9** | Python Version Support | P0 (Phase 1) | DR-1 |
| **DR-10** | Code Quality Standards | P0 (Phase 1) | None |
| **DR-11** | Security Requirements | P2 (Phase 2) | FR-5, FR-6 |
| **DR-12** | License & Legal | P0 (Phase 1) | None |
| **TR-1** | Unit Tests | P0 (Phase 1) | All FR, TS |
| **TR-2** | Integration Tests | P3 (Phase 3) | IR-2 |
| **TR-3** | Compatibility Tests | P2 (Phase 2) | FR-1 through FR-5 |
| **TR-4** | Performance Tests | P2 (Phase 2) | FR-1, FR-4 |
| **EH-1** | Error Categories | P0 (Phase 1) | None |
| **EH-2** | Error Messages | P0 (Phase 1) | EH-1 |
| **EH-3** | Exception Hierarchy | P0 (Phase 1) | EH-1 |

---

## Open Points

### Categorization Framework

Open points are categorized based on the phased implementation roadmap to clearly indicate which decisions block which phase:

- **Category A (Phase 1 Blocker)**: Decisions required before Phase 1 (MVP) implementation. Must be resolved immediately to unblock core development. These affect FR-1 through FR-5 scope and behavior.
- **Category B (Phase 2 Blocker)**: Decisions required before Phase 2 (Features) implementation. Can be deferred past Phase 1 launch but must be resolved before completing advanced features. These affect FR-6, FR-7, FR-4.3.
- **Category C (Phase 3 Blocker)**: Decisions required before Phase 3 (LangChain Integration) implementation. Can be deferred past Phase 2 but must be resolved before framework integration begins. These affect IR-2 and framework-specific work.
- **Category D (Post-Launch/Optional)**: Enhancements or refinements that don't block any phase. Can be addressed after v1.0 launch or deferred indefinitely based on feedback.

---

### OP-1: Directory Structure Configuration ✅ **RESOLVED**

---

### OP-2: Argument Schema Definition ✅ **RESOLVED (MVP → Deferred Feature)**

**Status**: RESOLVED - MVP uses simple approach, advanced schema support deferred to Phase 2+

**MVP Resolution (Phase 1 - v1.0)**:

The MVP uses **Option 3: No Schema** approach:
- Arguments are accepted as simple strings
- Passed to skills via `$ARGUMENTS` substitution placeholder
- Validation happens within skill content or bundled scripts
- No frontmatter schema definition required
- Maintains 100% Anthropic compatibility
- Minimal cognitive load for skill authors

**Implementation**: See FR-4.1 (MVP Argument Handling)

**Future Enhancement (Phase 2+ - v1.1+)**:

Advanced argument schemas will be supported in a future phase with the following rationale:
- MVP focuses on compatibility and simplicity
- Schema support adds minimal value for initial implementation
- Can be added non-breaking in v1.1+ without affecting existing skills
- Framework integrations can start with basic argument handling
- Allows more time to understand real-world usage patterns

**Future Schema Options** (to be detailed in v1.1 design document):

- **Option 1: YAML Frontmatter Schema** - Structured metadata in SKILL.md frontmatter
- **Option 2: JSON Schema in Frontmatter** - JSON Schema standard for argument validation
- **Option 3: LLM-Inferred Schema** - Auto-generate schema from skill instructions

**See Also**: FR-9 (Future: Advanced Argument Validation & Schemas) for deferred requirement details.

---

### OP-3: Skill Name Conflict Resolution ✅ **RESOLVED (integrated into FR-1.4)**

**Status**: RESOLVED - Implementation details integrated into FR-1.4

**Resolution Summary**:

Skill name conflicts are resolved using the directory search order established in OP-1:

**Priority Order (highest to lowest):**
1. **Project skills** (`./skills/` - primary default)
2. **Anthropic skills** (`./.claude/skills/` - optional, project-scoped)
3. **Plugin skills** (by plugin load order)
4. **Additional custom paths** (user-specified)

**Conflict Handling Rules**:
- **Within same source**: First discovered wins (filesystem order)
- **Across sources**: Priority order applies automatically
- **Plugin-to-plugin conflicts**: First loaded plugin wins, warning logged
- **Explicit qualification**: Users can use `plugin-name:skill-name` syntax for plugin skills

**Examples**:

```python
# Two skills named "data-processor"
# One in ./skills/data-processor/SKILL.md (project)
# One in plugin at data-processor:data-processor

manager = SkillManager()
skill = manager.get_skill("data-processor")  # Returns project version

# To get plugin version explicitly
plugin_skill = manager.get_skill("data-processor", plugin="data-processor")
# Or use fully qualified name syntax (if supported)
plugin_skill = manager.get_skill("data-processor:data-processor")
```

**Implementation Details**: See FR-1.4 for behavioral specification.

**Decision**: ✅ APPROVED - Proceed with priority order conflict resolution.

---

### OP-4: Tool Restriction Violation Behavior ⚠️ **Category B - Phase 2 Blocker**

**Status**: Open, deferred to Phase 2 (will not block Phase 1 MVP launch)

**Current State**: The PRD requires tool restriction enforcement but doesn't specify what happens when a skill attempts to use a disallowed tool. This is deferred to Phase 2 when FR-4.3 is implemented.

**Question**: What should happen when a skill tries to use a tool that's not in its `allowed-tools` list?

**Discussion Points**:
- **Option 1: Raise Exception and Halt**
  - Strict enforcement, security-focused
  - Clear error message with skill name, attempted tool, allowed tools
  - Execution stops immediately

- **Option 2: Log Warning and Continue**
  - Permissive approach, better for development
  - Risk: security policies can be bypassed
  - Not recommended for production

- **Option 3: Raise Exception with Override**
  - Default: raise exception
  - Allow `SkillManager(enforce_tool_restrictions=False)` for testing
  - Best of both worlds

**Recommended Resolution**: Option 3 (Exception with override)

**Behavioral Specification to Add to FR-4 (Phase 2):**
```markdown
### FR-4.3: Tool Restriction Violation Handling

When a skill attempts to use a tool not in its `allowed-tools` list:

1. **Default Behavior**: Raise `ToolRestrictionError` with message:
   "Tool '{tool_name}' not allowed for skill '{skill_name}'. Allowed tools: {allowed_tools}"

2. **Execution**: Halts immediately, no partial execution

3. **Logging**: ERROR level log entry created

4. **Override**: Set `SkillManager(enforce_tool_restrictions=False)` for testing/development

5. **Empty allowed-tools**: If field is missing/empty, all tools are allowed
```

**Why Deferred to Phase 2**:
- Phase 1 MVP does not enforce tool restrictions
- Tool restriction is primarily relevant for framework integrations (Phase 3 LangChain)
- Can be added in Phase 2 without affecting Phase 1 architecture
- Allows focus on core progressive loading in MVP

**Decision Required**: Approve recommended resolution before Phase 2 starts, or choose alternative approach.

---

### OP-5: $ARGUMENTS Substitution Edge Cases ✅ **RESOLVED**

**Status**: RESOLVED - Edge case behavior specified in FR-4.2

**Current State**: FR-4 describes basic `$ARGUMENTS` substitution but doesn't specify behavior for edge cases.

**Question**: How should the library handle edge cases in argument substitution?

**Edge Cases Needing Specification**:
1. Multiple `$ARGUMENTS` occurrences in content
2. Empty arguments provided
3. Literal text `$ARGUMENTS` (escaping)
4. No `$ARGUMENTS` placeholder in content

**Resolution (APPROVED):**

The following edge case behaviors have been approved and integrated into FR-4.2:

1. **Placeholder Syntax**: `$ARGUMENTS` (case-sensitive, exact match)
2. **Multiple Occurrences**: ALL instances of `$ARGUMENTS` replaced with the same value
3. **No Placeholder**: If arguments provided, append `\n\nARGUMENTS: {args}` to content
4. **Empty Arguments**: If placeholder exists, replace `$ARGUMENTS` with empty string
5. **Escaping**: Reserved for v1.1+ (use `$$ARGUMENTS` for literal text)
6. **Case Sensitivity**: Only exact `$ARGUMENTS` is replaced (not `$arguments` or `$Arguments`)

**Decision**: ✅ APPROVED - Proceed with specified edge case handling in FR-4.2.

---

### OP-6: Framework Version Compatibility Policy ⚠️ **Category C - Phase 3 Blocker**

**Status**: Open, deferred to Phase 3 (will not block Phase 1 or Phase 2, needed for LangChain integration)

**Current State**: Integration requirements specify which frameworks to support but don't specify version ranges. This is deferred to Phase 3 when LangChain integration (IR-2) is implemented.

**Question**: Which versions of each framework should be supported and tested?

**Impact**:
- Affects dependency specifications in pyproject.toml
- Affects CI/CD testing matrix
- Affects user expectations and support commitments
- Phase 3 focus: LangChain version support only

**Discussion Points**:
- Testing against only latest versions is risky (users may have older versions)
- Testing against too many versions is expensive (CI time/complexity)
- Some frameworks have breaking changes between major versions

**Recommended Resolution - Phase 3 LangChain Focus:**

```markdown
### DR-9.4: LangChain Version Support Matrix (Phase 3)

**Phase 3 (v1.0 Launch):**
- LangChain: Define version range (e.g., ≥ 0.1.0, < 3.0.0)
- Testing Strategy: MINIMUM and LATEST versions in CI
- Document any breaking changes in framework APIs

**Phase 4+ (Additional Frameworks):**
- When adding LlamaIndex, CrewAI, Haystack, Google ADK support
- Define version ranges for each framework independently
- Update CI matrix accordingly

**Version Pinning Philosophy:**
- Core library: No framework dependencies
- Integration modules: Relaxed version constraints (allow minor updates)
- Example: `langchain >= 0.1.0, < 3.0.0`

**Deprecation Policy:**
- Minimum 1 minor version warning before dropping framework version support
- Document in CHANGELOG and migration guide
```

**Why Deferred to Phase 3**:
- Only LangChain needs version support decision in Phase 3
- Phase 4+ frameworks (LlamaIndex, CrewAI, Haystack, Google ADK) can determine their version constraints when implemented
- Reduces initial decision complexity

**Decision Required**: Approve LangChain version range before Phase 3 implementation starts, or adjust based on current LangChain stability.

---

### OP-7: Model-Agnostic Scope Clarification ✅ **Category A - RESOLVED**

**Status**: RESOLVED
**Decision**: Adopted Approach C - Core standard with optional Claude extensions
**Target Audience**: Skills library for multi-LLM frameworks (Claude, GPT, Gemini, local LLMs, etc.)

---

### OP-7.1: Cross-LLM Model Selection Strategy (TBD) ⏳ **Category B - NICE-TO-HAVE**

**Status**: Open for future design
**Blocked by**: None (OP-7 resolved; this is optional enhancement)
**Related to**: OP-7 (model-agnostic design)

**Problem Statement**

The `model` field in SKILL.md currently contains Claude-specific values:
```yaml
model: inherit | sonnet | opus | claude-3-5-sonnet-20241022
```

For true multi-LLM compatibility, we need a framework-agnostic way to express model preferences that other frameworks can map to their own capabilities.

**Recommended Approach - Option C: Keep Current + Add Framework Hints**

```yaml
---
name: my-skill
description: Skill description
model: sonnet                    # Claude-specific (primary)

# NEW: Framework hints for cross-LLM mapping
model-hints:
  gpt: gpt-4-turbo
  gemini: gemini-2-0-pro
  default: gpt-4-turbo           # Fallback for unmapped frameworks
---
```

**Framework Implementation**

**Claude Framework:**
- Use `model` field value directly (existing behavior)
- Ignore `model-hints` section

**Other LLM Frameworks:**
- Check `model-hints` for framework-specific mapping
- If found: Use mapped model
- If not found: Use `default` from model-hints
- If `default` missing: Use framework defaults

**Example Implementations**

**GPT Framework:**
```python
# Pseudocode
if "gpt" in skill.model_hints:
    model_id = skill.model_hints["gpt"]
else:
    model_id = skill.model_hints.get("default", self.default_model)
```

**Gemini Framework:**
```python
# Pseudocode
if "gemini" in skill.model_hints:
    model_id = skill.model_hints["gemini"]
else:
    model_id = skill.model_hints.get("default", self.default_model)
```

**Benefits**

✅ Backward compatible (no breaking changes to existing SKILL.md files)
✅ Skill authors can express cross-LLM preferences
✅ Frameworks have clear fallback strategy
✅ No new parsing logic needed (YAML syntax)
✅ Works with existing CLI analysis implementation

**Non-Breaking Nature**

- Existing `model` field continues to work for Claude
- `model-hints` is optional (completely ignored if missing)
- Frameworks using current approach continue working unchanged
- Skill discovery/parsing unchanged

**Decision Required**

1. Approve Option C or select alternative from previous discussion
2. When to implement (Phase 1, Phase 2, or post-launch)
3. Framework rollout order

**Target Resolution**: Separate design document after core standard (OP-7) is validated with at least 2 non-Claude LLM frameworks.

---

### OP-8: Edge Case Behavior Documentation 📋 **Category B - SHOULD CLARIFY**

**Current State**: Common edge cases in file parsing and discovery are not documented.

**Question**: What should the expected behavior be for various edge cases?

**Impact**: Medium - Reduces ambiguity for implementers and sets user expectations

**Edge Cases to Document**:

**File Format:**
- Empty SKILL.md file → `SkillParsingError` (no frontmatter)
- Frontmatter only, no content → Valid skill with empty content
- Content only, no frontmatter → `SkillValidationError` (missing required fields)
- Multiple frontmatter blocks → Use first block, log warning about subsequent blocks
- Malformed UTF-8 encoding → `SkillParsingError` with encoding information

**Discovery:**
- Permission denied on skill directory → Log warning, continue with other sources
- Circular symlinks in skill directories → Detect and skip with warning
- SKILL.md is a directory (not a file) → Skip with warning
- Skill name contains `:` character → `SkillValidationError` (reserved for plugin prefix)

**Recommended Resolution**: Add these behaviors to FR-1 (Discovery) and FR-2 (Parsing) sections.

**Decision Required**: Approve addition or defer to implementation phase.

---

### OP-9: Framework Validation & Testing Criteria 📋 **Category C - DEFER TO TECHNICAL**

**Current State**: The PRD specifies testing requirements (TR-1 through TR-4) but lacks detailed criteria for validating framework integrations.

**Question**: What specific validation criteria and test suites are needed to confirm a framework integration is production-ready?

**Information Missing**:

**1. Framework Compatibility Validation**
- Which skill categories must be tested per framework?
- How to validate tool restriction enforcement per framework?
- Performance baselines per framework (response time, memory, throughput)?
- Error handling consistency across frameworks?

**2. Integration Acceptance Criteria**
- Minimum test coverage per integration (unit + integration)?
- Compatibility matrix testing (Python versions, framework versions, OS)?
- Real-world scenario testing (complex skills, multi-step workflows)?
- Documentation completeness requirements?

**3. Regression Test Suite**
- Baseline test cases that must always pass?
- Critical path scenarios per framework?
- Breaking change detection strategy?

**4. Release Readiness Checklist**
- Pre-release validation steps?
- Smoke test suite for CI/CD gate?
- Version compatibility matrix testing?

**Deferred Approach**

This is **implementation-level detail** appropriately deferred to the technical design phase. The core PRD has sufficient testing requirements (TR-1-4) to proceed. During implementation planning, create a companion **Framework Integration Testing Guide** documenting:

- Detailed test cases per framework
- Validation checklist for new integrations
- Regression test suite
- Release readiness criteria
- Continuous validation strategy

**Document Location**: `TECHNICAL_ANALYSIS.md` section on Testing & Validation

**Decision Required**: Confirm deferral to technical design phase or add specific criteria to PRD.

---

### Summary of Open Points Status

| ID | Open Point | Category | Status | Blocking |
|----|-----------|----------|--------|----------|
| OP-1 | Directory Structure | A (Phase 1) | ✅ **RESOLVED** | None |
| OP-2 | Argument Schema | A (Phase 1) | ✅ **RESOLVED (Deferred to v1.1)** | None |
| OP-3 | Name Conflicts | A (Phase 1) | ✅ **RESOLVED** | None |
| OP-4 | Tool Restriction Violations | B (Phase 2) | ⏳ Pending | Phase 2 start |
| OP-5 | $ARGUMENTS Edge Cases | A (Phase 1) | ✅ **RESOLVED** | None |
| OP-6 | Framework Versions | C (Phase 3) | ⏳ Pending | Phase 3 start |
| OP-7 | Model-Agnostic Scope | A (Phase 1) | ✅ **RESOLVED** | None |
| OP-7.1 | Cross-LLM Model Selection | D (Post-Launch) | ⏳ TBD | None |
| OP-8 | Edge Case Behaviors | D (Post-Launch) | ⏳ Deferred | None |
| OP-9 | Framework Validation Criteria | D (Post-Launch) | ✅ **DEFER TO TECHNICAL** | None |

**Summary by Phase**:
- **Phase 1 Blockers (Category A)**: 0 items - ✅ **ALL RESOLVED - PHASE 1 UNBLOCKED**
- **Phase 2 Blockers (Category B)**: 1 item (**OP-4** - Pending) - Resolve before Phase 2 starts
- **Phase 3 Blockers (Category C)**: 1 item (**OP-6** - Pending) - Resolve before Phase 3 starts
- **Resolved**: OP-1 ✅, OP-2 ✅, OP-3 ✅, OP-5 ✅, OP-7 ✅, OP-9 ✅
- **Deferred**: OP-7.1, OP-8 (post-launch or optional)

**Critical Path**: ✅ **Phase 1 is now unblocked and ready to start!**
- OP-4 resolution needed ~week 6-7 (before Phase 2 starts)
- OP-6 resolution needed ~week 9-10 (before Phase 3 starts)

**Next Steps**:
1. **✅ COMPLETED**: OP-5 ($ARGUMENTS edge cases) - RESOLVED
2. **Week 7**: Resolve OP-4 (tool restriction behavior)
3. **Week 9**: Resolve OP-6 (LangChain version support)

---

## Functional Requirements

### FR-1: Skill Discovery

**Description:** The library must discover skills from multiple configurable sources and load their metadata.

**Requirements:**

1.1. **Default Directory Scanning (Search Order)**

Primary discovery follows this priority order (OP-1 resolution):

1. **Project Skills** (primary default): `./skills/` - Scans project-local skills directory
2. **Anthropic Skills** (optional, project-scoped): `./.claude/skills/` - For Anthropic Claude Code compatibility
3. **Plugin Skills**: Automatically discovered within plugin directories
4. **Additional Custom Paths** (optional): User-specified directories via `additional_search_paths`

**Configuration**:
- `./skills/` is enabled by default; can be disabled with `project_skill_dir=None`
- All other directories are optional and require explicit configuration
- Anthropic workflows remain fully supported through `./.claude/skills/` configuration

**Directory Structure Support**:
- Flat structure (root `SKILL.md`): `./skills/skill-name/SKILL.md`
- Nested structure (subdirectories): `./skills/group-one/skill-name/SKILL.md`
- Both structures can coexist in same directory

1.2. **Plugin Support**

- Read `.claude-plugin/plugin.json` manifest (Anthropic plugin format)
- Support `skills` field (string or array) for additional skill directories within plugins
- Skill naming: `{plugin-name}:{skill-directory-name}`
- Default plugin skill location: `<plugin-root>/skills/`
- Support additional directories specified in plugin.json `skills` field

1.3. **File Detection**

- Case-insensitive SKILL.md detection (`SKILL.md`, `skill.md`, `Skill.md`)
- Validate YAML frontmatter presence (must have required fields)
- Detect supporting files in skill directory (scripts/, templates/, etc.)
- Handle symbolic links gracefully (resolve and check within allowed directories)

1.4. **Skill Name Conflict Resolution (OP-3)**

When multiple skills have the same name:
- **Within same source**: First discovered wins (filesystem order)
- **Across sources**: Priority order applies (project > anthropic > plugins > additional paths)
- **Plugin-to-plugin conflicts**: First loaded plugin wins, warning logged
- **Disambiguation**: Users can use fully qualified names `plugin-name:skill-name` for plugins

1.5. **Error Handling**

- Continue processing other skills if one fails to load
- Log errors with file path and error details
- Return both successful skills and error list
- Handle gracefully: missing directories, permission denied, invalid YAML, missing required fields

**Acceptance Criteria:**

- ✅ Discovers skills from `./skills/` by default
- ✅ Supports optional Anthropic and personal directory configuration
- ✅ Handles missing directories gracefully without errors
- ✅ Supports plugin manifest configuration
- ✅ Logs errors without stopping discovery
- ✅ Respects directory search order for name conflict resolution
- ✅ Supports both flat and nested skill structures

---

### FR-2: SKILL.md Parsing

**Description:** Parse SKILL.md files and extract frontmatter metadata and content.

**Requirements:**

2.1. **Frontmatter Parsing**

- Extract YAML frontmatter between `---` delimiters
- Validate required fields: `name`, `description`
- Parse optional fields: `allowed-tools`, `version`, `model`, `disable-model-invocation`
- Handle missing or malformed frontmatter

2.2. **Content Extraction**

- Extract markdown content after frontmatter
- Preserve formatting (whitespace, code blocks, etc.)
- Support empty content sections

2.3. **Field Validation**

| Field                      | Type    | Constraints                                       | Required |
| -------------------------- | ------- | ------------------------------------------------- | -------- |
| `name`                     | string  | Lowercase letters, numbers, hyphens; max 64 chars | Yes      |
| `description`              | string  | Max 1024 characters                               | Yes      |
| `allowed-tools`            | string  | Comma-separated tool names                        | No       |
| `version`                  | string  | Semantic version (e.g., "1.0.0")                  | No       |
| `model`                    | string  | "inherit", "sonnet", "opus", or model ID          | No       |
| `disable-model-invocation` | boolean | true/false                                        | No       |

**Note on Model-Agnosticity:** The `model` field contains Claude-specific identifiers and should be treated as optional metadata by non-Claude implementations. This ensures the library remains model-agnostic and compatible with any LLM.

2.4. **Tool List Parsing**

- Parse `allowed-tools: "Read, Write, Grep"` → `["Read", "Write", "Grep"]`
- Strip whitespace from tool names
- Support empty/missing allowed-tools (no restrictions)

**Acceptance Criteria:**

- ✅ Parses valid SKILL.md files correctly
- ✅ Validates all frontmatter fields
- ✅ Returns structured metadata object
- ✅ Handles malformed YAML with clear errors

---

### FR-3: Skill Metadata Management

**Description:** Manage skill metadata for agent consumption without loading full content.

**Requirements:**

3.1. **Metadata Structure**

- Store lightweight skill metadata (name, description, allowed-tools, etc.)
- Include file paths for lazy loading
- Track skill source (personal, project, plugin)

3.2. **Metadata Access**

- Provide list of all available skills
- Filter skills by source, name, or description keywords
- Fast lookup by skill name

3.3. **Lazy Loading**

- Load only metadata at initialization
- Defer full content loading until skill invocation
- Cache loaded content for repeated use

**Acceptance Criteria:**

- ✅ Metadata loading is fast (<100ms for 100 skills)
- ✅ Full content loaded only on demand
- ✅ Metadata includes all fields needed for agent decision-making

---

### FR-4: Skill Invocation

**Description:** Load and prepare skill content for agent execution.

**Requirements:**

4.1. **Content Loading**

- Load complete SKILL.md content
- Inject base directory context: `Base directory for this skill: {baseDir}`
- Prepend base directory line to content

4.2. **Argument Substitution (MVP)**

**Basic Behavior:**
- Support `$ARGUMENTS` placeholder in skill content
- Replace `$ARGUMENTS` with provided arguments (simple string substitution)
- **MVP Note:** Arguments are handled as simple strings without validation or typing (see OP-2). Advanced schema-based validation is planned for v1.1+ (see FR-9)

**Detailed Substitution Rules (OP-5 Resolution):**

1. **Placeholder Syntax**: `$ARGUMENTS` (case-sensitive, exact match)

2. **Multiple Occurrences**: ALL instances of `$ARGUMENTS` replaced with the same value
   - Example:
     - Content: `"Run script with $ARGUMENTS and save to $ARGUMENTS.out"`
     - Args: `"file.pdf"`
     - Result: `"Run script with file.pdf and save to file.pdf.out"`

3. **No Placeholder**:
   - If arguments provided: Append `\n\nARGUMENTS: {args}` to content
   - If arguments empty: No modification

4. **Empty Arguments**:
   - If placeholder exists: Replace `$ARGUMENTS` with empty string
   - If no placeholder: No modification

5. **Escaping**: Reserved for v1.1+ (use `$$ARGUMENTS` for literal text)

6. **Case Sensitivity**: Only exact `$ARGUMENTS` is replaced (not `$arguments` or `$Arguments`)

4.3. **Tool Restriction Application**

- Parse `allowed-tools` from frontmatter
- Provide tool allowlist to agent framework
- Framework must enforce restrictions during execution

4.4. **Return Format**

- Return processed skill content as text
- Include tool restrictions in metadata
- Provide base directory for file resolution

**Example:**

```python
# Skill content before invocation:
"""
---
name: pdf-extractor
description: Extract text from PDFs
allowed-tools: Read, Bash, Write
---

Use the extraction script with: $ARGUMENTS
"""

# After invocation with args="invoice.pdf":
"""
Base directory for this skill: /home/user/.claude/skills/pdf-extractor

Use the extraction script with: invoice.pdf
"""
```

**Acceptance Criteria:**

- ✅ Base directory context injected
- ✅ Arguments substituted correctly
- ✅ Tool restrictions returned with content
- ✅ Original file unchanged

---

### FR-5: File Reference Resolution

**Description:** Enable agents to access supporting files within skill directories.

**Requirements:**

5.1. **Base Directory Context**

- Provide skill base directory to agent
- Support relative path resolution
- Example: `reference.md` resolves to `{baseDir}/reference.md`

5.2. **File Access**

- Agent uses standard Read tool with resolved paths
- No special file access API needed (uses existing tools)

5.3. **Path Resolution**

- Resolve relative paths from skill base directory
- Support subdirectories (e.g., `scripts/helper.py`)
- Validate paths stay within skill directory (security)

**Acceptance Criteria:**

- ✅ Agent can read skill supporting files
- ✅ Relative paths resolved correctly
- ✅ Paths validated to prevent directory traversal

---

### FR-6: Script Execution Support

**Description:** Enable skills to bundle executable scripts for deterministic operations.

**Requirements:**

6.1. **Script Detection**

- Identify executable files in skill directory
- Common locations: `scripts/`, root directory
- Common extensions: `.py`, `.sh`, `.js`

6.2. **Execution Context**

- Scripts executed with skill base directory as working directory
- Environment variables include skill metadata
- Stdout/stderr captured and returned to agent

6.3. **Security Considerations**

- Scripts run with same permissions as agent process
- No automatic sandboxing (responsibility of agent framework)
- Skill `allowed-tools` should include `Bash` for script execution

**Acceptance Criteria:**

- ✅ Agent can execute skill scripts via Bash tool
- ✅ Working directory set to skill base directory
- ✅ Script output captured and returned

---

### FR-7: Plugin Integration

**Description:** Support Anthropic plugin structure for bundled skills.

**Requirements:**

7.1. **Plugin Manifest Parsing**

- Read `.claude-plugin/plugin.json`
- Extract plugin metadata: `name`, `version`, `description`, `author`
- Parse `skills` field (string or array)

7.2. **Plugin Manifest Schema**

```json
{
  "name": "demo-plugin",
  "description": "A demo plugin with skills",
  "version": "1.0.0",
  "author": {
    "name": "Author Name"
  },
  "skills": ["custom-skills-dir"]  // Optional: additional skill directories
}
```

7.3. **Skill Discovery from Plugins**

- Default: Scan `{plugin-root}/skills/` directory
- Additional: Scan directories specified in `skills` field
- Skill naming: `{plugin-name}:{skill-directory-name}`

7.4. **Multi-Plugin Support**

- Load skills from multiple plugins
- Handle skill name collisions (plugin prefix prevents conflicts)
- Aggregate errors across plugins

**Acceptance Criteria:**

- ✅ Loads skills from plugin directories
- ✅ Parses plugin.json correctly
- ✅ Supports additional skill directories
- ✅ Names skills with plugin prefix

---

### FR-8: Error Handling & Logging

**Description:** Robust error handling with informative logging.

**Requirements:**

8.1. **Error Categories**

- **Discovery Errors**: Directory not found, permission denied
- **Parsing Errors**: Invalid YAML, missing required fields
- **Validation Errors**: Field constraint violations
- **Invocation Errors**: Skill not found, file read errors

8.2. **Error Structure**

```python
@dataclass
class SkillError:
    type: Literal["discovery", "parsing", "validation", "invocation"]
    skill_path: str
    message: str
    details: Optional[dict] = None
```

8.3. **Logging Levels**

- **DEBUG**: File paths, parsing steps
- **INFO**: Skills discovered, skills loaded
- **WARNING**: Invalid skills, missing files
- **ERROR**: Critical failures, parsing errors

8.4. **Error Recovery**

- Continue processing after individual skill errors
- Return partial results with error list
- Don't raise exceptions for individual skill failures

**Acceptance Criteria:**

- ✅ All errors categorized and logged
- ✅ Processing continues after errors
- ✅ Error messages include file paths and details
- ✅ Structured error objects for programmatic handling

---

### FR-9: Advanced Argument Validation & Schemas

**Status:** Future Requirement (v1.1+) - Deferred per OP-2

**Description:** Support typed argument schemas with validation and framework-specific schema generation for enhanced type safety and improved LLM guidance.

**Rationale for Deferral:**

- MVP prioritizes compatibility and simplicity
- Current simple string argument approach is sufficient for initial release
- Allows time to understand real-world usage patterns and integration feedback
- Can be added non-breaking in v1.1+ without affecting existing skills
- Reduces scope for Phase 1 implementation

**Requirements (To be finalized in v1.1 design document):**

9.1. **Argument Schema Definition**

- Define approach for skill authors to specify argument structure
- Options to be evaluated:
  - YAML frontmatter schema with type information
  - JSON Schema in frontmatter for complex validation
  - Auto-generation from skill description via LLM
- Support optional vs required arguments
- Support default values
- Support argument descriptions and constraints

9.2. **Framework-Specific Schema Generation**

- LangChain: Generate StructuredTool parameter schemas from skill schemas
- LlamaIndex: Generate Annotated type hints for enhanced argument descriptions
- CrewAI: Generate Pydantic BaseModel for args_schema from skill definitions
- Haystack: Generate ComponentTool input schemas
- Google ADK: Generate function parameter definitions

9.3. **Validation**

- Validate arguments against defined schemas before invocation
- Provide clear error messages for validation failures
- Optional strict vs permissive validation modes
- Support for custom validation rules in skill scripts

9.4. **Backward Compatibility**

- MVP skills (without schemas) continue to work unchanged
- Old skills migrate to new schema format optionally
- No breaking changes to existing SKILL.md files
- Schema field completely optional

**Dependencies:** FR-4 (uses argument substitution infrastructure)

**Note:** This requirement is intentionally left open and high-level. Specific design will be developed during v1.1 planning phase based on:
- Real-world feedback from MVP users
- Framework integration patterns and constraints
- Schema validation library availability
- Community requests and use cases

---

## Technical Specifications

### TS-1: File Format Specification

#### SKILL.md Structure

```markdown
---
# Required fields
name: skill-name-kebab-case
description: |
  Brief description of what this skill does and when to use it.
  Maximum 1024 characters.

# Optional fields
allowed-tools: Read, Write, Grep, Glob, Bash
version: 1.0.0
model: inherit
disable-model-invocation: false
---

# Skill Content (Markdown)

Instructions for the agent...
```

#### Frontmatter Field Specifications

**name**

- Type: `string`
- Pattern: `^[a-z0-9-]+$` (lowercase letters, numbers, hyphens only)
- Max Length: 64 characters
- Required: ✅
- Example: `"pdf-form-filler"`

**description**

- Type: `string`
- Max Length: 1024 characters
- Required: ✅
- Best Practice: Include both capability ("Extract text from PDFs") and trigger keywords ("Use when working with PDF files")
- Example: `"Extract text and tables from PDFs and fill out form fields. Use when working with PDF files or document forms."`

**allowed-tools**

- Type: `string` (comma-separated)
- Pattern: Tool names separated by commas and optional spaces
- Required: ❌
- Default: No restrictions (all tools allowed)
- Example: `"Read, Write, Grep, Glob, Bash"`
- Common Patterns:
    - Read-only: `"Read, Grep, Glob"`
    - File manipulation: `"Read, Write, Edit"`
    - Script execution: `"Read, Bash, Write"`

**version**

- Type: `string`
- Pattern: Semantic versioning `X.Y.Z`
- Required: ❌
- Example: `"1.0.0"`, `"2.1.3"`

**model**

- Type: `string`
- Enum: `"inherit"`, `"sonnet"`, `"opus"`, or model ID
- Required: ❌
- Default: `"inherit"` (use parent agent's model)
- Example: `"claude-sonnet-4-5-20250929"`
- Note: This field contains Claude-specific model identifiers. Non-Claude implementations should treat this as optional metadata and can safely ignore it to maintain model-agnosticity

**disable-model-invocation**

- Type: `boolean`
- Required: ❌
- Default: `false`
- Use Case: For skills that only provide reference information without LLM processing
- Example: `true`

---

### TS-2: Directory Structure Specifications

Based on OP-1 resolution, the library supports multiple configurable directory structures:

#### 1. Project Skills Structure (Primary Default)

**Default Location**: `./skills/` (project root)

**Flat Structure (Root SKILL.md)**:
```
./skills/
└── skill-name/
    └── SKILL.md
```

**Nested Structure (Subdirectories)**:
```
./skills/
├── skill-one/
│   └── SKILL.md
├── skill-two/
│   ├── SKILL.md
│   ├── reference.md
│   └── scripts/
│       └── helper.py
└── group-one/
    ├── skill-three/
    │   └── SKILL.md
    └── skill-four/
        └── SKILL.md
```

**Skill Names**:
- Flat: `skill-name`
- Nested: `skill-one`, `skill-two`, `group-one:skill-three` (if using subgroups)

**Note**: Both flat and nested structures can coexist in the same `./skills/` directory.

#### 2. Anthropic Claude Code Structure (Optional, Configurable)

**Optional Location** (requires explicit configuration):
- Project-scoped: `./.claude/skills/` - For Anthropic Claude Code project-level compatibility

**Using Anthropic Skills**:

Users with existing Anthropic skills can configure access:

```python
# Option A: Use project Claude Config directory
manager = SkillManager(
    project_skill_dir=Path("./.claude/skills/")  # Override default
)

# Option B: Copy Anthropic skills to project directory
# cp -r ./.claude/skills/* ./skills/
manager = SkillManager()  # Uses ./skills/ (default)
```

#### 3. Plugin Structure (Automatic Discovery)

**Plugin Root Format**:
```
my-plugin/
├── .claude-plugin/
│   └── plugin.json
├── commands/              # Optional: Slash commands
│   └── greet.md
├── skills/                # Default plugin skill directory
│   ├── skill-one/
│   │   └── SKILL.md
│   └── skill-two/
│       └── SKILL.md
└── custom-skills/         # Additional directory (if specified in manifest)
    └── skill-three/
        └── SKILL.md
```

**Skill Names**:
- Default: `my-plugin:skill-one`, `my-plugin:skill-two`
- Additional: `my-plugin:skill-three`

**Plugin Configuration** (in `.claude-plugin/plugin.json`):
```json
{
  "name": "my-plugin",
  "skills": ["skills", "custom-skills"]  // Additional skill directories
}
```

#### 4. Supporting Files Structure

All skill directories support the same supporting file structure:

```
./skills/my-skill/
├── SKILL.md                    # Required
├── reference.md                # Optional: Additional documentation
├── docs/                       # Optional: Documentation files
│   ├── advanced.md
│   └── examples.md
├── scripts/                    # Optional: Executable scripts
│   ├── extract.py
│   ├── transform.sh
│   └── process.js
├── templates/                  # Optional: Template files
│   ├── template.jinja
│   └── config.yaml
├── data/                       # Optional: Static data files
│   ├── sample.json
│   └── reference.csv
└── README.md                   # Optional: Skill-specific readme
```

**File Resolution**:
- Relative paths in skill instructions resolve from skill base directory
- Example: `reference.md` → `./skills/my-skill/reference.md`
- Example: `scripts/extract.py` → `./skills/my-skill/scripts/extract.py`
- Path traversal prevention: paths must stay within skill directory

#### 5. Directory Discovery Priority (OP-1 Resolution)

**Search Order**:
1. Project Skills: `./skills/` (primary, always scanned by default)
2. Anthropic Skills: `./.claude/skills/` (optional, user-configured)
3. Plugin Skills: `<plugin-root>/skills/` (automatic via plugin discovery)
4. Additional Paths: User-specified via `additional_search_paths`

**Configuration Example**:
```python
manager = SkillManager(
    project_skill_dir=Path("./skills/"),                          # Primary (1)
    anthropic_config_dir=Path("./.claude/skills/"),               # Optional (2)
    plugin_dirs=[Path("./plugins/my-plugin/")],                   # Optional (3)
    additional_search_paths=[Path("./custom/skills/")]            # Optional (4)
)
```

---

### TS-3: Data Models

```python
from dataclasses import dataclass
from typing import Optional, Literal
from pathlib import Path

@dataclass
class SkillMetadata:
    """Lightweight skill metadata for agent consumption."""

    # Required fields
    name: str  # Unique identifier (includes plugin prefix if from plugin)
    description: str

    # Optional fields
    allowed_tools: Optional[list[str]] = None
    version: Optional[str] = None
    model: Optional[str] = None
    disable_model_invocation: bool = False

    # Internal fields
    file_path: Path  # Path to SKILL.md
    base_dir: Path  # Skill base directory
    source: Literal["personal", "project", "plugin"]  # Discovery source
    plugin_name: Optional[str] = None  # If from plugin


@dataclass
class SkillContent:
    """Full skill content loaded on invocation."""

    metadata: SkillMetadata
    content: str  # Full markdown content (excluding frontmatter)
    processed_content: str  # Content with base dir and args injected


@dataclass
class SkillError:
    """Error encountered during skill processing."""

    type: Literal["discovery", "parsing", "validation", "invocation"]
    skill_path: str
    message: str
    details: Optional[dict] = None


@dataclass
class PluginManifest:
    """Plugin manifest from plugin.json."""

    name: str
    description: str
    version: str
    author: dict  # {"name": "...", "email": "...", "url": "..."}
    skills: Optional[list[str] | str] = None  # Additional skill directories


@dataclass
class SkillDiscoveryResult:
    """Result of skill discovery operation."""

    skills: list[SkillMetadata]  # Successfully loaded skills
    errors: list[SkillError]  # Errors encountered
```

---

### TS-4: Core Library Architecture

```
skills-use/
├── __init__.py              # Public API
├── core/
│   ├── __init__.py
│   ├── discovery.py         # Skill discovery logic
│   ├── parser.py            # SKILL.md parsing
│   ├── manager.py           # Skill lifecycle management
│   └── plugin.py            # Plugin manifest handling
├── integrations/
│   ├── __init__.py
│   ├── langchain.py         # LangChain integration
│   ├── haystack.py          # Haystack integration
│   └── google_adk.py        # Google ADK integration
├── models.py                # Data models
├── errors.py                # Exception classes
└── utils.py                 # Utility functions
```

---

## Integration Requirements

### IR-1: Framework-Agnostic Core

**Requirement:** The core library must have ZERO dependencies on any agent framework.

**Architecture:**

```
┌─────────────────────────────────────────────────┐
│           Agent Framework Layer                 │
│  (LangChain, Haystack, Google ADK, etc.)       │
└─────────────────────────────────────────────────┘
                      ↓ uses
┌─────────────────────────────────────────────────┐
│         Integration Adapters Layer              │
│  (langchain.py, haystack.py, google_adk.py)    │
└─────────────────────────────────────────────────┘
                      ↓ uses
┌─────────────────────────────────────────────────┐
│          Core Skills Library                    │
│  (discovery, parsing, management - pure Python) │
└─────────────────────────────────────────────────┘
```

**Benefits:**

- Use skills without any framework
- Add new framework integrations easily
- Test core logic in isolation
- Minimal dependencies

---

### IR-2: LangChain Integration

**Description:** Provide LangChain-compatible tools for skill invocation.

**Requirements:**

2.1. **Tool Creation (MVP)**

- Create `StructuredTool` or `BaseTool` for each skill
- Tool name = skill name
- Tool description = skill description
- Tool input schema = simple string argument (MVP - see OP-2)

2.2. **Tool Restriction Enforcement**

- Use LangChain's tool filtering/restriction API
- Apply during skill execution
- Restore after skill completion

2.3. **Integration Pattern**

- Provide adapter class that converts skills to LangChain tools
- Support standard LangChain agent patterns (AgentExecutor, etc.)
- Enable seamless integration with existing LangChain workflows

2.4. **Async Support**

- Support both sync (`invoke`) and async (`ainvoke`) methods
- Use `StructuredTool.from_function` with both implementations

**Acceptance Criteria:**

- ✅ Skills appear as LangChain tools
- ✅ Tool restrictions enforced
- ✅ Supports sync and async execution
- ✅ Integrates with standard LangChain agents

---

### IR-3: Haystack Integration

**Description:** Provide Haystack-compatible components for skill invocation.

**Requirements:**

3.1. **ComponentTool Creation**

- Create custom Haystack component for each skill
- Component input: skill arguments
- Component output: skill execution result

3.2. **Pipeline Integration**

- Skills usable in Haystack pipelines
- Support agent-based and pipeline-based workflows

3.3. **Integration Pattern**

- Provide adapter class that converts skills to Haystack ComponentTools
- Support standard Haystack agent patterns
- Enable integration with Haystack pipelines and workflows

**Acceptance Criteria:**

- ✅ Skills work as Haystack ComponentTools
- ✅ Integrates with Haystack agents
- ✅ Tool restrictions enforced

---

### IR-4: Google ADK Integration

**Description:** Provide Google ADK-compatible function tools for skill invocation.

**Requirements:**

4.1. **Function Tool Creation**

- Convert skills to ADK function tools
- Use Python function definitions
- Auto-generate function signatures from skill metadata

4.2. **Integration Pattern**

- Provide adapter class that converts skills to Google ADK function tools
- Support standard ADK agent patterns
- Enable seamless integration with Google ADK workflows

**Acceptance Criteria:**

- ✅ Skills work as ADK function tools
- ✅ Integrates with ADK agents
- ✅ Tool restrictions enforced

---

### IR-5: LlamaIndex Integration

**Description:** Provide LlamaIndex-compatible tools for skill invocation.

LlamaIndex is the leading framework for building LLM-powered agents over data, designed to rapidly accelerate time-to-production of GenAI applications. It provides developer-first abstractions optimized for agents, RAG (Retrieval-Augmented Generation), and custom workflows. LlamaIndex features a minimal generic tool interface that requires a `__call__` method for execution and metadata including name and description. The framework supports multiple tool creation approaches including FunctionTool (for converting user-defined functions with automatic schema inference), QueryEngineTool (for wrapping existing query engines), and community-contributed ToolSpecs from LlamaHub. Both synchronous and asynchronous function tools are supported, with agents like ReActAgent and FunctionAgent consuming tools through clearly defined interfaces.

**Requirements:**

5.1. **FunctionTool Creation (MVP)**

- Convert skills to LlamaIndex FunctionTool instances
- Use skill name as tool name
- Use skill description as tool description
- Accept skill arguments as simple string parameters (MVP - see OP-2)
- Implement both `_run` and `_arun` methods for sync/async execution

5.2. **Tool Metadata**

- Provide detailed tool descriptions to guide LLM tool selection
- Include skill base directory context in tool metadata
- Support `return_direct` parameter for skills that should bypass agent interpretation
- *Future: Annotated types for enhanced argument descriptions (see FR-9 for future schema support)*

5.3. **Agent Integration**

- Support ReActAgent and FunctionAgent patterns
- Enable skills to be passed as tools during agent initialization
- Support tool composition (skills calling other skills if needed)
- Integrate with LlamaIndex's agent execution flow

5.4. **Tool Restriction Enforcement**

- Parse `allowed-tools` from skill frontmatter
- Implement tool filtering mechanism for agent execution
- Restrict available tools during skill execution based on frontmatter
- Restore full tool access after skill completion

5.5. **Async Support**

- Implement both synchronous and asynchronous tool execution
- Support `ainvoke` pattern for async agent workflows
- Handle async file operations and script execution

**Acceptance Criteria:**

- ✅ Skills work as LlamaIndex FunctionTool instances
- ✅ Integrates with ReActAgent and FunctionAgent
- ✅ Tool restrictions enforced during execution
- ✅ Supports both sync and async execution patterns
- ✅ Tool metadata properly formatted for LLM consumption

---

### IR-6: CrewAI Integration

**Description:** Provide CrewAI-compatible tools for skill invocation.

CrewAI is a lean, lightning-fast Python framework built entirely from scratch for orchestrating role-playing, autonomous AI agents. Designed for intelligent multi-agent collaboration, CrewAI enables agents to work together seamlessly on complex tasks. The framework provides two primary tool creation approaches: the `@tool` decorator for simple function-based tools, and BaseTool subclassing for more advanced implementations with input validation via Pydantic schemas. CrewAI offers 30+ pre-built tools for search, file operations, code analysis, web scraping, and media processing. The framework automatically handles execution of both synchronous and asynchronous tools, with agents accessing tools through a `tools` parameter during instantiation. CrewAI's flexible architecture works effortlessly with Python's extensive library ecosystem and supports integration with external services and APIs.

**Requirements:**

6.1. **BaseTool Implementation (MVP)**

- Create BaseTool subclass for each skill
- Define `name` attribute from skill name
- Define `description` attribute from skill description
- Accept skill arguments as simple string parameters (MVP - see OP-2)
- Implement `_run` method containing skill invocation logic

6.2. **Decorator-Based Tool Creation (MVP)**

- Provide optional `@tool` decorator pattern for simpler skill integration
- Auto-generate tool name and description from skill metadata
- Accept simple string arguments for MVP
- Enable quick skill prototyping and testing
- *Future: Support typed argument schemas based on skill requirements (see FR-9)*

6.3. **Agent Integration**

- Enable skills to be assigned to agents via `tools` parameter
- Support role-based agent workflows with skill assignment
- Integrate with CrewAI's task delegation and collaboration patterns
- Support `allow_delegation` control for skill execution scope

6.4. **Tool Restriction Enforcement**

- Parse `allowed-tools` from skill frontmatter
- Filter available tools during skill execution
- Implement tool access control at agent level
- Restore full tool access after skill completion

6.5. **Async Support**

- Implement asynchronous tool execution for non-blocking operations
- Support async file I/O and network requests within skills
- Enable async script execution for long-running operations
- Integrate with CrewAI's async agent execution flow

**Acceptance Criteria:**

- ✅ Skills work as CrewAI BaseTool instances
- ✅ Supports both decorator and class-based tool creation
- ✅ Integrates with CrewAI agents and crews
- ✅ Tool restrictions enforced during execution
- ✅ Supports both sync and async execution patterns
- ✅ Compatible with CrewAI's multi-agent collaboration features

---

## Distribution & Deployment Requirements

### DR-1: Packaging Configuration

**Description:** Configure modern Python packaging using pyproject.toml for distribution.

**Requirements:**

1.1. **pyproject.toml Structure**

- Use `[build-system]` table with modern build backend (setuptools, hatchling, or flit)
- Define `[project]` table with package metadata (name, version, description, authors, etc.)
- Specify Python version compatibility (e.g., `requires-python = ">=3.8"`)
- Define dependencies with appropriate version constraints

1.2. **Package Metadata**

- Package name following PyPI naming conventions
- Single source of truth for version (e.g., `__version__` in `__init__.py`)
- Rich description with keywords for discoverability
- Project URLs (homepage, documentation, repository, issues)
- License specification using SPDX identifiers
- Classifiers for Python versions, development status, audience

1.3. **Dependency Organization**

- Minimal core dependencies (framework-agnostic)
- Optional dependencies organized by integration:
  - `[langchain]` for LangChain integration
  - `[haystack]` for Haystack integration
  - `[llamaindex]` for LlamaIndex integration
  - `[crewai]` for CrewAI integration
  - `[all]` for all integrations
  - `[dev]` for development tools

1.4. **Source Layout**

- Use `src/` layout for better packaging isolation
- Proper `__init__.py` files with version and public API exports
- Clear module organization matching architecture (core, integrations, models, errors, utils)

**Acceptance Criteria:**

- ✅ Valid pyproject.toml conforming to PEP 621
- ✅ Package installable with `pip install skills-use`
- ✅ Optional dependencies installable with extras (e.g., `pip install skills-use[langchain]`)
- ✅ Version automatically synchronized across package

---

### DR-2: PyPI Distribution

**Description:** Publish the library to PyPI for easy installation.

**Requirements:**

2.1. **Build Artifacts**

- Generate wheel distribution (.whl) for fast installation
- Generate source distribution (.tar.gz) for compatibility
- Include all necessary files (code, README, LICENSE, etc.)
- Exclude development files (.git, tests, docs build artifacts)

2.2. **PyPI Publishing**

- Register package on PyPI with unique name
- Upload distributions using secure token authentication
- Provide rich PyPI project page with formatted README
- Include project links and classifiers for discoverability

2.3. **Version Management**

- Automated version bumping tied to git tags
- Pre-release versions supported (alpha, beta, rc)
- Clear version history on PyPI

**Acceptance Criteria:**

- ✅ Package available on PyPI
- ✅ Installable via `pip install skills-use`
- ✅ PyPI page displays formatted README and metadata
- ✅ Multiple versions available with clear release history

---

### DR-3: Documentation Infrastructure

**Description:** Establish Sphinx-based documentation hosted on ReadTheDocs.

**Requirements:**

3.1. **Sphinx Configuration**

- Initialize Sphinx documentation in `docs/` directory
- Configure theme (e.g., sphinx-rtd-theme, furo)
- Enable autodoc extension for API reference generation
- Configure napoleon or numpydoc for docstring parsing
- Support both reStructuredText and Markdown (via myst-parser)

3.2. **ReadTheDocs Integration**

- Configure `.readthedocs.yaml` for build settings
- Automatic builds on commit to main branch and tags
- Version selector for multiple documentation versions
- Search functionality enabled

3.3. **Documentation Structure**

- Landing page with project overview
- Installation instructions
- Quick start guide
- User guides organized by topic
- API reference (auto-generated)
- Framework integration guides
- Examples and tutorials

**Acceptance Criteria:**

- ✅ Documentation builds successfully on ReadTheDocs
- ✅ Auto-updates on new commits and releases
- ✅ Supports multiple versions (latest, stable, specific versions)
- ✅ Mobile-responsive and accessible

---

### DR-4: API Documentation

**Description:** Comprehensive auto-generated API reference documentation.

**Requirements:**

4.1. **Docstring Standards**

- All public classes, functions, and methods have docstrings
- Use NumPy or Google docstring format consistently
- Include parameter types, return types, and exceptions
- Provide usage examples in docstrings where helpful
- Type hints match docstring documentation

4.2. **API Reference Generation**

- Use Sphinx autodoc to generate API reference from code
- Organize by module (core, integrations, models, errors, utils)
- Include class hierarchy and inheritance information
- Show method signatures with type hints
- Cross-reference related classes and functions

4.3. **API Coverage**

- Document all public APIs (classes, functions, methods, attributes)
- Mark private/internal APIs clearly (underscore prefix)
- Include module-level documentation explaining purpose
- Document exceptions and error conditions

**Acceptance Criteria:**

- ✅ 100% of public API documented with docstrings
- ✅ API reference auto-generated and up-to-date
- ✅ Docstrings include parameters, returns, raises, and examples
- ✅ Type hints present for all function signatures

---

### DR-5: User Documentation

**Description:** Comprehensive user-facing documentation for library usage.

**Requirements:**

5.1. **Getting Started**

- Installation instructions (pip, from source)
- Basic usage example (minimal working code)
- Core concepts explanation (skills, metadata, invocation)
- Quick start tutorial (15-minute walkthrough)

5.2. **User Guides**

- Creating custom skills guide
- Skill directory structure explanation
- SKILL.md format reference
- Plugin development guide
- Framework integration guides:
  - Using with LangChain
  - Using with Haystack
  - Using with LlamaIndex
  - Using with CrewAI
  - Using without any framework

5.3. **Examples & Tutorials**

- Real-world usage examples
- Code snippets for common scenarios
- Jupyter notebooks demonstrating features
- Sample skills repository

5.4. **Troubleshooting**

- Common issues and solutions
- Debugging tips
- FAQ section
- Error message explanations

**Acceptance Criteria:**

- ✅ Complete installation and quick start guides
- ✅ Framework-specific integration documentation
- ✅ At least 5 practical examples/tutorials
- ✅ Troubleshooting section with common issues

---

### DR-6: Versioning Strategy

**Description:** Implement semantic versioning with PEP 440 compliance.

**Requirements:**

6.1. **Semantic Versioning**

- Follow SemVer specification (MAJOR.MINOR.PATCH)
- MAJOR: Breaking changes to public API
- MINOR: New features, backwards-compatible
- PATCH: Bug fixes, backwards-compatible
- Pre-release versions: `1.0.0a1` (alpha), `1.0.0b1` (beta), `1.0.0rc1` (release candidate)

6.2. **PEP 440 Compliance**

- Version identifiers conform to PEP 440
- Support version specifiers for dependencies
- Proper ordering of pre-release versions
- Compatible with pip version resolution

6.3. **Version Source**

- Single source of truth for version
- Options: `__version__` in `__init__.py`, pyproject.toml, or dynamic from git tags
- Accessible via `skills-use.__version__`
- Displayed in documentation and CLI tools

6.4. **Version Policy**

- Document versioning policy in documentation
- Deprecation warnings before breaking changes (minimum 1 minor version)
- Support policy (which versions receive bug fixes)
- Migration guides for major version upgrades

**Acceptance Criteria:**

- ✅ All releases follow semantic versioning
- ✅ Version identifiers PEP 440 compliant
- ✅ Version accessible programmatically
- ✅ Documented versioning and deprecation policy

---

### DR-7: Changelog Management

**Description:** Maintain detailed changelog following Keep a Changelog format.

**Requirements:**

7.1. **CHANGELOG.md Structure**

- Follow Keep a Changelog format
- Sections: Added, Changed, Deprecated, Removed, Fixed, Security
- Unreleased section for tracking upcoming changes
- Each version with release date
- Links to version comparison on GitHub

7.2. **Changelog Content**

- Document all user-facing changes
- Include breaking changes prominently
- Reference related issues/PRs
- Provide context for major changes
- Include migration instructions for breaking changes

7.3. **Changelog Automation**

- Update changelog before each release
- Generate release notes from changelog
- Validate changelog format in CI

**Acceptance Criteria:**

- ✅ CHANGELOG.md present and up-to-date
- ✅ All releases documented with categorized changes
- ✅ Breaking changes clearly marked
- ✅ Links to version diffs and related issues

---

### DR-8: CI/CD Pipeline

**Description:** Automated continuous integration and deployment pipeline.

**Requirements:**

8.1. **Continuous Integration**

- Automated testing on every PR and push
- Test matrix:
  - Python versions: 3.10, 3.11, 3.12
  - Operating systems: Ubuntu, macOS, Windows
  - Optional: Test with minimum vs latest dependencies
- Linting with ruff or flake8
- Type checking with mypy
- Code formatting validation with black or ruff format
- Security scanning (e.g., bandit, safety)

8.2. **Coverage Reporting**

- Generate coverage reports with pytest-cov
- Upload coverage to Codecov or Coveralls
- Display coverage badge in README
- Fail CI if coverage drops below threshold (e.g., 90%)
- Track coverage trends over time

8.3. **Continuous Deployment**

- Automated publishing to PyPI on version tags
- Build and publish documentation to ReadTheDocs on release
- Create GitHub releases with changelog excerpt
- Automated changelog updates (optional)

8.4. **Quality Gates**

- All tests must pass
- Coverage threshold met
- No linting errors
- Type checking passes
- Security checks pass

**Acceptance Criteria:**

- ✅ CI runs on all PRs and commits
- ✅ Tests run on multiple Python versions and OSes
- ✅ Coverage tracked and displayed
- ✅ Automated PyPI publishing on tags
- ✅ All quality gates enforced

---

### DR-9: Python Version Support

**Description:** Define and test Python version compatibility.

**Requirements:**

9.1. **Minimum Python Version**

- Support Python 3.8+ (or specify minimum based on dependency requirements)
- Document minimum version in README and documentation
- Declare in pyproject.toml `requires-python` field
- Use type hints compatible with minimum version

9.2. **Multi-Version Testing**

- Test on all supported Python versions in CI
- Test on Python 3.10, 3.11, 3.12
- Consider testing on pre-release Python versions (optional)

9.3. **Version Deprecation Policy**

- Clearly communicate when dropping Python version support
- Follow NEP 29 or similar dropping schedule
- Provide deprecation warnings in advance
- Document in changelog and migration guide

**Acceptance Criteria:**

- ✅ Minimum Python version clearly documented
- ✅ All supported versions tested in CI
- ✅ Type hints compatible with minimum version
- ✅ Version deprecation policy documented

---

### DR-10: Code Quality Standards

**Description:** Enforce code quality through tooling and standards.

**Requirements:**

10.1. **Type Hints**

- Full type hints on all public APIs
- Type hints on internal functions (encouraged)
- Use modern type hint syntax (e.g., `list[str]` instead of `List[str]` when Python 3.9+)
- Type aliases for complex types
- Generic types where appropriate

10.2. **Type Checking**

- Use mypy for static type checking
- Configure mypy in strict or nearly-strict mode
- Check types in CI pipeline
- No type errors in main branch

10.3. **Linting**

- Use ruff (modern, fast) or flake8 for linting
- Configure sensible rules (e.g., line length, complexity)
- Fail CI on linting errors
- Consistent code style across codebase

10.4. **Formatting**

- Use black or ruff format for consistent code formatting
- Configure in pyproject.toml
- Validate formatting in CI
- Provide pre-commit hooks for local formatting

10.5. **Pre-Commit Hooks**

- Configure pre-commit with hooks for:
  - Code formatting (black/ruff)
  - Linting (ruff/flake8)
  - Type checking (mypy)
  - Import sorting (isort or ruff)
  - Trailing whitespace, end-of-file fixes
- Document pre-commit setup in CONTRIBUTING.md

10.6. **Docstring Coverage**

- Aim for 95%+ docstring coverage on public APIs
- Use tools like interrogate to measure coverage
- Include in CI quality checks

**Acceptance Criteria:**

- ✅ All public APIs have type hints
- ✅ mypy passes in strict mode
- ✅ Linting passes with zero errors
- ✅ Code formatted consistently
- ✅ Pre-commit hooks configured and documented
- ✅ >95% docstring coverage on public APIs

---

### DR-11: Security Requirements

**Description:** Implement security best practices and vulnerability management.

**Requirements:**

11.1. **Path Traversal Prevention**

- Validate all file paths stay within skill directories
- Use `Path.resolve()` to normalize paths
- Check resolved paths against allowed base directories
- Reject paths with `..` components that escape skill directory
- Log security violations

11.2. **Script Execution Security**

- Document that scripts run with agent process permissions (no sandboxing)
- Recommend skills use `allowed-tools: Bash` explicitly
- Provide security guidelines for skill authors
- Warn users about untrusted skills
- Document best practices for reviewing skills before use

11.3. **Dependency Security**

- Regular dependency security audits
- Automated vulnerability scanning (e.g., pip-audit, safety)
- Dependabot or similar for automated updates
- Pin dependencies with known vulnerabilities
- Document security update process

11.4. **Security Policy**

- Create SECURITY.md with vulnerability reporting process
- Define supported versions for security updates
- Provide security contact email
- Document responsible disclosure policy

**Acceptance Criteria:**

- ✅ Path traversal prevention implemented and tested
- ✅ Security guidelines documented
- ✅ SECURITY.md present with reporting process
- ✅ Automated dependency vulnerability scanning
- ✅ Security considerations documented in user guide

---

### DR-12: License & Legal

**Description:** Define licensing and ensure legal compliance.

**Requirements:**

12.1. **License Selection**

- Choose appropriate open-source license (MIT, Apache 2.0, BSD, etc.)
- Include LICENSE file in repository root
- Specify license in pyproject.toml
- Display license prominently in documentation

12.2. **License Compliance**

- Ensure chosen license compatible with dependencies
- Document third-party licenses if required
- Include license headers in source files (optional, depends on license)
- Provide NOTICE file if required by license (e.g., Apache 2.0)

12.3. **Copyright Notice**

- Include copyright notice in LICENSE
- Update copyright year annually
- Attribute contributors appropriately

12.4. **Contributor License Agreement**

- Define contribution terms in CONTRIBUTING.md
- Clarify that contributions are under project license
- Consider DCO (Developer Certificate of Origin) if needed

**Acceptance Criteria:**

- ✅ LICENSE file present with chosen license
- ✅ License specified in pyproject.toml and documentation
- ✅ Third-party licenses documented if applicable
- ✅ Contribution terms clear in CONTRIBUTING.md

---

## Error Handling

### EH-1: Error Categories

| Category       | Description                            | Recovery Strategy                         |
| -------------- | -------------------------------------- | ----------------------------------------- |
| **Discovery**  | Directory not found, permission denied | Log warning, continue with other sources  |
| **Parsing**    | Invalid YAML, missing fields           | Log error, skip skill, continue discovery |
| **Validation** | Field constraint violations            | Log error, skip skill, continue discovery |
| **Invocation** | Skill not found, file read error       | Raise exception, halt invocation          |

### EH-2: Error Messages

**Good Error Messages:**

```
❌ Bad:  "Error parsing skill"
✅ Good: "Failed to parse SKILL.md: Invalid YAML frontmatter at /path/to/skill/SKILL.md:3 - missing required field 'description'"

❌ Bad:  "Skill not found"
✅ Good: "Skill 'pdf-extractor' not found. Available skills: ['data-processor', 'web-scraper', ...]"

❌ Bad:  "Tool restriction error"
✅ Good: "Tool 'Bash' not allowed for skill 'pdf-extractor'. Allowed tools: ['Read', 'Write', 'Grep']"
```

### EH-3: Exception Hierarchy

```python
class SkillException(Exception):
    """Base exception for all skill errors."""
    pass


class SkillDiscoveryError(SkillException):
    """Error during skill discovery."""
    pass


class SkillParsingError(SkillException):
    """Error parsing SKILL.md file."""
    pass


class SkillValidationError(SkillException):
    """Error validating skill metadata."""
    pass


class SkillInvocationError(SkillException):
    """Error invoking skill."""
    pass


class ToolRestrictionError(SkillException):
    """Tool restriction violation."""
    pass
```

---

## Testing Requirements

### TR-1: Unit Tests

**Test Categories:**

**Coverage Target:** 90%+

1. **Discovery Tests**

   - Discover from personal directory
   - Discover from project directory
   - Discover from plugin directory
   - Handle missing directories
   - Handle invalid plugin manifests
1. **Parsing Tests**

   - Parse valid SKILL.md
   - Parse with all optional fields
   - Handle missing frontmatter
   - Handle invalid YAML
   - Handle missing required fields
   - Validate field constraints
1. **Invocation Tests**

   - Load full content
   - Inject base directory
   - Substitute $ARGUMENTS
   - Append arguments without placeholder
   - Handle missing skill
1. **Plugin Tests**

   - Load plugin manifest
   - Discover from default skills directory
   - Discover from additional directories
   - Handle invalid manifest
1. **Tool Restriction Tests**

   - Parse allowed-tools field
   - Apply tool restrictions
   - Handle empty allowed-tools
   - Validate tool names

### TR-2: Integration Tests

**LangChain Integration:**

- Create tools from skills
- Execute skill with LangChain agent
- Enforce tool restrictions
- Test sync and async execution

**Haystack Integration:**

- Create ComponentTools from skills
- Execute skill with Haystack agent
- Enforce tool restrictions

**Google ADK Integration:**

- Create function tools from skills
- Execute skill with ADK agent
- Enforce tool restrictions

### TR-3: Compatibility Tests

**Anthropic Skills Compatibility:**

- Download official Anthropic skills repository
- Load all official skills without modification
- Validate metadata parsing
- Test skill invocation

**Real-World Plugin Tests:**

- Test with community plugins
- Validate plugin manifest parsing
- Test multi-plugin scenarios

### TR-4: Performance Tests

**Discovery Performance:**

- Load 100 skills < 100ms
- Load 1000 skills < 1s

**Invocation Performance:**

- Skill invocation overhead < 10ms

---

## Out of Scope

The following features are explicitly **OUT OF SCOPE** for this library:

1. ❌ **Marketplace / Distribution**

   - Skill marketplace infrastructure
   - Skill discovery/search UI
   - Publishing and versioning
1. ❌ **Analytics / Telemetry**

   - Usage tracking
   - Performance monitoring
   - Analytics dashboards
1. ❌ **Security Auditing**

   - Skill scanning tools
   - Dependency analysis
   - Sandboxing infrastructure
1. ❌ **Cross-Platform Sync**

   - Skill synchronization across devices
   - Cloud storage integration
1. ❌ **Advanced Features**

   - Skill dependency resolution
   - Skill composition/chaining
   - Skill conflict detection
1. ❌ **Development Tools**

   - Skill testing framework
   - Skill scaffolding CLI
   - Token usage profiler
1. ❌ **UI Components**

   - Web UI for skill management
   - Visual skill editor
   - Dashboard

---

## References

### Official Documentation

1. **Anthropic Engineering Blog**: [Equipping Agents for the Real World with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
1. **Claude Code Documentation**: [Agent Skills](https://docs.claude.com/en/docs/claude-code/skills)
1. **Claude Code Documentation**: [Plugins](https://docs.claude.com/en/docs/claude-code/plugins)

### Implementation Analysis

1. **SDK_SKILLS_ANALYSIS.md** - Python SDK implementation analysis
2. **CLI_SKILLS_ANALYSIS.md** - Claude Code CLI implementation analysis

### Framework Documentation

1. **LangChain**: [Custom Tools](https://python.langchain.com/docs/how_to/custom_tools/)
2. **Haystack**: [ComponentTool](https://docs.haystack.deepset.ai/docs/componenttool)
3. **Google ADK**: [Function Tools](https://google.github.io/adk-docs/tools/function-tools/)

---

## Appendix A: Example Skill

**File:** `example-plugin/SKILL.md`

```markdown
---
name: pdf-extractor
description: Extract text and tables from PDF files. Use when the user asks to read, analyze, or extract data from PDF documents.
allowed-tools: Read, Bash, Write
version: 1.0.0
---

# PDF Text Extraction Skill

This skill extracts text and structured data from PDF files.

## Instructions

When the user provides a PDF file:

1. Use the `extract_pdf.py` script in this skill's directory:
   ```bash
   python scripts/extract_pdf.py $ARGUMENTS
```

2. The script will output extracted text to stdout
3. If the user wants to save the output, write it to a file using the Write tool

## Script Usage

```bash
python scripts/extract_pdf.py <pdf_file> [--tables] [--output <file>]
```

Arguments:

- `<pdf_file>`: Path to PDF file (required)
- `--tables`: Also extract tables as CSV
- `--output <file>`: Save output to file instead of stdout

## Examples

Extract text:

```bash
python scripts/extract_pdf.py invoice.pdf
```

Extract text and tables:

```bash
python scripts/extract_pdf.py report.pdf --tables --output output.txt
```

```

**File Structure:**
```
pdf-extractor/
├── SKILL.md (shown above)
└── scripts/
    └── extract_pdf.py (executable script for PDF extraction)
```

**Note:** The script implementation is omitted for brevity. In practice, it would use libraries like pypdf or tabula-py to extract text and tables from PDFs.

---

## Appendix B: Example Plugin

**File:** `example-plugin/plugin.json`

```json
{
  "name": "demo-plugin",
  "description": "Demo plugin with example skills",
  "version": "1.0.0",
  "author": {
    "name": "Demo Author",
    "email": "demo@example.com"
  },
  "skills": ["additional-skills"]
}
```

**File:** `./plugins/demo-plugin/skills/data-processor/SKILL.md`

```markdown
---
name: data-processor
description: Process and transform structured data files (CSV, JSON, Excel). Use when user needs data cleaning, transformation, or analysis.
allowed-tools: Read, Write, Bash
version: 1.0.0
---

# Data Processing Skill

Process and transform structured data files.

## Capabilities

- CSV to JSON conversion
- Data cleaning (remove duplicates, handle missing values)
- Basic statistics (mean, median, count)
- Filtering and sorting

## Usage

Provide the data file path and desired operation:
$ARGUMENTS

## Supported Operations

- `convert`: Convert between formats (csv, json, xlsx)
- `clean`: Remove duplicates and handle missing values
- `stats`: Calculate basic statistics
- `filter`: Filter rows based on conditions
- `sort`: Sort by column

## Examples

Convert CSV to JSON:
```

data.csv convert json

```

Clean data:
```

messy_data.csv clean --remove-duplicates --fill-na=0

```

Calculate statistics:
```

sales_data.csv stats --columns=revenue,profit

```
```

---

**END OF DOCUMENT**