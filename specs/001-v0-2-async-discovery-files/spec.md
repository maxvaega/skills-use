# Feature Specification: v0.2 - Async Support, Advanced Discovery & File Resolution

**Feature Branch**: `001-v0-2-async-discovery-files`
**Created**: 2025-11-06
**Status**: Draft
**Input**: User description: "v0.2 including: Async Support (IR-2 incomplete) - adiscover() async discovery, ainvoke_skill() async invocation, Async file I/O, LangChain ainvoke support; Advanced Discovery (FR-1 incomplete) - Multiple search paths (project, anthropic, custom), Plugin directory support, Nested skill structure (group/skill-name/), Skill name conflict resolution across sources, Fully qualified names (plugin:skill-name); File Reference Resolution (FR-5 not implemented) - Relative path resolution from skill base, Supporting file access (scripts/, templates/, docs/), Path traversal security validation"

## Clarifications

### Session 2025-11-16

- Q: When default directories (`./.claude/skills` or `./skills`) don't exist in the current working directory, what should the initialization behavior be? → A: Initialize successfully with empty skill list and log info message
- Q: When SkillManager() is initialized without parameters and both default directories (`./skills/` and `./.claude/skills/`) exist, which directories are scanned during discovery? → A: Scan both directories with priority-based deduplication (./skills/ takes precedence over ./.claude/skills/ for name conflicts)
- Q: When a user explicitly passes `None` for directory parameters (e.g., `SkillManager(project_skill_dir=None)`), should this behave differently from omitting the parameter entirely? → A: Treat both the same (apply defaults for None and omitted parameters)
- Q: When a user explicitly provides a directory path that doesn't exist (e.g., `SkillManager(project_skill_dir="/nonexistent/path")`), what should happen? → A: Raise ConfigurationError with clear message indicating the path doesn't exist
- Q: How should users explicitly opt out of default directory discovery when they want SkillManager to start with zero skills regardless of what directories exist? → A: Use empty string `""` for directory parameters and empty list `[]` for plugin_dirs to disable discovery

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Async Skill Discovery for High-Performance Applications (Priority: P1)

A developer building a high-performance LLM application with 500+ available skills needs to initialize the skill manager without blocking their event loop. The async discovery allows their application to remain responsive while loading skill metadata in the background.

**Why this priority**: Core functionality that enables non-blocking operations in async applications (FastAPI, async agents). Without this, users cannot use skillkit in modern async Python applications without blocking.

**Independent Test**: Can be fully tested by initializing SkillManager with `await manager.adiscover()` in an async context and verifying that:
- The event loop remains responsive during discovery
- All skills are discovered correctly
- Performance is comparable to or better than sync discovery

**Acceptance Scenarios**:

1. **Given** an async application with 500 skills in multiple directories, **When** `await manager.adiscover()` is called, **Then** the event loop remains responsive and all 500 skills are discovered without blocking
2. **Given** a FastAPI application initializing at startup, **When** skill discovery runs asynchronously, **Then** the server can handle health check requests during discovery
3. **Given** multiple skill sources (project, anthropic, plugins), **When** async discovery runs, **Then** all sources are scanned concurrently for maximum performance

---

### User Story 2 - Async Skill Invocation for LangChain Agents (Priority: P1)

A developer using LangChain's async agents needs to invoke skills without blocking the event loop, enabling their agent to handle multiple concurrent requests efficiently. The async invocation integrates seamlessly with LangChain's `ainvoke` pattern.

**Why this priority**: Essential for production async agents. LangChain's async agents require async tool implementations, making this a blocker for async agent usage.

**Independent Test**: Can be fully tested by:
- Creating a LangChain async agent with skill tools
- Invoking a skill via `await tool.ainvoke({"args": "test"})`
- Verifying the event loop remains responsive and result is correct

**Acceptance Scenarios**:

1. **Given** a LangChain async agent with skill tools, **When** the agent invokes a skill via `ainvoke`, **Then** the skill executes asynchronously and returns the correct result
2. **Given** 10 concurrent skill invocations, **When** all invocations run in parallel via `asyncio.gather`, **Then** all complete successfully with correct results
3. **Given** a skill that performs file I/O, **When** invoked asynchronously, **Then** the event loop remains responsive during file operations

---

### User Story 3 - Multiple Skill Source Discovery (Priority: P2)

A developer wants to organize skills across multiple directories: project-specific skills in `./skills/`, reusable Anthropic skills in `./.claude/skills/`, and third-party plugin skills in `./plugins/`. The skill manager should automatically discover and deduplicate skills from all configured sources. When no parameters are provided, SkillManager defaults to `./skills/` for project_skill_dir and `./.claude/skills/` for anthropic_config_dir if these directories exist, enabling out-of-the-box usage. If default directories don't exist, the manager initializes successfully with an empty skill list and logs an informational message.

**Why this priority**: Enables proper skill organization and reuse across projects. Critical for maintaining separation of concerns and supporting the Anthropic ecosystem. Default directory behavior provides zero-configuration quick start.

**Independent Test**: Can be fully tested by:
- Configuring SkillManager with project_skill_dir, anthropic_config_dir, and plugin_dirs
- Verifying skills are discovered from all three sources
- Confirming priority order (project > anthropic > plugins) for conflict resolution
- Testing initialization without parameters when default directories exist and don't exist

**Acceptance Scenarios**:

1. **Given** skills in `./skills/`, `./.claude/skills/`, and `./plugins/my-plugin/skills/`, **When** SkillManager initializes, **Then** all skills from all three sources are discovered
2. **Given** a skill named "data-processor" exists in both project and plugin directories, **When** the manager resolves the name, **Then** the project version is used (priority order)
3. **Given** a user requests a plugin skill explicitly via "my-plugin:data-processor", **When** the manager retrieves it, **Then** the plugin version is returned despite name conflict
4. **Given** SkillManager() is called without parameters and `./skills/` exists, **When** discovery runs, **Then** skills from `./skills/` are discovered automatically
5. **Given** SkillManager() is called without parameters and both `./skills/` and `./.claude/skills/` exist with a skill name conflict, **When** discovery runs, **Then** both directories are scanned and the `./skills/` version takes precedence
6. **Given** SkillManager() is called without parameters and neither `./skills/` nor `./.claude/skills/` exist, **When** initialization completes, **Then** manager initializes successfully with zero skills and logs an info-level message
7. **Given** SkillManager is initialized with explicit nonexistent path `SkillManager(project_skill_dir="/nonexistent/path")`, **When** initialization is attempted, **Then** ConfigurationError is raised immediately with clear message indicating the invalid path
8. **Given** SkillManager is initialized with explicit opt-out `SkillManager(project_skill_dir="", anthropic_config_dir="", plugin_dirs=[])` and default directories exist, **When** initialization completes, **Then** manager initializes with zero skills and no directories are scanned (no INFO message logged)

---

### User Story 4 - Plugin Directory Support (Priority: P2)

A developer wants to package and distribute a collection of related skills as a plugin with a manifest file. The skill manager should automatically discover plugin manifests, parse their metadata, and load skills from the plugin's skill directories with proper namespacing.

**Why this priority**: Enables the plugin ecosystem and skill distribution. Essential for third-party skill packages and community contributions.

**Independent Test**: Can be fully tested by:
- Creating a plugin directory with `.claude-plugin/plugin.json` manifest
- Configuring SkillManager to scan the plugin directory
- Verifying plugin skills are discovered with correct namespacing (plugin-name:skill-name)

**Acceptance Scenarios**:

1. **Given** a plugin directory with `.claude-plugin/plugin.json`, **When** SkillManager scans the directory, **Then** the plugin manifest is parsed and skills are discovered
2. **Given** a plugin with custom skill directories specified in manifest, **When** discovery runs, **Then** skills from all specified directories are loaded
3. **Given** multiple plugins with overlapping skill names, **When** skills are retrieved, **Then** plugin namespace prevents conflicts (plugin-a:skill vs plugin-b:skill)

---

### User Story 5 - Nested Skill Structure Support (Priority: P2)

A developer with 100+ skills wants to organize them into logical groups using nested directories (e.g., `./skills/data-processing/csv-parser/`, `./skills/data-processing/json-transformer/`). The skill manager should support both flat and nested structures without configuration changes.

**Why this priority**: Improves skill organization and maintainability for large skill libraries. Without this, users are forced to use flat structures which become unmanageable at scale.

**Independent Test**: Can be fully tested by:
- Creating a nested skill structure with subdirectories
- Running skill discovery
- Verifying all skills are found regardless of nesting depth

**Acceptance Scenarios**:

1. **Given** skills in nested directories like `./skills/group-one/skill-name/SKILL.md`, **When** discovery runs, **Then** all nested skills are discovered with correct names
2. **Given** both flat (`./skills/skill-a/`) and nested (`./skills/group/skill-b/`) structures, **When** discovery runs, **Then** both structure types coexist and all skills are discovered
3. **Given** a three-level nesting like `./skills/cat/subcat/skill/`, **When** discovery runs, **Then** the skill is discovered and accessible

---

### User Story 6 - File Reference Resolution for Skills (Priority: P2)

A skill author needs to bundle supporting files (Python scripts, templates, documentation) with their skill and reference them using relative paths. The skill manager should resolve these paths from the skill's base directory and validate they don't escape the skill directory for security.

**Why this priority**: Enables rich, self-contained skills with bundled resources. Essential for skills that need helper scripts, configuration templates, or reference documentation.

**Independent Test**: Can be fully tested by:
- Creating a skill with supporting files in subdirectories
- Invoking the skill and accessing files via relative paths
- Verifying path traversal attempts are blocked

**Acceptance Scenarios**:

1. **Given** a skill with `scripts/helper.py` in its directory, **When** the skill content references "scripts/helper.py", **Then** the path resolves correctly to the full path from skill base directory
2. **Given** a skill attempting to access "../../../etc/passwd", **When** path resolution is attempted, **Then** a security error is raised preventing directory traversal
3. **Given** a skill with nested supporting files like `templates/config/default.yaml`, **When** the skill accesses this path, **Then** it resolves correctly within the skill directory

---

### User Story 7 - Graceful Conflict Resolution Across Skill Sources (Priority: P3)

A developer has the same skill name in multiple sources (e.g., "pdf-extractor" in both project skills and a plugin). The skill manager should resolve conflicts using priority order (project > anthropic > plugins) and allow explicit disambiguation using fully qualified names.

**Why this priority**: Prevents confusion and enables skill overrides. Users can customize plugin skills locally while maintaining the plugin version as a fallback.

**Independent Test**: Can be fully tested by:
- Creating skills with identical names in different sources
- Retrieving the skill by simple name (gets highest priority version)
- Retrieving by fully qualified name (gets specific version)

**Acceptance Scenarios**:

1. **Given** "pdf-extractor" exists in both `./skills/` and plugin, **When** retrieved by name, **Then** the project version is used
2. **Given** the same conflict scenario, **When** retrieved by "my-plugin:pdf-extractor", **Then** the plugin version is used
3. **Given** a skill name conflict warning is logged, **When** discovery completes, **Then** the warning includes all conflicting paths and the resolution used

---

### Edge Cases

- What happens when SkillManager is initialized without parameters and default directories (`./skills/`, `./.claude/skills/`) don't exist? → Manager initializes successfully with zero skills and logs INFO message "No skill directories found; initialized with empty skill list"
- What happens when user passes `SkillManager(project_skill_dir=None, anthropic_config_dir=None)`? → Treated identically to `SkillManager()` - defaults are applied and existing default directories are discovered
- What happens when user explicitly provides a nonexistent directory (e.g., `SkillManager(project_skill_dir="/bad/path")`)? → ConfigurationError is raised immediately with message "Explicitly configured directory does not exist: project_skill_dir='/bad/path'"
- What happens when user wants to disable default discovery entirely (e.g., `SkillManager(project_skill_dir="", anthropic_config_dir="", plugin_dirs=[])`)? → Manager initializes with zero skills, no directories are scanned, and no INFO message is logged (explicit opt-out is intentional, not an error condition)
- What happens when user mixes empty string opt-out with valid paths (e.g., `SkillManager(project_skill_dir="/valid/path", anthropic_config_dir="")`)? → Only `/valid/path` is scanned; anthropic directory discovery is explicitly disabled via empty string
- What happens when a plugin manifest is malformed or missing required fields? → Discovery logs an error for that plugin, continues with other plugins, and returns the plugin path in the error list
- What happens when async discovery is interrupted (e.g., timeout, cancellation)? → Partial results are discarded, SkillManager remains in uninitialized state, and a clear error is raised
- What happens when a skill's supporting file path contains `..` sequences? → Path validation raises SecurityError before file access, logging the attempted path and skill name
- What happens when multiple plugins have the same plugin name in their manifest? → First plugin wins, warning is logged with both plugin paths, subsequent plugins are prefixed with a disambiguator (plugin-name-2)
- What happens when async and sync discovery are called on the same manager instance? → Second call raises StateError indicating manager is already initialized
- What happens when a nested skill structure exceeds reasonable depth (e.g., 10+ levels)? → Discovery continues but logs a warning about potential filesystem organization issues
- What happens when skill directory has circular symlinks? → Symlink resolution detects the cycle, logs a warning, and skips that path to prevent infinite loops

## Requirements *(mandatory)*

### Functional Requirements

#### Async Support (IR-2.4 completion)

- **FR-001**: SkillManager MUST provide an `adiscover()` async method for non-blocking skill discovery across all configured sources
- **FR-002**: SkillManager MUST provide an `ainvoke_skill()` async method for non-blocking skill content loading and argument substitution
- **FR-003**: Async discovery MUST use async file I/O operations (aiofiles or equivalent) to avoid blocking the event loop
- **FR-004**: LangChain integration MUST support async tool invocation via `ainvoke` method matching LangChain's async tool interface
- **FR-005**: Async methods MUST maintain the same error handling and validation as their sync counterparts
- **FR-006**: SkillManager MUST allow calling both sync and async methods, but prevent mixing initialization states

#### Advanced Discovery (FR-1 completion)

- **FR-007**: SkillManager MUST support configuring multiple skill source directories: project_skill_dir, anthropic_config_dir, plugin_dirs, and additional_search_paths
- **FR-007a**: When SkillManager is initialized with omitted or None directory parameters (e.g., `SkillManager()` or `SkillManager(project_skill_dir=None)`), system MUST apply default values by checking for default directories `./skills/` and `./.claude/skills/` and scanning all that exist
- **FR-007b**: When both default directories exist, system MUST scan both with priority-based deduplication where `./skills/` (project) takes precedence over `./.claude/skills/` (anthropic) for name conflicts
- **FR-007c**: When default directories don't exist and no custom directories are provided (omitted or None), SkillManager MUST initialize successfully with an empty skill list and log an INFO-level message indicating no skill directories were found
- **FR-007d**: Explicit None values for directory parameters MUST be treated identically to omitted parameters (both trigger default directory discovery)
- **FR-007e**: When user explicitly provides a directory path that doesn't exist (non-None, non-empty, non-default), system MUST raise ConfigurationError immediately with clear message indicating which path doesn't exist and which parameter it was provided for
- **FR-007f**: Empty string `""` for directory parameters (project_skill_dir, anthropic_config_dir) and empty list `[]` for plugin_dirs MUST be treated as explicit opt-out from discovery for those sources, initializing with no skills from those sources and no default fallback
- **FR-007g**: When user provides `SkillManager(project_skill_dir="", anthropic_config_dir="", plugin_dirs=[])`, system MUST initialize successfully with zero skills and no INFO message (explicit intent, not missing configuration)
- **FR-008**: System MUST scan all configured directories in priority order: project > anthropic > plugins > additional paths
- **FR-009**: System MUST support plugin discovery by scanning for `.claude-plugin/plugin.json` manifests in plugin directories
- **FR-010**: System MUST parse plugin manifests extracting name, version, description, author, and skills field (string or array)
- **FR-011**: System MUST discover skills from plugin default location (`<plugin-root>/skills/`) and additional directories specified in manifest
- **FR-012**: Plugin skills MUST be namespaced with plugin name: `{plugin-name}:{skill-name}`
- **FR-013**: System MUST support both flat (`./skills/skill-name/SKILL.md`) and nested (`./skills/group/skill-name/SKILL.md`) directory structures simultaneously
- **FR-014**: System MUST resolve skill name conflicts using source priority order (project > anthropic > plugins > additional)
- **FR-015**: System MUST support fully qualified skill names for explicit plugin skill retrieval: `get_skill("plugin-name:skill-name")`
- **FR-016**: Within the same source, when multiple skills have the same name, system MUST use first discovered skill and log a warning
- **FR-017**: System MUST log warnings when skill name conflicts occur across sources, including all conflicting paths
- **FR-018**: System MUST handle symbolic links gracefully, resolving them and validating they stay within allowed directories
- **FR-019**: System MUST detect and prevent circular symlinks during discovery without crashing

#### File Reference Resolution (FR-5 implementation)

- **FR-020**: System MUST inject skill base directory context into skill content: `Base directory for this skill: {baseDir}`
- **FR-021**: System MUST provide a method to resolve relative file paths from a skill's base directory to absolute paths
- **FR-022**: Path resolution MUST support subdirectories (e.g., `scripts/helper.py`, `templates/config/settings.yaml`)
- **FR-023**: System MUST validate all resolved paths stay within the skill's base directory to prevent directory traversal attacks
- **FR-024**: Path validation MUST reject paths containing `..` sequences that escape the skill directory
- **FR-025**: Path validation MUST normalize paths (resolve symlinks, remove redundant separators) before validation
- **FR-026**: System MUST raise SecurityError with descriptive message when path traversal is attempted
- **FR-027**: System MUST log all path traversal attempts at ERROR level with skill name and attempted path

### Key Entities

- **SkillSource**: Represents a source location for skills (project directory, anthropic directory, plugin directory, custom path) with priority level and type
- **PluginManifest**: Parsed plugin metadata containing name, version, description, author info, and additional skill directories
- **QualifiedSkillName**: A skill identifier that may include optional plugin namespace (e.g., "skill-name" or "plugin:skill-name")
- **SkillPath**: A validated file path within a skill directory, guaranteed to not escape via directory traversal

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Async discovery of 500 skills completes in under 200ms (50% faster than sync) and never blocks event loop for more than 5ms
- **SC-002**: Async skill invocation adds less than 2ms overhead compared to sync invocation
- **SC-003**: LangChain async agents can invoke skills concurrently with 10+ parallel invocations without errors
- **SC-004**: Skill discovery correctly handles 3+ configured source directories with priority-based conflict resolution
- **SC-005**: Plugin discovery automatically finds all plugins in configured directories and correctly namespaces their skills
- **SC-006**: Nested skill structures with up to 5 levels of nesting are discovered correctly
- **SC-007**: Path traversal attempts are blocked 100% of the time with clear security errors
- **SC-008**: Supporting files within skills are accessible via relative paths with zero false positives in security validation
- **SC-009**: Fully qualified skill names (plugin:skill) resolve correctly even when name conflicts exist
- **SC-010**: Async and sync APIs produce identical results for discovery and invocation (except timing)

### User Satisfaction Metrics

- **SC-011**: Developers successfully integrate async skills into FastAPI applications within 15 minutes
- **SC-012**: Plugin authors successfully package and distribute skills with supporting files on first attempt
- **SC-013**: Users with 100+ skills report improved organization using nested structures
- **SC-014**: Zero security incidents related to path traversal in production deployments

## Assumptions *(if applicable)*

1. **Async runtime assumption**: Users will use modern async Python patterns (asyncio, FastAPI, async LangChain agents) rather than legacy async libraries
2. **Plugin manifest format**: Plugins follow Anthropic's `.claude-plugin/plugin.json` format exactly as specified in the PRD
3. **File system performance**: Async file I/O provides measurable benefits for 100+ skill discovery; for smaller sets, sync may be comparable
4. **Security context**: Path traversal validation is sufficient for skill isolation; full sandboxing (chroot, containers) is not in scope for v0.2
5. **Symlink usage**: Symlinks are uncommon in skill directories but must be supported for advanced users; circular symlinks are considered configuration errors
6. **Python version**: Minimum Python 3.10 for full async file I/O support via modern standard library features
7. **Conflict resolution policy**: Project-level skills should always override plugin skills (users customize/extend plugins locally)
8. **Plugin discovery**: Plugins are pre-installed in known locations; dynamic plugin installation/downloading is out of scope
9. **Nested structure limit**: While theoretically unlimited, nesting beyond 5 levels is considered poor filesystem organization and will trigger warnings
10. **Backward compatibility**: v0.1 code using sync APIs continues working unchanged; async APIs are purely additive

## Dependencies *(if applicable)*

1. **aiofiles**: Required for async file I/O operations (reading SKILL.md files, plugin manifests)
2. **LangChain Core**: Existing dependency, but need to verify async tool interface compatibility with latest version
3. **Python pathlib**: Standard library Path class provides path resolution and validation primitives
4. **Python asyncio**: Standard library for async runtime and event loop management

## Related Features/Stories *(if applicable)*

- **v0.1 MVP**: Foundation sync implementation (discovery, parsing, manager, LangChain sync integration) - must remain compatible
- **Future v0.3**: Tool restriction enforcement (FR-4.3), script execution support (FR-6), additional framework integrations (CrewAI, LlamaIndex)
- **Future v1.0**: Advanced argument schemas (FR-9), comprehensive documentation, production hardening

## Technical Constraints *(if applicable)*

1. **Backward compatibility**: v0.1 sync API must remain unchanged and functional
2. **Framework agnostic core**: Async support in core modules must not introduce framework-specific dependencies
3. **Memory efficiency**: Async discovery should not increase memory usage compared to sync (still use lazy loading)
4. **Performance requirement**: Async overhead should be minimal (<2ms per operation) to justify complexity
5. **Security boundary**: Path validation must be bulletproof; this is a security-critical feature
6. **Error handling**: Async errors must be as clear and actionable as sync errors
7. **Testing requirement**: Async code paths require separate test coverage with pytest-asyncio
8. **Type safety**: All async methods must have full type hints compatible with mypy strict mode

## Out of Scope *(if applicable)*

- **Async plugin manifest downloads**: Plugins are assumed pre-installed; dynamic download is not supported
- **Async script execution**: FR-6 (script execution) deferred to v0.3; only file reading is async in v0.2
- **Sandboxing/containerization**: Path traversal prevention is sufficient; full isolation out of scope
- **Skill dependency resolution**: Skills are independent; no dependency graphs or installation order
- **Advanced file access patterns**: Only simple relative path resolution; no glob patterns, regex, or dynamic paths
- **Cross-platform path quirks**: Path validation assumes POSIX-style paths; Windows UNC paths are best-effort
- **Skill versioning/updates**: Plugin manifest version field is informational only; no update mechanism
- **Performance monitoring**: No built-in metrics for async operations; users should instrument with their own tools
- **Concurrent write safety**: Discovery is read-only; concurrent writes to skill directories are user responsibility

## Risks & Mitigations *(if applicable)*

### Risk 1: Async complexity increases bug surface area

**Likelihood**: Medium
**Impact**: High
**Mitigation**:
- Implement async as thin wrappers over sync implementations where possible
- Use proven async patterns (async context managers, asyncio.gather)
- Comprehensive async test coverage with pytest-asyncio
- Code review focus on race conditions and event loop blocking

### Risk 2: Path traversal validation has edge cases or bypasses

**Likelihood**: Low
**Impact**: Critical
**Mitigation**:
- Use Python pathlib's resolve() for canonical path normalization
- Test against known path traversal attack vectors (../, symlinks, ...)
- Security review by multiple developers
- Fuzz testing with malicious path inputs
- Reference OWASP path traversal prevention guidelines

### Risk 3: Plugin manifest format diverges from Anthropic specification

**Likelihood**: Low
**Impact**: Medium
**Mitigation**:
- Use Anthropic's published schema as source of truth
- Test with real Anthropic plugins if available
- Implement strict schema validation with clear error messages
- Document any extensions or variations

### Risk 4: Async performance gains are negligible for typical use cases

**Likelihood**: Medium
**Impact**: Low
**Mitigation**:
- Benchmark both sync and async implementations with realistic skill counts
- Document performance characteristics in user guide
- Make async APIs optional; sync remains fully supported
- Target use case is 100+ skills or high-concurrency agents where benefits are clear

### Risk 5: Nested discovery increases complexity and maintenance burden

**Likelihood**: Low
**Impact**: Medium
**Mitigation**:
- Use recursive directory walking with depth limits
- Extensive testing with various nesting patterns
- Clear documentation of supported structures
- Warning logs for unusual nesting (>5 levels)
