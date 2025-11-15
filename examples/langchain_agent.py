#!/usr/bin/env python3
"""LangChain agent integration example for skillkit library.

This script demonstrates how to use discovered skills with LangChain agents,
including both synchronous and asynchronous patterns.

Requirements:
    pip install skillkit[langchain]
    pip install langchain-openai  # or other LLM provider
"""

import asyncio
import logging
import os
from pathlib import Path

from skillkit import SkillManager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")


def main() -> None:
    """Demonstrate LangChain agent integration."""
    print("=" * 60)
    print("skillkit: LangChain Agent Integration Example")
    print("=" * 60)

    # Check for LangChain availability
    try:
        from skillkit.integrations.langchain import create_langchain_tools
    except ImportError as e:
        print(f"\nError: {e}")
        print("\nInstall LangChain integration with:")
        print("  pip install skillkit[langchain]")
        return

    # Use example skills from examples/skills/ directory
    skills_dir = Path(__file__).parent / "skills"
    print(f"\nUsing skills directory: {skills_dir}")

    # Create skill manager and discover skills
    print("\n[1] Discovering skills...")
    manager = SkillManager(skills_dir)
    manager.discover()

    print(f"\nFound {len(manager.list_skills())} skills")

    # Convert skills to LangChain tools
    print("\n[2] Creating LangChain tools...")
    tools = create_langchain_tools(manager)

    print(f"Created {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:60]}...")

    # Demonstrate tool invocation
    print("\n[3] Testing tool invocation...")
    if tools:
        test_tool = tools[0]
        print(f"\nInvoking tool: {test_tool.name}")
        try:
            result = test_tool.invoke(
                {"arguments": "Review this Python function for security issues"}
            )
            print(f"\nResult preview (first 200 chars):\n{'-' * 60}")
            print(result[:200])
            print("..." if len(result) > 200 else "")
            print("-" * 60)
        except Exception as e:
            print(f"Error: {e}")

    # Example agent setup (requires API key)
    print("\n[4] Agent setup example (requires API key)...")
    if os.getenv("OPENAI_API_KEY"):
        try:
            from langchain.agents import AgentExecutor, create_react_agent
            from langchain_core.prompts import PromptTemplate
            from langchain_openai import ChatOpenAI

            # Create LLM
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

            # Create prompt
            template = """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Question: {input}
Thought: {agent_scratchpad}"""

            prompt = PromptTemplate.from_template(template)

            # Create agent
            agent = create_react_agent(llm, tools, prompt)
            _agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

            print("\nAgent created successfully!")
            print("\nExample usage:")
            print('  result = agent_executor.invoke({"input": "Review my code"})')

            # Uncomment to actually run the agent:
            # result = agent_executor.invoke({
            #     "input": "Help me write a commit message for adding a new feature"
            # })
            # print(f"\nAgent result: {result}")

        except Exception as e:
            print(f"Error creating agent: {e}")
    else:
        print("\nSet OPENAI_API_KEY environment variable to test agent execution")
        print("Example: export OPENAI_API_KEY='your-api-key-here'")

    print("\n" + "=" * 60)
    print("Example complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Set up your LLM API key")
    print("2. Uncomment the agent execution code above")
    print("3. Run: python examples/langchain_agent.py")


async def async_agent_demo() -> None:
    """Demonstrate async LangChain agent integration with skillkit.

    This example shows how to use async discovery and invocation
    for improved performance in async applications.
    """
    print("\n" + "=" * 60)
    print("skillkit: ASYNC LangChain Agent Integration Example")
    print("=" * 60)

    # Check for LangChain availability
    try:
        from skillkit.integrations.langchain import create_langchain_tools
    except ImportError as e:
        print(f"\nError: {e}")
        print("\nInstall LangChain integration with:")
        print("  pip install skillkit[langchain]")
        return

    # Use example skills from examples/skills/ directory
    skills_dir = Path(__file__).parent / "skills"
    print(f"\nUsing skills directory: {skills_dir}")

    # Create skill manager and discover skills ASYNCHRONOUSLY
    print("\n[1] Discovering skills asynchronously...")
    manager = SkillManager(skills_dir)
    await manager.adiscover()  # Async discovery (non-blocking)

    print(f"\nFound {len(manager.list_skills())} skills")

    # Convert skills to LangChain tools (with async support)
    print("\n[2] Creating LangChain tools with async support...")
    tools = create_langchain_tools(manager)

    print(f"Created {len(tools)} tools with both sync and async capabilities:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:60]}...")

    # Demonstrate ASYNC tool invocation
    print("\n[3] Testing ASYNC tool invocation...")
    if tools:
        test_tool = tools[0]
        print(f"\nInvoking tool asynchronously: {test_tool.name}")
        try:
            # Use ainvoke() for async invocation (non-blocking)
            result = await test_tool.ainvoke(
                {"arguments": "Review this Python function for security issues"}
            )
            print(f"\nAsync result preview (first 200 chars):\n{'-' * 60}")
            print(result[:200])
            print("..." if len(result) > 200 else "")
            print("-" * 60)
        except Exception as e:
            print(f"Error: {e}")

    # Demonstrate concurrent tool invocations (async advantage)
    print("\n[4] Testing CONCURRENT async tool invocations...")
    if len(tools) >= 3:
        print("\nInvoking 3 tools concurrently (non-blocking)...")
        try:
            # Run multiple tool invocations in parallel
            results = await asyncio.gather(
                tools[0].ainvoke({"arguments": "test input 1"}),
                tools[1].ainvoke({"arguments": "test input 2"}),
                tools[2].ainvoke({"arguments": "test input 3"}),
            )
            print(f"Successfully invoked {len(results)} tools concurrently!")
            for i, result in enumerate(results):
                print(f"  Tool {i + 1} result length: {len(result)} chars")
        except Exception as e:
            print(f"Error during concurrent invocation: {e}")

    # Example ASYNC agent setup (requires API key)
    print("\n[5] Async agent setup example (requires API key)...")
    if os.getenv("OPENAI_API_KEY"):
        try:
            from langchain.agents import AgentExecutor, create_react_agent
            from langchain_core.prompts import PromptTemplate
            from langchain_openai import ChatOpenAI

            # Create LLM
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

            # Create prompt
            template = """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Question: {input}
Thought: {agent_scratchpad}"""

            prompt = PromptTemplate.from_template(template)

            # Create agent
            agent = create_react_agent(llm, tools, prompt)
            _agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

            print("\nAsync agent created successfully!")
            print("\nExample usage:")
            print('  result = await agent_executor.ainvoke({"input": "Review my code"})')

            # Uncomment to actually run the async agent:
            # result = await agent_executor.ainvoke({
            #     "input": "Help me write a commit message for adding a new feature"
            # })
            # print(f"\nAsync agent result: {result}")

        except Exception as e:
            print(f"Error creating async agent: {e}")
    else:
        print("\nSet OPENAI_API_KEY environment variable to test async agent execution")
        print("Example: export OPENAI_API_KEY='your-api-key-here'")

    print("\n" + "=" * 60)
    print("Async example complete!")
    print("=" * 60)
    print("\nKey advantages of async pattern:")
    print("1. Non-blocking discovery (faster with many skills)")
    print("2. Concurrent tool invocations (10+ simultaneous)")
    print("3. Better event loop integration (FastAPI, Discord bots, etc.)")
    print("4. Lower overhead vs thread pool wrapping")


if __name__ == "__main__":
    import sys

    # Check if user wants to run async demo
    if "--async" in sys.argv:
        print("Running ASYNC demo...")
        asyncio.run(async_agent_demo())
    else:
        print("Running SYNC demo...")
        print("(Use --async flag to run async demo)")
        main()
