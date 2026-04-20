# Document Classification Agent — Workflow Diagram

Last updated: 2026-04-17

```mermaid
flowchart TD
    %% ── Input ────────────────────────────────────────────────
    IN([" 📄 Input PDF<br/>documents_need_classify/"])
    IN --> PREP["Convert pages<br/>to base64 images"]

    %% ── Classification ───────────────────────────────────────
    PREP --> CA

    subgraph CLASSIFY ["🤖 Classification Loop"]
        CA["classify_agent<br/>LLM · Kimi-K2.5<br/>system_prompt.md + keywords"]
        CA --> AR{Tool calls?}
        AR -- Yes --> TR["agent_tool_routing<br/>ToolNode"]
        TR -- loop --> CA
    end

    AR -- No / has classification --> CT

    %% ── Trust Check ──────────────────────────────────────────
    subgraph TRUST ["⚖️ Trust Check"]
        CT["check_trust<br/>evaluate type trust score"]
        CT --> TQ{"net_score ≥ 3<br/>AND confidence ≥ 85%?"}
    end

    %% ── Auto-Save Path ───────────────────────────────────────
    TQ -- "✅ Trusted + High Confidence" --> AUTO

    subgraph AUTOSAVE ["⚡ Auto-Classify"]
        AUTO["update_hit_count<br/>update_keywords_hit<br/>for matched_keyword_ids"]
    end

    AUTO --> HR_AUTO["handle_result<br/>status: completed<br/>approved: true"]

    %% ── Human Review Path ────────────────────────────────────
    TQ -- "⚠️ Not trusted or low confidence" --> HC

    subgraph HUMAN ["👤 Human Confirmation  ⏸ INTERRUPT"]
        HC["human_confirmation<br/>show: document, proposed type,<br/>confidence, trust scores"]
        HC --> HD{"Human<br/>decision"}
    end

    %% ── Approve Branch ───────────────────────────────────────
    HD -- "✅ approve" --> APP

    subgraph APPROVE ["✅ Approval Path"]
        APP["update_hit_count<br/>update_keywords_hit<br/>for matched_keyword_ids"]
    end

    APP --> HR_APPR["handle_result<br/>status: completed<br/>approved: true"]

    %% ── Correct Branch ───────────────────────────────────────
    HD -- "✏️ correct + correct_type" --> CORR

    subgraph LEARN ["📚 Learning Path"]
        CORR["update_miss_count<br/>update_keywords_miss<br/>for matched_keyword_ids"]
        CORR --> KEA["keyword_extraction_agent<br/>re-analyze with correct type<br/>build new keyword list"]
        KEA --> KET["keyword_extraction_tool_node<br/>save_extracted_keywords<br/>{text, keyword_type, source}"]
    end

    KET --> HR_CORR["handle_result<br/>status: completed<br/>learned_from_correction: true<br/>keywords_added: [...]"]

    %% ── Outputs ──────────────────────────────────────────────
    HR_AUTO & HR_APPR --> OUT_OK([" 🏷️ Output<br/>classification_type<br/>confidence_score<br/>reasoning"])
    HR_CORR --> OUT_LEARN([" 🏷️ Output<br/>classification_type ← corrected<br/>new keywords persisted to DB"])

    %% ── DB interactions ──────────────────────────────────────
    subgraph DB ["🗄️ PostgreSQL"]
        KW[("ClassificationKeywords<br/>[KeywordID] text (TYPE)<br/>HitCount · MissCount<br/>LastSeenDate")]
        TS[("ClassificationTypeTrustSystem<br/>HitCount · MissCount<br/>net_score = H - M")]
        CP[("LangGraph Checkpoint<br/>thread_id conversation history")]
    end

    CA -. "loads top-K keywords<br/>ranked by signal strength" .-> KW
    APP -. "increment HitCount<br/>LastSeenDate = NOW()" .-> KW
    CORR -. "increment MissCount<br/>LastSeenDate = NOW()" .-> KW
    AUTO -. "increment HitCount<br/>LastSeenDate = NOW()" .-> KW
    APP -. "increment HitCount" .-> TS
    CORR -. "increment MissCount" .-> TS
    AUTO -. "increment HitCount" .-> TS
    HC -. "read trust scores" .-> TS
    CT -. "read trust scores" .-> TS
    HC -. "save/resume state<br/>via thread_id" .-> CP

    %% ── Styling ──────────────────────────────────────────────
    classDef node fill:#1e293b,stroke:#64748b,color:#f1f5f9
    classDef decision fill:#1e3a5f,stroke:#3b82f6,color:#f1f5f9
    classDef io fill:#14532d,stroke:#22c55e,color:#f1f5f9
    classDef db fill:#3b1f5e,stroke:#a855f7,color:#f1f5f9
    classDef result fill:#1c3a2e,stroke:#34d399,color:#f1f5f9

    class CA,TR,CT,AUTO,APP,CORR,KEA,KET,PREP node
    class AR,TQ,HD decision
    class IN,OUT_OK,OUT_LEARN io
    class KW,TS,CP db
    class HR_AUTO,HR_APPR,HR_CORR result
```

---

## Node Reference

| Node | Role |
|---|---|
| `classify_agent` | LLM node — reads system prompt + top-K keywords, calls `classify_document` tool |
| `agent_tool_routing` | Executes any tool calls the LLM made, loops back to `classify_agent` |
| `check_trust` | Reads `ClassificationTypeTrustSystem`; routes to auto-save or human review |
| `human_confirmation` | LangGraph `interrupt` — pauses graph, waits for human approve/correct |
| `keyword_extraction_agent` | Re-runs LLM with the correct type to extract distinguishing keywords |
| `keyword_extraction_tool_node` | Calls `save_extracted_keywords` to persist typed keywords to DB |
| `handle_result` | Final aggregation node before END |

## Trust Threshold

```
Auto-classify when:  (HitCount - MissCount) >= 3  AND  confidence >= 85%
Otherwise:           route to human_confirmation
```

## Learning Loop

Every human correction feeds back into `ClassificationKeywords`:
- New keywords saved with `keyword_type` + `source = HUMAN_CORRECTED`
- Matched keyword `MissCount` incremented (lowers future signal rank)
- Next classification loads updated top-K keyword list from DB