# Architecture Overview — Agent Hub

Last updated: 2026-04-16

## Project Purpose

**Agent Hub** is a centralized platform for AI agents, currently focused on **document classification with Human-in-the-Loop (HITL) learning**. It classifies business documents (Invoices, Purchase Orders, Referrals, Fax Monitoring, Production Monitoring) using an LLM, then learns from human corrections to improve over time.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Web framework | FastAPI 0.100.0 |
| ASGI server | Uvicorn 0.23.0 |
| Async DB driver | asyncpg 0.29.0 |
| ORM/query builder | SQLAlchemy 2.0.0 (used synchronously in DAL) |
| Database | PostgreSQL |
| LLM provider | Moonshot AI — Kimi-K2.5 (via OpenAI-compatible API) |
| Agent orchestration | LangGraph 0.1.0 (StateGraph) |
| LLM chains/tools | LangChain-core 0.2.0, LangChain-OpenAI 0.1.0 |
| Observability | LangSmith 0.1.0 |
| PDF processing | PyMuPDF (fitz) 1.23.0, pdf2image 1.16.0, Pillow 10.0.0 |
| Data validation | Pydantic 2.0.0 |
| Testing | Pytest, httpx |
| Deployment | Docker, Azure Container Apps (via GitHub Actions) |

---

## Directory Structure

```
Agent_Hub_Git/
├── app/
│   ├── main.py                          # FastAPI app (lifespan, router registration)
│   ├── controllers/
│   │   └── document_classify_controller.py   # HTTP route handlers
│   ├── src/
│   │   ├── agents/
│   │   │   └── document_classify_agent/
│   │   │       ├── agent.py             # LangGraph StateGraph definition
│   │   │       ├── state.py             # ClassificationAgentState
│   │   │       ├── tool.py              # Agent tools (classify, keywords, trust)
│   │   │       └── system_prompt.md     # LLM instructions for classification
│   │   ├── DAL/                         # Data Access Layer (synchronous)
│   │   │   ├── classification_keywords_DA.py
│   │   │   ├── classification_types_DA.py
│   │   │   └── classification_trust_system_DA.py
│   │   ├── services/
│   │   │   └── postgres_db_service.py   # Async wrappers over DAL
│   │   ├── models/                      # Pydantic request/response models
│   │   ├── core/
│   │   │   ├── db_connection.py         # SQLAlchemy sync engine
│   │   │   └── env_config.py            # Environment variable config
│   │   └── infrastructure/
│   │       └── postgres_db.py           # asyncpg pool init/teardown
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── unit/
│   │   └── integration/                 # (empty — not yet implemented)
│   └── init_db/
│       ├── create_tables.sql
│       └── create_store_procedures_and_functions.sql
├── main.py                              # CLI entry point for HITL document processing
├── main_learning.py                     # Alternative learning entry point
├── documents_need_classify/             # Input PDFs
├── docker-compose.yml
├── Dockerfile
└── .github/workflows/ci.yml
```

---

## Application Layers

### 1. HTTP Layer (controllers)
FastAPI router mounted at `/api/document-classify`. Handles request parsing/validation and delegates to the service layer.

### 2. Service Layer (services)
Thin async wrappers over the DAL. Intended to allow controllers to `await` operations. Currently has an async/sync mismatch bug (see known-bugs.md).

### 3. Data Access Layer — DAL (src/DAL)
Synchronous SQL execution via SQLAlchemy. Three modules:
- `classification_keywords_DA.py` — CRUD for document keywords
- `classification_types_DA.py` — read/add classification types
- `classification_trust_system_DA.py` — hit/miss trust tracking

### 4. Infrastructure (src/infrastructure)
Manages asyncpg connection pool lifecycle (startup/shutdown via FastAPI lifespan).

### 5. LangGraph Agent (src/agents/document_classify_agent)
See **Agent Workflow** section below.

---

## Agent Workflow (LangGraph StateGraph)

**Entry:** `main.py` CLI — loads PDFs, converts pages to base64 images, passes to agent.

```
START
  └─► classify_agent          (LLM classifies document using system_prompt.md)
        │
        ├─► agent_tool_routing (if tool calls present)
        │       └─► [tool execution] ──► classify_agent (loop)
        │
        └─► check_trust        (is this type trusted? net_score = hits - misses ≥ 3?)
              │
              ├─► auto_save    (trusted + confidence ≥ 85% → auto-classify, increment hits)
              │       └─► handle_result ──► END
              │
              └─► human_confirmation  ◄── INTERRUPT (user reviews image)
                    │
                    ├── "approve"  → increment HitCount → handle_result → END
                    │
                    └── "correct"  → keyword_extraction_agent
                                         └─► [save keywords, remove bad ones]
                                               └─► handle_result → END
```

**Agent State** (`ClassificationAgentState`):
- `messages` — annotated message history
- `classification_type` — predicted type
- `confidence_score` — float 0–1
- `reasoning` — explanation string
- `keywords` — list of extracted keywords
- `keyword_ids` — DB IDs of saved keywords
- `document_name`, `document_id`, `document_url`, `document_content`, `document_type`

**Agent Tools:**
- `create_classification_reasoning` — structures classification output
- `classify_document` — records the final classification
- `save_extracted_keywords` — persists learned keywords to DB
- `remove_keywords` — deletes unhelpful keywords from DB

**State Persistence:** LangGraph AsyncPostgresSaver checkpointer (PostgreSQL).

---

## Trust System

| Concept | Detail |
|---------|--------|
| Trust Score | `HitCount - MissCount` per classification type |
| Auto-classify threshold | `net_score >= 3` AND `confidence >= 85%` |
| Human approval | Increments `HitCount` |
| Human correction | Increments `MissCount`, triggers keyword learning |

---

## LLM Classification Rules (system_prompt.md)

- Semantic understanding — not keyword matching alone
- Validate keywords with contextual patterns (invoice # + line items + totals)
- Check absence of expected patterns (lowers confidence)
- Multi-page analysis: review all pages, one classification per document
- Confidence bands: 90–100% (perfect match), 0–20% (no patterns)

---

## CI/CD Pipeline (.github/workflows/ci.yml)

**Triggers:** Push or PR to `main` / `dev`

**Steps:**
1. Load secrets into `.env`
2. Docker Compose build
3. Run pytest in container: `docker compose run --rm app python -m pytest app/tests/ -q`
4. Push image to Azure Container Registry (ACR)
5. Deploy to Azure Container Apps
6. `docker compose down -v` cleanup (always)

**Secrets required:** `POSTGRES_CONNECTION_STRING`, `OPENAI_API_KEY`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`, `LANGSMITH_TRACING`, `LANGSMITH_ENDPOINT`, ACR credentials, Azure service principal.

---

## Entry Points

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI web server — starts asyncpg pool, mounts router |
| `main.py` | CLI HITL runner — processes PDFs from `documents_need_classify/` |
| `main_learning.py` | Alternative learning/batch entry point |

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `POSTGRES_CONNECTION_STRING` | PostgreSQL DSN |
| `OPENAI_API_KEY` | LLM API key (Moonshot/Azure OpenAI compatible) |
| `FOUNDRY_PROJECT_ENDPOINT` | Azure AI Foundry endpoint |
| `LANGSMITH_API_KEY` | LangSmith tracing |
| `LANGSMITH_PROJECT` | LangSmith project name |
| `LANGSMITH_TRACING` | Enable/disable tracing (true/false) |
| `LANGSMITH_ENDPOINT` | LangSmith API endpoint |
