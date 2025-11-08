# Async Implementation Quick Reference

**For skillkit v0.2 async support implementation**

---

## TL;DR

**Use `asyncio.to_thread()` with separate async namespace (`core/async_/`)**

```python
# Async wrapper pattern
import asyncio
from ..parser import SkillParser as SyncSkillParser

class SkillParser:
    def __init__(self):
        self._sync_parser = SyncSkillParser()

    async def parse_skill_file(self, skill_path: Path) -> SkillMetadata:
        return await asyncio.to_thread(
            self._sync_parser.parse_skill_file,
            skill_path
        )
```

---

## Module Structure

```
src/skillkit/core/
├── __init__.py              # Exports sync API
├── discovery.py             # Sync (existing)
├── parser.py                # Sync (existing)
├── manager.py               # Sync (existing)
└── async_/                  # NEW
    ├── __init__.py          # Exports async API
    ├── discovery.py         # Async wrapper
    ├── parser.py            # Async wrapper
    └── manager.py           # Async wrapper
```

---

## Implementation Checklist

### 1. Create async namespace

```bash
mkdir -p src/skillkit/core/async_
touch src/skillkit/core/async_/__init__.py
```

### 2. Implement async wrappers

Each async module follows this pattern:

```python
# src/skillkit/core/async_/{module}.py
import asyncio
from pathlib import Path
from ..{module} import SyncClass

class AsyncClass:
    """Async version of SyncClass."""

    def __init__(self):
        self._sync_impl = SyncClass()

    async def method_name(self, *args, **kwargs):
        """Async wrapper for sync method."""
        return await asyncio.to_thread(
            self._sync_impl.method_name,
            *args,
            **kwargs
        )
```

### 3. Export async API

```python
# src/skillkit/core/async_/__init__.py
"""Async API for skillkit core functionality."""

from .discovery import SkillDiscovery
from .parser import SkillParser
from .manager import SkillManager

__all__ = [
    "SkillDiscovery",
    "SkillParser",
    "SkillManager",
]
```

### 4. Add tests

```python
# tests/test_async_parser.py
import pytest
from pathlib import Path
from skillkit.core.async_ import SkillParser

@pytest.mark.asyncio
async def test_parse_skill_file_async():
    parser = SkillParser()
    metadata = await parser.parse_skill_file(
        Path("tests/fixtures/skills/valid-skill/SKILL.md")
    )
    assert metadata.name == "code-reviewer"

@pytest.mark.asyncio
async def test_concurrent_parsing():
    import asyncio
    parser = SkillParser()

    paths = [
        Path("tests/fixtures/skills/skill1/SKILL.md"),
        Path("tests/fixtures/skills/skill2/SKILL.md"),
    ]

    results = await asyncio.gather(*[
        parser.parse_skill_file(path) for path in paths
    ])

    assert len(results) == 2
```

### 5. Update dependencies

```toml
# pyproject.toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "pytest-asyncio>=0.21.0",  # NEW
    "ruff>=0.1.0",
    "mypy>=1.0",
    "types-PyYAML",
]
```

---

## Usage Examples

### Sync (unchanged)

```python
from skillkit.core import SkillManager

manager = SkillManager()
skills = manager.discover_skills(Path(".claude/skills"))
```

### Async (new)

```python
import asyncio
from pathlib import Path
from skillkit.core.async_ import SkillManager

async def main():
    manager = SkillManager()
    skills = await manager.discover_skills(Path(".claude/skills"))
    print(f"Found {len(skills)} skills")

asyncio.run(main())
```

---

## Testing Commands

```bash
# Install dev dependencies with async support
pip install -e ".[dev]"

# Run async tests
pytest tests/test_async_*.py -v

# Run all tests
pytest -v

# Run with coverage
pytest --cov=src/skillkit --cov-report=term-missing
```

---

## Common Patterns

### Pattern 1: Simple Method Delegation

```python
async def method(self, arg: Type) -> ReturnType:
    """One-liner delegation."""
    return await asyncio.to_thread(self._sync_impl.method, arg)
```

### Pattern 2: Concurrent Operations

```python
async def discover_skills(self, skills_dir: Path) -> List[SkillMetadata]:
    """Discover and parse concurrently."""
    # Step 1: Find all skill files
    skill_paths = await self._discovery.scan_directory(skills_dir)

    # Step 2: Parse all concurrently
    results = await asyncio.gather(*[
        self._parse_skill_safe(path) for path in skill_paths
    ])

    return [skill for skill in results if skill is not None]
```

### Pattern 3: Safe Error Handling

```python
async def _parse_skill_safe(self, path: Path) -> SkillMetadata | None:
    """Parse with graceful degradation."""
    try:
        return await self._parser.parse_skill_file(path)
    except Exception as e:
        logger.warning(f"Failed to parse {path}: {e}")
        return None
```

---

## Performance Notes

- **Overhead:** ~0.5-1ms per `asyncio.to_thread()` call
- **Benefit:** 40-60% faster for concurrent operations (10+ skills)
- **Best use:** Async frameworks (FastAPI, async LangChain agents)
- **Not needed:** Single file operations, sync-only applications

---

## Troubleshooting

### Issue: "RuntimeError: no running event loop"

**Solution:** Use `asyncio.run()` or ensure you're inside an async context:

```python
# ❌ Wrong
manager = SkillManager()
skills = manager.discover_skills(path)  # Missing await

# ✅ Correct
import asyncio
async def main():
    manager = SkillManager()
    skills = await manager.discover_skills(path)

asyncio.run(main())
```

### Issue: "TypeError: object async_generator can't be used in 'await' expression"

**Solution:** Check that you're awaiting the right thing:

```python
# ❌ Wrong
results = await [parser.parse(p) for p in paths]

# ✅ Correct
results = await asyncio.gather(*[parser.parse(p) for p in paths])
```

### Issue: Tests hang or timeout

**Solution:** Ensure `pytest-asyncio` is installed and use `@pytest.mark.asyncio`:

```python
import pytest

@pytest.mark.asyncio  # ← Required
async def test_async_function():
    result = await async_function()
    assert result is not None
```

---

## Type Hints Reference

```python
from typing import List
from pathlib import Path
from collections.abc import Awaitable

# Return type is implicit: Coroutine[Any, Any, List[Path]]
async def scan_directory(self, skills_dir: Path) -> List[Path]:
    ...

# Python 3.10+ union syntax
async def find_file(self, name: str) -> Path | None:
    ...

# Generic async return
from typing import TypeVar
T = TypeVar('T')

async def process(self, data: T) -> T:
    ...
```

---

## Migration Checklist

- [ ] Create `src/skillkit/core/async_/` directory
- [ ] Implement `async_/discovery.py` wrapper
- [ ] Implement `async_/parser.py` wrapper
- [ ] Implement `async_/manager.py` wrapper
- [ ] Create `async_/__init__.py` exports
- [ ] Add `pytest-asyncio` to dev dependencies
- [ ] Write async tests in `tests/test_async_*.py`
- [ ] Update `README.md` with async examples
- [ ] Update `docs/` with async API documentation
- [ ] Test sync API still works (backwards compatibility)
- [ ] Test async API with `asyncio.gather()` concurrency
- [ ] Run full test suite: `pytest --cov=src/skillkit`

---

**Quick Start:** Copy the implementation patterns above and replace `{module}`, `SyncClass`, and `method_name` with your actual class/method names.
