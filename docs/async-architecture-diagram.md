# Async Architecture Diagram

Visual representation of skillkit v0.2 async implementation.

---

## Module Structure

```
src/skillkit/
│
├── core/                          # Framework-agnostic core
│   │
│   ├── __init__.py                # Exports: SkillDiscovery, SkillParser, SkillManager
│   │
│   ├── discovery.py               # SYNC IMPLEMENTATION (existing)
│   │   └── class SkillDiscovery
│   │       ├── scan_directory()
│   │       └── find_skill_files()
│   │
│   ├── parser.py                  # SYNC IMPLEMENTATION (existing)
│   │   └── class SkillParser
│   │       ├── parse_skill_file()
│   │       ├── _extract_frontmatter()
│   │       └── _extract_required_field()
│   │
│   ├── manager.py                 # SYNC IMPLEMENTATION (existing)
│   │   └── class SkillManager
│   │       ├── discover_skills()
│   │       └── load_skill_content()
│   │
│   ├── models.py                  # SHARED (no I/O)
│   │   ├── SkillMetadata
│   │   └── Skill
│   │
│   ├── exceptions.py              # SHARED (no I/O)
│   │   ├── SkillkitError
│   │   ├── InvalidYAMLError
│   │   └── MissingRequiredFieldError
│   │
│   ├── processors.py              # SHARED (no I/O)
│   │   └── ContentProcessor
│   │
│   └── async_/                    # ASYNC WRAPPERS (NEW in v0.2)
│       │
│       ├── __init__.py            # Exports: SkillDiscovery, SkillParser, SkillManager
│       │
│       ├── discovery.py           # ASYNC WRAPPER
│       │   └── class SkillDiscovery
│       │       ├── _sync_discovery: SyncSkillDiscovery
│       │       ├── async scan_directory() ──────┐
│       │       └── async find_skill_files() ────┤
│       │                                         │
│       ├── parser.py               # ASYNC WRAPPER          │
│       │   └── class SkillParser                │
│       │       ├── _sync_parser: SyncSkillParser│
│       │       └── async parse_skill_file() ────┤
│       │                                         │
│       └── manager.py              # ASYNC WRAPPER          │
│           └── class SkillManager               │
│               ├── _discovery: AsyncSkillDiscovery
│               ├── _parser: AsyncSkillParser    │
│               ├── async discover_skills() ─────┤
│               └── async load_skill_content() ──┤
│                                                 │
│       ┌─────────────────────────────────────────┘
│       │
│       └──> asyncio.to_thread() ──> ThreadPoolExecutor ──> Sync Implementation
│                                                                  │
│                                                                  ├─> pathlib.Path.read_text()
│                                                                  ├─> yaml.safe_load()
│                                                                  └─> Business logic
```

---

## Data Flow: Sync vs Async

### Sync Flow (v0.1 - existing)

```
User Code
   │
   └──> SkillManager.discover_skills()
           │
           ├──> SkillDiscovery.scan_directory()
           │       │
           │       └──> Path.iterdir() ────> filesystem
           │
           └──> SkillParser.parse_skill_file()
                   │
                   ├──> Path.read_text() ────> filesystem
                   └──> yaml.safe_load() ────> parsing
                           │
                           └──> SkillMetadata
```

**Execution:** Sequential, blocking

---

### Async Flow (v0.2 - new)

```
User Code (async)
   │
   └──> await SkillManager.discover_skills()
           │
           ├──> await SkillDiscovery.scan_directory()
           │       │
           │       └──> asyncio.to_thread(sync_discovery.scan_directory)
           │               │
           │               └──> ThreadPoolExecutor
           │                       │
           │                       └──> Path.iterdir() ────> filesystem
           │
           └──> asyncio.gather([parse_skill_file() for each skill])
                   │
                   ├──> await SkillParser.parse_skill_file() ──┐
                   ├──> await SkillParser.parse_skill_file() ──┤ Concurrent
                   └──> await SkillParser.parse_skill_file() ──┘
                           │
                           └──> asyncio.to_thread(sync_parser.parse_skill_file)
                                   │
                                   └──> ThreadPoolExecutor
                                           │
                                           ├──> Path.read_text() ────> filesystem
                                           └──> yaml.safe_load() ────> parsing
                                                   │
                                                   └──> SkillMetadata
```

**Execution:** Concurrent, non-blocking (via thread pool)

---

## Import Paths

### Sync API (v0.1 - unchanged)

```python
from skillkit.core import SkillDiscovery, SkillParser, SkillManager
from skillkit.core.models import SkillMetadata, Skill
from skillkit.core.exceptions import SkillkitError, InvalidYAMLError

# Usage
manager = SkillManager()
skills = manager.discover_skills(Path(".claude/skills"))
```

### Async API (v0.2 - new)

```python
from skillkit.core.async_ import SkillDiscovery, SkillParser, SkillManager
from skillkit.core.models import SkillMetadata, Skill  # Shared models
from skillkit.core.exceptions import SkillkitError      # Shared exceptions

# Usage
manager = SkillManager()
skills = await manager.discover_skills(Path(".claude/skills"))
```

**Key:** Same class names, different namespace (`core` vs `core.async_`)

---

## Concurrency Model

### Thread Pool Execution

```
Main Async Event Loop
   │
   ├─ Coroutine 1: parse skill A ──> asyncio.to_thread() ──┐
   ├─ Coroutine 2: parse skill B ──> asyncio.to_thread() ──┤
   ├─ Coroutine 3: parse skill C ──> asyncio.to_thread() ──┤
   └─ Coroutine 4: parse skill D ──> asyncio.to_thread() ──┤
                                                             │
                           ┌─────────────────────────────────┘
                           │
                      ThreadPoolExecutor
                      (default: max_workers = min(32, os.cpu_count() + 4))
                           │
                           ├─ Thread 1: sync_parser.parse(A) ────> I/O + YAML
                           ├─ Thread 2: sync_parser.parse(B) ────> I/O + YAML
                           ├─ Thread 3: sync_parser.parse(C) ────> I/O + YAML
                           └─ Thread 4: sync_parser.parse(D) ────> I/O + YAML
                                   │
                                   └──> Return SkillMetadata ──> Event Loop
```

**Benefit:** Multiple files processed concurrently (40-60% faster for 10+ skills)

---

## Error Handling Flow

### Sync (existing)

```
SkillManager.discover_skills()
   │
   └──> for each skill_path:
           try:
               parse_skill_file(skill_path)
           except Exception as e:
               log warning
               continue  # Graceful degradation
```

### Async (new)

```
SkillManager.discover_skills()
   │
   └──> asyncio.gather([_parse_skill_safe(path) for path in paths])
           │
           └──> for each path (concurrent):
                   try:
                       await parse_skill_file(path)
                   except Exception as e:
                       log warning
                       return None  # Graceful degradation
```

**Same behavior:** Failed skills are logged and skipped, successful ones returned.

---

## Type System

### Sync Function Signature

```python
def discover_skills(self, skills_dir: Path) -> List[SkillMetadata]:
    """Synchronous discovery."""
    ...
```

**Return type:** `List[SkillMetadata]` (immediate)

### Async Function Signature

```python
async def discover_skills(self, skills_dir: Path) -> List[SkillMetadata]:
    """Asynchronous discovery."""
    ...
```

**Return type:** `Coroutine[Any, Any, List[SkillMetadata]]` (implicit)
**Usage:** `skills = await manager.discover_skills(path)`

---

## Memory Layout

### Shared Objects (no duplication)

```
┌─────────────────────────────────────────┐
│  SkillMetadata (dataclass)              │  Shared by sync & async
│  ├─ name: str                           │  (immutable, no I/O)
│  ├─ description: str                    │
│  ├─ skill_path: Path                    │
│  └─ allowed_tools: tuple[str, ...]      │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  SkillkitError (exception)              │  Shared by sync & async
│  InvalidYAMLError                        │  (no state, no I/O)
│  MissingRequiredFieldError               │
└─────────────────────────────────────────┘
```

### Async Wrapper Objects (lightweight)

```
┌─────────────────────────────────────────┐
│  AsyncSkillParser                       │  Wrapper (~100 bytes)
│  ├─ _sync_parser: SyncSkillParser       │  ← Reference to sync impl
│  └─ async methods (code, not data)      │
└─────────────────────────────────────────┘
```

**Memory overhead:** ~300 bytes per async manager instance (3 wrappers × ~100 bytes)

---

## Performance Timeline

### Sync (sequential) - 10 skills

```
Time (ms):  0     30    60    90   120   150   180   210   240   270   300
            │─────│─────│─────│─────│─────│─────│─────│─────│─────│─────│
Parse 1:    [====]
Parse 2:          [====]
Parse 3:                [====]
Parse 4:                      [====]
Parse 5:                            [====]
Parse 6:                                  [====]
Parse 7:                                        [====]
Parse 8:                                              [====]
Parse 9:                                                    [====]
Parse 10:                                                         [====]
            │─────────────────────────────────────────────────────│
            Total: ~300ms (30ms × 10)
```

### Async (concurrent) - 10 skills

```
Time (ms):  0     30    60    90   120
            │─────│─────│─────│─────│
Parse 1:    [====]
Parse 2:    [====]
Parse 3:    [====]
Parse 4:    [====]
Parse 5:          [====]
Parse 6:          [====]
Parse 7:          [====]
Parse 8:          [====]
Parse 9:                [====]
Parse 10:               [====]
            │─────────────────│
            Total: ~120ms (4 threads × 30ms + overhead)
```

**Speedup:** 2.5x faster (limited by thread pool size)

---

## Testing Architecture

### Sync Tests (comprehensive - existing)

```
tests/
├── test_discovery.py          # 15 tests (edge cases, errors, etc.)
├── test_parser.py             # 20 tests (YAML parsing, validation, etc.)
└── test_manager.py            # 10 tests (integration, error handling, etc.)
```

**Coverage:** 70%+ (business logic thoroughly tested)

### Async Tests (delegation verification - new)

```
tests/
├── test_async_discovery.py    # 3 tests (delegation, concurrency)
├── test_async_parser.py       # 3 tests (delegation, concurrency)
└── test_async_manager.py      # 5 tests (integration, gather, error handling)
```

**Coverage:** Verifies async wrappers delegate correctly; sync tests cover logic

---

## Backwards Compatibility

### v0.1 Code (still works)

```python
from skillkit.core import SkillManager

manager = SkillManager()
skills = manager.discover_skills(Path(".claude/skills"))
# ✅ No changes needed
```

### v0.2 Code (new async API)

```python
from skillkit.core.async_ import SkillManager

async def main():
    manager = SkillManager()
    skills = await manager.discover_skills(Path(".claude/skills"))

asyncio.run(main())
# ✅ New functionality, opt-in
```

**Guarantee:** v0.1 sync API unchanged; v0.2 adds parallel async API

---

## Decision Tree: When to Use Async

```
                   ┌─────────────────────┐
                   │ Using async         │
                   │ framework?          │
                   │ (FastAPI, async     │
                   │ LangChain, etc.)    │
                   └──────┬──────────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
             YES                     NO
              │                       │
              │                       └──> Use sync API
              │                           (simpler, less overhead)
              │
              └──> Use async API
                   (integrates cleanly)
```

**Rule of thumb:** Use async for API consistency in async codebases, not for raw speed.

---

**Diagram Legend:**
- `──>` : Synchronous call
- `~~~>` : Asynchronous call (await)
- `[====]` : Execution time
- `│` : Sequential execution
- `├─┤` : Concurrent execution
