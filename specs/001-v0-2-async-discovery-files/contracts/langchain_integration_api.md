# LangChain Integration API Contract

**Version**: v0.2
**Module**: `skillkit.integrations.langchain`

This document specifies the LangChain integration API with async support for v0.2.

---

## Purpose

The LangChain integration converts skillkit skills into LangChain `StructuredTool` objects, enabling seamless use in LangChain agents (both sync and async).

---

## Function: `create_langchain_tools()`

### Signature

```python
def create_langchain_tools(
    manager: SkillManager,
    include_qualified: bool = False,
) -> list[StructuredTool]
```

### Parameters

- `manager: SkillManager` - Initialized SkillManager instance (must have called `discover()` or `adiscover()`)
- `include_qualified: bool` - Include plugin-qualified names as separate tools. Default: `False`

### Returns

- `list[StructuredTool]` - List of LangChain StructuredTool objects, one per skill

### Behavior

1. Retrieves all skills from manager via `list_skills(include_qualified)`
2. For each skill:
   - Creates a `StructuredTool` with skill name as tool name
   - Sets tool description from skill metadata
   - Creates input schema using Pydantic model
   - Binds both sync (`func`) and async (`coroutine`) implementations
3. Returns list of tools ready for agent use

### Tool Properties

Each generated tool has:
- **Name**: Skill name (simple or qualified: `"csv-parser"` or `"data-tools:csv-parser"`)
- **Description**: From `SkillMetadata.description`
- **Input Schema**: Pydantic model with single `arguments` field (string, max 1MB)
- **Sync Function**: Calls `manager.invoke_skill(name, arguments)`
- **Async Coroutine**: Calls `await manager.ainvoke_skill(name, arguments)`

### Exceptions

- `StateError`: If `manager.init_mode == InitMode.UNINITIALIZED` (discovery not run)
- `SkillNotFoundError`: If a skill is deleted between listing and tool creation

### Examples

```python
from skillkit import SkillManager
from skillkit.integrations.langchain import create_langchain_tools
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_anthropic import ChatAnthropic

# Setup
manager = SkillManager(plugin_dirs=["./plugins"])
manager.discover()

# Create tools (simple names only)
tools = create_langchain_tools(manager)
print(f"Created {len(tools)} tools")

# Create tools (including qualified names)
tools_with_qualified = create_langchain_tools(manager, include_qualified=True)
# Result: ["csv-parser", "data-tools:csv-parser", "json-parser", ...]

# Use in sync agent
llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")
agent = create_tool_calling_agent(llm, tools)
executor = AgentExecutor(agent=agent, tools=tools)
result = executor.invoke({"input": "Parse data.csv using csv-parser"})
```

---

## Async Support (v0.2 Enhancement)

### Dual Sync/Async Pattern

All tools created by `create_langchain_tools()` support **both** sync and async invocation:

**Sync Usage**:
```python
tool = tools[0]  # Get first tool
result = tool.invoke({"arguments": "test.csv"})
```

**Async Usage**:
```python
async def process():
    tool = tools[0]
    result = await tool.ainvoke({"arguments": "test.csv"})
```

### Async Agent Integration

```python
import asyncio
from langchain.agents import AgentExecutor
from langchain_anthropic import ChatAnthropic

async def run_async_agent():
    # Setup (discovery can be async too)
    manager = SkillManager(plugin_dirs=["./plugins"])
    await manager.adiscover()

    tools = create_langchain_tools(manager)

    # Create async agent
    llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")
    agent = create_tool_calling_agent(llm, tools)
    executor = AgentExecutor(agent=agent, tools=tools)

    # Invoke asynchronously
    result = await executor.ainvoke({
        "input": "Parse both data.csv and data.json concurrently"
    })
    return result

# Run
result = asyncio.run(run_async_agent())
```

### Concurrent Tool Invocations

```python
async def concurrent_processing():
    manager = SkillManager()
    await manager.adiscover()
    tools = create_langchain_tools(manager)

    # Find tools by name
    csv_tool = next(t for t in tools if t.name == "csv-parser")
    json_tool = next(t for t in tools if t.name == "json-parser")

    # Invoke 10+ tools concurrently
    results = await asyncio.gather(
        csv_tool.ainvoke({"arguments": "data1.csv"}),
        csv_tool.ainvoke({"arguments": "data2.csv"}),
        json_tool.ainvoke({"arguments": "data.json"}),
        # ... more concurrent invocations
    )
    return results
```

---

## Tool Input Schema

### Pydantic Model

Each tool uses this input schema:

```python
from pydantic import BaseModel, Field

class SkillInput(BaseModel):
    """Input schema for skill invocation."""

    arguments: str = Field(
        default="",
        description="Arguments to pass to the skill (optional)",
        max_length=1_048_576,  # 1MB limit
    )
```

### Schema Validation

- **Field**: `arguments` (string, optional, default `""`)
- **Max Length**: 1MB (1,048,576 characters)
- **Validation**: Pydantic validates before tool invocation
- **Error**: Raises `ValidationError` if arguments exceed limit

### Tool Invocation Format

LangChain agents invoke tools with:
```json
{
  "arguments": "user input string here"
}
```

---

## Error Handling

### Exception Propagation

All skillkit exceptions propagate to LangChain:
- `SkillNotFoundError` → Tool execution fails with error message
- `ContentLoadError` → Tool execution fails with file I/O error
- `ArgumentProcessingError` → Tool execution fails with processing error
- `PathSecurityError` → Tool execution fails with security error

### LangChain Error Handling

Agents can handle tool errors via:
- **Default**: Agent receives error message as tool output
- **Custom**: Configure `handle_tool_error` in `AgentExecutor`

**Example**:
```python
executor = AgentExecutor(
    agent=agent,
    tools=tools,
    handle_tool_error=True,  # Continue on tool errors
)
```

---

## Tool Metadata

### Tool Name

- **Simple skills**: Use skill name directly (e.g., `"csv-parser"`)
- **Qualified skills**: Use full qualified name (e.g., `"data-tools:csv-parser"`)
- **Name conflicts**: If `include_qualified=False` and conflict exists, highest priority version is used

### Tool Description

- **Source**: `SkillMetadata.description` field from SKILL.md frontmatter
- **Format**: Plain text (no markdown rendering)
- **Length**: No limit, but LLMs work best with 1-3 sentence descriptions

### Tool Tags (Future)

Not implemented in v0.2. Planned for v0.3:
- Tags from `SkillMetadata.allowed_tools` → LangChain tool tags
- Enable filtering: `tools = [t for t in tools if "data" in t.tags]`

---

## Performance Characteristics

### Tool Creation Overhead

- **Time**: ~0.1ms per tool (very fast Pydantic model creation)
- **Memory**: ~1-2KB per tool object
- **Recommendation**: Create tools once at startup, reuse across agent invocations

### Tool Invocation Overhead

| Operation | Sync | Async | Notes |
|-----------|------|-------|-------|
| First invocation | ~10-25ms | ~12-27ms | Includes content loading |
| Subsequent invocations | ~1-5ms | ~2-6ms | Content cached |
| LangChain overhead | ~1-3ms | ~1-3ms | StructuredTool processing |
| **Total (first)** | ~11-28ms | ~13-30ms | Acceptable for LLM agents |
| **Total (cached)** | ~2-8ms | ~3-9ms | Negligible compared to LLM latency |

**Note**: LLM inference (Claude API call) dominates at ~500-2000ms, making tool overhead negligible.

---

## Backward Compatibility

### v0.1 Sync-Only Behavior

**v0.1 code works unchanged**:
```python
# v0.1 usage (still works)
manager = SkillManager("./skills")
manager.discover()
tools = create_langchain_tools(manager)
# Tools support sync invocation
```

### v0.2 Async Enhancement

**v0.2 adds async support (opt-in)**:
```python
# v0.2 async usage
manager = SkillManager("./skills")
await manager.adiscover()
tools = create_langchain_tools(manager)
# Tools support BOTH sync and async invocation
```

**Key Point**: All tools created in v0.2 support both sync and async, regardless of how manager was initialized.

---

## Testing

### Unit Tests

**Test Coverage**:
- Tool creation from manager with 0 skills (edge case)
- Tool creation from manager with 100+ skills
- Tool invocation (sync and async)
- Error propagation (SkillNotFoundError, ContentLoadError, etc.)
- Input validation (arguments exceeding 1MB)

### Integration Tests

**LangChain Agent Tests**:
- Sync agent with skill tools
- Async agent with skill tools
- Concurrent tool invocations via asyncio.gather()
- Error handling in agents (tool failures)

**Test Fixtures**:
```python
@pytest.fixture
async def manager_with_skills():
    manager = SkillManager("./tests/fixtures/skills")
    await manager.adiscover()
    return manager

@pytest.fixture
def langchain_tools(manager_with_skills):
    return create_langchain_tools(manager_with_skills)

@pytest.mark.asyncio
async def test_async_tool_invocation(langchain_tools):
    tool = langchain_tools[0]
    result = await tool.ainvoke({"arguments": "test"})
    assert result is not None
```

---

## Platform Compatibility

### LangChain Version Requirements

- **Minimum**: `langchain-core >= 0.1.0`
- **Recommended**: `langchain-core >= 0.2.0` (better async support)
- **Testing**: CI tests against 0.1.x and 0.2.x

### Python Version Requirements

- **Minimum**: Python 3.10 (same as skillkit core)
- **Async Support**: Requires Python 3.10+ for full asyncio features

### Framework Compatibility

The LangChain integration is tested with:
- ✅ LangChain (official)
- ✅ LangGraph (async workflows)
- ⚠️ LangServe (HTTP endpoints) - not yet tested in v0.2

---

## Migration Guide

### From v0.1 to v0.2

**No breaking changes**. Existing code works as-is.

**Optional async enhancements**:
```python
# v0.1 sync code (still works)
manager = SkillManager("./skills")
manager.discover()
tools = create_langchain_tools(manager)

# v0.2 async enhancement (opt-in)
manager = SkillManager("./skills")
await manager.adiscover()  # NEW: async discovery
tools = create_langchain_tools(manager)
# Tools now support await tool.ainvoke() in async agents
```

### Best Practices

1. **Discovery**: Use async discovery for large skill sets (100+ skills)
2. **Tool Creation**: Create tools once at startup, not per agent invocation
3. **Async Agents**: Prefer async for high-concurrency scenarios (10+ concurrent requests)
4. **Error Handling**: Configure `handle_tool_error=True` for robust agents
5. **Qualified Names**: Use `include_qualified=True` only when plugin disambiguation is needed

---

## Future Enhancements (v0.3+)

- **Tool Tags**: Map `allowed_tools` to LangChain tool tags for filtering
- **Tool Discovery**: Auto-refresh when new skills added at runtime
- **Tool Metrics**: Built-in instrumentation (invocation counts, latency, errors)
- **Custom Input Schemas**: Support skills with structured arguments (not just strings)
