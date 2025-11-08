# Quickstart Guide: skillkit v0.1 MVP

**Version**: 0.1.0
**Date**: November 3, 2025
**Target Audience**: Python developers integrating LLM agents

## Overview

This guide will get you up and running with skillkit in under 5 minutes. You'll learn how to:

1. Install the library
2. Create your first skill
3. Use skills standalone (without frameworks)
4. Integrate skills with LangChain agents

---

## Installation

### Core Library Only

```bash
pip install skillkit
```

### With LangChain Integration

```bash
pip install skillkit[langchain]
```

### For Development

```bash
pip install skillkit[dev]
```

---

## Prerequisites

- **Python**: 3.9 or higher
- **Skills Directory**: `~/.claude/skills/` (automatically created if missing)
- **LangChain** (optional): For agent integration

---

## Step 1: Create Your First Skill

Skills are markdown files with YAML frontmatter stored in `~/.claude/skills/`.

### Create Skill Directory

```bash
mkdir -p ~/.claude/skills/code-reviewer
```

### Create SKILL.md File

Create `~/.claude/skills/code-reviewer/SKILL.md`:

```markdown
---
name: code-reviewer
description: Reviews Python code for common mistakes and bugs
allowed-tools: Read, Grep
---

You are an expert Python code reviewer.

Please review the following code for:
- Syntax errors
- Logic bugs (division by zero, null pointer, etc.)
- Style issues (PEP 8 compliance)
- Security vulnerabilities

Code to review:

$ARGUMENTS

Provide a clear, actionable summary of issues found.
```

**Key Points**:
- `---` delimiters mark YAML frontmatter
- `name` and `description` are required
- `allowed-tools` is optional (not enforced in v0.1)
- `$ARGUMENTS` is a placeholder that gets replaced with user input

---

## Step 2: Use Skills Standalone

### Basic Usage

```python
from skillkit import SkillManager

# Initialize manager
manager = SkillManager()

# Discover skills from ~/.claude/skills/
manager.discover()

# List available skills
skills = manager.list_skills()
for skill in skills:
    print(f"✓ {skill.name}: {skill.description}")

# Output:
# ✓ code-reviewer: Reviews Python code for common mistakes and bugs
```

### Invoke a Skill

```python
# Invoke skill with arguments
result = manager.invoke_skill(
    "code-reviewer",
    """
def calculate_average(numbers):
    total = sum(numbers)
    return total / len(numbers)
    """
)

print(result)
```

**Output**:
```
Base directory for this skill: /Users/you/.claude/skills/code-reviewer

You are an expert Python code reviewer.

Please review the following code for:
- Syntax errors
- Logic bugs (division by zero, null pointer, etc.)
- Style issues (PEP 8 compliance)
- Security vulnerabilities

Code to review:

def calculate_average(numbers):
    total = sum(numbers)
    return total / len(numbers)

Provide a clear, actionable summary of issues found.
```

**What happened**:
1. `$ARGUMENTS` was replaced with the provided code
2. Base directory was injected at the beginning
3. Processed content is ready for LLM consumption

---

## Step 3: Use with LangChain (Optional)

### Setup LangChain Agent

```python
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from skillkit.integrations.langchain import create_langchain_tools

# Create skills as LangChain tools
tools = create_langchain_tools()

# Setup LLM
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0,
    api_key="YOUR_API_KEY"  # Or set OPENAI_API_KEY env var
)

# Create prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant. Use available skills when appropriate."),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Create agent
agent = create_openai_functions_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True
)
```

### Use the Agent

```python
# Agent automatically selects and uses skills
result = agent_executor.invoke({
    "input": "Please review this Python code for bugs: def foo(x): return 1/x"
})

print(result["output"])
```

**What happens**:
1. Agent receives your request
2. Agent sees "code-reviewer" skill in available tools
3. Agent decides to use the skill based on description
4. Skill is invoked with the code as arguments
5. Processed skill content is sent to LLM
6. LLM generates review based on skill instructions
7. Agent returns final response

---

## Common Patterns

### Pattern 1: Custom Skills Directory

```python
from pathlib import Path
from skillkit import SkillManager

# Use project-local skills directory
manager = SkillManager(skills_directory=Path("./my-skills"))
manager.discover()
```

### Pattern 2: Error Handling

```python
from skillkit import SkillNotFoundError, SkillParsingError

try:
    result = manager.invoke_skill("my-skill", "test")
except SkillNotFoundError:
    print("Skill not found. Check skill name.")
except SkillParsingError as e:
    print(f"Failed to parse skill: {e}")
```

### Pattern 3: Skill Metadata Access

```python
# Get detailed info about a skill
metadata = manager.get_skill("code-reviewer")
print(f"Name: {metadata.name}")
print(f"Description: {metadata.description}")
print(f"Path: {metadata.skill_path}")
print(f"Allowed tools: {metadata.allowed_tools}")
```

### Pattern 4: Multiple Arguments

If your skill has multiple `$ARGUMENTS` placeholders, all will be replaced:

```markdown
---
name: compare-code
description: Compares two code snippets
---

Compare these implementations:

Version 1: $ARGUMENTS
Version 2: $ARGUMENTS

Explain differences.
```

```python
result = manager.invoke_skill(
    "compare-code",
    "def foo(): return 1"
)

# Both $ARGUMENTS replaced with same value
```

### Pattern 5: No Placeholder

If skill has no `$ARGUMENTS` but you provide arguments, they're appended:

```markdown
---
name: generic-helper
description: Generic coding assistant
---

You are a helpful coding assistant.
```

```python
result = manager.invoke_skill(
    "generic-helper",
    "Help me debug this code"
)

# Output includes:
# You are a helpful coding assistant.
#
# ARGUMENTS: Help me debug this code
```

---

## Creating More Skills

### Example: Markdown Formatter

`~/.claude/skills/markdown-formatter/SKILL.md`:

```markdown
---
name: markdown-formatter
description: Formats and validates markdown documents
allowed-tools: Read, Write
---

You are a markdown formatting expert.

Please format the following markdown document:
- Fix heading hierarchy
- Ensure proper list formatting
- Add missing blank lines
- Fix link syntax

Document:

$ARGUMENTS

Return the corrected markdown.
```

### Example: Git Helper

`~/.claude/skills/git-helper/SKILL.md`:

```markdown
---
name: git-helper
description: Helps with git commands and workflows
allowed-tools: Bash
---

You are a git expert assistant.

User question: $ARGUMENTS

Provide:
1. Clear explanation of the git concept/command
2. Example usage
3. Common pitfalls to avoid
```

---

## Debugging Tips

### Check Skill Discovery

```python
import logging
logging.basicConfig(level=logging.DEBUG)

manager = SkillManager()
manager.discover()

# DEBUG logs show discovery process
```

### Verify Skills Directory

```bash
# Check if skills directory exists
ls -la ~/.claude/skills/

# Expected output:
# drwxr-xr-x  code-reviewer/
# drwxr-xr-x  markdown-formatter/
```

### Validate SKILL.md Format

```python
from skillkit.core.parser import SkillParser
from pathlib import Path

parser = SkillParser()
try:
    metadata = parser.parse_skill_file(
        Path("~/.claude/skills/my-skill/SKILL.md").expanduser()
    )
    print(f"✓ Valid: {metadata.name}")
except Exception as e:
    print(f"✗ Invalid: {e}")
```

---

## Next Steps

### Learn More
- **API Reference**: See [contracts/public-api.md](./contracts/public-api.md) for complete API documentation
- **Data Models**: See [data-model.md](./data-model.md) for entity relationships
- **Architecture**: See [research.md](./research.md) for design decisions

### Create Your Own Skills
- Study the SKILL.md format specification: `.docs/SKILL format specification.md`
- Use `$ARGUMENTS` for user input substitution
- Keep descriptions concise (LLM uses them for tool selection)
- Test skills with `manager.invoke_skill()` before using with agents

### Advanced Usage
- **Multiple frameworks**: LlamaIndex, CrewAI (v1.1+)
- **Async support**: Coming in v0.2
- **Tool restriction enforcement**: Coming in v0.2
- **Plugin integration**: Coming in v0.3

---

## Troubleshooting

### Issue: "Skill not found"

**Cause**: Skill name mismatch or discovery not run

**Solution**:
```python
# Verify skill exists
skills = manager.list_skills()
print([s.name for s in skills])

# Check exact name in SKILL.md frontmatter
```

### Issue: "No valid YAML frontmatter found"

**Cause**: Missing `---` delimiters or malformed YAML

**Solution**:
```markdown
# Correct format:
---
name: my-skill
description: Description here
---

Content here
```

### Issue: "Missing required field 'name'"

**Cause**: YAML frontmatter missing required field

**Solution**: Ensure frontmatter has both `name` and `description`:
```yaml
---
name: my-skill          # Required
description: My skill   # Required
allowed-tools: []       # Optional
---
```

### Issue: LangChain import error

**Cause**: LangChain not installed

**Solution**:
```bash
pip install skillkit[langchain]
```

---

## Performance Tips

### Tip 1: Call `discover()` Once

```python
# Good: Discover once at startup
manager = SkillManager()
manager.discover()  # ~100ms for 10 skills

# Then use repeatedly
for task in tasks:
    result = manager.invoke_skill("my-skill", task)

# Bad: Discover on every invocation (slow)
for task in tasks:
    manager = SkillManager()
    manager.discover()  # Wasteful
    result = manager.invoke_skill("my-skill", task)
```

### Tip 2: Reuse SkillManager

```python
# Create once, use many times
manager = SkillManager()
manager.discover()

# Efficient: Manager caches metadata
result1 = manager.invoke_skill("skill1", "args1")
result2 = manager.invoke_skill("skill2", "args2")
```

### Tip 3: Keep Skills Focused

```markdown
# Good: Focused skill (fast to process)
---
name: validate-json
description: Validates JSON syntax
---
Validate this JSON: $ARGUMENTS

# Bad: Large skill with examples (slow to process)
---
name: json-expert
description: JSON expert
---
[5000 lines of JSON documentation and examples]
$ARGUMENTS
```

---

## Complete Example: End-to-End

```python
#!/usr/bin/env python3
"""Complete example: skillkit with LangChain agent."""

from pathlib import Path
from skillkit import SkillManager
from skillkit.integrations.langchain import create_langchain_tools
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

def main():
    # Step 1: Create skill manager
    print("🔍 Discovering skills...")
    manager = SkillManager()
    manager.discover()

    # Step 2: List available skills
    skills = manager.list_skills()
    print(f"✓ Found {len(skills)} skills:")
    for skill in skills:
        print(f"  - {skill.name}: {skill.description}")

    # Step 3: Test standalone skill invocation
    print("\n📝 Testing standalone invocation...")
    result = manager.invoke_skill(
        "code-reviewer",
        "def divide(a, b): return a / b"
    )
    print(f"✓ Skill invoked successfully ({len(result)} chars)")

    # Step 4: Create LangChain tools
    print("\n🔧 Creating LangChain tools...")
    tools = create_langchain_tools(manager)
    print(f"✓ Created {len(tools)} tools")

    # Step 5: Setup LangChain agent
    print("\n🤖 Setting up agent...")
    llm = ChatOpenAI(model="gpt-4", temperature=0)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful coding assistant. Use skills when appropriate."),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_openai_functions_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    # Step 6: Use agent
    print("\n💬 Running agent...")
    result = agent_executor.invoke({
        "input": "Review this code: def foo(x): return 1/x"
    })

    print("\n✅ Agent response:")
    print(result["output"])

if __name__ == "__main__":
    main()
```

**Run it**:
```bash
python example.py
```

---

## Summary

You've learned:
- ✅ How to install skillkit
- ✅ How to create SKILL.md files
- ✅ How to use skills standalone
- ✅ How to integrate with LangChain agents
- ✅ Common patterns and troubleshooting

**Next**: Build your own skills library and integrate with your AI agents!

---

**Document Version**: 1.0
**Library Version**: 0.1.0
**Last Updated**: November 3, 2025
