# 🏥 RxChat

**Your trusted AI pharmacy companion.**

Get instant, reliable answers about medications, drug interactions, and health guidance — anytime, anywhere. Built for everyone, from patients to caregivers, with expert pharmacist support when you need it most.

---

## ✨ Features

- 💊 **Medication Q&A** — Ask about dosages, side effects, precautions, and usage instructions
- ⚠️ **Drug Interaction Checker** — Get alerts about potential drug-drug interactions
- 🏪 **OTC Recommendations** — Find over-the-counter alternatives for common symptoms
- 💬 **Smart Conversations** — AI-powered responses grounded in verified pharmaceutical data
- 🔒 **Session-based Chat** — Start chatting instantly, register only to save your history
- 🌍 **Global Coverage** — Powered by WHO, DrugBank, and international drug databases

## 🎯 Coming Soon

- ⏰ Medication reminders
- 🩺 Symptom triage
- 📷 Prescription image scanning
- 👨‍⚕️ Live pharmacist escalation
- 🌐 Multi-language support

---

## 🛠 Tech Stack

| Layer | Technology |
|:---|:---|
| **Frontend** | React |
| **Backend** | Django + Django REST Framework |
| **AI/LLM** | Google Gemini via LangChain |
| **RAG** | ChromaDB (vector database) |
| **Database** | PostgreSQL |
| **Deployment** | Vercel (frontend) · Render (backend) |

---

## 🏗 Architecture

```
React Frontend (Vercel)
        │
        │ REST API
        ▼
Django Backend (Render)
  ├── DRF API Router
  ├── RAG Pipeline (LangChain + ChromaDB)
  ├── Google Gemini API (inference)
  └── PostgreSQL (users & chat history)
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Environment Variables

Create a `.env` file in the backend directory:

```env
GEMINI_API_KEY=your_google_ai_api_key
DATABASE_URL=your_postgresql_url
SECRET_KEY=your_django_secret_key
```

---

## 📌 Disclaimer

> RxChat provides general pharmaceutical information for educational purposes only. It is **not a substitute for professional medical advice, diagnosis, or treatment**. Always consult a qualified healthcare provider for medical guidance.

---

## 📄 License

MIT

---

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request.
