# Known Bugs — Agent Hub

Last updated: 2026-04-16

---

## BUG-001: Controller function shadows imported service (RecursionError)

**File:** `app/controllers/document_classify_controller.py`
**Severity:** High — endpoint crashes at runtime

**Description:**
The POST `/api/document-classify/classification-type` endpoint handler function is named `classification_type`. The controller also imports a service function called `classification_type` from the service module. Because the function definition overwrites the name in the module scope, calling the service function inside the handler actually calls the handler itself recursively, causing a `RecursionError`.

**Workaround in tests:** `test_controller.py` (lines 6–12) patches the service import to avoid the recursion.

**Fix:** Rename either the endpoint handler function or import the service function under an alias.
```python
# Option A: alias the import
from app.src.services.postgres_db_service import classification_type as create_classification_type_svc

# Option B: rename the route handler
async def add_classification_type(...):
```

---

## BUG-002: Async/sync mismatch in service layer (TypeError)

**File:** `app/src/services/postgres_db_service.py`
**Severity:** High — service calls fail at runtime

**Description:**
The service layer wraps DAL functions with `async def` and `await`s the return value. However, the underlying DAL functions (e.g., `get_keywords_by_type()`) are plain synchronous functions, not coroutines. Awaiting a non-awaitable raises `TypeError: object NoneType/list can't be used in 'await' expression`.

**Evidence:** `test_service.py` (lines 7–12) documents this behavior.

**Fix:** Either:
- Remove `await` from service calls that wrap sync DAL functions, or
- Convert DAL functions to async using `asyncpg` directly, or
- Use `asyncio.get_event_loop().run_in_executor()` to run sync DAL in a thread pool.

---

## BUG-003: POST /classify endpoint not implemented

**File:** `app/controllers/document_classify_controller.py`
**Severity:** Medium — feature gap

**Description:**
The `/api/document-classify/classify` POST endpoint is stubbed with a TODO comment. The actual document classification workflow runs only through the CLI (`main.py`). There is no HTTP-accessible way to trigger classification.

**Status:** Known — not a crash, but limits API usability.

---

## BUG-004: Naming conflict in conftest.py for oddly-named model file

**File:** `app/tests/conftest.py` (lines around 50–57)
**Severity:** Low — test-only workaround

**Description:**
There is a Pydantic model file named `document_classify_response.model.py` (contains a dot before `py` in the middle of the filename). Python's import system cannot import a module whose name contains a dot. `conftest.py` works around this by manually loading the file.

**Fix:** Rename the file to `document_classify_response_model.py` or `document_classify_response.py`.
