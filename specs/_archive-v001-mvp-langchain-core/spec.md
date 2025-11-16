# Feature Specification: skillkit v0.1 MVP - Core Functionality & LangChain Integration

**Feature Branch**: `001-mvp-langchain-core`
**Created**: October 28, 2025
**Status**: Draft
**Input**: User description: "skillkit v0.1 MVP: Core skill discovery, parsing, metadata management, invocation, and LangChain integration with progressive disclosure pattern"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Basic Skill Discovery and Usage (Priority: P1)

A LangChain developer wants to create an AI agent that can leverage pre-packaged expertise (skills) stored in their `.claude/skills/` directory. They need the agent to discover available skills, understand what each skill does, and invoke them when needed.

**Why this priority**: This is the fundamental value proposition - enabling agents to discover and use modular skills. Without this, the library provides no value.

**Independent Test**: Can be fully tested by placing a SKILL.md file in `.claude/skills/skill-name/`, running the discovery process, and verifying the skill is found with correct metadata. Delivers immediate value as a skill discovery tool even without LangChain integration.

**Acceptance Scenarios**:

1. **Given** a `.claude/skills/` directory with 3 skill subdirectories each containing SKILL.md files, **When** the developer runs skill discovery, **Then** all 3 skills are discovered and their names and descriptions are accessible
2. **Given** an empty `.claude/skills/` directory, **When** the developer runs skill discovery, **Then** an empty skill list is returned without errors
3. **Given** a `.claude/skills/` directory does not exist, **When** the developer runs skill discovery, **Then** an empty skill list is returned without errors

---

### User Story 2 - Skill Metadata Access Without Loading Full Content (Priority: P1)

A developer building an agent needs to present available skills to the LLM without consuming excessive context window space. They want to load only skill metadata (name, description) initially, deferring full content loading until a skill is actually invoked.

**Why this priority**: Progressive disclosure is a core architectural principle that differentiates this library from traditional function-calling approaches. Critical for context efficiency.

**Independent Test**: Can be tested by loading 10 skills and measuring that only metadata is loaded (verifying full markdown content is not in memory). Delivers value as a memory-efficient skill browser.

**Acceptance Scenarios**:

1. **Given** 10 skills in `.claude/skills/`, **When** the developer calls `list_skills()`, **Then** only metadata (name, description, path, allowed-tools) is loaded, not full markdown content
2. **Given** a skill has been discovered, **When** the developer calls `get_skill(name)`, **Then** the skill metadata is returned immediately without loading content
3. **Given** 100 skills are discovered, **When** metadata loading completes, **Then** the process takes less than 500ms

---

### User Story 3 - Skill Invocation with Argument Substitution (Priority: P1)

A developer needs to invoke a skill with user-provided arguments, having the skill content processed with proper context (base directory) and argument substitution before being sent to the LLM.

**Why this priority**: Core functionality that makes skills actionable. Without invocation, skills are just static metadata.

**Independent Test**: Can be tested by invoking a skill with specific arguments and verifying the returned content has base directory injected and arguments substituted correctly. Delivers value as a skill content processor.

**Acceptance Scenarios**:

1. **Given** a skill with `$ARGUMENTS` placeholder in content, **When** the developer invokes the skill with "review main.py", **Then** the returned content has `$ARGUMENTS` replaced with "review main.py" and includes base directory context
2. **Given** a skill without `$ARGUMENTS` placeholder, **When** the developer invokes with arguments "test input", **Then** the returned content has "\n\nARGUMENTS: test input" appended
3. **Given** a skill is invoked with empty arguments, **When** `$ARGUMENTS` placeholder exists, **Then** it is replaced with an empty string
4. **Given** a skill is invoked, **When** content loading occurs, **Then** the base directory path is injected at the beginning as "Base directory for this skill: {path}"

---

### User Story 4 - LangChain Agent Integration (Priority: P1)

A LangChain developer wants to convert discovered skills into LangChain StructuredTool objects so their agent can automatically discover, select, and invoke skills as part of its tool-using workflow.

**Why this priority**: LangChain is the target framework for v0.1 MVP. This integration validates the entire vertical slice and delivers end-to-end value.

**Independent Test**: 
Can be tested by creating LangChain tools from skills, passing them to a LangChain agent, and verifying the agent can successfully invoke skills using the tools provided. Delivers complete end-to-end functionality.

**Acceptance Scenarios**:

1. **Given** 3 skills discovered from `.claude/skills/`, **When** the developer calls `create_langchain_tools(manager)`, **Then** 3 LangChain StructuredTool objects are returned
2. **Given** a LangChain StructuredTool created from a skill, **When** the tool is invoked with arguments "analyze code.py", **Then** the processed skill content (with arguments substituted) is returned
3. **Given** a LangChain agent with skill tools, **When** the agent receives a task matching a skill's description, **Then** the agent successfully invokes the skill and receives processed content
4. **Given** a skill tool is invoked, **When** execution completes, **Then** the invocation overhead is less than 10ms (excluding LLM time)

---

### User Story 5 - SKILL.md Parsing and Validation (Priority: P2)

A developer creates a new SKILL.md file and wants the library to parse the YAML frontmatter, extract required fields, and validate the skill format before making it available for use.

**Why this priority**: Essential for ensuring skill quality and preventing runtime errors, but secondary to basic discovery and usage. Can initially work with valid skills only.

**Independent Test**: Can be tested by providing valid and invalid SKILL.md files and verifying parsing succeeds/fails appropriately with clear error messages. Delivers value as a skill format validator.

**Acceptance Scenarios**:

1. **Given** a SKILL.md with valid YAML frontmatter (name, description), **When** the file is parsed, **Then** metadata is extracted correctly and validation passes
2. **Given** a SKILL.md missing required `name` field, **When** parsing occurs, **Then** a clear error message indicates the missing field
3. **Given** a SKILL.md missing required `description` field, **When** parsing occurs, **Then** a clear error message indicates the missing field
4. **Given** a SKILL.md with optional `allowed-tools` field, **When** parsing occurs, **Then** the tools list is extracted (but not enforced in v0.1)
5. **Given** a SKILL.md with markdown content after frontmatter, **When** parsing occurs, **Then** the content is extracted and separated from metadata

---

### User Story 6 - Example Skills for Testing (Priority: P2)

A developer evaluating the library wants to see working examples of skills that demonstrate common use cases and validate the library works end-to-end.

**Why this priority**: Critical for adoption and validation but not core functionality. Can be developed after core features work.

**Independent Test**: Can be tested by running example agent code with provided skills and verifying successful task completion. Delivers value as a learning resource and proof of concept.

**Acceptance Scenarios**:

1. **Given** example skills are provided in [.docs/SKILL format specification.md](.docs/SKILL format specification.md) (code-reviewer, markdown-formatter, git-helper), **When** a developer uses them with a LangChain agent, **Then** each skill successfully guides the agent to complete relevant tasks
2. **Given** a new user installs the library, **When** they follow the README quick start, **Then** the example code runs without modification and demonstrates working skill usage
3. **Given** an example skill, **When** it is invoked, **Then** the resulting output is clear and actionable for the agent

---

### Edge Cases

- **What happens when a SKILL.md file exists but is empty?** - Parsing fails with clear error indicating missing required fields
- **What happens when frontmatter YAML is malformed?** - Parsing fails with clear error indicating YAML syntax issue
- **What happens when a skill directory contains files but no SKILL.md?** - Directory is skipped silently (not considered a skill)
- **What happens when `$ARGUMENTS` appears multiple times in content?** - All occurrences are replaced with the provided arguments
- **What happens when both `$ARGUMENTS` placeholder exists AND content ends without newline?** - Only placeholder is replaced; no append occurs
- **What happens when skill name contains special characters or spaces?** - Names are used as-is for v0.1 (validation deferred to v0.2)
- **What happens when two skills have the same name?** - First discovered skill takes precedence (conflict resolution deferred to v0.2)
- **What happens when skill invocation is called on a skill that doesn't exist?** - Raises KeyError with skill name
- **What happens when the `.claude/skills/` directory is not readable (permission denied)?** - Returns empty list (treats as if directory doesn't exist)

## Requirements *(mandatory)*

### Functional Requirements

#### CP-1: Basic Skill Discovery

- **FR-001**: System MUST scan the `.claude/skills/` directory for skill subdirectories
- **FR-002**: System MUST detect SKILL.md files within skill subdirectories (case-insensitive matching)
- **FR-003**: System MUST support flat directory structure: `.claude/skills/skill-name/SKILL.md`
- **FR-004**: System MUST return an empty list when `.claude/skills/` directory does not exist
- **FR-005**: System MUST return an empty list when `.claude/skills/` directory is empty
- **FR-006**: System MUST NOT fail when skill directories contain non-SKILL.md files

#### CP-2: Minimal SKILL.md Parsing

- **FR-007**: System MUST extract YAML frontmatter between `---` delimiters
- **FR-008**: System MUST validate presence of required field: `name`
- **FR-009**: System MUST validate presence of required field: `description`
- **FR-010**: System MUST extract optional field: `allowed-tools` (list of strings)
- **FR-011**: System MUST extract markdown content appearing after frontmatter
- **FR-012**: System MUST raise clear error message when required field `name` is missing
- **FR-013**: System MUST raise clear error message when required field `description` is missing
- **FR-014**: System MUST raise clear error message when YAML frontmatter is malformed

#### CP-3: Lightweight Metadata Management

- **FR-015**: System MUST store skill metadata in a structured data format (dataclass or dict)
- **FR-016**: System MUST load only metadata during discovery, not full content
- **FR-017**: System MUST provide `list_skills()` method returning all discovered skill metadata
- **FR-018**: System MUST provide `get_skill(name)` method for individual skill metadata lookup
- **FR-019**: System MUST raise KeyError when `get_skill(name)` is called with non-existent skill name
- **FR-020**: System MUST complete metadata loading in under 500ms for 10 skills

#### CP-4: Basic Skill Invocation

- **FR-021**: System MUST load full SKILL.md content when skill is invoked
- **FR-022**: System MUST inject base directory at beginning of content: "Base directory for this skill: {path}"
- **FR-023**: System MUST replace all occurrences of `$ARGUMENTS` placeholder with provided argument string
- **FR-024**: System MUST replace `$ARGUMENTS` with empty string when arguments are empty
- **FR-025**: System MUST append "\n\nARGUMENTS: {args}" when no `$ARGUMENTS` placeholder exists and arguments are provided
- **FR-026**: System MUST perform case-sensitive matching for `$ARGUMENTS` placeholder
- **FR-027**: System MUST NOT modify the original SKILL.md file during invocation
- **FR-028**: System MUST return processed content as a string

#### CP-5: LangChain Integration (Sync Only)

- **FR-029**: System MUST provide `create_langchain_tools(manager)` function that returns list of StructuredTool objects
- **FR-030**: System MUST create one StructuredTool per discovered skill
- **FR-031**: System MUST map skill name to tool name
- **FR-032**: System MUST map skill description to tool description
- **FR-033**: System MUST define single string input parameter for skill arguments
- **FR-034**: System MUST implement synchronous tool invocation (`invoke` method)
- **FR-035**: System MUST return processed skill content to agent when tool is invoked
- **FR-036**: System MUST complete tool invocation in under 10ms overhead (excluding content loading)
- **FR-037**: System MUST work with LangChain LCEL chains and agents

#### CP-6: Minimal Testing

- **FR-038**: System MUST include unit tests for skill discovery (happy path and missing directory)
- **FR-039**: System MUST include unit tests for parsing (valid SKILL.md and missing fields)
- **FR-040**: System MUST include unit tests for metadata management (list and get operations)
- **FR-041**: System MUST include unit tests for invocation (with and without `$ARGUMENTS`)
- **FR-042**: System MUST include integration test demonstrating end-to-end LangChain usage
- **FR-043**: System MUST achieve at least 70% code coverage
- **FR-044**: System MUST have all tests passing with pytest

#### CP-7: Minimal Documentation & Distribution

- **FR-045**: System MUST include `pyproject.toml` with package metadata and dependencies
- **FR-046**: System MUST include README.md with installation instructions and basic example
- **FR-047**: System MUST include LICENSE file (MIT license)
- **FR-048**: System MUST be installable via `pip install skillkit`
- **FR-049**: System MUST have README example that is copy-pasteable and works without modification
- **FR-050**: System MUST include basic SKILL.md format documentation in README

### Key Entities

- **SkillMetadata**: Represents discovered skill information without full content
  - Attributes: name (string), description (string), skill_path (Path), allowed_tools (list of strings or None)
  - Purpose: Enable lightweight skill browsing and decision-making without loading full content

- **Skill**: Represents a fully loaded skill with content
  - Attributes: metadata (SkillMetadata), content (string)
  - Purpose: Provides full skill content for invocation and processing

- **SkillManager**: Central registry managing skill discovery and access
  - Responsibilities: Discover skills from filesystem, parse SKILL.md files, provide metadata access, coordinate skill invocation
  - Purpose: Single entry point for all skill operations

- **LangChainTool**: Adapter wrapping skill as LangChain StructuredTool
  - Attributes: name (from skill), description (from skill), args_schema (single string parameter)
  - Purpose: Bridge between skillkit library and LangChain framework

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can discover all skills in `.claude/skills/` directory and access their metadata in under 500ms for 10 skills
- **SC-002**: Developers can invoke a skill with arguments and receive processed content (with base directory and argument substitution) in a single function call
- **SC-003**: LangChain agents can successfully use skill tools to complete tasks, with tool invocation overhead under 10ms
- **SC-004**: The library achieves 70% test coverage with all tests passing
- **SC-005**: A new developer can install the library via pip and run the README example without modification, successfully demonstrating skill usage within 5 minutes
- **SC-006**: Skills with `$ARGUMENTS` placeholder have all occurrences replaced correctly 100% of the time
- **SC-007**: The library handles edge cases (empty directory, missing SKILL.md, malformed YAML) gracefully with clear error messages
- **SC-008**: The package is successfully published to PyPI and installable in clean Python environments (3.9+)

## Assumptions

1. **Target Python version**: v0.1 targets Python 3.9+ (single version testing acceptable; multi-version testing deferred to v1.0)
2. **Default skill location**: `.claude/skills/` is the standard location; custom paths deferred to v0.3
3. **SKILL.md format**: Follows Anthropic's standard format with YAML frontmatter and markdown content
4. **Tool restriction enforcement**: Not implemented in v0.1 (allowed-tools field is parsed but not enforced)
5. **Async support**: Not included in v0.1 (synchronous operations only)
6. **Performance**: Metadata loading for 10 skills should complete in under 500ms on standard hardware (no caching optimization needed for v0.1)
7. **Error handling**: Basic exception raising with clear messages is sufficient; comprehensive error categorization deferred to v0.2
8. **LangChain version**: Compatible with LangChain 0.1.x and later (exact version TBD based on StructuredTool API stability)
9. **Nested directories**: Not supported in v0.1 (flat structure only)
10. **Plugin support**: Deferred to v0.3
11. **Conflict resolution**: First discovered skill wins when names collide (priority-based resolution deferred to v0.2)
12. **Security**: Basic path validation only; comprehensive path traversal prevention deferred to v0.2

## Scope Boundaries

### In Scope for v0.1

- Skill discovery from `.claude/skills/` directory only
- SKILL.md parsing (YAML frontmatter + markdown content)
- Metadata management (name, description, allowed-tools, path)
- Progressive disclosure (metadata-first loading)
- Skill invocation with argument substitution
- LangChain StructuredTool integration (sync only)
- Basic unit and integration tests (70% coverage)
- Minimal README documentation
- PyPI publishing

### Explicitly Out of Scope for v0.1

- Async support (deferred to v0.2)
- Dynamic tool discovery from scripts/ directories (deferred to v0.2)
- Plugin integration (deferred to v0.3)
- Tool restriction enforcement (deferred to v0.3)
- Multiple search paths (deferred to v0.3)
- Nested directory structures (deferred to v0.3)
- Comprehensive documentation site (deferred to v1.0)
- CI/CD pipeline (deferred to v0.2)
- 90% test coverage (deferred to v1.0)
- Performance optimization beyond basic functionality
- Advanced argument schemas (deferred to v1.1+)
- Multi-framework support (LlamaIndex, CrewAI, etc. - deferred to v1.1+)
- Caching mechanisms (deferred to v0.2+)
- Skill versioning (future consideration)
- Skill marketplace integration (future consideration)

## Dependencies

- **Python 3.9+**: Minimum supported version
- **PyYAML**: For YAML frontmatter parsing
- **LangChain**: For StructuredTool integration (framework integration)
- **pytest**: For testing
- **pytest-cov**: For coverage measurement
- **pathlib**: For filesystem operations (standard library)

## Notes

- This specification focuses exclusively on v0.1 MVP functionality as defined in the vertical slice plan
- All deferred features are documented in `.docs/MVP_VERTICAL_SLICE_PLAN.md` with clear timelines
- The progressive disclosure pattern is a core architectural principle that should not be compromised
- LangChain integration is elevated to v0.1 critical path to enable early validation with real users
- 70% test coverage is acceptable for MVP; quality over perfection principle
- User feedback from v0.1 will shape v0.2+ feature prioritization
