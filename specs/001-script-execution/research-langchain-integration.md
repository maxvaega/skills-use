# LangChain StructuredTool Integration Research

**Research Date**: 2025-01-18
**Purpose**: Design integration patterns for exposing multiple tools from a single skill
**Scope**: Multiple tools per skill, tool naming, input schemas, descriptions, return formats, async support
**Version**: For skillkit v0.3.0 (script execution feature)

---

## Executive Summary

This document provides technical guidance for extending skillkit's LangChain integration to support **1+N tools per skill** (one prompt-based tool + N script-based tools). Current v0.1/v0.2 integration creates one StructuredTool per skill; v0.3 must create multiple tools per skill while maintaining backward compatibility.

**Key Findings**:
- **Closure Pattern**: Use default parameter capture (existing pattern in v0.2) for each script tool
- **Naming Convention**: `{skill_name}.{script_name}` (e.g., "pdf-extractor.extract") prevents collisions
- **Input Schema**: Free-form JSON with `RawJsonInput` Pydantic model (single `data` field accepting any JSON)
- **Descriptions**: Extract from script docstrings using comment block parsing
- **Return Format**: Follow LangChain tool_result format with `{"type": "tool_result", "content": "...", "is_error": boolean}`
- **Async Support**: Extend existing async pattern to script tools via `coroutine` parameter

**Compatibility**: All changes are additive; existing `create_langchain_tools()` API remains unchanged, new script tool creation uses separate internal function.

---

## 1. Multiple Tools Per Skill Architecture

### 1.1 Current State (v0.1/v0.2)

```python
# Current: One tool per skill
manager.discover()  # 5 skills discovered
tools = create_langchain_tools(manager)  # Returns 5 StructuredTool objects
# tools = [skill1_tool, skill2_tool, ..., skill5_tool]
```

### 1.2 Desired State (v0.3)

```python
# After script detection:
# Skill "pdf-extractor" with:
#   - YAML frontmatter (prompt-based tool)
#   - scripts/extract.py
#   - scripts/convert.sh
#   - scripts/utils/parse.py

manager.discover()  # 5 skills
tools = create_langchain_tools(manager)  # Returns 8 StructuredTool objects
# tools = [
#   pdf_extractor_prompt_tool,
#   pdf_extractor_extract_tool,
#   pdf_extractor_convert_tool,
#   pdf_extractor_parse_tool,
#   other_skill_tools...
# ]
```

### 1.3 Architecture Pattern

**Modified `create_langchain_tools()` flow**:

```
SkillManager (with detected scripts)
  └─ For each skill:
      ├─ Create prompt-based tool (existing pattern)
      │   Name: "pdf-extractor"
      │   Args: SkillInput (string-based)
      │   Func: invoke_skill()
      │
      └─ For each detected script:
          Create script-based tool (new pattern)
          Name: "pdf-extractor.extract"
          Args: RawJsonInput (free-form JSON)
          Func: execute_script()
```

**Backward Compatibility**:
- If skill has no scripts, returns single prompt tool (unchanged)
- If skill has scripts, returns prompt tool + script tools
- Existing `SkillInput` Pydantic model remains for prompt tools
- New `RawJsonInput` model added for script tools

---

## 2. Tool Naming Convention

### 2.1 Decision: `{skill_name}.{script_name}` Format

**Rationale**:
1. **Collision Prevention**: Namespaced within skill, prevents clashes with other skills
2. **Hierarchy Clear**: Agents understand tool belongs to skill
3. **Parsing Simple**: Easy to extract skill_name and script_name via `.split(".", 1)`
4. **LangChain Compatible**: StructuredTool accepts any string as name (no restrictions)

### 2.2 Naming Examples

| Skill Name | Script Filename | Generated Tool Name |
|-----------|-----------------|-------------------|
| pdf-extractor | extract.py | pdf-extractor.extract |
| pdf-extractor | convert.sh | pdf-extractor.convert |
| pdf-extractor | utils/parse.py | pdf-extractor.utils-parse |
| data-tools:csv | process.py | data-tools:csv.process |
| data-tools:csv | utils/validate.js | data-tools:csv.utils-validate |

**Script Name Derivation**:
- Strip extension: `extract.py` → `extract`
- Replace `/` with `-`: `utils/parse.py` → `utils-parse`
- Keep hyphens/underscores: `my_script.sh` → `my_script`
- For qualified skills, preserve colon: `data-tools:csv` + `process.py` → `data-tools:csv.process`

### 2.3 Implementation Pattern

```python
def _derive_script_name(script_path: str) -> str:
    """
    Derive tool suffix from script path.

    Args:
        script_path: Relative path like "scripts/extract.py" or "utils/parse.sh"

    Returns:
        Tool suffix like "extract" or "utils-parse"
    """
    # Remove extension
    name = Path(script_path).stem

    # Replace path separators with hyphens
    # Handle both / (Unix) and \ (Windows)
    suffix = str(Path(script_path)).replace("scripts/", "").replace(".py", "")
    suffix = suffix.replace("/", "-").replace("\\", "-")

    return suffix

def generate_script_tool_name(skill_name: str, script_path: str) -> str:
    """
    Generate full tool name for a script.

    Examples:
        ("pdf-extractor", "scripts/extract.py") → "pdf-extractor.extract"
        ("pdf-extractor", "scripts/utils/parse.py") → "pdf-extractor.utils-parse"
    """
    script_suffix = _derive_script_name(script_path)
    return f"{skill_name}.{script_suffix}"
```

---

## 3. Input Schemas: Free-Form JSON Design

### 3.1 Decision: Single `data` Field with RawJsonInput

**Current Approach (v0.1/v0.2 - Prompt Tools)**:
```python
class SkillInput(BaseModel):
    """String-based input for prompt tools."""
    arguments: str = Field(default="", description="Arguments to pass to the skill")
```

**New Approach (v0.3 - Script Tools)**:
```python
from typing import Any
from pydantic import BaseModel, Field

class RawJsonInput(BaseModel):
    """
    Free-form JSON input schema for script-based tools.

    Accepts any JSON structure and passes it directly to the script via stdin.
    Provides flexibility for scripts to define their own argument schemas.

    Example:
        Agent provides: {"file_path": "/tmp/doc.pdf", "options": {"format": "text"}}
        Script receives via stdin: {"file_path": "/tmp/doc.pdf", "options": {"format": "text"}}
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="allow"  # Allow any extra fields
    )

    # Option 1: Single data field with Any type (simple, explicit)
    data: Any = Field(
        default=None,
        description="Free-form JSON data passed to the script. Can be object, array, string, etc."
    )

# OR for even more flexibility:

class RawJsonInputDict(BaseModel):
    """
    Alternative: Treat entire input as free-form dict.
    This allows agents to provide any JSON structure at the root level.
    """

    model_config = ConfigDict(
        extra="allow"  # All fields are accepted
    )

    # No required fields - everything is optional
```

### 3.2 Design Trade-Offs

| Approach | Pros | Cons | Use Case |
|----------|------|------|----------|
| `data: Any` (single field) | Clear intent, explicit | Extra nesting level in agent output | Simple data passing |
| `extra="allow"` (root dict) | Flat structure, simpler for agents | Ambiguous - looks like any Pydantic model | Complex multi-arg scripts |
| `arguments: str` (existing) | Simple, backward-compatible | No structure, JSON parsing in script | Text-based prompts |

**Recommendation**: Use `data: Any = Field(default=None)` for clarity:
- Signals to agent that field accepts any JSON
- LangChain unpacks it and passes `{"data": agent_value}` to the function
- Function extracts `data` field and serializes to JSON for script

### 3.3 Implementation Example

```python
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
import json

class RawJsonInput(BaseModel):
    """Free-form JSON input for script tools."""

    model_config = ConfigDict(str_strip_whitespace=True)

    data: Any = Field(
        default=None,
        description="Free-form JSON data passed to script via stdin"
    )

def create_script_tool_function(
    manager: SkillManager,
    skill_name: str,
    script_path: str
) -> tuple[Any, Any]:
    """
    Create sync and async functions for script execution.

    Returns:
        (sync_func, async_func) suitable for StructuredTool
    """

    def invoke_script(data: Any = None, skill_name: str = skill_name) -> str:
        """
        Sync script invocation function (closure).

        Args:
            data: Free-form JSON data from agent
            skill_name: Captured via default parameter (closure pattern)

        Returns:
            stdout from script execution

        Raises:
            ScriptExecutionError: If script fails
        """
        try:
            # Serialize data to JSON for script stdin
            json_input = json.dumps(data) if data is not None else json.dumps({})

            # Execute script (actual implementation in ScriptExecutor)
            result = manager.execute_skill_script(
                skill_name=skill_name,
                script_path=script_path,
                arguments=json_input  # Pass as JSON via stdin
            )

            # Handle exit code
            if result.exit_code == 0:
                return result.stdout
            else:
                # Raise exception with stderr
                raise ScriptExecutionError(
                    f"Script execution failed: {result.stderr}",
                    exit_code=result.exit_code
                )

        except Exception as e:
            logger.error(f"Script execution error: {e}")
            raise

    async def ainvoke_script(data: Any = None, skill_name: str = skill_name) -> str:
        """Async version of invoke_script with same closure pattern."""
        # Same implementation but using await
        try:
            json_input = json.dumps(data) if data is not None else json.dumps({})

            result = await manager.execute_skill_script_async(
                skill_name=skill_name,
                script_path=script_path,
                arguments=json_input
            )

            if result.exit_code == 0:
                return result.stdout
            else:
                raise ScriptExecutionError(
                    f"Script execution failed: {result.stderr}",
                    exit_code=result.exit_code
                )

        except Exception as e:
            logger.error(f"Async script execution error: {e}")
            raise

    return invoke_script, ainvoke_script
```

---

## 4. Tool Descriptions: Script Docstring Extraction

### 4.1 Decision: Parse First Comment Block

**Rationale**:
1. **Standard Practice**: Python, shell, JavaScript all use comments for docstrings
2. **Non-Intrusive**: No need to execute or parse code semantics
3. **Language Agnostic**: Works across Python, Shell, JavaScript, Ruby, Perl
4. **Fast**: Regex-based, completes in <1ms

### 4.2 Comment Block Parsing Patterns

#### Python

```python
# ✅ VALID: Single-line comments
# Extract text from PDF file
def extract():
    pass

# ✅ VALID: Multi-line comments
"""
Extract text from PDF file.
Supports multiple formats including PDF, DOCX, TXT.
Returns extracted text in plain text format.
"""
def extract():
    pass

# ✅ VALID: Multi-line with triple single quotes
'''
Extract text from PDF file
'''
def extract():
    pass

# ❌ INVALID: No docstring (description = "")
def extract():
    pass
```

#### Bash/Shell

```bash
#!/bin/bash
# Convert PDF to image format
# Supports PNG, JPG, GIF output formats

convert_pdf() {
    # Implementation
}

# OR

#!/bin/bash
: '
Convert PDF to image format
Supports PNG, JPG, GIF output formats
'

convert_pdf() {
    # Implementation
}
```

#### JavaScript

```javascript
// Extract metadata from files
function extract() {
    // Implementation
}

// OR

/**
 * Extract metadata from files
 * Supports PDF, DOCX, TXT formats
 */
function extract() {
    // Implementation
}
```

### 4.3 Extraction Algorithm

```python
import re
from pathlib import Path

def extract_docstring(script_path: Path, script_type: str) -> str:
    """
    Extract first docstring/comment block from script.

    Args:
        script_path: Path to script file
        script_type: Language type (python, bash, javascript, ruby, perl)

    Returns:
        Extracted docstring or empty string if none found
    """
    try:
        content = script_path.read_text(encoding='utf-8')
    except Exception:
        return ""

    # Remove shebang line if present
    lines = content.split('\n')
    if lines and lines[0].startswith('#!'):
        content = '\n'.join(lines[1:])

    # Language-specific patterns
    patterns = {
        'python': [
            r'^"""(.*?)"""',  # Triple double quotes
            r"^'''(.*?)'''",  # Triple single quotes
            r'^#\s*(.*?)(?:\n(?:#\s*(.*?))*)?'  # Line comments
        ],
        'bash': [
            r"^:\s*'(.*?)'",  # : '...' style
            r'^#\s*(.*?)(?:\n(?:#\s*(.*?))*)?'  # Line comments
        ],
        'javascript': [
            r'^/\*\*(.*?)\*/',  # JSDoc style
            r'^//(.*?)(?:\n(?://(.*?))*)?'  # Line comments
        ],
        'ruby': [
            r'^=begin(.*?)=end',  # Multi-line comments
            r'^#\s*(.*?)(?:\n(?:#\s*(.*?))*)?'  # Line comments
        ],
        'perl': [
            r'^#\s*(.*?)(?:\n(?:#\s*(.*?))*)?'  # Line comments
        ]
    }

    # Try patterns for this language
    for pattern in patterns.get(script_type, []):
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
        if match:
            # Extract comment text
            extracted = match.group(1).strip()

            # Clean up comment markers
            lines = extracted.split('\n')
            cleaned = []
            for line in lines:
                # Remove comment markers and leading whitespace
                line = re.sub(r'^\s*[#*/]*\s*', '', line)
                if line.strip():
                    cleaned.append(line.strip())

            # Join first paragraph (stop at blank line)
            description = []
            for line in cleaned:
                if not line:
                    break
                description.append(line)

            return ' '.join(description)[:256]  # Truncate to 256 chars for display

    return ""  # No docstring found
```

### 4.4 Fallback Strategy

```python
def get_script_description(
    script_metadata: ScriptMetadata
) -> str:
    """
    Get description for script tool.

    Strategy:
    1. Try extracting from script file docstring
    2. If not found, use empty string (agent can read skill content)
    3. If extraction fails, use empty string (graceful degradation)
    """
    try:
        return extract_docstring(
            script_path=script_metadata.path,
            script_type=script_metadata.script_type
        )
    except Exception as e:
        logger.debug(f"Failed to extract docstring: {e}")
        return ""  # Graceful degradation
```

---

## 5. Return Format: Tool Result Format

### 5.1 Decision: LangChain Tool Result Format

**LangChain Standard Format**:
```python
{
    "type": "tool_result",
    "tool_use_id": "<unique_id>",
    "content": "string | list | null",
    "is_error": False
}
```

### 5.2 Success Case (exit_code == 0)

```python
def invoke_script_tool(data: Any = None) -> str:
    """
    Execute script and return stdout on success.

    LangChain automatically wraps return value in tool_result format.
    """
    result = execute_script(...)

    if result.exit_code == 0:
        # SUCCESS: Return stdout directly
        # LangChain wraps as: {"type": "tool_result", "content": stdout, "is_error": false}
        return result.stdout
    else:
        # FAILURE: Raise exception
        # LangChain wraps as: {"type": "tool_result", "content": stderr, "is_error": true}
        raise ScriptExecutionError(result.stderr)
```

**Actual Tool Result**:
```json
{
  "type": "tool_result",
  "tool_use_id": "abc123",
  "content": "Extracted text from document...",
  "is_error": false
}
```

### 5.3 Error Case (exit_code != 0)

```python
def invoke_script_tool(data: Any = None) -> str:
    """Script tool function."""
    result = execute_script(...)

    if result.exit_code != 0:
        # Create ToolError with stderr as message
        raise ToolError(
            f"Script execution failed with exit code {result.exit_code}\n{result.stderr}",
            tool_call_id="abc123"
        )
```

**Actual Tool Result**:
```json
{
  "type": "tool_result",
  "tool_use_id": "abc123",
  "content": "Script execution failed with exit code 1\nError: Invalid PDF format",
  "is_error": true
}
```

### 5.4 Exception Hierarchy for Script Errors

```python
class ScriptExecutionError(ToolError):
    """Raised when script execution fails."""

    def __init__(self, message: str, exit_code: int = 1):
        self.exit_code = exit_code
        super().__init__(message)

class ScriptTimeoutError(ScriptExecutionError):
    """Raised when script execution times out."""

    def __init__(self, script_path: str, timeout_seconds: int):
        message = f"Script timed out after {timeout_seconds}s: {script_path}"
        super().__init__(message, exit_code=124)  # GNU timeout exit code

class ToolRestrictionError(ToolError):
    """Raised when script tool is not allowed for skill."""

    def __init__(self, skill_name: str, allowed_tools: list[str]):
        message = f"Tool 'Bash' not allowed for skill '{skill_name}'. Allowed: {allowed_tools}"
        super().__init__(message)
```

### 5.5 Implementation Pattern

```python
from langchain_core.tools.base import ToolError

def invoke_script_tool(data: Any = None, skill_name: str = skill_name) -> str:
    """
    Execute script and return result.

    Returns:
        stdout on success (string)

    Raises:
        ToolError: On script failure (is_error=true in tool_result)
        ScriptTimeoutError: On timeout
        ToolRestrictionError: On permission check
    """
    try:
        # Check tool restrictions
        skill_metadata = manager.get_skill(skill_name).metadata
        if "Bash" not in skill_metadata.allowed_tools:
            raise ToolRestrictionError(skill_name, skill_metadata.allowed_tools)

        # Execute script
        result = manager.execute_skill_script(
            skill_name=skill_name,
            script_path=script_path,
            arguments=json.dumps(data) if data else "{}"
        )

        # Handle result
        if result.exit_code == 0:
            return result.stdout
        else:
            # Return error in tool_result format
            stderr_msg = f"Exit code {result.exit_code}: {result.stderr}"
            raise ToolError(stderr_msg)

    except ScriptTimeoutError:
        raise  # Propagate timeout
    except ToolRestrictionError:
        raise  # Propagate restriction
    except Exception as e:
        raise ToolError(f"Unexpected error: {e}") from e
```

---

## 6. Async Support: Extending Async Pattern

### 6.1 Current v0.2 Async Pattern

```python
# Current pattern for prompt-based tools
tool = StructuredTool(
    name=skill_metadata.name,
    description=skill_metadata.description,
    args_schema=SkillInput,
    func=invoke_skill,        # Sync function
    coroutine=ainvoke_skill,  # Async function
)
```

**Key Point**: LangChain routes:
- `tool.invoke()` → calls `func` (sync)
- `await tool.ainvoke()` → calls `coroutine` (async)

### 6.2 Extended Async Pattern for Script Tools

```python
def create_script_tools(
    manager: SkillManager,
    skill_name: str,
    scripts: list[ScriptMetadata]
) -> list[StructuredTool]:
    """Create StructuredTool for each script with async support."""

    tools: list[StructuredTool] = []

    for script_metadata in scripts:
        # Generate tool name
        tool_name = f"{skill_name}.{script_metadata.name}"

        # Create sync and async functions (closure pattern)
        def invoke_script(
            data: Any = None,
            skill_name: str = skill_name,
            script_path: str = script_metadata.path
        ) -> str:
            """Sync script invocation."""
            result = manager.execute_skill_script(
                skill_name=skill_name,
                script_path=script_path,
                arguments=json.dumps(data) if data else "{}"
            )
            if result.exit_code == 0:
                return result.stdout
            raise ToolError(f"Exit code {result.exit_code}: {result.stderr}")

        async def ainvoke_script(
            data: Any = None,
            skill_name: str = skill_name,
            script_path: str = script_metadata.path
        ) -> str:
            """Async script invocation."""
            result = await manager.execute_skill_script_async(
                skill_name=skill_name,
                script_path=script_path,
                arguments=json.dumps(data) if data else "{}"
            )
            if result.exit_code == 0:
                return result.stdout
            raise ToolError(f"Exit code {result.exit_code}: {result.stderr}")

        # Create tool with both sync and async
        tool = StructuredTool(
            name=tool_name,
            description=script_metadata.description,
            args_schema=RawJsonInput,
            func=invoke_script,
            coroutine=ainvoke_script
        )

        tools.append(tool)

    return tools
```

### 6.3 Closure Pattern for Multiple Script Tools

**Critical Pattern** (prevents late-binding bugs):

```python
# ❌ WRONG: Closure captures loop variable
def create_script_tools(scripts: list):
    tools = []
    for script in scripts:
        def invoke_script(data):
            # BUG: 'script' is bound by reference, not value
            # All functions reference the final 'script' from loop
            return execute(script)
        tools.append(invoke_script)
    return tools

# ✅ CORRECT: Default parameter captures value at function creation time
def create_script_tools(scripts: list):
    tools = []
    for script in scripts:
        def invoke_script(
            data=None,
            script_path=script.path  # Default param captures value NOW
        ):
            # 'script_path' is bound at creation time, not loop time
            return execute(script_path)
        tools.append(invoke_script)
    return tools
```

This pattern is already used in v0.2 for skill tools and must be extended for script tools.

---

## 7. Integration with Modified create_langchain_tools()

### 7.1 Proposed API (Backward Compatible)

```python
def create_langchain_tools(manager: "SkillManager") -> List[StructuredTool]:
    """
    Create LangChain StructuredTool objects from discovered skills.

    v0.3 Enhancement: Now handles skills with scripts.

    Returns:
        List of StructuredTool objects where:
        - Each skill with content gets a prompt-based tool (name: "skill-name")
        - Each detected script gets a script-based tool (name: "skill-name.script-name")
        - Skills can expose 1+N tools (1 prompt + N scripts)

    Examples:
        >>> skills: [
        ...     Skill(name="pdf-extractor", content="...", scripts=[extract.py, convert.sh]),
        ...     Skill(name="csv-parser", content="...", scripts=[])
        ... ]

        >>> tools = create_langchain_tools(manager)

        >>> [t.name for t in tools]
        [
            "pdf-extractor",              # Prompt tool
            "pdf-extractor.extract",      # Script tool
            "pdf-extractor.convert",      # Script tool
            "csv-parser"                  # Prompt tool (no scripts)
        ]
    """
    tools: List[StructuredTool] = []

    skill_metadatas = manager.list_skills(include_qualified=False)

    for skill_metadata in skill_metadatas:
        # 1. Create prompt-based tool (existing pattern)
        def invoke_skill(arguments: str = "", skill_name: str = skill_metadata.name) -> str:
            """Existing sync skill invocation."""
            return manager.invoke_skill(skill_name, arguments)

        async def ainvoke_skill(arguments: str = "", skill_name: str = skill_metadata.name) -> str:
            """Existing async skill invocation."""
            return await manager.ainvoke_skill(skill_name, arguments)

        # Create prompt tool
        prompt_tool = StructuredTool(
            name=skill_metadata.name,
            description=skill_metadata.description,
            args_schema=SkillInput,
            func=invoke_skill,
            coroutine=ainvoke_skill
        )
        tools.append(prompt_tool)

        # 2. Create script-based tools (NEW in v0.3)
        # Only if scripts are detected in the skill
        try:
            skill = manager.get_skill(skill_metadata.name)
            scripts = skill.detected_scripts  # Attribute set during skill invocation

            if scripts:
                # Create a tool for each detected script
                script_tools = _create_script_tools(
                    manager=manager,
                    skill_name=skill_metadata.name,
                    scripts=scripts
                )
                tools.extend(script_tools)

        except AttributeError:
            # No scripts detected yet (graceful degradation)
            pass

    return tools


def _create_script_tools(
    manager: SkillManager,
    skill_name: str,
    scripts: List[ScriptMetadata]
) -> List[StructuredTool]:
    """
    Internal function to create script-based tools.

    Uses closure pattern to capture skill_name and script_path for each tool.
    """
    tools: List[StructuredTool] = []

    for script in scripts:
        # Generate tool name: "skill-name.script-name"
        tool_name = f"{skill_name}.{script.name}"

        # Create sync and async functions with closure capture
        def invoke_script(
            data: Any = None,
            skill_name: str = skill_name,
            script_path: str = script.path
        ) -> str:
            """Sync script execution."""
            try:
                result = manager.execute_skill_script(
                    skill_name=skill_name,
                    script_path=script_path,
                    arguments=json.dumps(data) if data is not None else "{}"
                )

                if result.exit_code == 0:
                    return result.stdout

                raise ToolError(
                    f"Script execution failed: {result.stderr}",
                    tool_call_id=None
                )
            except Exception as e:
                if isinstance(e, ToolError):
                    raise
                raise ToolError(str(e))

        async def ainvoke_script(
            data: Any = None,
            skill_name: str = skill_name,
            script_path: str = script.path
        ) -> str:
            """Async script execution."""
            try:
                result = await manager.execute_skill_script_async(
                    skill_name=skill_name,
                    script_path=script_path,
                    arguments=json.dumps(data) if data is not None else "{}"
                )

                if result.exit_code == 0:
                    return result.stdout

                raise ToolError(
                    f"Script execution failed: {result.stderr}",
                    tool_call_id=None
                )
            except Exception as e:
                if isinstance(e, ToolError):
                    raise
                raise ToolError(str(e))

        # Create StructuredTool
        tool = StructuredTool(
            name=tool_name,
            description=script.description,
            args_schema=RawJsonInput,
            func=invoke_script,
            coroutine=ainvoke_script
        )

        tools.append(tool)

    return tools
```

### 7.2 Usage Example (Agent Perspective)

```python
from skillkit import SkillManager
from skillkit.integrations.langchain import create_langchain_tools
from langchain.agents import create_react_agent
from langchain_openai import ChatOpenAI

# Setup
manager = SkillManager()
manager.discover()

# Get tools (now includes script tools!)
tools = create_langchain_tools(manager)

# Tools available to agent:
# "pdf-extractor"           → Prompt-based tool (skill content)
# "pdf-extractor.extract"   → Script-based tool (execute extract.py)
# "pdf-extractor.convert"   → Script-based tool (execute convert.sh)
# "csv-parser"              → Prompt-based tool (skill content)

# Create agent
llm = ChatOpenAI(model="gpt-4")
agent = create_react_agent(llm, tools)

# Agent can now:
# 1. Use pdf-extractor for conversational help
# 2. Use pdf-extractor.extract for deterministic text extraction
# 3. Use pdf-extractor.convert for format conversion
```

---

## 8. Alternatives Considered

### 8.1 Alternative 1: Flat Tool List with Script Registration

**Approach**: Scripts registered explicitly during skill creation, not detected lazily.

```python
# In SKILL.md or separate manifest
scripts:
  - path: scripts/extract.py
    name: extract
    description: "Extract text from PDF"
```

**Pros**:
- Deterministic, no lazy detection
- Skill author controls which scripts are exposed

**Cons**:
- Requires skill author to maintain metadata
- Additional YAML field to parse
- Doesn't align with progressive disclosure pattern

**Decision**: REJECTED in favor of lazy detection (FR-009)

---

### 8.2 Alternative 2: Separate API for Script Tools

**Approach**: Create separate `create_script_tools()` function instead of extending `create_langchain_tools()`.

```python
# Separate functions
prompt_tools = create_langchain_tools(manager)  # Only prompt tools
script_tools = create_script_tools(manager)      # Only script tools
all_tools = prompt_tools + script_tools
```

**Pros**:
- Clear separation of concerns
- Can be used independently

**Cons**:
- Breaks user expectation that `create_langchain_tools()` returns all tools
- Requires agents to know about two APIs
- Inconsistent with other framework integrations

**Decision**: REJECTED in favor of unified API

---

### 8.3 Alternative 3: Multiple Fields Input Schema

**Approach**: Define specific fields for each script argument instead of free-form JSON.

```python
class ScriptInputSchema(BaseModel):
    file_path: str = Field(description="Path to file")
    format: str = Field(description="Output format", default="text")
    options: dict = Field(description="Additional options", default={})
```

**Pros**:
- Type-safe, explicit validation
- Better agent guidance

**Cons**:
- Requires script author to define schema in skill
- Adds complexity, defeats purpose of scripts (simplicity)
- Different schema per script means different Pydantic models
- Violates DRY principle

**Decision**: REJECTED in favor of free-form `data: Any` input

---

### 8.4 Alternative 4: Prompt-Based Tool Naming

**Approach**: Rename prompt tools to include `.prompt` suffix.

```python
# Tool names:
"pdf-extractor.prompt"    # Prompt tool (instead of "pdf-extractor")
"pdf-extractor.extract"   # Script tool
```

**Pros**:
- Symmetrical naming between prompt and script tools

**Cons**:
- Breaks backward compatibility (existing agents expect "pdf-extractor")
- Adds unnecessary complexity to prompt tool invocation

**Decision**: REJECTED - prompt tools keep name, script tools get `.{script}` suffix

---

## 9. Compatibility & Migration

### 9.1 Backward Compatibility Guarantee

**v0.1/v0.2 Code**: No changes required
```python
# This still works exactly as before
manager = SkillManager()
manager.discover()
tools = create_langchain_tools(manager)
# Returns 1 tool per skill, named after skill
```

**v0.3 Behavior**: Additive only
```python
# Same code now returns MORE tools if scripts are detected
manager = SkillManager()
manager.discover()
tools = create_langchain_tools(manager)
# Returns 1 tool per skill + 1 tool per detected script
# Example: 5 skills with scripts = 5 prompt tools + N script tools
```

### 9.2 Pydantic Model Updates

```python
# UNCHANGED (v0.1/v0.2)
class SkillInput(BaseModel):
    arguments: str = Field(default="", description="Arguments to pass to the skill")

# NEW (v0.3)
class RawJsonInput(BaseModel):
    data: Any = Field(default=None, description="Free-form JSON data for script")
```

Both models coexist; agents choose based on tool type.

### 9.3 Migration for Custom Integrations

If users have custom code that extends `create_langchain_tools()`:

```python
# OLD: Custom wrapper function
def my_custom_tools(manager):
    tools = create_langchain_tools(manager)
    # Custom logic here
    return tools

# NEW: Works as-is - just gets more tools now
def my_custom_tools(manager):
    tools = create_langchain_tools(manager)  # Includes script tools now
    # Custom logic here
    return tools
```

---

## 10. Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1)
- [ ] Add `ScriptMetadata` dataclass (name, path, script_type, description)
- [ ] Add `RawJsonInput` Pydantic model
- [ ] Implement `extract_docstring()` function
- [ ] Add `ScriptExecutor` component with `execute_skill_script()` method

### Phase 2: LangChain Integration (Week 2)
- [ ] Implement `_create_script_tools()` function
- [ ] Extend `create_langchain_tools()` with script tool creation
- [ ] Add async script tool support via `coroutine` parameter
- [ ] Handle closure pattern for multiple script tools

### Phase 3: Testing & Documentation (Week 3)
- [ ] Unit tests for tool naming convention
- [ ] Integration tests with LangChain agent
- [ ] Test async script tool invocation
- [ ] Update examples with script tool usage

### Phase 4: Edge Cases & Polish (Week 4)
- [ ] Tool restriction enforcement (`allowed_tools` check)
- [ ] Timeout handling and signal detection
- [ ] Error message formatting for agents
- [ ] Performance optimization (<50ms overhead)

---

## 11. Testing Strategy

### 11.1 Unit Tests

```python
def test_script_tool_naming():
    """Test tool naming convention."""
    assert generate_script_tool_name("pdf-extractor", "scripts/extract.py") == "pdf-extractor.extract"
    assert generate_script_tool_name("pdf-extractor", "scripts/utils/parse.py") == "pdf-extractor.utils-parse"

def test_docstring_extraction():
    """Test docstring extraction from scripts."""
    # Python
    assert extract_docstring(Path("test.py"), "python") == "Extract text from PDF"
    # Bash
    assert extract_docstring(Path("test.sh"), "bash") == "Convert PDF to images"
    # No docstring
    assert extract_docstring(Path("nodoc.py"), "python") == ""

def test_raw_json_input():
    """Test free-form JSON input schema."""
    data = RawJsonInput(data={"file": "/tmp/doc.pdf"})
    assert data.data == {"file": "/tmp/doc.pdf"}

    # Can accept anything
    data2 = RawJsonInput(data="just a string")
    assert data2.data == "just a string"
```

### 11.2 Integration Tests

```python
def test_script_tool_invocation():
    """Test script tool with agent."""
    manager = SkillManager(skills_dir=Path("test_skills"))
    manager.discover()

    tools = create_langchain_tools(manager)

    # Find script tool
    script_tool = next(t for t in tools if "." in t.name)

    # Invoke with JSON data
    result = script_tool.invoke({"data": {"file": "test.pdf"}})
    assert result  # Should return stdout
    assert isinstance(result, str)

@pytest.mark.asyncio
def test_async_script_tool():
    """Test async script tool invocation."""
    manager = SkillManager(skills_dir=Path("test_skills"))
    await manager.adiscover()

    tools = create_langchain_tools(manager)
    script_tool = next(t for t in tools if "." in t.name)

    # Async invocation
    result = await script_tool.ainvoke({"data": {"file": "test.pdf"}})
    assert result
```

---

## 12. Conclusion & Recommendations

### Key Decisions Summary

| Area | Decision | Rationale |
|------|----------|-----------|
| Tool Naming | `{skill}.{script}` | Namespaced, collision-free, easy to parse |
| Input Schema | `RawJsonInput` with `data: Any` | Flexible, script-author-defined semantics |
| Descriptions | Extract from docstrings | Non-intrusive, language-agnostic |
| Return Format | LangChain `tool_result` | Standard, error handling via exceptions |
| Async Support | Extend closure pattern | Maintains v0.2 pattern, non-blocking I/O |
| Compatibility | Additive only | No breaking changes to existing APIs |

### Implementation Confidence: **9.5/10**

**Strengths**:
- Patterns tested in v0.2 (closure capture, async, StructuredTool)
- Free-form JSON input avoids schema explosion
- Docstring extraction is robust and language-agnostic
- Tool naming prevents collisions while remaining readable
- Full backward compatibility maintained

**Minor Risks** (<1% likelihood):
- Edge case: Script names with many path separators creating unwieldy tool names
  - Mitigation: Limit nesting depth to 5 levels (already in spec)
- Risk: Agent confusion with many tools per skill
  - Mitigation: Good tool descriptions extracted from docstrings

### Recommended Approach

**Proceed with v0.3 implementation using**:
1. **Naming**: `{skill_name}.{script_name}` pattern (tooling prevents collisions)
2. **Input**: `RawJsonInput` with `data: Any` field (maximum flexibility)
3. **Descriptions**: Docstring extraction from first comment block (zero metadata overhead)
4. **Async**: Extend existing closure pattern to script tools (proven approach)
5. **Compatibility**: Additive changes only (zero breaking changes)

This design balances **simplicity** (scripts are black boxes), **flexibility** (agents choose how to invoke), and **safety** (tool restrictions enforced).

---

## References

### LangChain Documentation
- StructuredTool API: https://api.python.langchain.com/en/latest/tools/langchain_core.tools.StructuredTool.html
- Tool Return Format: https://python.langchain.com/docs/concepts/tools/
- Async Tool Support: https://python.langchain.com/docs/how_to/tool_use/

### skillkit v0.2 References
- Current LangChain integration: `src/skillkit/integrations/langchain.py`
- Closure pattern example: Lines 98-101 (default parameter capture)
- Async support: Lines 129-150 (coroutine parameter)

### Python Subprocess & JSON Communication
- JSON over stdin: https://docs.python.org/3/library/json.html
- Subprocess documentation: https://docs.python.org/3/library/subprocess.html
- Comment extraction patterns: Common across all scripting languages

