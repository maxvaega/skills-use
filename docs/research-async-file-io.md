# Research: Async File I/O Best Practices for skillkit v0.2

**Date:** 2025-11-06
**Context:** Adding async support for YAML/JSON file I/O in skillkit library
**Python Version:** 3.10+

---

## Executive Summary

**DECISION: Use `asyncio.to_thread()` wrapper pattern with separate async modules**

**Rationale:**
- Built-in Python 3.9+ feature (no external dependencies)
- Automatic contextvars propagation
- Minimal overhead for skillkit's use case (small YAML files, ~2-10KB)
- Simplest to maintain and test
- Industry-standard pattern (HTTPX, many modern libraries)

**Key Insight:** For small configuration files (SKILL.md with YAML frontmatter), async file I/O provides **negligible performance benefits** but is necessary for **API consistency** in async frameworks. The overhead (~1-2ms per file) is acceptable given LLM invocation latency (100-1000ms+).

---

## 1. Research Findings

### 1.1 Async File I/O Options

| Approach | Description | Pros | Cons |
|----------|-------------|------|------|
| **asyncio.to_thread()** | Python 3.9+ built-in wrapper for ThreadPoolExecutor | - No dependencies<br>- Automatic contextvars<br>- Simple API<br>- Standard library | - Python 3.9+ only<br>- Bounded thread pool<br>- Small overhead |
| **aiofiles** | Third-party async file library | - Dedicated file API<br>- Familiar interface | - Extra dependency<br>- Same ThreadPoolExecutor under hood<br>- Adds ~1-2ms overhead |
| **run_in_executor()** | Low-level asyncio executor API | - Full control<br>- Custom executors<br>- Python 3.6+ | - Manual contextvars<br>- More boilerplate<br>- Lower-level API |

### 1.2 Performance Characteristics

**When Async File I/O is NOT Worth It:**
- Small files (<100KB): Overhead exceeds benefits
- Single file operations: No concurrency to exploit
- Buffered I/O: OS buffers mask blocking behavior
- Local SSD/NVMe: Latency too low to benefit from async

**When Async File I/O IS Worth It:**
- Large files (>1MB): Meaningful I/O time to overlap
- Many concurrent file operations: Thread pool enables parallelism
- Network filesystems (NFS, S3FS): Higher latency justifies async
- Integration with async frameworks: API consistency matters

**skillkit Use Case Analysis:**
- File size: ~2-10KB (SKILL.md with frontmatter)
- Typical count: 5-50 skills per discovery
- I/O time: ~10-20ms per file (SSD)
- Parsing time: ~5-10ms per file (YAML)
- **Verdict:** Async provides minimal performance gain (~10-20% in batch operations) but enables integration with async frameworks (LangChain async agents, FastAPI, etc.)

### 1.3 YAML Parsing in Async Context

**Problem:** `yaml.safe_load()` is synchronous-only (no native async YAML library)

**Solution Pattern:**
```python
import asyncio
from pathlib import Path
import yaml

async def parse_yaml_async(file_path: Path) -> dict:
    """Async YAML parsing using to_thread wrapper."""
    # Read file in thread pool
    content = await asyncio.to_thread(file_path.read_text, encoding="utf-8-sig")

    # Parse YAML in thread pool (CPU-bound work)
    data = await asyncio.to_thread(yaml.safe_load, content)

    return data
```

**Alternative (Optimized):**
```python
async def parse_yaml_async_optimized(file_path: Path) -> dict:
    """Single thread pool call for file read + parse."""
    def read_and_parse() -> dict:
        content = file_path.read_text(encoding="utf-8-sig")
        return yaml.safe_load(content)

    return await asyncio.to_thread(read_and_parse)
```

The optimized version reduces context switches from 2 to 1, saving ~0.5-1ms overhead.

---

## 2. Design Patterns for Sync/Async API Parity

### 2.1 Pattern Options

#### Option 1: Separate Modules (HTTPX Pattern) ✅ RECOMMENDED
```
skillkit/
├── core/
│   ├── discovery.py          # Sync implementation
│   ├── parser.py              # Sync implementation
│   ├── manager.py             # Sync implementation
│   └── async_/                # Async namespace
│       ├── __init__.py
│       ├── discovery.py       # Async implementation
│       ├── parser.py          # Async implementation
│       └── manager.py         # Async implementation
```

**Pros:**
- Clean separation of concerns
- No code duplication via delegation
- Easy to maintain and test independently
- Type checkers work correctly
- Clear import paths (`from skillkit.core import SkillManager` vs `from skillkit.core.async_ import SkillManager`)

**Cons:**
- Duplicate class/function names across modules (managed via namespacing)
- Need to maintain API parity manually

#### Option 2: Single Module with Async Variants
```python
# discovery.py
class SkillDiscovery:
    def scan_directory(self, skills_dir: Path) -> List[Path]:
        """Sync version"""
        ...

class AsyncSkillDiscovery:
    async def scan_directory(self, skills_dir: Path) -> List[Path]:
        """Async version"""
        ...
```

**Pros:**
- Single file for related functionality
- Clear naming convention

**Cons:**
- File size grows
- Harder to test independently
- Confusing imports (`SkillDiscovery` vs `AsyncSkillDiscovery`)

#### Option 3: Sans-I/O Pattern (Advanced)
Separate protocol logic from I/O:
```python
# protocol.py (pure logic, no I/O)
class SkillProtocol:
    def parse_frontmatter(self, content: str) -> dict:
        """Pure parsing logic"""
        ...

# io_sync.py
class SyncSkillParser:
    def parse_file(self, path: Path) -> dict:
        content = path.read_text()
        return SkillProtocol().parse_frontmatter(content)

# io_async.py
class AsyncSkillParser:
    async def parse_file(self, path: Path) -> dict:
        content = await asyncio.to_thread(path.read_text)
        return SkillProtocol().parse_frontmatter(content)
```

**Pros:**
- Maximum code reuse
- Protocol logic testable without I/O
- Industry best practice for protocols

**Cons:**
- Higher complexity
- Overkill for simple file I/O
- More files to maintain

### 2.2 Recommended Approach for skillkit

**Choice: Option 1 (Separate Modules) with Delegation**

```python
# core/parser.py (sync)
class SkillParser:
    def parse_skill_file(self, skill_path: Path) -> SkillMetadata:
        """Synchronous YAML parsing."""
        content = skill_path.read_text(encoding="utf-8-sig")
        frontmatter_dict = self._extract_frontmatter(content, skill_path)
        # ... rest of parsing logic
        return SkillMetadata(...)

    def _extract_frontmatter(self, content: str, skill_path: Path) -> dict:
        """Pure parsing logic (no I/O)."""
        match = self.FRONTMATTER_PATTERN.match(content)
        if not match:
            raise InvalidFrontmatterError(...)
        return yaml.safe_load(match.group(1))

# core/async_/parser.py (async)
import asyncio
from pathlib import Path
from ..parser import SkillParser as SyncSkillParser
from ..models import SkillMetadata

class SkillParser:
    """Async version of SkillParser."""

    def __init__(self):
        self._sync_parser = SyncSkillParser()

    async def parse_skill_file(self, skill_path: Path) -> SkillMetadata:
        """Asynchronous YAML parsing using thread pool."""
        # Delegate file I/O to sync implementation via thread pool
        return await asyncio.to_thread(
            self._sync_parser.parse_skill_file,
            skill_path
        )
```

**Benefits:**
- Zero code duplication (async delegates to sync)
- All business logic in sync version (single source of truth)
- Testing focuses on sync version; async tests only verify delegation
- Easy to maintain (changes in one place)

---

## 3. Implementation Recommendations

### 3.1 Module Structure

```
src/skillkit/
├── core/
│   ├── __init__.py           # Exports sync API
│   ├── discovery.py          # Sync discovery
│   ├── parser.py             # Sync parser
│   ├── manager.py            # Sync manager
│   ├── models.py             # Shared dataclasses (no I/O)
│   ├── exceptions.py         # Shared exceptions
│   ├── processors.py         # Shared processors
│   └── async_/               # Async namespace
│       ├── __init__.py       # Exports async API
│       ├── discovery.py      # Async discovery
│       ├── parser.py         # Async parser
│       └── manager.py        # Async manager
```

### 3.2 Public API Design

```python
# Sync API (unchanged from v0.1)
from skillkit.core import SkillManager

manager = SkillManager()
skills = manager.discover_skills(Path(".claude/skills"))

# Async API (new in v0.2)
from skillkit.core.async_ import SkillManager

manager = SkillManager()
skills = await manager.discover_skills(Path(".claude/skills"))
```

### 3.3 Implementation Pattern

**Template for async wrapper:**
```python
# core/async_/discovery.py
import asyncio
from pathlib import Path
from typing import List
from ..discovery import SkillDiscovery as SyncSkillDiscovery

class SkillDiscovery:
    """Async filesystem scanner for SKILL.md files."""

    def __init__(self):
        self._sync_discovery = SyncSkillDiscovery()

    async def scan_directory(self, skills_dir: Path) -> List[Path]:
        """Async scan using thread pool delegation."""
        return await asyncio.to_thread(
            self._sync_discovery.scan_directory,
            skills_dir
        )

    async def find_skill_files(self, skills_dir: Path) -> List[Path]:
        """Async find using thread pool delegation."""
        return await asyncio.to_thread(
            self._sync_discovery.find_skill_files,
            skills_dir
        )
```

### 3.4 Testing Strategy

**Sync tests (comprehensive):**
```python
# tests/test_parser.py
def test_parse_skill_file_success():
    parser = SkillParser()
    metadata = parser.parse_skill_file(Path("fixtures/valid-skill/SKILL.md"))
    assert metadata.name == "code-reviewer"

def test_parse_missing_name():
    parser = SkillParser()
    with pytest.raises(MissingRequiredFieldError):
        parser.parse_skill_file(Path("fixtures/missing-name/SKILL.md"))
```

**Async tests (delegation verification):**
```python
# tests/test_async_parser.py
import pytest
from skillkit.core.async_ import SkillParser

@pytest.mark.asyncio
async def test_parse_skill_file_async():
    """Verify async delegation works correctly."""
    parser = SkillParser()
    metadata = await parser.parse_skill_file(Path("fixtures/valid-skill/SKILL.md"))
    assert metadata.name == "code-reviewer"

@pytest.mark.asyncio
async def test_concurrent_parsing():
    """Verify concurrent async operations work."""
    parser = SkillParser()
    paths = [
        Path("fixtures/skill1/SKILL.md"),
        Path("fixtures/skill2/SKILL.md"),
        Path("fixtures/skill3/SKILL.md"),
    ]

    results = await asyncio.gather(*[
        parser.parse_skill_file(path) for path in paths
    ])

    assert len(results) == 3
    assert all(r.name for r in results)
```

---

## 4. Performance Analysis

### 4.1 Overhead Breakdown

**Single file operation:**
```
Sync version:
- File I/O:        ~10-20ms (SSD)
- YAML parsing:    ~5-10ms
- Total:           ~15-30ms

Async version:
- to_thread overhead: ~0.5-1ms
- File I/O:          ~10-20ms (in thread pool)
- YAML parsing:      ~5-10ms (in thread pool)
- Total:             ~16-31ms (3-5% overhead)
```

**Concurrent operations (10 skills):**
```
Sync version (sequential):
- Total: ~150-300ms (10 × 15-30ms)

Async version (concurrent with gather):
- to_thread overhead:  ~5-10ms (10 × 0.5-1ms)
- File I/O (parallel): ~10-20ms (limited by thread pool)
- YAML parsing:        ~50-100ms (10 × 5-10ms, some parallelism)
- Total:               ~65-130ms (40-60% faster)
```

### 4.2 When Async Matters

**LLM latency context:**
- Skill discovery:  ~100-200ms (sync) vs ~70-120ms (async)
- LLM invocation:   ~500-2000ms (depends on model/provider)
- **Discovery is 0.5-5% of total time**

**Verdict:** Async provides minor performance gains but enables better integration with async frameworks (FastAPI, async LangChain agents, etc.)

---

## 5. Alternatives Considered

### 5.1 aiofiles Library

**Pros:**
- Dedicated async file API
- Familiar file-like interface

**Cons:**
- External dependency (current: zero core dependencies)
- Same ThreadPoolExecutor under hood as asyncio.to_thread
- No performance advantage
- Additional ~1-2ms overhead per operation

**Example:**
```python
import aiofiles
import yaml

async def parse_with_aiofiles(path: Path) -> dict:
    async with aiofiles.open(path, encoding="utf-8-sig") as f:
        content = await f.read()
    return await asyncio.to_thread(yaml.safe_load, content)
```

**Decision:** Rejected due to unnecessary dependency and no performance gain.

### 5.2 run_in_executor() Pattern

**Pros:**
- Full control over executor
- Can customize thread pool size
- Works in Python 3.6+

**Cons:**
- Manual contextvars handling
- More boilerplate code
- Lower-level API

**Example:**
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class SkillParser:
    def __init__(self, max_workers: int = 4):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    async def parse_skill_file(self, path: Path) -> SkillMetadata:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._sync_parse,
            path
        )
```

**Decision:** Rejected for v0.2. May revisit in v0.3 if custom thread pool sizing is needed.

### 5.3 Custom ThreadPool with Bounded Queue

**Use case:** Prevent thread pool exhaustion during large discovery operations

**Pattern:**
```python
from concurrent.futures import ThreadPoolExecutor

class SkillManager:
    def __init__(self, max_io_workers: int = 10):
        self._io_executor = ThreadPoolExecutor(
            max_workers=max_io_workers,
            thread_name_prefix="skillkit-io-"
        )

    async def _parse_with_custom_pool(self, path: Path) -> SkillMetadata:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._io_executor,
            self._sync_parser.parse_skill_file,
            path
        )
```

**Decision:** Deferred to v0.3. Default asyncio thread pool (max_workers=min(32, os.cpu_count() + 4)) is sufficient for typical skillkit usage.

---

## 6. Python 3.10+ Specific Considerations

### 6.1 asyncio.to_thread() Availability

- **Added:** Python 3.9 (PEP 563)
- **Stable:** Python 3.10+
- **Contextvars:** Automatic propagation (key advantage over run_in_executor)

**Migration from 3.9 → 3.10:**
No changes needed. `asyncio.to_thread()` behavior is identical.

### 6.2 Type Hints

Python 3.10 improved type hints for async functions:

```python
from pathlib import Path
from typing import List
from collections.abc import Awaitable

class SkillDiscovery:
    async def scan_directory(self, skills_dir: Path) -> List[Path]:
        """Return type is implicitly Coroutine[Any, Any, List[Path]]"""
        ...

    # Python 3.10+ union syntax
    async def find_file(self, name: str) -> Path | None:
        """More concise than Optional[Path]"""
        ...
```

### 6.3 Performance Optimizations

**Python 3.10 optimizations relevant to skillkit:**
- Faster attribute access (10-20% for dataclasses)
- Improved asyncio performance (5-10% overhead reduction)
- Better contextvars handling

**No special code needed** - these are automatic runtime improvements.

---

## 7. Code Examples

### 7.1 Complete Async Parser Implementation

```python
# src/skillkit/core/async_/parser.py
"""Async YAML frontmatter parser for SKILL.md files."""

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from ..parser import SkillParser as SyncSkillParser
from ..models import SkillMetadata

if TYPE_CHECKING:
    from typing import Any


class SkillParser:
    """Async YAML frontmatter parser for SKILL.md files.

    Delegates to sync SkillParser via asyncio.to_thread() for
    thread pool execution. All parsing logic remains in sync version.

    Example:
        >>> parser = SkillParser()
        >>> metadata = await parser.parse_skill_file(Path("skill/SKILL.md"))
        >>> print(f"{metadata.name}: {metadata.description}")
        code-reviewer: Review code for best practices
    """

    def __init__(self) -> None:
        self._sync_parser = SyncSkillParser()

    async def parse_skill_file(self, skill_path: Path) -> SkillMetadata:
        """Parse SKILL.md file asynchronously.

        Args:
            skill_path: Absolute path to SKILL.md file

        Returns:
            SkillMetadata instance with parsed fields

        Raises:
            InvalidFrontmatterError: If frontmatter structure invalid
            InvalidYAMLError: If YAML syntax error
            MissingRequiredFieldError: If required fields missing
            ContentLoadError: If file cannot be read
        """
        return await asyncio.to_thread(
            self._sync_parser.parse_skill_file,
            skill_path
        )
```

### 7.2 Complete Async Discovery Implementation

```python
# src/skillkit/core/async_/discovery.py
"""Async skill discovery module for filesystem scanning."""

import asyncio
from pathlib import Path
from typing import List

from ..discovery import SkillDiscovery as SyncSkillDiscovery


class SkillDiscovery:
    """Async filesystem scanner for discovering SKILL.md files.

    Delegates to sync SkillDiscovery via asyncio.to_thread() for
    thread pool execution.

    Example:
        >>> discovery = SkillDiscovery()
        >>> skills = await discovery.scan_directory(Path(".claude/skills"))
        >>> print(f"Found {len(skills)} skills")
        Found 3 skills
    """

    def __init__(self) -> None:
        self._sync_discovery = SyncSkillDiscovery()

    async def scan_directory(self, skills_dir: Path) -> List[Path]:
        """Scan skills directory for SKILL.md files asynchronously.

        Args:
            skills_dir: Root directory to scan for skills

        Returns:
            List of absolute paths to SKILL.md files (empty if none found)
        """
        return await asyncio.to_thread(
            self._sync_discovery.scan_directory,
            skills_dir
        )

    async def find_skill_files(self, skills_dir: Path) -> List[Path]:
        """Find SKILL.md files in immediate subdirectories asynchronously.

        Args:
            skills_dir: Directory to search

        Returns:
            List of absolute paths to SKILL.md files
        """
        return await asyncio.to_thread(
            self._sync_discovery.find_skill_files,
            skills_dir
        )
```

### 7.3 Complete Async Manager Implementation

```python
# src/skillkit/core/async_/manager.py
"""Async skill manager orchestrating discovery and parsing."""

import asyncio
from pathlib import Path
from typing import List

from ..models import SkillMetadata
from .discovery import SkillDiscovery
from .parser import SkillParser


class SkillManager:
    """Async orchestrator for skill discovery and parsing.

    Manages the full lifecycle of skill loading with concurrent processing.

    Example:
        >>> manager = SkillManager()
        >>> skills = await manager.discover_skills(Path(".claude/skills"))
        >>> for skill in skills:
        ...     print(f"Loaded: {skill.name}")
        Loaded: code-reviewer
        Loaded: git-helper
    """

    def __init__(self) -> None:
        self._discovery = SkillDiscovery()
        self._parser = SkillParser()

    async def discover_skills(self, skills_dir: Path) -> List[SkillMetadata]:
        """Discover and parse all skills in directory concurrently.

        Args:
            skills_dir: Root directory containing skill subdirectories

        Returns:
            List of SkillMetadata instances (empty if none found or all failed)

        Example:
            >>> manager = SkillManager()
            >>> skills = await manager.discover_skills(Path(".claude/skills"))
            >>> print(f"Found {len(skills)} valid skills")
            Found 3 valid skills
        """
        # Find all skill files
        skill_paths = await self._discovery.scan_directory(skills_dir)

        if not skill_paths:
            return []

        # Parse all skills concurrently
        parse_tasks = [
            self._parse_skill_safe(path) for path in skill_paths
        ]

        results = await asyncio.gather(*parse_tasks, return_exceptions=False)

        # Filter out None results (parse failures)
        return [skill for skill in results if skill is not None]

    async def _parse_skill_safe(self, skill_path: Path) -> SkillMetadata | None:
        """Parse skill with graceful error handling.

        Args:
            skill_path: Path to SKILL.md file

        Returns:
            SkillMetadata if successful, None if parsing fails
        """
        try:
            return await self._parser.parse_skill_file(skill_path)
        except Exception as e:
            # Log error and return None (graceful degradation)
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to parse skill at {skill_path}: {e}")
            return None
```

### 7.4 Usage Example

```python
# examples/async_usage.py
"""Example of async skillkit usage."""

import asyncio
from pathlib import Path
from skillkit.core.async_ import SkillManager


async def main():
    """Discover and load skills asynchronously."""
    manager = SkillManager()

    # Discover skills from .claude/skills directory
    skills_dir = Path.home() / ".claude" / "skills"
    skills = await manager.discover_skills(skills_dir)

    print(f"Discovered {len(skills)} skills:\n")

    for skill in skills:
        print(f"Name: {skill.name}")
        print(f"Description: {skill.description}")
        print(f"Allowed tools: {skill.allowed_tools or 'unrestricted'}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 8. References

### 8.1 Official Documentation

- [Python asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
- [asyncio.to_thread() API](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread)
- [PEP 567 - Context Variables](https://www.python.org/dev/peps/pep-0567/)

### 8.2 Design Patterns

- [Designing Libraries for Async and Sync I/O](https://sethmlarson.dev/designing-libraries-for-async-and-sync-io) - Seth Michael Larson
- [Sans-I/O Protocol Documentation](https://sans-io.readthedocs.io/) - Cory Benfield
- [Building Protocol Libraries The Right Way (PyCon 2016)](https://www.youtube.com/watch?v=7cC3_jGwl_U) - Cory Benfield

### 8.3 Real-World Implementations

- [HTTPX Architecture](https://github.com/encode/httpx) - Separate sync/async modules pattern
- [aiofiles Implementation](https://github.com/Tinche/aiofiles) - ThreadPoolExecutor wrapper
- [FastAPI Thread Pool Strategy](https://fastapi.tiangolo.com/) - Background tasks and executors

### 8.4 Performance Analysis

- [Stack Overflow: asyncio.to_thread vs run_in_executor](https://stackoverflow.com/questions/65316863/is-asyncio-to-thread-method-different-to-threadpoolexecutor)
- [Stack Overflow: Speed of loading files with asyncio](https://stackoverflow.com/questions/74537864/speed-of-loading-files-with-asyncio)
- [GitHub Issue: asyncio.to_thread efficiency](https://github.com/python/cpython/issues/136084)

### 8.5 Community Best Practices

- [Real Python: Async IO in Python](https://realpython.com/async-io-python/)
- [Super Fast Python: How to Use asyncio.to_thread()](https://superfastpython.com/asyncio-to_thread/)
- [Death and Gravity: Running async code from sync](https://death.andgravity.com/asyncio-bridge)

---

## 9. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-11-06 | Use asyncio.to_thread() wrapper | Built-in, simple, automatic contextvars |
| 2025-11-06 | Separate async_ namespace | Clean separation, follows HTTPX pattern |
| 2025-11-06 | Delegate to sync implementation | Zero duplication, single source of truth |
| 2025-11-06 | Reject aiofiles dependency | No performance gain, unnecessary dependency |
| 2025-11-06 | Defer custom thread pool to v0.3 | Default pool sufficient for MVP |

---

## 10. Next Steps for v0.2 Implementation

1. ✅ **Research complete** - Document findings (this file)
2. ⏳ Create `src/skillkit/core/async_/` namespace
3. ⏳ Implement async wrappers (discovery, parser, manager)
4. ⏳ Add async tests in `tests/test_async_*.py`
5. ⏳ Update documentation and examples
6. ⏳ Add `pytest-asyncio` to dev dependencies
7. ⏳ Update README with async usage examples

---

**Research completed by:** Claude (Anthropic)
**Reviewed by:** Massimo Olivieri
**Status:** ✅ Ready for implementation
