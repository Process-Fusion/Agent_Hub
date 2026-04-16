# Database Schema — Agent Hub

Last updated: 2026-04-16

## Database

PostgreSQL. Schema defined in `app/init_db/create_tables.sql` and `app/init_db/create_store_procedures_and_functions.sql`.

---

## Tables

### ClassificationTypes

Defines the known document categories.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| TypeID | int | PK, auto-increment | |
| TypeName | varchar(100) | UNIQUE, NOT NULL | Invoice, Purchase Order, Referral, Fax_Monitoring, Production_Monitoring |
| Description | varchar(500) | nullable | |
| IsActive | boolean | default true | soft-delete flag |
| CreatedDate | timestamp | default now() | |
| ModifiedDate | timestamp | auto-updated by trigger | |

---

### ClassificationKeywords

Keywords/phrases associated with each classification type. Populated by the LLM learning process.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| KeywordID | int | PK, auto-increment | |
| TypeID | int | FK → ClassificationTypes | |
| ClassificationKeywords | varchar(500) | NOT NULL | keyword or phrase text |
| Stage | int | default 1 | multi-stage matching pipeline |
| IsActive | boolean | default true | soft-delete |
| CreatedDate | timestamp | default now() | |
| ModifiedDate | timestamp | auto-updated by trigger | |

---

### ClassificationTypeTrustSystem

Tracks classification accuracy per type to enable auto-classification.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| TrustID | int | PK, auto-increment | |
| TypeID | int | FK → ClassificationTypes, UNIQUE | one record per type |
| HitCount | int | default 0 | correct classifications (human approved) |
| MissCount | int | default 0 | incorrect classifications (human corrected) |
| CreatedDate | timestamp | default now() | |
| ModifiedDate | timestamp | auto-updated by trigger | |

**Trust Score formula:** `HitCount - MissCount`
**Auto-classify when:** `trust_score >= 3` AND `confidence >= 85%`

---

## Triggers

| Trigger | On | Action |
|---------|----|--------|
| `trg_classification_types_modified` | UPDATE on ClassificationTypes | Calls `update_modified_date()` |
| `trg_classification_keywords_modified` | UPDATE on ClassificationKeywords | Calls `update_modified_date()` |
| `trg_trust_system_modified` | UPDATE on ClassificationTypeTrustSystem | Calls `update_modified_date()` |
| `trg_insert_trust_on_new_type` | INSERT on ClassificationTypes | Calls `insert_trust_on_new_type()` — auto-creates trust record |

---

## Functions & Stored Procedures

### `update_modified_date()` (function)
Automatically sets `ModifiedDate = NOW()` on any UPDATE. Used by the three update triggers above.

### `get_classification_types()` (function)
Returns all active classification types with name and description.
```sql
SELECT TypeID, TypeName, Description FROM ClassificationTypes WHERE IsActive = true
```

### `insert_classification_type(p_TypeName varchar, p_Description varchar)` (procedure)
Inserts a new classification type. The `trg_insert_trust_on_new_type` trigger automatically creates a corresponding trust record.

---

## Seed Data

Five predefined types with initial keywords (from `create_tables.sql` lines 105–127):

| Type | Example Keywords |
|------|-----------------|
| Invoice | "invoice", vendor names |
| Purchase Order | "Purchase Order", "Requisition" |
| Referral | "Diagnostic", "Referral" |
| Fax_Monitoring | fax command patterns |
| Production_Monitoring | production monitoring patterns |

---

## Connection

- **Sync (DAL):** SQLAlchemy engine via `app/src/core/db_connection.py`
- **Async (infrastructure):** asyncpg pool via `app/src/infrastructure/postgres_db.py`
- **DSN format:** `postgresql://user:password@host:port/dbname`
- **Local dev port:** 5433 (docker-compose maps 5432 → 5433)
