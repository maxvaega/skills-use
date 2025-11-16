"""LangChain integration for skillkit library.

This module provides adapters to convert discovered skills into LangChain
StructuredTool objects for use with LangChain agents.

Installation:
    pip install skillkit[langchain]
"""

from typing import TYPE_CHECKING, List

# Import guards for optional dependencies
try:
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel, ConfigDict, Field
except ImportError as e:
    raise ImportError(
        "LangChain integration requires additional dependencies. "
        "Install with: pip install skillkit[langchain]"
    ) from e

if TYPE_CHECKING:
    from skillkit.core.manager import SkillManager
    from skillkit.core.models import SkillMetadata


class SkillInput(BaseModel):
    """Pydantic schema for skill tool input.

    Configuration:
        - str_strip_whitespace: True (automatically strips leading/trailing whitespace)

    Fields:
        - arguments: String input for skill invocation (default: empty string)
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    arguments: str = Field(default="", description="Arguments to pass to the skill")


def create_langchain_tools(manager: "SkillManager") -> List[StructuredTool]:
    """Create LangChain StructuredTool objects from discovered skills with async support.

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

    Raises:
        Various skillkit exceptions during tool invocation (bubbled up)

    Example (Sync Agent):
        >>> from skillkit import SkillManager
        >>> from skillkit.integrations.langchain import create_langchain_tools

        >>> manager = SkillManager()
        >>> manager.discover()

        >>> tools = create_langchain_tools(manager)
        >>> print(f"Created {len(tools)} tools")
        Created 5 tools

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

    return tools
