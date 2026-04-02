# RxChat — Manual Setup TODO

## 🔑 API Keys & Accounts (Do These First)
- [ ] **Google Gemini API Key** — Go to [aistudio.google.com](https://aistudio.google.com) → "Get API Key" → Create → Copy key → Paste in `backend/.env` as `GEMINI_API_KEY`
- [ ] **PostgreSQL Database** — Set up a PostgreSQL database (local or Render managed) → Copy URL → Paste in `backend/.env` as `DATABASE_URL`

## 📧 Email (Gmail App Password — Required for OTP)
- [ ] **Enable 2-Step Verification** on your Google Account (required for app passwords)
- [ ] Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) → App: "RxChat" → Generate → Copy the 16-char password
- [ ] Paste in `backend/.env`:
  ```
  EMAIL_HOST_USER=your_gmail@gmail.com
  EMAIL_HOST_PASSWORD=xxxx xxxx xxxx xxxx
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

## 🚀 Deployment Accounts
- [ ] **Vercel** — Sign up at [vercel.com](https://vercel.com) → Connect GitHub → Import `RxChat` repo → Set root to `frontend/`
- [ ] **Render** — Sign up at [render.com](https://render.com) → Create Web Service → Connect GitHub → Set root to `backend/`

## 📦 Drug Data (For RAG — When Backend is Ready)
- [ ] Download [WHO Essential Medicines List](https://essentialmeds.org) (Excel)
- [ ] Download [DrugBank Open Data](https://go.drugbank.com/releases/latest) (XML — requires free account)
- [ ] Download [OpenFDA drug labels](https://open.fda.gov/apis/drug/label/download/) (JSON)
- [ ] Ingest downloaded data into ChromaDB (script will be provided)

## 🌐 GitHub Repo Settings
- [ ] Add repo description: "Your trusted AI pharmacy companion. Get instant, reliable answers about medications, drug interactions, and health guidance — anytime, anywhere."
- [ ] Add topics: `pharmacy`, `chatbot`, `ai`, `react`, `django`, `langchain`, `rag`, `healthcare`
- [ ] Set GitHub Pages or link to deployed frontend URL
