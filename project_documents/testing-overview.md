# Testing Overview — Agent Hub

Last updated: 2026-04-16

## Framework

- **Pytest** for unit tests
- **httpx** (async HTTP client) for controller tests
- Integration tests directory exists but is empty — not yet implemented

---

## Test Configuration

**File:** `app/tests/conftest.py`

Key setup:
- Adds `app/` to `sys.path` so imports resolve correctly
- Pre-sets `POSTGRES_CONNECTION_STRING` environment variable
- Sets up `sys.path` and env vars only — the oddly-named model workaround has been removed (BUG-004 resolved)

---

## Test Files

| File | Layer | Tests | Notes |
|------|-------|-------|-------|
| `unit/test_smoke.py` | Sanity | Minimal | CI placeholder — always passes |
| `unit/test_controller.py` | HTTP routes | ~22 tests | Patches service to avoid RecursionError (BUG-001) |
| `unit/test_models.py` | Pydantic models | ~18 tests | Request/response validation |
| `unit/test_service.py` | Service layer | Several | Documents async/sync mismatch bug (BUG-002) |
| `unit/test_keywords_da.py` | DAL — keywords | ~12 test classes | Comprehensive CRUD coverage |
| `unit/test_trust_system_da.py` | DAL — trust | ~9 test classes | Hit/miss tracking coverage |

---

## Running Tests

**Locally:**
```bash
cd app
python -m pytest tests/ -q
```

**In Docker (as CI does):**
```bash
docker compose run --rm app python -m pytest app/tests/ -q
```

---

## CI Integration

Tests run automatically on every push/PR via GitHub Actions (`.github/workflows/ci.yml`). The test job builds the Docker image and runs pytest inside the container before any deployment steps.
