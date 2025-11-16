"""LangChain integration tests for skillkit library.

Tests validate that create_langchain_tools() correctly converts discovered skills
into LangChain StructuredTool objects that can be invoked by agents.

Test Coverage:
    - Tool creation and structure validation
    - Tool invocation with various argument patterns
    - Error propagation from skills to LangChain
    - Large argument handling

Markers:
    - integration: LangChain framework integration tests
    - requires_langchain: Requires langchain-core package
"""

import pytest
from pathlib import Path

# Skip all tests in this file if langchain-core is not installed
pytest.importorskip("langchain_core")

from skillkit.core.manager import SkillManager
from skillkit.core.exceptions import SkillNotFoundError, SizeLimitExceededError
from skillkit.integrations.langchain import create_langchain_tools, SkillInput
from langchain_core.tools import StructuredTool


@pytest.mark.integration
@pytest.mark.requires_langchain
def test_create_langchain_tools_returns_list(isolated_manager, skill_factory):
    """Test create_langchain_tools() returns List[StructuredTool].

    Validates:
        - Return type is list
        - List contains StructuredTool instances
        - Empty manager returns empty list
    """
    # Test with empty directory
    isolated_manager.discover()
    tools = create_langchain_tools(isolated_manager)

    assert isinstance(tools, list)
    assert len(tools) == 0

    # Test with skills
    skill_factory("test-skill", "A test skill", "Content")
    isolated_manager.discover()
    tools = create_langchain_tools(isolated_manager)

    assert isinstance(tools, list)
    assert len(tools) == 1
    assert all(isinstance(tool, StructuredTool) for tool in tools)


@pytest.mark.integration
@pytest.mark.requires_langchain
def test_langchain_tool_count_matches_skills(isolated_manager, skill_factory):
    """Test that 3 skills create 3 StructuredTool objects.

    Validates:
        - One tool created per skill
        - Tool count matches skill count
        - All skills converted to tools
    """
    # Create 3 skills
    skill_factory("skill-1", "First skill", "Content 1")
    skill_factory("skill-2", "Second skill", "Content 2")
    skill_factory("skill-3", "Third skill", "Content 3")

    # Discover and convert to tools
    isolated_manager.discover()
    tools = create_langchain_tools(isolated_manager)

    # Verify count
    assert len(tools) == 3
    assert len(isolated_manager.list_skills()) == 3


@pytest.mark.integration
@pytest.mark.requires_langchain
def test_langchain_tool_has_correct_name(isolated_manager, skill_factory):
    """Test that tool.name matches skill name.

    Validates:
        - StructuredTool.name equals skill metadata name
        - Names preserved during conversion
        - Each tool has unique name
    """
    skill_factory("code-reviewer", "Reviews code quality", "Review this: $ARGUMENTS")
    skill_factory("test-generator", "Generates unit tests", "Generate tests for: $ARGUMENTS")

    isolated_manager.discover()
    tools = create_langchain_tools(isolated_manager)

    # Create name mapping
    tool_names = {tool.name for tool in tools}

    assert "code-reviewer" in tool_names
    assert "test-generator" in tool_names
    assert len(tool_names) == 2  # All unique


@pytest.mark.integration
@pytest.mark.requires_langchain
def test_langchain_tool_has_correct_description(temp_skills_dir, skill_factory):
    """Test that tool.description matches skill description.

    Validates:
        - StructuredTool.description equals skill metadata description
        - Descriptions preserved during conversion
        - Agents can see skill purpose
    """
    skill_factory("markdown-formatter", "Formats markdown documents", "Format: $ARGUMENTS")

    manager = SkillManager(temp_skills_dir)
    manager.discover()
    tools = create_langchain_tools(manager)

    tool = tools[0]
    assert tool.name == "markdown-formatter"
    assert tool.description == "Formats markdown documents"


@pytest.mark.integration
@pytest.mark.requires_langchain
def test_langchain_tool_invocation_with_arguments(temp_skills_dir, skill_factory):
    """Test tool.invoke({"arguments": "test"}) works correctly.

    Validates:
        - Tool invocation succeeds with arguments dict
        - Arguments passed through SkillInput schema
        - $ARGUMENTS placeholder substituted correctly
    """
    skill_factory("greeter", "Greets someone", "Hello $ARGUMENTS!")

    manager = SkillManager(temp_skills_dir)
    manager.discover()
    tools = create_langchain_tools(manager)

    tool = tools[0]
    # LangChain StructuredTool converts dict input to Pydantic model and passes to func
    result = tool.invoke(input={"arguments": "World"})

    # Result includes base directory prefix and full SKILL.md content (design choice)
    assert "Hello World!" in result
    assert "Base directory for this skill:" in result
    assert str(temp_skills_dir / "greeter") in result


@pytest.mark.integration
@pytest.mark.requires_langchain
def test_langchain_tool_invocation_returns_content(temp_skills_dir, skill_factory):
    """Test tool invocation return value matches expected content.

    Validates:
        - Return value is processed skill content
        - Content matches skill definition
        - Both with and without placeholders work
    """
    # Test with placeholder
    skill_factory("echo", "Echoes input", "You said: $ARGUMENTS")

    # Test without placeholder
    skill_factory("static", "Returns static content", "This is static content")

    manager = SkillManager(temp_skills_dir)
    manager.discover()
    tools = create_langchain_tools(manager)

    # Find tools by name
    echo_tool = next(t for t in tools if t.name == "echo")
    static_tool = next(t for t in tools if t.name == "static")

    # Test dynamic content (includes base directory and frontmatter)
    result = echo_tool.invoke(input={"arguments": "hello"})
    assert "You said: hello" in result
    assert "Base directory for this skill:" in result

    # Test static content (includes base directory and frontmatter)
    result = static_tool.invoke(input={"arguments": "ignored"})
    assert "This is static content" in result
    assert "Base directory for this skill:" in result


@pytest.mark.integration
@pytest.mark.requires_langchain
def test_langchain_tool_invocation_with_long_arguments(temp_skills_dir, skill_factory):
    """Test tool handles 10KB+ arguments correctly.

    Validates:
        - Large arguments processed without truncation
        - No arbitrary size limits below 1MB
        - Performance acceptable for agent use
    """
    skill_factory("processor", "Processes large input", "Processed: $ARGUMENTS")

    manager = SkillManager(temp_skills_dir)
    manager.discover()
    tools = create_langchain_tools(manager)

    tool = tools[0]

    # Create 10KB+ argument (approx 10,000 chars)
    large_input = "x" * 10_000

    result = tool.invoke(input={"arguments": large_input})

    # Result includes base directory, frontmatter, and processed content
    assert "Processed:" in result
    assert len(result) > 10_000
    assert "x" * 100 in result  # Sample check - arguments were processed


@pytest.mark.integration
@pytest.mark.requires_langchain
def test_langchain_tool_error_propagation(temp_skills_dir, skill_factory):
    """Test skill errors propagate to LangChain correctly.

    Validates:
        - skillkit exceptions bubble up through tool
        - LangChain can catch and handle exceptions
        - Error messages preserved for agent debugging
    """
    skill_factory("test-skill", "Test skill", "Content: $ARGUMENTS")

    manager = SkillManager(temp_skills_dir)
    manager.discover()
    tools = create_langchain_tools(manager)

    tool = tools[0]

    # Test 1: Skill not found error (after discovery but skill removed)
    # Remove skill from manager's cache to simulate deletion
    manager._skills.clear()

    with pytest.raises(SkillNotFoundError) as exc_info:
        tool.invoke(input={"arguments": "test"})

    assert "test-skill" in str(exc_info.value)

    # Re-discover for next test
    manager.discover()
    tools = create_langchain_tools(manager)
    tool = tools[0]

    # Test 2: Size limit exceeded (1MB+ argument)
    huge_input = "x" * (1024 * 1024 + 1)  # Just over 1MB

    with pytest.raises(SizeLimitExceededError) as exc_info:
        tool.invoke(input={"arguments": huge_input})

    # Error message mentions size limit (exact format may vary)
    error_msg = str(exc_info.value)
    assert "exceed" in error_msg.lower() or "too large" in error_msg.lower()
    assert "1000000" in error_msg or "1048576" in error_msg or "1 MB" in error_msg or "1MB" in error_msg
