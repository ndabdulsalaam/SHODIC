# 🏥 RxChat Chatbot — RAG & Fine-Tuning Strategy Guide

> A no-code planning document to help you understand, compare, and decide between RAG and Fine-Tuning for RxChat, with platform recommendations, data sources, costs, and learning resources.

---

## 📍 Where You Are Now

Your current stack:

| Component | Status |
|:---|:---|
| **LLM** | DeepSeek (via `openai` / DeepSeek API) | ✅ Target Stack |
| **Framework** | LangChain + LangGraph | ✅ Installed |
| **Vector DB** | ChromaDB (`langchain-chroma`) | ✅ Installed, not wired |
| **Backend** | Django + DRF | ✅ Working |
| **Chat History** | Conversation/Message models | ✅ Working |
| **Drug Data** | WHO, DrugBank, OpenFDA | 📋 Listed in TODO, not downloaded |

Your `ai_service.py` currently has placeholders for Gemini but is structured for DeepSeek's prefix caching.

---

## 🧠 The Two Approaches: RAG vs Fine-Tuning

### What is RAG (Retrieval-Augmented Generation)?

```
User Question → Embed Query → Search Vector DB → Retrieve Relevant Chunks → 
Inject into LLM Prompt as Context → LLM Generates Answer Grounded in Data
```

**How it works for RxChat:**
1. **Ingest Phase (one-time):** Download drug data (WHO, DrugBank, OpenFDA) → Parse into text chunks → Generate embeddings → Store in ChromaDB
2. **Query Phase (every chat):** User asks "What are side effects of metformin?" → Query is embedded → ChromaDB finds the top 3-5 most relevant drug information chunks → Those chunks are injected into the DeepSeek prompt → DeepSeek generates a response *grounded in real drug data*

**Your existing stack supports this.** LangChain + ChromaDB + DeepSeek is a textbook RAG pipeline.

---

### What is Fine-Tuning?

```
Curated Dataset (Q&A pairs) → Train/Adjust LLM Weights → 
Deploy Custom Model → LLM Responds from Learned Knowledge
```

**How it works for RxChat:**
1. **Data Preparation:** Create thousands of pharmacy Q&A pairs from drug databases, pharmacist conversations, clinical guidelines
2. **Training:** Upload dataset to a fine-tuning platform → Model trains on your specific pharmacy domain
3. **Deployment:** Use the fine-tuned model endpoint instead of (or alongside) the base Gemini model

---

## ⚖️ RAG vs Fine-Tuning — Head-to-Head Comparison

| Criteria | RAG | Fine-Tuning |
|:---|:---|:---|
| **Setup Complexity** | ⭐ Medium — you already have the libraries installed | ⭐⭐ High — need data curation, training pipeline, hosting |
| **Cost** | 💰 Low — only pay for Gemini API calls + ChromaDB is free/local | 💰💰💰 High — training costs ($5-$500+ per run) + hosting a custom model |
| **Data Freshness** | ✅ Easy — re-ingest new data anytime, no retraining | ❌ Hard — must retrain model to incorporate new data |
| **Accuracy on Drug Data** | ✅ High — responses cite actual retrieved documents | ⚠️ Variable — depends on training data quality and quantity |
| **Hallucination Control** | ✅ Strong — answers are grounded in retrieved chunks | ⚠️ Weaker — model may still hallucinate confidently |
| **Latency** | ⚠️ Slightly higher — embedding + retrieval adds ~200-500ms | ✅ Fast — single model call |
| **Scalability** | ✅ Easy — add more data to ChromaDB anytime | ⚠️ Must retrain or manage multiple models |
| **Time to First Value** | ✅ Days — can have a working RAT pipeline within a week | ❌ Weeks to months — data curation is the bottleneck |
| **Best For** | Factual lookups, drug info, interaction checks | Tone/personality, response style, specialized reasoning |

---

## 🎯 Recommendation for RxChat

### Start with RAG (Phase 1) — Then Consider Fine-Tuning (Phase 2)

> [!IMPORTANT]
> **RAG is the right starting point for RxChat.** Your use case (drug info, interactions, side effects) is fundamentally a *knowledge retrieval* problem, not a *style/behavior* problem. RAG excels here.

**Why RAG first:**
- Your drug data changes (FDA updates, new drug approvals) — RAG handles this without retraining
- Pharmaceutical accuracy requires grounding in verified sources — RAG provides citations
- You already have the libraries installed (LangChain, ChromaDB, langchain-google-genai)
- ChromaDB is free and runs locally — zero additional cost
- Patient safety demands traceable answers — RAG retrieval makes this auditable

**When to add Fine-Tuning (later):**
- If you want RxChat to develop a unique "pharmacist personality" or conversational style
- If you find that Gemini's base pharmacy knowledge is weak in specific areas despite good RAG retrieval
- If you want faster responses by reducing dependence on retrieval for common queries
- If you accumulate enough real user conversations (thousands) to create a training set

---

## 📐 RAG Architecture — Detailed Template

### Step 1: Data Ingestion Pipeline

```
Drug Data Sources (WHO, DrugBank, OpenFDA)
        │
        ▼
   Data Parsers (Excel/XML/JSON → Plain Text)
        │
        ▼
   Text Chunking (LangChain RecursiveCharacterTextSplitter)
        │  - chunk_size: 1000 chars
        │  - chunk_overlap: 200 chars
        │  - metadata: {source, drug_name, category}
        ▼
   Embedding Generation (Gemini text-embedding-004)
        │
        ▼
   ChromaDB (local persistent storage)
        │  - Collection: "drug_knowledge"
        │  - ~50,000-200,000 chunks expected
        ▼
   Ready for retrieval
```

### Step 2: Query Pipeline (Enhanced ai_service.py)

```
User Message: "Can I take ibuprofen with blood thinners?"
        │
        ▼
   Embed Query (Gemini text-embedding-004)
        │
        ▼
   ChromaDB Similarity Search
        │  - top_k: 5 most relevant chunks
        │  - distance_threshold: filter irrelevant matches
        ▼
   Retrieved Context:
        │  [Chunk 1: "Ibuprofen drug interactions from DrugBank..."]
        │  [Chunk 2: "NSAID + anticoagulant warnings from FDA..."]
        │  [Chunk 3: "WHO guidelines on NSAID safety..."]
        ▼
   Augmented Prompt to DeepSeek:
        │  System: "You are RxChat..."
        │  Context: {retrieved chunks}
        │  User: "Can I take ibuprofen with blood thinners?"
        ▼
   DeepSeek Response (streamed & grounded in data)
```

### Step 3: Key Design Decisions for RAG

| Decision | Recommended Choice | Why |
|:---|:---|:---|
| **Embedding Model** | `text-embedding-004` (Gemini) or DeepSeek | Cost-effective and high quality |
| **Vector DB** | ChromaDB (already installed) | Free, local, good for <1M documents |
| **Chunk Size** | 1000 characters, 200 overlap | Balances context richness with retrieval precision |
| **Top-K Retrieval** | 5 chunks | Enough context without overwhelming the prompt |
| **Re-ranking** | Optional (add later) | Cross-encoder re-ranking improves quality but adds latency |
| **Metadata Filtering** | By drug category, source | Allows scoped searches (e.g., only FDA data for US-specific queries) |

---

## 📐 Fine-Tuning Architecture — Detailed Template

### If/When You Pursue Fine-Tuning

### Step 1: Training Data Preparation

```
Source Data
   ├── Drug databases (parsed Q&A pairs)
   ├── Pharmacist-patient conversation logs
   ├── Clinical case studies
   └── Drug label summaries
        │
        ▼
   Format as JSONL:
   {"messages": [
     {"role": "system", "content": "You are RxChat..."},
     {"role": "user", "content": "What is metformin used for?"},
     {"role": "assistant", "content": "Metformin is a first-line medication for..."}
   ]}
        │
        ▼
   Train/Validation Split (80/20)
        │  - Minimum: 100 examples (bare minimum)
        │  - Good: 1,000-5,000 examples
        │  - Excellent: 10,000+ examples
        ▼
   Upload to Fine-Tuning Platform
```

### Step 2: Platform Options for Fine-Tuning

| Platform | Model | Cost per Training | Hosting Cost | Pros | Cons |
|:---|:---|:---|:---|:---|:---|
| **Google Gemini** | gemini-1.5-flash | ~$0.40/1M tokens (tuning) | Pay-per-use API | Same ecosystem you use, via AI Studio | Limited fine-tuning customization |
| **OpenAI** | gpt-4o-mini | ~$3/1M training tokens | Pay-per-use API | Best fine-tuning tooling & docs | Must switch from Gemini, costs add up |
| **Together AI** | Llama 3.1/3.2 | ~$2-5/hour of training | $0.20/1M tokens inference | Open-source models, cheaper | Need to learn a new platform |
| **Hugging Face** | Any open model | Free (your compute) | Free tier on Spaces | Full control, no vendor lock-in | You manage everything yourself |
| **Unsloth** | Llama/Mistral | Free (your GPU) | Self-host or deploy to HF | 2x faster fine-tuning, low VRAM | Need a GPU (Colab free tier works) |

> [!TIP]
> **Best value for RxChat:** If you pursue fine-tuning, start with **Google's Gemini fine-tuning** (stays in your ecosystem) or **Unsloth + Llama 3.2** on Google Colab (free).

### Step 3: Fine-Tuning Workflow

```
1. Prepare JSONL dataset (1000+ Q&A pairs)
2. Upload to Google AI Studio or Colab
3. Configure hyperparameters:
   - Epochs: 3-5
   - Learning rate: 1e-5 to 5e-5
   - Batch size: 4-8
4. Train (takes 30min to several hours)
5. Evaluate on held-out test set
6. Deploy model endpoint
7. Update ai_service.py to call fine-tuned model
```

---

## 🔀 Hybrid Approach — RAG + Fine-Tuning Together

The most powerful approach combines both:

```
User Question
     │
     ├──► RAG retrieves factual drug data from ChromaDB
     │
     ├──► Fine-tuned model understands pharmacy context deeply
     │
     ▼
Fine-Tuned Model + Retrieved Context = Best Answers
```

**When this makes sense:** Once you have RAG working well (Phase 1), and you've accumulated enough conversation data from real users to create a fine-tuning dataset (Phase 2).

---

## 📊 Data Sources — Detailed Breakdown

### Primary Sources (Already in your TODO.md)

| Source | Format | Size | Content | License | Access |
|:---|:---|:---|:---|:---|:---|
| [WHO Essential Medicines](https://list.essentialmeds.org) | Excel/PDF | ~500 drugs | Core drug list, indications, dosage | Open | Free download |
| [DrugBank Open Data](https://go.drugbank.com/releases/latest) | XML | ~13,000+ drugs | Interactions, mechanisms, targets | CC BY-NC 4.0 | Free account required |
| [OpenFDA Drug Labels](https://open.fda.gov/apis/drug/label/) | JSON API | ~100K+ labels | FDA-approved labeling, warnings, dosage | Public Domain | Free API (no key needed) |

### Additional Recommended Sources

| Source | Format | Content | Cost |
|:---|:---|:---|:---|
| [RxNorm (NIH)](https://www.nlm.nih.gov/research/umls/rxnorm/index.html) | API/Download | Drug name normalization, clinical drug forms | Free |
| [MedlinePlus](https://medlineplus.gov/xml.html) | XML | Patient-friendly drug info, side effects | Free |
| [DailyMed](https://dailymed.nlm.nih.gov/dailymed/spl-resources-all-drug-labels.cfm) | XML/ZIP | Full FDA label text, structured product labels | Free |
| [PubChem](https://pubchem.ncbi.nlm.nih.gov/) | JSON API | Chemical data, compound info | Free |
| [SIDER (Side Effects Resource)](http://sideeffects.embl.de/) | TSV | Drug-side effect pairs from labels | Free for research |

> [!WARNING]
> **DrugBank Commercial Use:** DrugBank Open Data is licensed CC BY-NC 4.0 (non-commercial only). If RxChat becomes a commercial product, you'll need a [DrugBank commercial license](https://www.drugbank.com/legal/terms_of_use) ($2,500+/year). OpenFDA and WHO data are fully open.

### Data Source Pros & Cons

| Source | Pros | Cons |
|:---|:---|:---|
| **WHO Essential Medicines** | Globally recognized, trustworthy, focused list | Limited to ~500 "essential" drugs, not comprehensive |
| **DrugBank** | Most comprehensive free drug DB, rich interaction data | Non-commercial license, XML parsing is complex |
| **OpenFDA** | Public domain, massive dataset, real FDA labels | US-focused, very verbose labels need parsing |
| **RxNorm** | Best for drug name normalization | Doesn't contain clinical info, just naming |
| **MedlinePlus** | Patient-friendly language, great for chatbot tone | Less technical depth than DrugBank |
| **DailyMed** | Full official FDA labeling | Very large downloads, complex XML structure |

---

## 🏗️ Platform Recommendations

### For RAG (What to Use)

| Component | Recommendation | Why |
|:---|:---|:---|
| **LLM** | Google Gemini 2.0 Flash (keep current) | Free tier: 15 RPM, great for dev; $0.10/1M tokens in production |
| **Embeddings** | Google `text-embedding-004` | Free tier available, integrates with `langchain-google-genai` |
| **Vector DB** | ChromaDB (keep current) | Already installed, free, runs locally, good for your data volume |
| **Framework** | LangChain (keep current) | Already installed, great RAG tooling |
| **Deployment** | Render (backend, keep current) | ChromaDB persistence works on Render's disk |

> [!NOTE]
> **If you outgrow ChromaDB** (>1M documents or need cloud-hosted): Consider [Pinecone](https://www.pinecone.io/) (free tier: 100K vectors) or [Weaviate Cloud](https://weaviate.io/) (free sandbox). But ChromaDB is plenty for RxChat's scale.

### For Fine-Tuning (If/When Needed)

| Use Case | Platform | Cost |
|:---|:---|:---|
| **Lowest effort** | Google AI Studio (Gemini tuning) | ~$0.40/1M training tokens |
| **Cheapest** | Google Colab + Unsloth + Llama 3.2 | Free (Colab free tier GPU) |
| **Best tooling** | OpenAI fine-tuning API | ~$3/1M training tokens |
| **Most flexible** | Together AI | ~$2-5/hr training |

---

## 💰 Cost Breakdown

### RAG Costs (Phase 1)

| Item | Cost | Notes |
|:---|:---|:---|
| ChromaDB | **$0** | Local, open-source |
| Gemini API (dev) | **$0** | Free tier: 15 RPM for Flash |
| Gemini API (prod) | **~$0.10/1M input tokens** | Per 1M tokens (very cheap) |
| Gemini Embeddings | **$0** | Free tier covers most use cases |
| Drug data download | **$0** | All recommended sources are free |
| Render hosting | **$7/month** | Starter plan for backend |
| **Total Phase 1** | **$0 – $7/month** | Mostly free for development |

### Fine-Tuning Costs (Phase 2)

| Item | Cost | Notes |
|:---|:---|:---|
| Gemini fine-tuning | **$4-40 per training run** | Depends on dataset size (10K-100K examples) |
| OpenAI fine-tuning | **$15-150 per run** | gpt-4o-mini, depends on dataset size |
| Colab + Unsloth | **$0** | Free tier GPU (T4), limited hours |
| Self-host fine-tuned model | **$20-80/month** | GPU cloud instance (RunPod, Lambda) |
| **Total Phase 2** | **$0 – $80/month** | Wide range depending on approach |

---

## 📚 Learning Resources

### RAG — Understanding & Implementation

| Resource | Type | Link | Why Read This |
|:---|:---|:---|:---|
| **LangChain RAG Tutorial** | Docs | [python.langchain.com/docs/tutorials/rag](https://python.langchain.com/docs/tutorials/rag/) | Official tutorial using your exact stack |
| **LangChain + ChromaDB Guide** | Docs | [python.langchain.com/docs/integrations/vectorstores/chroma](https://python.langchain.com/docs/integrations/vectorstores/chroma/) | ChromaDB-specific integration guide |
| **Google Gemini Embeddings** | Docs | [ai.google.dev/gemini-api/docs/embeddings](https://ai.google.dev/gemini-api/docs/embeddings) | How to generate embeddings with Gemini |
| **RAG from Scratch (DeepLearning.AI)** | Free Course | [deeplearning.ai/short-courses/building-evaluating-advanced-rag](https://www.deeplearning.ai/short-courses/building-evaluating-advanced-rag/) | Best free course on advanced RAG techniques |
| **ChromaDB Getting Started** | Docs | [docs.trychroma.com/docs/overview/getting-started](https://docs.trychroma.com/docs/overview/getting-started) | ChromaDB fundamentals |
| **Pinecone RAG Guide** | Blog | [pinecone.io/learn/retrieval-augmented-generation](https://www.pinecone.io/learn/retrieval-augmented-generation/) | Excellent conceptual explanation (vendor-agnostic) |

### Fine-Tuning — Understanding & Implementation

| Resource | Type | Link | Why Read This |
|:---|:---|:---|:---|
| **Google Gemini Fine-Tuning** | Docs | [ai.google.dev/gemini-api/docs/model-tuning](https://ai.google.dev/gemini-api/docs/model-tuning) | Fine-tuning in your current ecosystem |
| **Unsloth Fine-Tuning Guide** | GitHub | [github.com/unslothai/unsloth](https://github.com/unslothai/unsloth) | Free, fast fine-tuning on Colab |
| **Fine-Tuning LLMs (DeepLearning.AI)** | Free Course | [deeplearning.ai/short-courses/finetuning-large-language-models](https://www.deeplearning.ai/short-courses/finetuning-large-language-models/) | Best free course on fine-tuning concepts |
| **OpenAI Fine-Tuning Guide** | Docs | [platform.openai.com/docs/guides/fine-tuning](https://platform.openai.com/docs/guides/fine-tuning) | Industry-standard documentation |
| **Hugging Face Fine-Tuning** | Docs | [huggingface.co/docs/transformers/training](https://huggingface.co/docs/transformers/training) | Open-source fine-tuning fundamentals |

### RAG vs Fine-Tuning — When to Use Which

| Resource | Type | Link |
|:---|:---|:---|
| **RAG vs Fine-Tuning (Hopsworks)** | Blog | [hopsworks.ai/dictionary/rag-vs-fine-tuning](https://www.hopsworks.ai/dictionary/rag-vs-fine-tuning) |
| **When to RAG vs Fine-Tune (Anyscale)** | Blog | [anyscale.com/blog/fine-tuning-vs-rag](https://www.anyscale.com/blog/fine-tuning-vs-rag) |
| **LLM Optimization Guide (Google)** | Docs | [cloud.google.com/vertex-ai/docs/generative-ai/learn/models](https://cloud.google.com/vertex-ai/docs/generative-ai/learn/models) |

### Healthcare AI Specific

| Resource | Type | Link |
|:---|:---|:---|
| **Building Medical AI Apps** | Blog | [huggingface.co/blog/medical-llm-leaderboard](https://huggingface.co/blog/medical-llm-leaderboard) |
| **OpenFDA API Docs** | API Docs | [open.fda.gov/apis/](https://open.fda.gov/apis/) |
| **DrugBank Documentation** | Docs | [docs.drugbank.com/](https://docs.drugbank.com/) |

---

## 🗺️ Full Implementation Roadmap

### Phase 1: RAG Pipeline (Weeks 1-3)

```
Week 1: Data Collection & Parsing
├── Download WHO Essential Medicines List
├── Create DrugBank account, download open data
├── Set up OpenFDA API data pulls
└── Write parsers for each format (Excel, XML, JSON)

Week 2: Embedding & Storage
├── Design text chunking strategy
├── Generate embeddings (Gemini text-embedding-004)
├── Store in ChromaDB with metadata
├── Build ingestion script (rerunnable for updates)
└── Test retrieval quality with sample queries

Week 3: Integration & Testing
├── Update ai_service.py with RAG pipeline
├── Add retrieval step before Gemini call
├── Test with 50+ pharmacy questions
├── Tune chunk_size, top_k, prompts
└── Deploy to Render
```

### Phase 2: RAG Optimization (Weeks 4-5)

```
Week 4: Quality Improvements
├── Add metadata filtering (drug category, source)
├── Implement query routing (FAQ vs. deep lookup)
├── Add conversation-aware retrieval
└── Handle multi-drug interaction queries

Week 5: Production Hardening
├── Add embedding caching for common queries
├── Implement fallback if ChromaDB is empty
├── Add source citations in responses
├── Monitor retrieval quality with logging
└── Load test with concurrent users
```

### Phase 3: Fine-Tuning (Weeks 6-10, Optional)

```
Week 6-7: Data Curation
├── Extract Q&A pairs from drug databases
├── Generate synthetic Q&A using Gemini
├── Collect real user conversations (after launch)
├── Format into JSONL training dataset
└── Create train/validation split

Week 8-9: Training & Evaluation
├── Choose platform (Gemini tuning or Unsloth)
├── Run initial fine-tuning experiment
├── Evaluate on pharmacy benchmarks
├── Compare fine-tuned vs base model quality
└── Iterate on dataset and hyperparameters

Week 10: Integration
├── Deploy fine-tuned model endpoint
├── Update ai_service.py for hybrid (RAG + fine-tuned)
├── A/B test fine-tuned vs RAG-only
└── Monitor and collect feedback
```

---

## ⚠️ Risks & Mitigations

| Risk | Impact | Mitigation |
|:---|:---|:---|
| **Drug data parsing complexity** | High — XML/JSON schemas are complex | Start with WHO (simplest), add others incrementally |
| **Hallucination despite RAG** | Critical — wrong drug info is dangerous | Always include "consult your pharmacist" disclaimer; add confidence scoring |
| **ChromaDB data loss** | Medium — local DB can be lost | Persist to disk, back up, keep ingestion script rerunnable |
| **Gemini API costs scaling** | Medium — high traffic = high costs | Cache common queries, use embedding caching, set rate limits |
| **Fine-tuning overfitting** | Medium — small dataset = bad generalization | Start with 1000+ diverse examples, use validation set |
| **Regulatory compliance** | High — medical info has legal implications | Add clear disclaimers, don't claim to replace medical advice |

---

## ✅ Decision Checklist

Before you start coding, answer these:

- [ ] **RAG or Fine-Tuning first?** → RAG (recommended)
- [ ] **Which data source first?** → WHO Essential Medicines (simplest, most global)
- [ ] **Embedding model?** → Gemini `text-embedding-004` (free, same ecosystem)
- [ ] **Vector DB?** → ChromaDB (already installed)
- [ ] **Chunk size?** → Start with 1000 chars, 200 overlap
- [ ] **Top-K retrieval?** → 5 chunks
- [ ] **Fine-tuning platform (for later)?** → Google AI Studio or Unsloth + Colab
- [ ] **Budget for Phase 1?** → $0-$7/month (all free tier)
