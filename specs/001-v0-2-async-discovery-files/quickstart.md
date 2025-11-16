# Quickstart Guide: v0.2 - Async Support, Advanced Discovery & File Resolution

**Feature**: v0.2 Async, Multi-Source Discovery, File Path Resolution
**Target Audience**: Developers implementing v0.2 features

This guide provides practical examples of the new v0.2 capabilities.

---

## Quick Links

- [Async Discovery](#async-discovery)
- [Multi-Source Discovery](#multi-source-discovery)
- [Plugin Integration](#plugin-integration)
- [File Path Resolution](#file-path-resolution)
- [LangChain Async Agents](#langchain-async-agents)
- [Migration from v0.1](#migration-from-v01)

---

## Installation

```bash
# Install with async support
pip install skillkit[async]

# Or install with LangChain integration
pip install skillkit[langchain]

# Or install all extras
pip install skillkit[all]
```

---

## Async Discovery

### Basic Async Usage

```python
import asyncio
from skillkit import SkillManager

async def discover_skills():
    # Create manager with default paths
    manager = SkillManager()

    # Async discovery (non-blocking)
    skills = await manager.adiscover()

    print(f"Discovered {len(skills)} skills asynchronously")
    for name, metadata in skills.items():
        print(f"  - {name}: {metadata.description}")

# Run
asyncio.run(discover_skills())
```

### Async Skill Invocation

```python
async def invoke_skills_async():
    manager = SkillManager()
    await manager.adiscover()

    # Single async invocation
    result = await manager.ainvoke_skill("csv-parser", "data.csv")
    print(result)

    # Concurrent invocations (10+ parallel)
    results = await asyncio.gather(
        manager.ainvoke_skill("csv-parser", "data1.csv"),
        manager.ainvoke_skill("csv-parser", "data2.csv"),
        manager.ainvoke_skill("json-parser", "data.json"),
    )

    for i, result in enumerate(results):
        print(f"Result {i+1}:", result[:100], "...")

asyncio.run(invoke_skills_async())
```

### FastAPI Integration

```python
from fastapi import FastAPI
from skillkit import SkillManager

app = FastAPI()

# Global manager (initialized at startup)
manager = SkillManager()

@app.on_event("startup")
async def startup_event():
    """Initialize skill manager asynchronously during startup."""
    await manager.adiscover()
    print(f"Discovered {len(manager.list_skills())} skills")

@app.get("/skills")
async def list_skills():
    """List all available skills."""
    return {"skills": manager.list_skills()}

@app.post("/skills/{skill_name}/invoke")
async def invoke_skill(skill_name: str, arguments: str = ""):
    """Invoke a skill asynchronously (non-blocking)."""
    try:
        result = await manager.ainvoke_skill(skill_name, arguments)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}, 400
```

---

## Multi-Source Discovery

### Configuring Multiple Sources

```python
from pathlib import Path
from skillkit import SkillManager

# Configure all skill sources
manager = SkillManager(
    project_skill_dir="./skills",                # Priority: 100
    anthropic_config_dir="./.claude/skills",    # Priority: 50
    plugin_dirs=[                                # Priority: 10 each
        "./plugins/data-tools",
        "./plugins/web-tools",
    ],
    additional_search_paths=[                    # Priority: 5 each
        "./shared-skills",
        "../team-skills",
    ],
)

# Discover from all sources
skills = manager.discover()

# Check skill sources
for name, metadata in skills.items():
    print(f"{name}: {metadata.skill_path}")
```

### Priority-Based Conflict Resolution

```python
# Project skills override plugin skills
# Scenario: "csv-parser" exists in both project and plugin

manager = SkillManager(
    project_skill_dir="./skills",
    plugin_dirs=["./plugins/data-tools"],
)
manager.discover()

# Simple name gets highest priority version (project)
skill = manager.get_skill("csv-parser")
print(skill.metadata.skill_path)
# Output: ./skills/csv-parser/SKILL.md

# Qualified name gets plugin version explicitly
skill = manager.get_skill("data-tools:csv-parser")
print(skill.metadata.skill_path)
# Output: ./plugins/data-tools/skills/csv-parser/SKILL.md
```

### Listing Skills with Sources

```python
manager = SkillManager(
    project_skill_dir="./skills",
    plugin_dirs=["./plugins/data-tools"],
)
manager.discover()

# List all skills (simple + qualified)
all_skills = manager.list_skills(include_qualified=True)
print("All skills:", all_skills)
# Output: ["csv-parser", "data-tools:csv-parser", "json-parser", ...]

# List simple names only (highest priority versions)
simple_skills = manager.list_skills(include_qualified=False)
print("Simple skills:", simple_skills)
# Output: ["csv-parser", "json-parser", ...]
```

---

## Plugin Integration

### Creating a Plugin

**Directory Structure**:
```
plugins/my-plugin/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest
└── skills/
    ├── skill-one/
    │   └── SKILL.md
    └── skill-two/
        └── SKILL.md
```

**Plugin Manifest** (`.claude-plugin/plugin.json`):
```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "My custom skill collection",
  "author": "John Doe",
  "skills": ["skills/"]
}
```

### Using Plugins

```python
from skillkit import SkillManager

# Configure plugin directory
manager = SkillManager(
    plugin_dirs=["./plugins/my-plugin"]
)
manager.discover()

# Access plugin skills via qualified names
skill = manager.get_skill("my-plugin:skill-one")
result = skill.invoke("test arguments")
```

### Plugin with Multiple Skill Directories

**Manifest with Additional Directories**:
```json
{
  "name": "data-tools",
  "version": "2.0.0",
  "description": "Data processing skills",
  "skills": ["skills/", "experimental/"]
}
```

**Directory Structure**:
```
plugins/data-tools/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── csv-parser/
│       └── SKILL.md
└── experimental/
    └── new-parser/
        └── SKILL.md
```

**Usage**:
```python
manager = SkillManager(plugin_dirs=["./plugins/data-tools"])
manager.discover()

# Both discovered
print(manager.list_skills())
# Output: ["data-tools:csv-parser", "data-tools:new-parser"]
```

---

## File Path Resolution

### Skill with Supporting Files

**Directory Structure**:
```
skills/data-processor/
├── SKILL.md
├── scripts/
│   ├── helper.py
│   └── validator.py
├── templates/
│   └── config.yaml
└── docs/
    └── README.md
```

**SKILL.md Content**:
```markdown
---
name: data-processor
description: Process data files with validation
---

# Data Processor Skill

This skill uses helper scripts for data processing.

**Helper script**: `scripts/helper.py`
**Validator script**: `scripts/validator.py`
**Config template**: `templates/config.yaml`
**Documentation**: `docs/README.md`

Please execute the helper script with: python $BASE_DIR/scripts/helper.py
```

### Accessing Supporting Files

```python
from pathlib import Path
from skillkit import SkillManager
from skillkit.core.path_resolver import FilePathResolver

# Setup
manager = SkillManager()
manager.discover()

# Get skill
skill = manager.get_skill("data-processor")

# Get base directory from skill
base_dir = skill.base_directory

# Resolve supporting files securely
helper_path = FilePathResolver.resolve_path(base_dir, "scripts/helper.py")
config_path = FilePathResolver.resolve_path(base_dir, "templates/config.yaml")

print(f"Helper script: {helper_path}")
print(f"Config template: {config_path}")

# Read files
helper_code = helper_path.read_text()
config_data = config_path.read_text()
```

### Security Validation

```python
from skillkit.core.path_resolver import FilePathResolver
from skillkit.core.exceptions import PathSecurityError

base_dir = Path("./skills/my-skill")

# Valid paths (allowed)
try:
    path = FilePathResolver.resolve_path(base_dir, "scripts/helper.py")
    print(f"Valid: {path}")
except PathSecurityError as e:
    print(f"Blocked: {e}")

# Invalid path traversal (blocked)
try:
    path = FilePathResolver.resolve_path(base_dir, "../../../etc/passwd")
    print(f"Valid: {path}")
except PathSecurityError as e:
    print(f"Blocked: {e}")  # This will execute

# Invalid absolute path (blocked)
try:
    path = FilePathResolver.resolve_path(base_dir, "/etc/passwd")
    print(f"Valid: {path}")
except PathSecurityError as e:
    print(f"Blocked: {e}")  # This will execute
```

---

## LangChain Async Agents

### Async Agent with Skill Tools

```python
import asyncio
from skillkit import SkillManager
from skillkit.integrations.langchain import create_langchain_tools
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_anthropic import ChatAnthropic

async def run_async_agent():
    # Setup skill manager (async discovery)
    manager = SkillManager(
        project_skill_dir="./skills",
        plugin_dirs=["./plugins"],
    )
    await manager.adiscover()

    # Create LangChain tools (support both sync and async)
    tools = create_langchain_tools(manager)
    print(f"Created {len(tools)} tools for agent")

    # Create async agent
    llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")
    agent = create_tool_calling_agent(llm, tools)
    executor = AgentExecutor(agent=agent, tools=tools)

    # Invoke agent asynchronously
    result = await executor.ainvoke({
        "input": "Parse data.csv using the csv-parser skill"
    })

    print("Agent result:", result["output"])
    return result

# Run
result = asyncio.run(run_async_agent())
```

### Concurrent Tool Invocations

```python
async def concurrent_tool_usage():
    manager = SkillManager()
    await manager.adiscover()
    tools = create_langchain_tools(manager)

    # Find specific tools
    csv_tool = next(t for t in tools if t.name == "csv-parser")
    json_tool = next(t for t in tools if t.name == "json-parser")
    xml_tool = next(t for t in tools if t.name == "xml-parser")

    # Invoke 10+ tools concurrently (non-blocking)
    results = await asyncio.gather(
        csv_tool.ainvoke({"arguments": "data1.csv"}),
        csv_tool.ainvoke({"arguments": "data2.csv"}),
        csv_tool.ainvoke({"arguments": "data3.csv"}),
        json_tool.ainvoke({"arguments": "data.json"}),
        xml_tool.ainvoke({"arguments": "data.xml"}),
        # ... more concurrent invocations
    )

    print(f"Processed {len(results)} files concurrently")
    return results

asyncio.run(concurrent_tool_usage())
```

---

## Migration from v0.1

### v0.1 Code (No Changes Required)

Your existing v0.1 code works unchanged:

```python
from skillkit import SkillManager

# v0.1 usage (still works in v0.2)
manager = SkillManager("./skills")
manager.discover()

skill = manager.get_skill("my-skill")
result = skill.invoke("test arguments")
```

### v0.2 Enhancements (Opt-In)

Add async support without breaking existing code:

```python
from skillkit import SkillManager

# v0.2 async usage (opt-in)
manager = SkillManager(
    project_skill_dir="./skills",  # Was skill_dir in v0.1
    plugin_dirs=["./plugins"]       # NEW in v0.2
)

# Async discovery (NEW in v0.2)
await manager.adiscover()

# Async invocation (NEW in v0.2)
result = await manager.ainvoke_skill("my-skill", "test arguments")
```

### Gradual Migration Strategy

**Step 1**: Update constructor (backward compatible)
```python
# Before (v0.1)
manager = SkillManager("./skills")

# After (v0.2, same behavior)
manager = SkillManager(project_skill_dir="./skills")
```

**Step 2**: Add plugin support (optional)
```python
manager = SkillManager(
    project_skill_dir="./skills",
    plugin_dirs=["./plugins"],  # NEW
)
```

**Step 3**: Adopt async (optional, for high-concurrency apps)
```python
# Replace sync with async
# Before: manager.discover()
await manager.adiscover()

# Before: manager.invoke_skill(name, args)
await manager.ainvoke_skill(name, args)
```

---

## Testing Examples

### Unit Test: Async Discovery

```python
import pytest
from skillkit import SkillManager

@pytest.mark.asyncio
async def test_async_discovery():
    manager = SkillManager("./tests/fixtures/skills")
    skills = await manager.adiscover()

    assert len(skills) > 0
    assert "csv-parser" in skills

@pytest.mark.asyncio
async def test_async_invocation():
    manager = SkillManager("./tests/fixtures/skills")
    await manager.adiscover()

    result = await manager.ainvoke_skill("csv-parser", "test.csv")
    assert result is not None
    assert "csv-parser" in result.lower()
```

### Integration Test: Multi-Source Discovery

```python
def test_multi_source_priority():
    manager = SkillManager(
        project_skill_dir="./tests/fixtures/project-skills",
        plugin_dirs=["./tests/fixtures/plugins/data-tools"],
    )
    manager.discover()

    # Simple name gets project version (higher priority)
    skill = manager.get_skill("csv-parser")
    assert "project-skills" in str(skill.metadata.skill_path)

    # Qualified name gets plugin version
    skill = manager.get_skill("data-tools:csv-parser")
    assert "plugins/data-tools" in str(skill.metadata.skill_path)
```

### Security Test: Path Traversal

```python
import pytest
from skillkit.core.path_resolver import FilePathResolver
from skillkit.core.exceptions import PathSecurityError

def test_path_traversal_blocked():
    base_dir = Path("./skills/test-skill")

    # Valid path (allowed)
    path = FilePathResolver.resolve_path(base_dir, "scripts/helper.py")
    assert path.is_relative_to(base_dir)

    # Path traversal (blocked)
    with pytest.raises(PathSecurityError, match="Path traversal"):
        FilePathResolver.resolve_path(base_dir, "../../../etc/passwd")

    # Absolute path (blocked)
    with pytest.raises(PathSecurityError, match="Absolute paths not allowed"):
        FilePathResolver.resolve_path(base_dir, "/etc/passwd")
```

---

## Performance Benchmarks

### Async Discovery Performance

```python
import time
import asyncio
from skillkit import SkillManager

# Sync discovery
manager_sync = SkillManager()
start = time.time()
manager_sync.discover()
sync_time = time.time() - start
print(f"Sync discovery: {sync_time:.3f}s")

# Async discovery
async def bench_async():
    manager_async = SkillManager()
    start = time.time()
    await manager_async.adiscover()
    async_time = time.time() - start
    print(f"Async discovery: {async_time:.3f}s")
    return async_time

asyncio.run(bench_async())

# Expected: Async is 30-50% faster for 100+ skills
```

---

## Common Patterns

### Pattern 1: Global Singleton Manager

```python
# app.py
from skillkit import SkillManager

# Global manager (initialized once at startup)
skill_manager = None

async def initialize_skills():
    global skill_manager
    skill_manager = SkillManager(
        project_skill_dir="./skills",
        plugin_dirs=["./plugins"],
    )
    await skill_manager.adiscover()

# Use in handlers
async def handle_request(skill_name: str, args: str):
    return await skill_manager.ainvoke_skill(skill_name, args)
```

### Pattern 2: Context Manager (Future)

```python
# Not yet implemented, planned for v0.3
async with SkillManager() as manager:
    await manager.adiscover()
    result = await manager.ainvoke_skill("my-skill", "args")
# Auto-cleanup on exit
```

### Pattern 3: Skill Caching

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_skill(manager: SkillManager, name: str):
    return manager.get_skill(name)

# Reuse skill objects across invocations
skill = get_cached_skill(manager, "csv-parser")
result1 = skill.invoke("data1.csv")
result2 = skill.invoke("data2.csv")  # Reuses cached skill
```

---

## Troubleshooting

### Error: AsyncStateError

**Problem**: Mixing sync and async discovery
```python
manager.discover()
await manager.adiscover()  # ERROR: AsyncStateError
```

**Solution**: Use only one initialization method
```python
# Choose one:
manager.discover()  # Sync
# OR
await manager.adiscover()  # Async
```

### Error: SkillNotFoundError

**Problem**: Skill name not found in registry
```python
manager.discover()
skill = manager.get_skill("unknown-skill")  # ERROR
```

**Solution**: List available skills first
```python
available = manager.list_skills()
print("Available skills:", available)
```

### Error: PathSecurityError

**Problem**: Path traversal attempt
```python
FilePathResolver.resolve_path(base, "../../etc/passwd")  # ERROR
```

**Solution**: Use relative paths within skill directory
```python
# Valid
path = FilePathResolver.resolve_path(base, "scripts/helper.py")
```

---

## Next Steps

- **Read**: [data-model.md](./data-model.md) - Detailed entity specifications
- **Read**: [contracts/](./contracts/) - API contracts for all modules
- **Implement**: Follow tasks.md (generated by `/speckit.tasks` command)
- **Test**: Use test fixtures in `tests/fixtures/` for validation
