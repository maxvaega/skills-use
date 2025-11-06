## SKILL.md Format Specification

The SKILL.md file is the core component of every Anthropic Agent Skill—a structured Markdown document that combines YAML metadata with instructions to teach the agent how to complete specific tasks in a repeatable way.

## Required Structure

### YAML Frontmatter

Every SKILL.md must begin with YAML frontmatter containing two required fields :

- **name**: A human-friendly skill identifier (64 characters maximum). Use lowercase with hyphens for consistency (e.g., `brand-guidelines`, `contract-reviewer`)
- **description**: A clear explanation of what the skill does and when the agent should use it (200 characters maximum). This field is critical—the agent uses it to determine skill relevance 

### Optional Metadata Fields

- **version**: Track iterations of your skill (e.g., `1.0.0`) 
- **dependencies**: Required software packages (e.g., `python>=3.8, pandas>=1.5.0`) 
- **allowed-tools**: Restrict which built-in tools the agent can use while the skill is active (e.g., `Read, Grep, Glob`)

### Markdown Body

After the frontmatter, the Markdown body contains instructions, workflows, examples, and references to supporting files. This content should be focused and clear, with more detailed information split into separate referenced files .

## Progressive Disclosure System

Skills implement a three-level information hierarchy that prevents context window overload :

1. **Level 1**: Metadata (`name` and `description`)—pre-loaded into system prompt at startup for all skills
2. **Level 2**: SKILL.md body—loaded only when the agent determines the skill is relevant to the current task
3. **Level 3+**: Additional referenced files—loaded on-demand as the agent navigates through specific scenarios 

## Directory Structure

A complete skill directory typically contains :

```
skill-name/
├── SKILL.md          # Required: core instructions and metadata
├── resources/        # Optional: reference materials
│   ├── reference.md
│   ├── examples.md
│   └── checklist.txt
├── templates/        # Optional: reusable templates
└── scripts/          # Optional: executable code
    └── tool.py
```

The folder name should match your skill's name for consistency .

## Example SKILL.md

```markdown
---
name: brand-guidelines
description: Apply Acme Corp brand guidelines to presentations and documents, including official colors, fonts, and logo usage.
version: 1.0.0
allowed-tools: Read, Write, Bash
---

# Brand Guidelines Skill

## Overview
This skill provides Acme Corp's official brand guidelines for creating consistent, professional materials. Apply these standards whenever creating external-facing materials or documents.

## Brand Colors
- Primary: #FF6B35 (Coral)
- Secondary: #004E89 (Navy Blue)
- Accent: #F7B801 (Gold)

## Typography
- Headers: Montserrat Bold (32pt for H1, 24pt for H2)
- Body text: Open Sans Regular (11pt)

## When to Apply
Apply these guidelines when creating:
- PowerPoint presentations
- Word documents for external sharing
- Marketing materials

## Resources
For detailed logo usage rules, see resources/logo-guidelines.md.
For presentation templates, see templates/slide-deck.pptx.
```


## Code Execution

Skills can include executable Python or JavaScript code that the agent runs as tools without loading the code into context. This approach enables deterministic, efficient operations like sorting data or processing PDFs . On the agent and the agent Code, packages can be installed from standard repositories (PyPI, npm) at runtime; API skills require pre-installed dependencies .

## Best Practices

### Skill Design
- **Focus**: Create separate skills for different workflows rather than one monolithic skill
- **Clarity**: Write specific descriptions that clearly indicate when the skill applies 
- **Simplicity**: Start with basic Markdown instructions before adding complex scripts 
- **Examples**: Include sample inputs and outputs to demonstrate success 

### Development Process
- **Start with evaluation**: Identify capability gaps by observing where the agent struggles on representative tasks 
- **Structure for scale**: Split large SKILL.md files into separate referenced documents; keep mutually exclusive contexts in separate paths 
- **Monitor usage**: Watch how the agent uses your skill and iterate based on observations 
- **Iterate with the agent**: Ask the agent to capture successful approaches and common mistakes directly into the skill 

### Security
- Only install skills from trusted sources
- Audit less-trusted skills thoroughly before use, examining bundled code, dependencies, and network access instructions
- Never hardcode sensitive information like API keys or passwords 

## Packaging and Distribution

To upload a custom skill :

1. Ensure the folder name matches your skill's name
2. Create a ZIP file containing the skill folder as its root (not as a subfolder)
3. Upload via Settings > Capabilities in the agent

**Correct ZIP structure**:
```
my-skill.zip
└── my-skill/
    ├── SKILL.md
    └── resources/
```


For more information, check out:
- [What are skills?](https://support.claude.com/en/articles/12512176-what-are-skills)
- [Using skills in Claude](https://support.claude.com/en/articles/12512180-using-skills-in-claude)
- [How to create custom skills](https://support.claude.com/en/articles/12512198-creating-custom-skills)
- [equipping-agents-for-the-real-world-with-agent-skills](https://anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)