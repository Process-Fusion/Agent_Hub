# Keyword Learning & Memory Improvements

Last updated: 2026-04-16 (Schema Changes completed)

Based on LLM Wiki concepts: Signal Detection, Memory Metadata, Memory Staleness, Scope Separation, Hybrid Retrieval, Structured Facts, Selective Retrieval.

---

## Schema Changes (`ClassificationKeywords`)

- [x] **Add `keyword_type` column** (enum: `primary`, `contextual`, `absence`, `structural`, `semantic_alias`)
  - `primary` — core identifier, strong signal (e.g. `"Invoice"`, `"Purchase Order"`)
  - `contextual` — must co-exist with primary to validate (e.g. `"Due Date"`, `"Line Items"`)
  - `absence` — its absence disproves the type (e.g. `"no invoice number"`)
  - `structural` — document layout fingerprint (e.g. `"line items table"`)
  - `semantic_alias` — synonym/semantic equivalent (e.g. `"Bill"` for Invoice)

- [x] **Add `source` column** (enum: `seed`, `agent_extracted`, `human_corrected`)
  - `seed` — hardcoded at init, high trust, do not remove lightly
  - `agent_extracted` — LLM-learned, not yet validated by human, lower trust
  - `human_corrected` — came from a human correction event, high trust

- [x] **Add `keyword_hit_count` column** (int, default 0)
  - Incremented when this keyword appeared in a correctly classified document

- [x] **Add `keyword_miss_count` column** (int, default 0)
  - Incremented when this keyword appeared in a misclassified document

- [x] **Add `last_seen_date` column** (timestamp, nullable)
  - Updated each time this keyword matches a document; used for staleness detection

---

## Agent / Tool Changes

- [x] **Extend `save_extracted_keywords` tool** to accept typed keywords
  - Change `keywords: list[str]` → `keywords: list[dict]` with `text`, `keyword_type`
  - Update DAL `insert_keywords` to persist these fields

- [x] **Update system prompt learning scenario** to instruct the LLM to categorize each keyword by type and stage when calling `save_extracted_keywords`

- [x] **Selective keyword loading** in system prompt (`{classification_keywords}`)
  - Instead of dumping all keywords, load top-K per type ranked by `(keyword_hit_count - keyword_miss_count)` DESC
  - Reduces token usage and prevents prompt bloat as keywords accumulate

- [x] **Keyword staleness auto-deactivation**
  - Add a job or inline check: if `last_seen_date` is older than 2 month, flag `IsActive = false` for review, add API call so that a scheduler from Azure can call this weekly.

- [x] **Keyword Hit Count, Miss Count and LastSeenDate Update**


---

## New Seed Keywords Per Document Type

### Invoice
- [x] Semantic aliases: `"Bill"`, `"Statement"`, `"Tax Invoice"`, `"Charges"`, `"Payment Due"`
- [x] Contextual validators: `"Invoice No."`, `"Invoice Date"`, `"Due Date"`, `"Bill To"`, `"Subtotal"`, `"Tax Rate"`, `"Amount Due"`, `"Net 30"`, `"Net 60"`, `"Remit To"`
- [x] Structural: `"line items table"`, `"quantity × unit price"`, `"vendor letterhead"`
- [x] Absence indicators: `"no line items"`, `"no total amount"`

### Purchase Order
- [x] Semantic aliases: `"PO#"`, `"P.O."`, `"Order Form"`, `"Procurement Form"`
- [x] Contextual validators: `"Ship To"`, `"Delivery Date"`, `"Requested By"`, `"Approved By"`, `"Order Date"`, `"Requisition Number"`, `"Vendor"`, `"Supplier"`
- [x] Structural: `"authorization signature block"`, `"delivery instructions section"`
- [x] Absence indicators: `"no invoice number"`, `"no 'amount due'"`, `"no 'remit to'"`

### Referral
- [x] Semantic aliases: `"Referral Form"`, `"Consultation Request"`, `"Patient Transfer"`
- [x] Contextual validators: `"Referring Physician"`, `"Referring Provider"`, `"Date of Birth"`, `"Diagnosis Code"`, `"ICD-10"`, `"Clinical Information"`, `"Reason for Referral"`, `"Specialist"`
- [x] Structural: `"clinical notes section"`, `"patient demographics block"`

### Fax_Monitoring
- [x] Semantic aliases: `"Facsimile"`, `"FAX TRANSMISSION"`, `"Fax Cover Sheet"`
- [x] Contextual validators: `"Fax Number"`, `"Number of Pages"`, `"Date/Time Sent"`, `"Transmission Report"`, `"OK/ERROR status"`
- [x] Structural: `"transmission log table"`, `"fax header strip"`

### Production_Monitoring
- [x] Semantic aliases: `"Production Report"`, `"Daily Production"`, `"Shift Report"`, `"Output Summary"`
- [x] Contextual validators: `"Units Produced"`, `"Batch Number"`, `"Production Line"`, `"Shift Date"`, `"Downtime"`, `"Efficiency %"`, `"Defect Rate"`
- [x] Structural: `"production metrics table"`, `"shift supervisor signature"`
