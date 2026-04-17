# RxChat — RAG Chatbot Implementation Plan

> Production architecture and implementation roadmap for RxChat's Retrieval-Augmented Generation pipeline.
> For detailed explanations of technical concepts, see the companion [Explanation Document](./CHATBOT_PLAN_EXPLAINED.md).

---

## Stack Overview

| Component | Technology | Purpose |
|:---|:---|:---|
| **Frontend** | React + Vite → Vercel | Chat UI, auth flows, pre-chat disclaimer |
| **Backend** | Django + DRF → Render | API, RAG orchestrator, background jobs |
| **Database** | Supabase Postgres | Users, conversations, messages, audit logs |
| **Vector DB** | Qdrant Cloud (unified collection) | Drug data embeddings + hybrid search |
| **Embeddings** | OpenAI `text-embedding-3-small` | Query + document embedding (1536-dim) |
| **LLM** | DeepSeek (prefix caching + SSE) | Role-aware answer generation |
| **Task Queue** | Django-Q2 (Postgres broker) | Ingestion jobs, scheduled tasks |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  User (React SPA on Vercel)                                     │
│  ├── Chat UI with SSE streaming                                 │
│  ├── Pre-chat medical disclaimer (shown once per session)       │
│  └── Auth: email → OTP → profile (role set in profile)          │
└──────────────┬──────────────────────────────────────────────────┘
               │ HTTPS / SSE
┌──────────────▼──────────────────────────────────────────────────┐
│  Django API on Render                                           │
│  ├── Auth endpoints (existing)                                  │
│  ├── Chat endpoints (existing — RAG injected transparently)     │
│  ├── ai_service.py — prompt assembly + DeepSeek streaming       │
│  └── rag_service.py — embed → search → filter → format         │
│       │                                                         │
│       ├── 1. Reformulate query (conversation-aware)             │
│       ├── 2. Embed query → OpenAI text-embedding-3-small        │
│       ├── 3. Hybrid search → Qdrant (dense + sparse)            │
│       ├── 4. Relevance gate (score ≥ 0.75 / 0.50 / discard)    │
│       └── 5. Augment prompt → DeepSeek (stream response)        │
└──────────────┬────────┬────────┬────────────────────────────────┘
               │        │        │
    ┌──────────▼──┐  ┌──▼────┐  ┌▼──────────┐
    │  Supabase   │  │Qdrant │  │ DeepSeek  │
    │  Postgres   │  │Cloud  │  │ API       │
    │             │  │       │  │           │
    │ Users       │  │drug_  │  │ Prefix    │
    │ Messages    │  │know-  │  │ caching   │
    │ Audit logs  │  │ledge  │  │ SSE       │
    │ Ingestion   │  │(unified│ │ streaming │
    │ metadata    │  │collection)│           │
    └─────────────┘  └───────┘  └───────────┘
```

---

## Data Sources

### Priority & Status

| Priority | Source | Content | Format | License | Status |
|:---|:---|:---|:---|:---|:---|
| **P0** | NEML (8th Ed, 2024) | Nigeria essential medicines | PDF | Free (govt) | Download from health.gov.ng |
| **P0** | NAFDAC Greenbook | Registered drugs in Nigeria | Web portal | Free (govt) | Scrape from greenbook.nafdac.gov.ng |
| **P0** | NHIA STG | Treatment guidelines | PDF (~124 MB) | Free (govt) | Download from nhia.gov.ng |
| **P1** | WHO EML | Global essential medicines | Excel | Free | Download from essentialmeds.org |
| **P1** | DrugBank | Drug interactions, mechanisms | XML (~700 MB) | CC BY-NC 4.0 | Free for dev; commercial license needed later |
| **P1** | OpenFDA Labels | US drug labelling | JSON API | Public domain | Free API, no key needed |
| **P2** | EMDEX | Comprehensive Nigerian drug ref | API (licensed) | Commercial | Contact Editor@Emdex.org for licensing |

### Storage Estimates

**Qdrant Cloud (free tier: 1 GB):**
- P0 sources only: ~55–120 MB ✅ fits in free tier
- P0 + P1 (curated): ~200–400 MB ⚠️ may need curation
- All sources: ~255–515 MB ⚠️ curate DrugBank/OpenFDA to Nigerian drugs only

**Supabase Postgres (free tier: 500 MB):**
- Estimated total: ~100–160 MB ✅ comfortably fits

---

## Retrieval Pipeline

```
User message
    │
    ├── 1. CLASSIFY: drug lookup / general chat / emergency
    │       └── Emergency → safety escalation (skip RAG)
    │
    ├── 2. REFORMULATE: use conversation context for ambiguous queries
    │       └── "What about side effects?" → "side effects of metformin"
    │
    ├── 3. EMBED: OpenAI text-embedding-3-small → 1536-dim vector
    │
    ├── 4. HYBRID SEARCH: Qdrant dense + sparse (BM25)
    │       ├── top_k: 8 (over-retrieve)
    │       ├── score_threshold: 0.50 (pre-filter)
    │       └── metadata filters: source, category (optional)
    │
    ├── 5. RELEVANCE GATE:
    │       ├── ≥ 0.75 → high-confidence context
    │       ├── 0.50–0.75 → supplementary context
    │       └── < 0.50 → discarded
    │       └── Zero chunks pass → NO_CONTEXT_NOTE fallback
    │
    ├── 6. PROMPT ASSEMBLY:
    │       ├── Static prefix (system + behaviour + safety + role)
    │       │   └── DeepSeek prefix caching reuses this block
    │       ├── RAG context (chunks — NOT shown to user)
    │       └── User query
    │
    ├── 7. GENERATE: DeepSeek stream via SSE
    │
    └── 8. LOG: audit metadata to Postgres
```

### Role Handling

- Role is read from `UserProfile` (set during profile setup)
- Retrieval is **role-agnostic** — same drug data retrieved for all roles
- Generation is **role-aware** — DeepSeek adjusts tone/depth via role prompts
- If user implies a different role mid-conversation, AI confirms before switching

---

## Implementation Phases

### Phase 1: Infrastructure (Weeks 1–2)

- [ ] Migrate SQLite → Supabase Postgres
- [ ] Create Qdrant Cloud cluster + unified collection `drug_knowledge`
- [ ] Set up OpenAI API for embeddings
- [ ] Remove `chromadb`, `langchain-*` from `requirements.txt`
- [ ] Add `qdrant-client`, `pdfplumber` to `requirements.txt`
- [ ] Build PDF parsing infrastructure (for NEML, NAFDAC, NHIA STG)
- [ ] Build base text chunker (1000 chars, 200 overlap)

### Phase 2: Ingestion & RAG (Weeks 3–4)

- [ ] Build parsers: NEML, NAFDAC Greenbook, NHIA STG, WHO, DrugBank, OpenFDA
- [ ] Build embedding + upsert pipeline (OpenAI → Qdrant)
- [ ] Build `rag_service.py`: embed, hybrid search, relevance gate, reformulation
- [ ] Integrate RAG into `ai_service.py`
- [ ] Wire into `views.py` `send_message()` flow
- [ ] Add `IngestionRun` and `AuditLog` models
- [ ] Create `ingest_drugs` management command
- [ ] Run full ingestion of all P0 + P1 sources

### Phase 3: Testing & Deploy (Week 5)

- [ ] Test with 100+ pharmacy queries (Nigeria-specific + general)
- [ ] Test conversation-aware retrieval
- [ ] Test hybrid search accuracy
- [ ] Test role-based response variations
- [ ] Add pre-chat disclaimer to frontend
- [ ] Deploy to Render + Vercel
- [ ] Create golden test set for ongoing evaluation

### Phase 4: Hardening (Weeks 6–9)

- [ ] Re-ranking (if hybrid search quality insufficient)
- [ ] Query classification (drug lookup / general / emergency)
- [ ] Rate limiting per subscription tier
- [ ] Prompt injection sanitization
- [ ] Django-Q2 scheduled jobs (data freshness, OTP cleanup, usage)
- [ ] Monitoring + structured logging
- [ ] Weekly RAG evaluation against golden test set
- [ ] EMDEX integration (when licensed)
- [ ] User feedback mechanism (thumbs up/down)

---

## Key Design Decisions

| Decision | Choice | Rationale |
|:---|:---|:---|
| No source citations in UI | Sources used internally only | User preference — cleaner chat experience |
| Pre-chat disclaimer only | Shown once per session, not per message | User preference — less intrusive |
| Unified Qdrant collection | Metadata handles classification | Simpler ops, flexible filtering |
| Hybrid search from day one | Dense + sparse (BM25) | Drug names need exact keyword matching |
| No LangChain | Direct OpenAI + Qdrant clients | Simpler, fewer dependencies |
| Django-Q2 over Celery | Postgres broker | No Redis needed |
| No offline AI fallback | Show error when backend unreachable | User preference — no fake responses |

---

## Backend File Changes

```
backend/
├── chat/
│   ├── ai_service.py          # [MODIFY] Wire RAG context into prompt
│   ├── rag_service.py         # [NEW] Embed + hybrid search + reformulation
│   ├── ingestion/             # [NEW] Data ingestion package
│   │   ├── __init__.py
│   │   ├── base.py            # Base parser + chunker
│   │   ├── neml_parser.py     # NEML PDF parser
│   │   ├── nafdac_parser.py   # NAFDAC Greenbook scraper
│   │   ├── nhia_stg_parser.py # NHIA STG PDF parser
│   │   ├── who_parser.py      # WHO EML Excel parser
│   │   ├── drugbank_parser.py # DrugBank XML parser
│   │   └── openfda_parser.py  # OpenFDA JSON API puller
│   ├── management/commands/
│   │   └── ingest_drugs.py    # [NEW] Management command
│   ├── models.py              # [MODIFY] Add IngestionRun, AuditLog
│   ├── views.py               # [MODIFY] Wire RAG into send_message
│   └── tasks.py               # [NEW] Django-Q2 task definitions
├── config/settings.py         # [MODIFY] Supabase, Qdrant, OpenAI config
└── requirements.txt           # [MODIFY] Swap deps
```

---

## Risks & Mitigation

| Risk | Mitigation |
|:---|:---|
| Hallucinated drug info | Relevance threshold, NO_CONTEXT_NOTE fallback, pre-chat disclaimer |
| Nigerian PDF parsing quality | Manual QA on parsed chunks; OCR fallback for scanned PDFs |
| DrugBank commercial license | Track source metadata; removable if needed before monetizing |
| EMDEX access | Contact early; defer to P2 if licensing takes time |
| Qdrant free tier overflow | Curate DrugBank/OpenFDA to Nigeria-relevant drugs only |
| DeepSeek data residency | Strip PII before sending; architecture supports LLM swap |
