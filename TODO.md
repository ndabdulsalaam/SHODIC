# RxChat — Implementation TODO

## 🔑 API Keys & Accounts (Do These First)

- [ ] **DeepSeek API Key** — Go to [platform.deepseek.com](https://platform.deepseek.com) → API Keys → Create → Copy key → Paste in `backend/.env` as `DEEPSEEK_API_KEY`
- [ ] **OpenAI API Key** (for embeddings only) — Go to [platform.openai.com](https://platform.openai.com) → API Keys → Create → Copy key → Paste in `backend/.env` as `OPENAI_API_KEY`
- [ ] **Neon Postgres** — Sign up at [neon.tech](https://neon.tech) → Create Project → Copy connection string → Paste in `backend/.env` as `DATABASE_URL`
- [ ] **Qdrant Cloud** — Sign up at [cloud.qdrant.io](https://cloud.qdrant.io) → Create Cluster (free tier: 1GB) → Copy API key + cluster URL → Paste in `backend/.env`:
  ```
  QDRANT_URL=https://your-cluster-id.us-east4-0.gcp.cloud.qdrant.io
  QDRANT_API_KEY=your-api-key
  ```

## 📧 Brevo Email API (Required for OTP Delivery)

- [ ] **Sign up** at [brevo.com](https://brevo.com) (free — 300 emails/day, no credit card)
- [ ] **Get API key**: Settings → SMTP & API → API Keys → Generate a New API Key → Copy
- [ ] **Add verified sender**: Settings → Senders, Domains & Dedicated IPs → Add Sender → Enter your email (e.g. `ndabdulsalaam@gmail.com`) → Check inbox and click verification link
- [ ] **Paste in `backend/.env`**:
  ```
  BREVO_API_KEY=xkeysib-xxxxxxxxxxxx
  BREVO_SENDER_EMAIL=your_verified_email@gmail.com
  BREVO_SENDER_NAME=RxChat
  ```
- [ ] Without these, OTP codes print to the Django terminal (dev fallback)

## 🔐 Google OAuth (Optional — For "Continue with Google")

- [ ] Go to [Google Cloud Console](https://console.cloud.google.com) → Create Project → APIs & Services → OAuth Consent Screen → External
- [ ] Configure OAuth: Credentials → Create OAuth Client ID → Web App
- [ ] Authorized redirect URI: `http://localhost:8000/api/auth/google/callback/`
- [ ] Copy Client ID and Secret → Paste in `backend/.env`:
  ```
  GOOGLE_CLIENT_ID=...
  GOOGLE_CLIENT_SECRET=...
  ```

---

## 📦 Drug Data Sources — Acquisition Guide

### 🟢 P0 — Nigeria Core Sources (Get These First)

These are the foundational data sources. All are free. Expect PDF format.

#### 1. NEML — Nigeria Essential Medicines List (8th Edition, 2024)

- **What it is:** Nigeria's official list of essential medicines — drugs, formulations, dosages, and therapeutic categories
- **Where to get it:**
  - [ ] Visit [health.gov.ng](https://health.gov.ng) (Federal Ministry of Health and Social Welfare)
  - [ ] Search for "Essential Medicines List" or navigate to the Resources/Publications section
  - [ ] Download "Nigeria Essential Medicines List for Adults (8th Edition, 2024)" — PDF
  - [ ] Also download "Nigeria Essential Medicines List for Children (2nd Edition, 2024)" — PDF
  - [ ] Alternative: Search on [fmohconnect.gov.ng](https://fmohconnect.gov.ng)
- **Format:** PDF (~5–15 MB)
- **License:** Government publication — free for public use
- **Save to:** `backend/data/sources/neml/`

#### 2. NAFDAC Greenbook — Registered Products Database

- **What it is:** Official database of all NAFDAC-registered pharmaceutical products in Nigeria
- **Where to get it:**
  - [ ] Visit [greenbook.nafdac.gov.ng](https://greenbook.nafdac.gov.ng)
  - [ ] ⚠️ **No bulk download available** — this is a searchable web portal
  - [ ] **Option A (recommended):** Write a web scraper to extract product listings by category (drugs, biologics, etc.)
  - [ ] **Option B:** Manually search and export by drug category if scraping isn't feasible
  - [ ] Search by: product name, active ingredient, NAFDAC registration number, manufacturer
- **Format:** Web portal (HTML) — will need scraping to structured data
- **License:** Government data — free for public use
- **Save to:** `backend/data/sources/nafdac/`
- **Note:** The data is dynamic (new products registered regularly). Plan for periodic re-scraping.

#### 3. NHIA STG — Standard Treatment Guidelines & Referral Protocol

- **What it is:** Clinical treatment protocols for conditions covered under Nigeria's health insurance scheme — diagnosis, treatment algorithms, referral criteria
- **Where to get it:**
  - [ ] Visit [nhia.gov.ng](https://nhia.gov.ng) → Resources section
  - [ ] Search for "NHIA Standard Treatment Guidelines And Referral Protocol"
  - [ ] Download the PDF (~124 MB — large document)
  - [ ] Alternative: Contact NHIA directly if the download link isn't accessible
- **Format:** PDF (~124 MB)
- **License:** Government publication — free for public use
- **Save to:** `backend/data/sources/nhia_stg/`

---

### 🔵 P1 — International Sources (Get These After P0)

These provide comprehensive drug data that complements Nigeria-specific sources.

#### 4. WHO Essential Medicines List

- **What it is:** Global reference list of essential medicines (model for NEML)
- **Where to get it:**
  - [ ] Visit [list.essentialmeds.org](https://list.essentialmeds.org)
  - [ ] Download the Excel/CSV export
- **Format:** Excel/CSV (~1–2 MB)
- **License:** Open — free for any use
- **Save to:** `backend/data/sources/who/`

#### 5. DrugBank Open Data

- **What it is:** The most comprehensive free drug database globally — 13,000+ drugs with interactions, mechanisms, targets, pharmacology
- **Where to get it:**
  - [ ] Visit [go.drugbank.com/releases/latest](https://go.drugbank.com/releases/latest)
  - [ ] Create a free account (academic/research)
  - [ ] Download the full XML database (~700 MB uncompressed)
- **Format:** XML (compressed ~80–100 MB download, ~700 MB extracted)
- **License:** ⚠️ **CC BY-NC 4.0 (Non-Commercial Only)** — see license section below
- **Save to:** `backend/data/sources/drugbank/`

#### 6. OpenFDA Drug Labels

- **What it is:** All FDA-approved drug labelling — warnings, dosage, side effects, interactions
- **Where to get it:**
  - [ ] Visit [open.fda.gov/apis/drug/label](https://open.fda.gov/apis/drug/label/)
  - [ ] Use the free API (no key required) to pull label data
  - [ ] Or download bulk data from [open.fda.gov/apis/drug/label/download](https://open.fda.gov/apis/drug/label/download/)
- **Format:** JSON API / bulk JSON download (~2–5 GB for full dataset, but we only ingest relevant fields)
- **License:** Public domain (US government) — fully free for any use
- **Save to:** `backend/data/sources/openfda/`

---

### 🟡 P2 — Premium Source (Requires Licensing)

#### 7. EMDEX — Essential Medicines Index (Nigeria)

- **What it is:** The most comprehensive Nigerian drug reference — used by healthcare professionals nationwide. Contains NAFDAC-approved drug info, clinical guidelines, standard treatment recommendations, drug interactions, and pricing
- **Why it matters:** EMDEX is the gold standard for Nigerian pharmacy practice. Having it in RxChat would make the chatbot significantly more authoritative for Nigerian users.
- **How to get it:**
  - [ ] Visit [emdex.org](https://emdex.org) or [RxNigeria.com](https://www.RxNigeria.com)
  - [ ] **Contact for API/data licensing:** Email **Editor@Emdex.org**
  - [ ] **Ask about:** API access for integration into healthcare AI applications
  - [ ] **Address:** 25, Osolo Way, Off MM Int'l Airport Road, Ajao Estate, Lagos State, Nigeria
  - [ ] EMDEX has a mobile app (Android/iOS) and web platform — they may offer API access
- **Format:** API (if licensed) — structured data
- **License:** ⚠️ **Commercial / Proprietary** — requires a licensing agreement
- **Cost:** Unknown — must negotiate with EMDEX directly
- **Save to:** `backend/data/sources/emdex/` (when licensed)

---

## ⚖️ DrugBank License — What It Means for RxChat

### The License: CC BY-NC 4.0

DrugBank's open data is licensed under **Creative Commons Attribution-NonCommercial 4.0 International**.

**What you CAN do (free):**
- ✅ Use DrugBank data for personal learning and development
- ✅ Use it in a non-commercial research project
- ✅ Use it during development/testing of RxChat
- ✅ Build and demo a prototype that uses DrugBank data

**What you CANNOT do (without a paid license):**
- ❌ Use DrugBank data in a product that generates revenue (subscriptions, ads, etc.)
- ❌ Use it in a product offered to paying users
- ❌ Redistribute DrugBank data as part of a commercial service
- ❌ Use it in a commercial API

### When Does This Become a Problem?

| Stage | Commercial? | DrugBank OK? |
|:---|:---|:---|
| Building & testing locally | No | ✅ Free |
| Deployed for free use (no revenue) | Debatable | ⚠️ Grey area — technically OK if truly free |
| Accepting subscriptions/payments | Yes | ❌ Need commercial license |
| Showing ads | Yes | ❌ Need commercial license |

### What to Do

1. **For now:** Use DrugBank freely during development and MVP testing
2. **Before monetizing:** Either:
   - Purchase a DrugBank commercial license (contact [drugbank.com](https://www.drugbank.com/legal/terms_of_use) — starts at ~$2,500+/year)
   - Or remove DrugBank data and rely on free sources only (OpenFDA + NEML + NAFDAC + NHIA STG + WHO)
3. **Track which chunks came from DrugBank** — your metadata (`source: "drugbank"`) makes it easy to remove later if needed

---

## 💾 Storage Impact Analysis

### Qdrant Cloud (Free Tier: 1 GB RAM)

Qdrant free tier gives you **1 GB of RAM** for vector storage.

| Source | Est. Text | Est. Chunks | Vectors (1536-dim × 4 bytes) | Metadata | Total in Qdrant |
|:---|:---|:---|:---|:---|:---|
| NEML (Adults + Children) | ~200 KB | ~250 | ~1.5 MB | ~75 KB | ~1.6 MB |
| NAFDAC Greenbook | ~5–20 MB | ~3,000–8,000 | ~18–49 MB | ~1–3 MB | ~19–52 MB |
| NHIA STG | ~30–50 MB | ~5,000–10,000 | ~31–61 MB | ~2–4 MB | ~33–65 MB |
| WHO EML | ~500 KB | ~600 | ~3.7 MB | ~180 KB | ~3.9 MB |
| DrugBank (relevant fields) | ~100–200 MB | ~20,000–40,000 | ~123–246 MB | ~8–16 MB | ~131–262 MB |
| OpenFDA (curated subset) | ~50–100 MB | ~10,000–20,000 | ~61–123 MB | ~4–8 MB | ~65–131 MB |
| **Totals** | | **~40,000–80,000** | **~240–485 MB** | **~15–31 MB** | **~255–515 MB** |

> ⚠️ **The full dataset may exceed the Qdrant free tier (1 GB).** Mitigation strategies:
> - **Start with P0 sources only** (~55–120 MB) — fits comfortably in free tier
> - **Curate DrugBank:** Only ingest drugs available in Nigeria (cross-reference with NAFDAC Greenbook) — reduces DrugBank from ~40K to ~5K chunks
> - **Curate OpenFDA:** Only ingest labels for drugs registered in Nigeria
> - **Upgrade Qdrant:** Paid plans start at ~$25/month for 4 GB

### Neon Postgres (Free Tier: 512 MB)

| Data | Est. Size | Notes |
|:---|:---|:---|
| Django models (users, profiles, auth) | ~5 MB | Small unless 10K+ users |
| Conversations + messages | ~50–100 MB | At ~1000 active users over time |
| Ingestion metadata | < 1 MB | ~7–10 rows (one per source) |
| Audit logs (90-day retention) | ~30–50 MB | At 500 queries/day |
| Django-Q2 task queue | ~5 MB | Auto-pruned |
| **Total estimated** | **~100–160 MB** | **20–32% of free tier** ✅ |

> ✅ **Neon free tier is sufficient** for MVP and early production. Upgrade to a paid plan becomes relevant at ~2000+ active users.

---

## 🚀 Deployment Accounts

- [ ] **Vercel** — Sign up at [vercel.com](https://vercel.com) → Connect GitHub → Import `RxChat` repo → Set root to `frontend/`
- [ ] **Render** — Sign up at [render.com](https://render.com) → Create Web Service → Connect GitHub → Set root to `backend/`

## 🌐 GitHub Repo Settings

- [ ] Add repo description: "Your trusted AI pharmacy companion. Get instant, reliable answers about medications, drug interactions, and health guidance — anytime, anywhere."
- [ ] Add topics: `pharmacy`, `chatbot`, `ai`, `react`, `django`, `rag`, `healthcare`, `nigeria`
- [ ] Set GitHub Pages or link to deployed frontend URL
