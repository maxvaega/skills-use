"""LangChain integration for skills-use library.

This module provides adapters to convert discovered skills into LangChain
StructuredTool objects for use with LangChain agents.

Installation:
    pip install skills-use[langchain]
"""

from typing import TYPE_CHECKING, List

# Import guards for optional dependencies
try:
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel, ConfigDict, Field
except ImportError as e:
    raise ImportError(
        "LangChain integration requires additional dependencies. "
        "Install with: pip install skills-use[langchain]"
    ) from e

if TYPE_CHECKING:
    from skills_use.core.manager import SkillManager


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
    """Create LangChain StructuredTool objects from discovered skills.

    Note: Tools use synchronous invocation. When used in async agents,
    LangChain automatically wraps calls in asyncio.to_thread() with
    ~1-2ms overhead. For native async support, see v0.2.

    CRITICAL PATTERN: Uses default parameter (skill_name=skill_metadata.name)
    to capture the skill name at function creation time. This prevents Python's
    late-binding closure issue where all functions would reference the final
    loop value.

    Args:
        manager: SkillManager instance with discovered skills

    Returns:
        List of StructuredTool objects ready for agent use

    Raises:
        Various skills-use exceptions during tool invocation (bubbled up)

    Example:
        >>> from skills_use import SkillManager
        >>> from skills_use.integrations.langchain import create_langchain_tools

        >>> manager = SkillManager()
        >>> manager.discover()

        >>> tools = create_langchain_tools(manager)
        >>> print(f"Created {len(tools)} tools")
        Created 5 tools

        >>> # Use with LangChain agent
        >>> from langchain.agents import create_react_agent
        >>> from langchain_openai import ChatOpenAI

        >>> llm = ChatOpenAI(model="gpt-4")
        >>> agent = create_react_agent(llm, tools)
    """
    tools: List[StructuredTool] = []

    for skill_metadata in manager.list_skills():
        # CRITICAL: Use default parameter to capture skill name at function creation
        # Without this, all functions would reference the final loop value (Python late binding)
        def invoke_skill(skill_input: SkillInput, skill_name: str = skill_metadata.name) -> str:
            """Invoke skill with arguments.

            This function is created dynamically for each skill, with the skill
            name captured via default parameter to avoid late-binding issues.

            Args:
                skill_input: Pydantic model containing arguments
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
            # 1. Let skills-use exceptions bubble up (detailed error messages)
            # 2. LangChain catches and formats them for agent
            # 3. Agent decides whether to retry or report to user
            return manager.invoke_skill(skill_name, skill_input.arguments)

        # Create StructuredTool with skill metadata
        tool = StructuredTool(
            name=skill_metadata.name,
            description=skill_metadata.description,
            args_schema=SkillInput,
            func=invoke_skill,
        )

        tools.append(tool)

    return tools
