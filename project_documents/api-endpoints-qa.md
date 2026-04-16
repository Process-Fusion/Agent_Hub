# API Endpoints — Agent Hub

Last updated: 2026-04-16

## Base URL

```
http://localhost:8000
```

---

## Root

| Method | Path | Response |
|--------|------|----------|
| GET | `/` | `{"service": "agent-hub", "docs": "/docs"}` |

---

## Document Classification

**Router prefix:** `/api/document-classify`
**File:** `app/controllers/document_classify_controller.py`

| Method | Path | Purpose | Implementation Status |
|--------|------|---------|----------------------|
| POST | `/api/document-classify/classify` | Classify a document | **Stubbed / TODO** — not yet implemented |
| GET | `/api/document-classify/types` | List all active classification types | Implemented |
| GET | `/api/document-classify/keywords/{classification_type}` | Get keywords for a type | Implemented |
| POST | `/api/document-classify/type` | Add a new classification type | Implemented (has naming-conflict bug — see known-bugs.md) |

---

## Endpoint Details

### GET `/api/document-classify/types`

Returns all active classification types from `ClassificationTypes` table.

**Response model:** list of `ClassificationTypeResponse`
```json
[
  { "TypeID": 1, "TypeName": "Invoice", "Description": "..." },
  ...
]
```

---

### GET `/api/document-classify/keywords/{classification_type}`

Returns keywords associated with the given classification type name.

**Path param:** `classification_type` — string name (e.g., `"Invoice"`)

**Response model:** list of `ClassificationKeywordResponse`
```json
[
  { "KeywordID": 1, "TypeID": 1, "ClassificationKeywords": "invoice", "Stage": 1 },
  ...
]
```

---

### POST `/api/document-classify/type`

Adds a new classification type.

**Request body:**
```json
{
  "TypeName": "New Type",
  "Description": "Optional description"
}
```

**Response:** Created type record.

**Known bug:** The controller function is named `classification_type`, which shadows the imported service function of the same name, causing a `RecursionError`. This is worked around in tests by patching. See [known-bugs.md](known-bugs.md).

---

### POST `/api/document-classify/classify`

**Status: NOT IMPLEMENTED** — stub only.

Intended to accept a document (PDF or image) and return a classification result. The full classification flow currently runs via the CLI (`main.py`), not this endpoint.

---

## Interactive API Docs

FastAPI auto-generates Swagger UI at `/docs` and ReDoc at `/redoc`.

---

## Notes

- Classification is currently triggered via the CLI (`main.py`) HITL workflow, not through the REST API.
- The REST API primarily supports CRUD operations for classification types and keywords.
- Agent state persistence uses LangGraph AsyncPostgresSaver (PostgreSQL-backed checkpointer).
