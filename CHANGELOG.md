# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-11-15

### Added

#### Async Support
- **Async discovery**: `adiscover()` method for non-blocking skill discovery
- **Async invocation**: `ainvoke_skill()` method for concurrent skill execution
- **Async file I/O**: Using `asyncio.to_thread()` for non-blocking file operations
- **LangChain async integration**: Full support for async agents via `ainvoke()` method on tools

#### Multi-Source Discovery
- **Multiple skill sources**: Support for project, Anthropic config, plugins, and custom directories
- **Priority-based conflict resolution**: Configurable priority order (project > anthropic > plugins > custom)
- **Fully qualified skill names**: Access specific versions with `plugin:skill` syntax
- **list_skills() enhancements**: Optional `include_qualified` parameter for conflict disambiguation

#### Plugin Ecosystem
- **MCPB manifest support**: Full implementation of Anthropic's plugin.json specification
- **Plugin discovery**: Automatic scanning of `.claude-plugin/plugin.json` manifests
- **Namespaced skills**: Plugin skills accessible via qualified names
- **Multiple skill directories**: Plugins can specify multiple skill source paths

#### Advanced Discovery
- **Nested directory structures**: Support for skills nested up to 5 levels deep
- **Recursive discovery**: Automatic traversal of subdirectories
- **Symlink handling**: Circular symlink detection and resolution
- **Depth warnings**: Warns when skill nesting exceeds recommended depth

#### Secure File Resolution
- **FilePathResolver**: New utility class for secure path resolution
- **Path traversal prevention**: OWASP-compliant validation using `Path.resolve()` + `is_relative_to()`
- **Supporting files**: Skills can safely access scripts, templates, and documentation
- **Security logging**: ERROR-level logging for all path security violations

#### New Data Models
- **SourceType enum**: PROJECT, ANTHROPIC, PLUGIN, CUSTOM
- **SkillSource dataclass**: Represents skill source with priority and metadata
- **PluginManifest dataclass**: Parsed plugin.json with validation
- **QualifiedSkillName**: Parser for plugin:skill syntax
- **InitMode enum**: Tracks sync/async initialization state

#### New Exceptions
- **AsyncStateError**: Raised when mixing sync/async initialization
- **PathSecurityError**: Raised on path traversal attempts
- **ManifestNotFoundError**: Missing plugin.json file
- **ManifestParseError**: Invalid JSON in manifest
- **ManifestValidationError**: Manifest validation failures

### Changed

- **SkillManager constructor**: Now accepts multiple source parameters:
  - `project_skill_dir` (was `skill_dir`)
  - `anthropic_config_dir` (new)
  - `plugin_dirs` (new)
  - `additional_search_paths` (new)
- **Skill.base_directory**: New property exposing skill's base directory for file resolution
- **LangChain tools**: Now support both sync (`invoke`) and async (`ainvoke`) calls
- **list_skills()**: Return type updated to support qualified names

### Enhanced

- **Error messages**: More detailed context including skill name, path, and source
- **Logging**: Structured logging with additional context fields
- **Type hints**: Full mypy strict mode compatibility
- **Performance**: Concurrent file I/O for async discovery (~30-50% faster for 100+ skills)

### Documentation

- **README.md**: Updated with v0.2 async examples and multi-source configuration
- **examples/basic_usage.py**: Now demonstrates both sync and async patterns
- **examples/async_usage.py**: New comprehensive async example with FastAPI integration
- **examples/multi_source.py**: Demonstrates multi-source discovery and conflict resolution
- **examples/file_references.py**: Shows secure file path resolution

### Backward Compatibility

- **100% v0.1 compatible**: All existing v0.1 code continues to work unchanged
- **Optional async**: Async is opt-in; sync methods remain default
- **Constructor compatibility**: v0.1 constructor signature still supported
- **No breaking changes**: All v0.1 APIs preserved

### Dependencies

- **New optional dependency**: `pytest-asyncio` for async tests
- **Minimum Python version**: Still Python 3.10+
- **No new required dependencies**: Async uses stdlib `asyncio.to_thread()`

### Testing

- **Async test suite**: 42+ async-specific tests with 100% coverage
- **Integration tests**: Multi-source, plugin, and path security scenarios
- **Security fuzzing**: 100+ malicious path patterns tested
- **Performance benchmarks**: Sync vs async comparison tests

## [0.1.0] - 2024-XX-XX

### Added

- Initial release
- Core skill discovery and metadata management
- YAML frontmatter parsing with validation
- Progressive disclosure pattern (metadata-first loading)
- Skill invocation with argument substitution
- LangChain integration (sync only)
- 70% test coverage
- Framework-agnostic core design

### Core Features

- **SkillManager**: Main orchestration class for skill lifecycle
- **SkillDiscovery**: Filesystem scanning for SKILL.md files
- **SkillParser**: YAML frontmatter extraction and validation
- **SkillMetadata**: Lightweight metadata for discovered skills
- **Skill**: Full skill with lazy content loading
- **Content processors**: Argument substitution, size limits, security checks

### Integrations

- **LangChain**: Convert skills to StructuredTool objects
- **Pydantic**: Input schema validation

### Documentation

- Comprehensive README with quick start guide
- Example skills (code-reviewer, markdown-formatter, git-helper)
- Basic usage examples

[0.2.0]: https://github.com/maxvaega/skillkit/releases/tag/v0.2.0
[0.1.0]: https://github.com/maxvaega/skillkit/releases/tag/v0.1.0
