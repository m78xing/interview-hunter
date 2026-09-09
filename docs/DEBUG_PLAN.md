# Debug Plan - Interview Hunter

## Error Inventory

### Category A: Pre-existing errors (not caused by our changes)

---

#### A1: `app.py` - `setup_logging` type mismatch (4 errors)

**File**: `app.py` lines 30-43

**Errors**:
1. Line 33: `Path` not assignable to `str | None`
2. Line 35: `str | None` not assignable to `StrPath`
3. Line 36: `open()` no matching overload
4. Line 36: `str | None` not assignable to `FileDescriptorOrPath`

**Root cause**: Parameter `config_path: Optional[str]` is reassigned to `Path` inside the function, breaking type narrowing.

**Fix**: Change type to `str | Path | None` or use `str(config_path)`:
```python
def setup_logging(config_path: Optional[str | Path] = None):
```

**Impact**: Low. Only affects static analysis. Runtime works fine since `Path` is always set before use.

---

#### A2: `collector.py` - Missing imports (2 errors)

**File**: `src/agents/collector.py` lines 67, 78

**Errors**:
1. Line 67: `Import "nowcoder_spider" could not be resolved`
2. Line 78: `Import "xhs_spider" could not be resolved`

**Root cause**: These are dynamic imports from `skills/` directories added to `sys.path` at runtime. Pyright can't resolve them statically.

**Fix**: Add `# type: ignore[reportMissingImports]` or use `TYPE_CHECKING` guard:
```python
if TYPE_CHECKING:
    from nowcoder_spider import nowcoderSpider  # type: ignore
```

**Impact**: None. These are runtime-only imports. Fixing is cosmetic only.

---

#### A3: `embedding_provider.py` - Missing imports (2 errors)

**File**: `src/core/embedding_provider.py` lines 87, 125

**Errors**:
1. Line 87: `Import "cohere" could not be resolved`
2. Line 125: `Import "sentence_transformers" could not be resolved`

**Root cause**: Optional dependencies not installed in current environment.

**Fix**: Add `# type: ignore[reportMissingImports]` or install the packages.

**Impact**: None. These are conditional imports guarded by `if provider == "cohere"`.

---

#### A4: `experiment_framework.py` - Return type mismatch (1 error)

**File**: `src/core/experiment_framework.py` line 344

**Error**: `tuple[dict[Unknown, Unknown], dict[Unknown, floating[Any]]]` not assignable to `Tuple[Dict[str, float], Dict[str, float]]`

**Root cause**: `scipy.stats` returns `floating[Any]` not `float`.

**Fix**: Change return type to `Tuple[Dict[str, float], Dict[str, Any]]` or cast values.

**Impact**: Low. Only affects type checking. Runtime values are valid floats.

---

#### A5: `reranker.py` - None passed to str parameter (3 errors)

**File**: `src/core/reranker.py` lines 127, 128, 145

**Errors**:
1. Line 127: `card_id` of type `Unknown | None` passed to `calculate_retrievability_score(card_id: str)`
2. Line 128: Same for `calculate_weakness_score`
3. Line 145: Same for `RankedResult.__init__`

**Root cause**: Loop iterates over results where `card_id` could be `None`.

**Fix**: Add null check before calling methods:
```python
if card_id:
    retrievability = self.calculate_retrievability_score(card_id)
```

**Impact**: Medium. Could cause runtime `TypeError` if `card_id` is actually `None`.

---

#### A6: `user_memory.py` - None assigned to str parameter (4 errors)

**File**: `src/core/user_memory.py` line 89-90

**Errors**:
1. Line 89: `None` assigned to `company: str`
2. Line 89: `None` assigned to `position: str`
3. Line 90: `None` assigned to `company: str`
4. Line 90: `None` assigned to `position: str`

**Root cause**: Function parameters have `str` type but callers pass `None`.

**Fix**: Change parameter types to `Optional[str]`:
```python
def update_company_preference(self, company: Optional[str] = None, ...):
```

**Impact**: Medium. Runtime works but type checker flags potential `None` usage.

---

#### A7: `chroma_client.py` - Optional subscript (10 errors)

**File**: `src/storage/chroma_client.py` lines 86, 93, 94, 109, 116, 128, 129, 144, 145, 175, 176

**Errors**: All `Object of type "None" is not subscriptable`

**Root cause**: Methods return `Optional[dict]` but code directly subscriptes without null check.

**Fix**: Add null checks or use `.get()`:
```python
result = self.collection.get(ids=[card_id])
if result and result.get("documents"):
    return result["documents"][0]
```

**Impact**: High. Could cause runtime `TypeError` if Chroma returns `None`.

---

### Category B: Errors from our changes

---

#### B1: `chat_learning.py` - Optional member access (3 errors)

**File**: `pages/chat_learning.py` lines 53, 61, 78

**Errors**:
1. Line 53: `"route" is not a known attribute of "None"` - `learning_router` could be `None`
2. Line 61: `"chat" is not a known attribute of "None"` - `anxiety_agent` could be `None`
3. Line 78: `"chat" is not a known attribute of "None"` - `llm_client` could be `None`

**Root cause**: `st_state.get()` returns `Optional[T]`, but code calls methods without null checks.

**Fix options**:

**Option 1**: Add null guards (verbose but safe):
```python
if not learning_router:
    response = "路由未初始化"
else:
    route_result = learning_router.route(user_input)
```

**Option 2**: Use assertion (cleaner, assumes init is correct):
```python
assert learning_router is not None
route_result = learning_router.route(user_input)
```

**Option 3**: Use `cast` (tells type checker we know it's not None):
```python
from typing import cast
route_result = cast(LearningRouter, learning_router).route(user_input)
```

**Recommended**: Option 1 for `learning_router` (it's the main entry point), Option 2 for others (they're initialized together).

**Impact**: Medium. If `app.py` initialization fails silently, these would crash at runtime. But the existing `if not all([llm_client, learning_router])` guard at line 26 should catch this.

---

## Summary

| Category | Count | Severity | Action |
|----------|-------|----------|--------|
| A: Pre-existing | 26 | Low-Medium | Fix separately, not blocking |
| B: Our changes | 3 | Low | Add null guards or assertions |

---

## Fix Results

✅ **All 29 errors fixed successfully.**

| File | Errors Before | Errors After | Status |
|------|--------------|--------------|--------|
| `app.py` | 4 | 0 | ✅ Fixed |
| `collector.py` | 2 | 0 | ✅ Fixed |
| `embedding_provider.py` | 2 | 0 | ✅ Fixed |
| `experiment_framework.py` | 1 | 0 | ✅ Fixed |
| `reranker.py` | 3 | 0 | ✅ Fixed |
| `user_memory.py` | 4 | 0 | ✅ Fixed |
| `chroma_client.py` | 10 | 0 | ✅ Fixed |
| `chat_learning.py` | 3 | 0 | ✅ Fixed |
| **Total** | **29** | **0** | **100%** |

### Verification
- `src/` - 35 files scanned, 0 errors
- `pages/` - 5 files scanned, 0 errors
- `app.py` - 0 errors
