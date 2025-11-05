#!/usr/bin/env python3
"""LangChain agent integration example for skills-use library.

This script demonstrates how to use discovered skills with LangChain agents.

Requirements:
    pip install skills-use[langchain]
    pip install langchain-openai  # or other LLM provider
"""

import logging
import os
from pathlib import Path

from skills_use import SkillManager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")


def main() -> None:
    """Demonstrate LangChain agent integration."""
    print("=" * 60)
    print("Skills-use: LangChain Agent Integration Example")
    print("=" * 60)

    # Check for LangChain availability
    try:
        from skills_use.integrations.langchain import create_langchain_tools
    except ImportError as e:
        print(f"\nError: {e}")
        print("\nInstall LangChain integration with:")
        print("  pip install skills-use[langchain]")
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
            agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

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


if __name__ == "__main__":
    main()
