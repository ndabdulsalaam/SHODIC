# RxChat RAG — Explanation of AI Implementation Plan

> This document clarifies specific technical concepts from the architecture plan that were flagged for further explanation.

---

## 1. What is "Conversation-Aware Retrieval"?

**Short answer:** It means using the context of the ongoing conversation (the last 2–3 messages) to build a better search query for Qdrant — not just the latest single message.

### The Problem It Solves

Consider this conversation:

```
User: "What is metformin used for?"
AI:   "Metformin is used for type 2 diabetes..."
User: "What about side effects?"    ← THIS is the problem
```

The second message — "What about side effects?" — contains **no drug name**. If you embed just "What about side effects?" and search Qdrant, you'll get garbage results because the query has no specificity.

### How It Works

**Without** conversation-aware retrieval:
```
Search query = "What about side effects?"
→ Qdrant returns random side-effect chunks from many drugs
→ Bad answer
```

**With** conversation-aware retrieval:
```
Search query = "What about side effects?" + context from last 2 messages
→ Reformulated as: "side effects of metformin"
→ Qdrant returns metformin-specific side-effect data
→ Accurate answer
```

### How to Implement It

The simplest approach: before embedding the user's query, prepend relevant context from the conversation history:

```
augmented_query = f"{last_assistant_drug_mention}: {user_query}"
```

Or use the LLM itself to reformulate:
```
"Given this conversation history, rewrite the user's latest question
 as a standalone search query: ..."
```

### Is It Role-Aware?

**No — conversation-aware retrieval is NOT about roles.** It's purely about making the search query more specific by using conversation context.

Role handling is entirely separate:
- **Retrieval** searches Qdrant the same way regardless of role — it finds the same drug data chunks for a patient or pharmacist
- **Generation** is where DeepSeek adjusts its response tone and depth based on the role (via your existing role prompts in `ai_service.py`)

The retrieval is role-agnostic. The LLM is role-aware. This is the correct design — you don't want to hide drug interaction data from a patient just because they're not a pharmacist; you want to present it differently.

---

## 2. What is "Audit Logging" and Will It Fill Up My Database?

### What It Means

Audit logging means saving a record of **what happened** during each AI interaction. For a medical chatbot, this is important for:

1. **Debugging** — When the AI gives a bad answer, you can look at what chunks were retrieved and why
2. **Quality improvement** — Track which queries get poor retrieval scores over time
3. **Compliance** — If someone questions an answer the chatbot gave, you have a record
4. **Cost tracking** — Know how many tokens each user consumes

### What Gets Logged (Per Query)

A single audit log row stores:

| Field | Size | Example |
|:---|:---|:---|
| `user_id` | 36 bytes | UUID |
| `query` | ~100–500 bytes | The user's question text |
| `chunk_ids_retrieved` | ~200 bytes | List of 5 Qdrant point IDs |
| `top_score` | 8 bytes | `0.87` |
| `model_used` | ~20 bytes | `deepseek-chat` |
| `tokens_used` | 8 bytes | `2847` |
| `latency_ms` | 8 bytes | `1850` |
| `timestamp` | 8 bytes | datetime |
| **Total per row** | **~400–800 bytes** | |

### Storage Impact on Supabase Free Tier

Supabase free tier gives you **500 MB** of Postgres storage.

| Usage Level | Queries/Day | Storage/Month | Months Before 500 MB |
|:---|:---|:---|:---|
| Light (dev/testing) | 50 | ~1.2 MB | **400+ months** |
| Moderate (small user base) | 500 | ~12 MB | **40+ months** |
| Heavy (growing product) | 5,000 | ~120 MB | **4 months** |

**Verdict:** Audit logging will NOT fill up your database for a very long time. Even at 500 queries/day, you'd use ~12 MB/month — just 2.4% of the free tier per month.

### Recommended Approach

- **Log everything during development and early production** — it's invaluable for debugging
- **Add a retention policy later** — e.g., delete audit logs older than 90 days (a simple scheduled job)
- **Don't log the full AI response text** in the audit table — that's already in the `Message` model

---

## 3. What is "Embedding Documentation"?

This was poorly worded in the original plan. It does **NOT** mean documenting every individual embedding vector. Here's what it actually refers to:

### What It Means

**Ingestion metadata tracking** — when you run the ingestion pipeline to load drug data into Qdrant, you record:

| Field | Purpose |
|:---|:---|
| `source` | Which data source (NAFDAC, NEML, etc.) |
| `version` | What version of the source data |
| `chunks_created` | How many chunks were ingested |
| `run_date` | When the ingestion happened |
| `status` | Success/failure |
| `file_hash` | SHA256 of the source file (to detect changes) |

### Why It Matters

- **Know what's in your vector DB** — "Was the latest NAFDAC data ingested?"
- **Avoid duplicate ingestion** — Compare file hash before re-ingesting
- **Debug retrieval issues** — "The NEML data was ingested 6 months ago, it might be outdated"

### Storage Impact

This is **one row per ingestion run** — maybe 5–10 rows total. Negligible storage.

---

## 4. What Does "Offline Resilience" Mean?

In the original plan, "offline resilience" meant: **show a friendly error state in the frontend when the backend is unreachable** — not that the frontend would try to answer questions on its own.

### What You Want (Confirmed)

- ❌ Frontend does NOT answer anything when backend is down
- ✅ Frontend shows a clear error message: *"Unable to reach the server. Please check your connection and try again."*
- ✅ Frontend disables the input field and send button when disconnected
- ✅ Frontend retries automatically when connection is restored

This is **standard error handling**, not an AI feature. The revised plan removes the term "offline resilience" to avoid confusion.

---

## 5. Hybrid Search — What It Is and Why You Want It

### Dense Search (Vector Only)

Embeds the query as a vector and finds chunks with similar vectors. Good for **semantic** meaning:

```
Query: "medications for high blood sugar"
Finds: chunks about "metformin", "insulin", "antidiabetics"
       (even though those exact words weren't in the query)
```

### Sparse Search (Keyword / BM25)

Traditional keyword matching. Good for **exact terms**:

```
Query: "metformin 500mg dosage"
Finds: chunks containing exactly "metformin" and "500mg"
       (won't miss a chunk just because its vector was slightly different)
```

### Hybrid = Both Combined

Qdrant supports running both searches simultaneously and merging the results. This catches:
- Semantic matches that keywords would miss
- Exact keyword matches that vectors might underrank

**For a drug database, hybrid is particularly valuable** because drug names, dosages, and chemical terms are very specific — you don't want vector search alone to swap "metformin" for "glimepiride" because their embeddings are similar (both are antidiabetics).

---

## 6. Nigeria Data Sources — Availability & Access Assessment

| Source | What It Contains | Format | Access | Concern |
|:---|:---|:---|:---|:---|
| **NAFDAC Greenbook** | Registered drugs in Nigeria, manufacturers, approval status | Likely PDF/web scrape | NAFDAC website; may need web scraping | Data may not be in clean structured format |
| **EMDEX** | Comprehensive Nigerian drug reference (dosing, interactions, pricing) | Book / possibly PDF | **Proprietary / Commercial** — published by Lindoz Products | ⚠️ Licensing required; cannot freely ingest |
| **NEML** | Nigeria's Essential Medicines List (similar to WHO EML but Nigeria-specific) | PDF | Federal Ministry of Health website | Free but PDF parsing needed |
| **NHIA STG** | Standard Treatment Guidelines and Referral Protocol | PDF | NHIA / FMOH publications | Free but very large PDFs |
| **NAFDAC Drug Regulations** | Regulatory guidelines, GMP standards, import rules | PDF / web | NAFDAC website | Free; more regulatory than clinical |
| **Clinical Trials Database** | Ongoing/completed clinical trials in Nigeria | Web portal | Pan African Clinical Trials Registry / NCTR | May need API or scraping |
| **NNMDA Traditional Medicine Database** | Registered traditional/herbal medicines | Unknown | National Agency for Traditional Medicine | Availability uncertain; may need formal request |

> [!WARNING]
> **EMDEX is a commercial publication.** It is the most comprehensive Nigerian drug reference but is copyrighted by Lindoz Products Ltd. You cannot legally ingest its content without a license agreement. Consider contacting Lindoz for API/data access, or treat EMDEX as a "nice to have" and focus on the freely available sources first.

### Recommended Priority for Nigeria Sources

| Priority | Source | Reason |
|:---|:---|:---|
| **P0 (MVP)** | NEML | Nigeria's official essential medicines — free, foundational |
| **P0 (MVP)** | NAFDAC Greenbook | Registered drug list — verifies what's legally available in Nigeria |
| **P0 (MVP)** | NHIA STG | Treatment protocols — critical for clinical decision support |
| **P1 (Phase 2)** | WHO Essential Medicines | Global reference, complements NEML |
| **P1 (Phase 2)** | DrugBank Open Data | Rich interaction/mechanism data not in Nigerian sources |
| **P1 (Phase 2)** | OpenFDA Labels | Detailed drug labelling (US-originated drugs sold in Nigeria) |
| **P2 (Phase 3)** | NAFDAC Regulations | Regulatory context, lower clinical value |
| **P2 (Phase 3)** | Clinical Trials DB | Supplementary, research-oriented |
| **P3 (If licensed)** | EMDEX | Best Nigerian reference — needs commercial license |
| **P3 (If available)** | NNMDA Traditional Medicine | Niche, uncertain availability |

### Data Parsing Challenge

Most Nigerian sources are in **PDF format**, not structured data (JSON/XML/Excel). This means:
- You'll need a PDF parsing step (using libraries like `pdfplumber` or `PyMuPDF`)
- PDF quality varies — scanned PDFs may need OCR
- Table extraction from PDFs is error-prone and needs manual verification
- Budget **extra time** for Nigerian source parsing compared to WHO/DrugBank/OpenFDA which have clean structured formats
