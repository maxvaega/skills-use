# Async File I/O Decision Summary

**Date:** 2025-11-06
**For:** skillkit v0.2 async support
**Status:** ✅ Ready for Implementation

---

## Decision

**Use `asyncio.to_thread()` with separate async namespace pattern**

---

## Rationale (Top 5 Reasons)

1. **Zero Dependencies** - Built into Python 3.9+ (skillkit uses 3.10+)
2. **Automatic Context Propagation** - `contextvars` handled automatically (vs manual with `run_in_executor`)
3. **Simplest Implementation** - One-line delegation to sync version
4. **Industry Standard** - HTTPX and other modern libraries use this pattern
5. **Minimal Overhead** - ~0.5-1ms per call, negligible vs LLM latency (500-2000ms)

---

## Architecture

```
src/skillkit/core/
├── discovery.py          # Sync (existing - no changes)
├── parser.py             # Sync (existing - no changes)
├── manager.py            # Sync (existing - no changes)
└── async_/               # NEW - async wrappers
    ├── __init__.py
    ├── discovery.py
    ├── parser.py
    └── manager.py
```

**Key Principle:** Async modules delegate to sync implementations (zero duplication)

---

## Code Pattern

```python
# src/skillkit/core/async_/parser.py
import asyncio
from pathlib import Path
from ..parser import SkillParser as SyncSkillParser
from ..models import SkillMetadata

class SkillParser:
    """Async YAML parser delegating to sync implementation."""

    def __init__(self):
        self._sync_parser = SyncSkillParser()

    async def parse_skill_file(self, skill_path: Path) -> SkillMetadata:
        """Parse SKILL.md asynchronously using thread pool."""
        return await asyncio.to_thread(
            self._sync_parser.parse_skill_file,
            skill_path
        )
```

**That's it!** All business logic stays in sync version.

---

## Performance Characteristics

| Scenario | Sync | Async | Notes |
|----------|------|-------|-------|
| Single file | 15-30ms | 16-31ms | +3-5% overhead (negligible) |
| 10 files (concurrent) | 150-300ms | 65-130ms | 40-60% faster |
| LLM invocation | 500-2000ms | 500-2000ms | File I/O is <5% of total |

**Verdict:** Async enables better framework integration (FastAPI, async agents) with acceptable overhead.

---

## Alternatives Considered (and Rejected)

| Alternative | Why Rejected |
|-------------|--------------|
| **aiofiles** | External dependency, no performance gain over `asyncio.to_thread()` |
| **run_in_executor** | Manual contextvars, more boilerplate, no benefit for skillkit |
| **Sans-I/O pattern** | Over-engineering for simple file I/O operations |
| **Single module with AsyncXXX classes** | Confusing imports, file bloat |

---

## Usage Examples

### Sync API (unchanged)
```python
from skillkit.core import SkillManager

manager = SkillManager()
skills = manager.discover_skills(Path(".claude/skills"))
```

### Async API (new)
```python
import asyncio
from skillkit.core.async_ import SkillManager

async def main():
    manager = SkillManager()
    skills = await manager.discover_skills(Path(".claude/skills"))
    print(f"Found {len(skills)} skills")

asyncio.run(main())
```

---

## Testing Strategy

**Sync tests:** Comprehensive (existing - no changes)
**Async tests:** Lightweight delegation verification

```python
# tests/test_async_parser.py
import pytest
from skillkit.core.async_ import SkillParser

@pytest.mark.asyncio
async def test_parse_skill_file_async():
    """Verify async delegation works."""
    parser = SkillParser()
    metadata = await parser.parse_skill_file(Path("fixtures/valid-skill/SKILL.md"))
    assert metadata.name == "code-reviewer"
```

---

## Implementation Checklist

- [ ] Create `src/skillkit/core/async_/` namespace
- [ ] Implement 3 async wrappers (discovery, parser, manager)
- [ ] Add `pytest-asyncio>=0.21.0` to dev dependencies
- [ ] Write async tests (`tests/test_async_*.py`)
- [ ] Update README with async examples
- [ ] Verify backwards compatibility (sync API unchanged)

**Estimated effort:** 4-6 hours

---

## References

**Full Research:** [`docs/research-async-file-io.md`](/Users/massimoolivieri/Developer/skillkit/docs/research-async-file-io.md) (800+ lines)
**Implementation Guide:** [`docs/async-implementation-guide.md`](/Users/massimoolivieri/Developer/skillkit/docs/async-implementation-guide.md) (330+ lines)

**Key Sources:**
- [Python asyncio.to_thread docs](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread)
- [Seth Larson: Designing Libraries for Async/Sync I/O](https://sethmlarson.dev/designing-libraries-for-async-and-sync-io)
- [HTTPX architecture](https://github.com/encode/httpx) - Real-world example

---

## Decision Approval

**Reviewed by:** Massimo Olivieri
**Status:** ✅ Approved for v0.2 implementation
**Date:** 2025-11-06
