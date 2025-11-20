"""LangChain integration for skillkit library.

This module provides adapters to convert discovered skills into LangChain
StructuredTool objects for use with LangChain agents.

Installation:
    pip install skillkit[langchain]
"""

from typing import TYPE_CHECKING, Any, Dict, List, TypedDict

# Import guards for optional dependencies
try:
    from langchain_core.tools import StructuredTool, ToolException
    from pydantic import BaseModel, ConfigDict, Field
except ImportError as e:
    raise ImportError(
        "LangChain integration requires additional dependencies. "
        "Install with: pip install skillkit[langchain]"
    ) from e

if TYPE_CHECKING:
    from skillkit.core.manager import SkillManager
    from skillkit.core.models import Skill, SkillMetadata


class ScriptToolResult(TypedDict):
    """Return format for LangChain script tools.

    Follows LangChain tool result protocol:
    - On success (exit_code==0): content = stdout, is_error = False
    - On failure (exit_code!=0): raise ToolException with stderr message

    This TypedDict documents the expected structure, but tools
    typically return just the content string or raise exceptions.
    """

    type: str  # Always "tool_result"
    tool_use_id: str  # Unique identifier for this invocation
    content: "str | list[str] | None"  # stdout on success, None on error
    is_error: bool  # False on success, True on error


class SkillInput(BaseModel):
    """Pydantic schema for skill tool input.

    Configuration:
        - str_strip_whitespace: True (automatically strips leading/trailing whitespace)

    Fields:
        - arguments: String input for skill invocation (default: empty string)
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    arguments: str = Field(default="", description="Arguments to pass to the skill")


class ScriptInput(BaseModel):
    """Pydantic schema for script tool input.

    Configuration:
        - arbitrary_types_allowed: True (allows any JSON-serializable types)

    Fields:
        - arguments: Free-form dictionary containing script arguments
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    arguments: Dict[str, Any] = Field(
        default_factory=dict,
        description="JSON-serializable arguments to pass to the script via stdin",
    )


def create_langchain_tools(manager: "SkillManager") -> List[StructuredTool]:
    """Create LangChain StructuredTool objects from discovered skills with async support.

    Creates tools for both prompt-based skills and script-based skills:
    - Prompt-based tools: Named "{skill_name}" (e.g., "csv-parser")
    - Script-based tools: Named "{skill_name}.{script_name}" (e.g., "pdf-extractor.extract")

    Tools support both sync and async invocation patterns:
    - Sync agents: Use tool.invoke() → calls func parameter (sync)
    - Async agents: Use await tool.ainvoke() → calls coroutine parameter (async)

    CRITICAL PATTERN: Uses default parameter (skill_name=skill_metadata.name)
    to capture the skill name at function creation time. This prevents Python's
    late-binding closure issue where all functions would reference the final
    loop value.

    Args:
        manager: SkillManager instance with discovered skills

    Returns:
        List of StructuredTool objects ready for agent use (sync and async)
        Includes both prompt-based and script-based tools (v0.3+)

    Raises:
        Various skillkit exceptions during tool invocation (bubbled up)

    Example (Sync Agent):
        >>> from skillkit import SkillManager
        >>> from skillkit.integrations.langchain import create_langchain_tools

        >>> manager = SkillManager()
        >>> manager.discover()

        >>> tools = create_langchain_tools(manager)
        >>> print(f"Created {len(tools)} tools")
        Created 5 tools (3 prompt-based + 2 script-based)

        >>> # Use with sync LangChain agent
        >>> from langchain.agents import create_react_agent
        >>> from langchain_openai import ChatOpenAI

        >>> llm = ChatOpenAI(model="gpt-4")
        >>> agent = create_react_agent(llm, tools)

    Example (Async Agent):
        >>> # Initialize manager asynchronously
        >>> manager = SkillManager()
        >>> await manager.adiscover()

        >>> tools = create_langchain_tools(manager)

        >>> # Use with async LangChain agent
        >>> from langchain.agents import AgentExecutor
        >>> result = await executor.ainvoke({"input": "Use csv-parser skill"})
    """
    tools: List[StructuredTool] = []

    # Get skill metadata list (explicitly not qualified to get SkillMetadata objects)
    skill_metadatas: List[SkillMetadata] = manager.list_skills(include_qualified=False)  # type: ignore[assignment]

    for skill_metadata in skill_metadatas:
        # CRITICAL: Use default parameter to capture skill name at function creation
        # Without this, all functions would reference the final loop value (Python late binding)
        def invoke_skill(arguments: str = "", skill_name: str = skill_metadata.name) -> str:
            """Sync skill invocation for sync agents.

            This function is created dynamically for each skill, with the skill
            name captured via default parameter to avoid late-binding issues.

            Note: LangChain's StructuredTool unpacks the Pydantic model fields
            as kwargs, so we accept 'arguments' as a kwarg directly rather than
            receiving a SkillInput object.

            Args:
                arguments: Arguments to pass to the skill (from SkillInput.arguments)
                skill_name: Skill name (captured from outer scope via default)

            Returns:
                Processed skill content

            Raises:
                SkillNotFoundError: If skill no longer exists
                ContentLoadError: If skill file cannot be read
                ArgumentProcessingError: If processing fails
                SizeLimitExceededError: If arguments exceed 1MB
            """
            # Three-layer error handling approach:
            # 1. Let skillkit exceptions bubble up (detailed error messages)
            # 2. LangChain catches and formats them for agent
            # 3. Agent decides whether to retry or report to user
            return manager.invoke_skill(skill_name, arguments)

        async def ainvoke_skill(arguments: str = "", skill_name: str = skill_metadata.name) -> str:
            """Async skill invocation for async agents.

            This async function provides native async support for async agents,
            avoiding thread executor overhead. Uses the same closure capture
            pattern as the sync version.

            Args:
                arguments: Arguments to pass to the skill (from SkillInput.arguments)
                skill_name: Skill name (captured from outer scope via default)

            Returns:
                Processed skill content

            Raises:
                AsyncStateError: If manager was initialized with sync discover()
                SkillNotFoundError: If skill no longer exists
                ContentLoadError: If skill file cannot be read
                ArgumentProcessingError: If processing fails
                SizeLimitExceededError: If arguments exceed 1MB
            """
            return await manager.ainvoke_skill(skill_name, arguments)

        # Create StructuredTool with both sync and async support
        # LangChain automatically routes:
        # - tool.invoke() → func (sync)
        # - await tool.ainvoke() → coroutine (async)
        tool = StructuredTool(
            name=skill_metadata.name,
            description=skill_metadata.description,
            args_schema=SkillInput,
            func=invoke_skill,  # Sync version
            coroutine=ainvoke_skill,  # Async version (v0.2+)
        )

        tools.append(tool)

        # v0.3+: Also create script-based tools for this skill
        # Get the full Skill object (not just metadata) to access scripts property
        try:
            skill = manager.load_skill(skill_metadata.name)
            script_tools = create_script_tools(skill, manager)
            tools.extend(script_tools)
        except Exception:
            # If script detection fails, continue without script tools
            # This ensures backward compatibility and graceful degradation
            pass

    return tools


def create_script_tools(skill: "Skill", manager: "SkillManager") -> List[StructuredTool]:
    """Create LangChain StructuredTool objects for all scripts in a skill.

    Each script is exposed as a separate tool with format "{skill_name}.{script_name}".
    For example, if skill "pdf-extractor" has scripts "extract" and "convert",
    this function creates two tools: "pdf-extractor.extract" and "pdf-extractor.convert".

    Tools support both sync and async invocation patterns:
    - Sync agents: Use tool.invoke() → calls func parameter (sync)
    - Async agents: Use await tool.ainvoke() → calls coroutine parameter (async)

    Script execution behavior:
    - Arguments passed as JSON dict via stdin
    - On success (exit_code==0): Returns stdout string
    - On failure (exit_code!=0): Raises ToolException with stderr message
    - Timeouts enforced (default: 30s, configurable via manager.default_script_timeout)

    Args:
        skill: Skill object with detected scripts (accessed via skill.scripts property)
        manager: SkillManager instance for executing scripts

    Returns:
        List of StructuredTool objects, one per detected script

    Raises:
        Various skillkit exceptions during tool invocation (bubbled up as ToolException)

    Example:
        >>> from skillkit import SkillManager
        >>> from skillkit.integrations.langchain import create_script_tools

        >>> manager = SkillManager()
        >>> manager.discover()

        >>> skill = manager.get_skill("pdf-extractor")
        >>> script_tools = create_script_tools(skill, manager)
        >>> print(f"Created {len(script_tools)} script tools")
        Created 2 script tools

        >>> # Tool names: "pdf-extractor.extract", "pdf-extractor.convert"
        >>> for tool in script_tools:
        ...     print(f"  - {tool.name}: {tool.description}")

        >>> # Use with LangChain agent
        >>> from langchain.agents import AgentExecutor
        >>> executor = AgentExecutor(agent=agent, tools=script_tools)
    """
    tools: List[StructuredTool] = []

    # Access scripts via lazy-loaded property (triggers detection on first access)
    scripts = skill.scripts

    for script in scripts:
        # Get fully qualified tool name: "{skill_name}.{script_name}"
        tool_name = script.get_fully_qualified_name(skill.metadata.name)

        # Use description from script metadata (extracted from comments/docstrings)
        # Empty string if no description found (per FR-009)
        tool_description = (
            script.description if script.description else f"Execute {script.name} script"
        )

        # CRITICAL: Use default parameters to capture values at function creation time
        # This prevents Python's late-binding closure issue
        def invoke_script(
            arguments: Dict[str, Any] | None = None,
            skill_name: str = skill.metadata.name,
            script_name: str = script.name,
        ) -> str:
            if arguments is None:
                arguments = {}
            """Sync script execution wrapper for sync agents.

            Args:
                arguments: JSON-serializable dict to pass to script via stdin
                skill_name: Skill name (captured from outer scope via default)
                script_name: Script name (captured from outer scope via default)

            Returns:
                Script stdout on success (exit_code==0)

            Raises:
                ToolException: If script execution fails (exit_code!=0)
            """
            try:
                result = manager.execute_skill_script(
                    skill_name=skill_name,
                    script_name=script_name,
                    arguments=arguments,
                    timeout=None,  # Use manager's default_script_timeout
                )

                # Success: return stdout
                if result.exit_code == 0:
                    return result.stdout

                # Failure: raise ToolException with error details
                error_msg = f"Script failed with exit code {result.exit_code}"
                if result.stderr:
                    error_msg += f"\nError: {result.stderr}"
                if result.timeout:
                    error_msg += "\n(Script timed out)"
                if result.signal:
                    error_msg += f"\n(Killed by signal: {result.signal})"

                raise ToolException(error_msg)

            except Exception as e:
                # Convert skillkit exceptions to ToolException
                # This includes: ScriptNotFoundError, InterpreterNotFoundError,
                # PathSecurityError, ToolRestrictionError, etc.
                raise ToolException(f"Script execution error: {str(e)}") from e

        async def ainvoke_script(
            arguments: Dict[str, Any] | None = None,
            skill_name: str = skill.metadata.name,
            script_name: str = script.name,
        ) -> str:
            if arguments is None:
                arguments = {}
            """Async script execution wrapper for async agents.

            Args:
                arguments: JSON-serializable dict to pass to script via stdin
                skill_name: Skill name (captured from outer scope via default)
                script_name: Script name (captured from outer scope via default)

            Returns:
                Script stdout on success (exit_code==0)

            Raises:
                ToolException: If script execution fails (exit_code!=0)
            """
            # Note: execute_skill_script is not async, so we use sync version
            # Future v0.3.1+ could add aexecute_skill_script for true async
            try:
                result = manager.execute_skill_script(
                    skill_name=skill_name,
                    script_name=script_name,
                    arguments=arguments,
                    timeout=None,
                )

                if result.exit_code == 0:
                    return result.stdout

                error_msg = f"Script failed with exit code {result.exit_code}"
                if result.stderr:
                    error_msg += f"\nError: {result.stderr}"
                if result.timeout:
                    error_msg += "\n(Script timed out)"
                if result.signal:
                    error_msg += f"\n(Killed by signal: {result.signal})"

                raise ToolException(error_msg)

            except Exception as e:
                raise ToolException(f"Script execution error: {str(e)}") from e

        # Create StructuredTool with both sync and async support
        tool = StructuredTool(
            name=tool_name,  # "{skill_name}.{script_name}"
            description=tool_description,
            args_schema=ScriptInput,  # Free-form JSON dict
            func=invoke_script,  # Sync version
            coroutine=ainvoke_script,  # Async version
        )

        tools.append(tool)

    return tools
