# RxChat

RxChat is a free, anonymous-session AI pharmacy chat app for medication questions, drug interaction support, OTC guidance, and healthcare decision support with a Nigeria-first product direction.

The app uses browser sessions for chat history. There is no public registration, login, OTP, password reset, profile, plan, subscription, organization, or chat attachment flow. Django admin remains available for staff/superusers to manage RxChat data and run ingestion workflows.

> Medical disclaimer: RxChat provides general health and medication information only. It is not a substitute for professional medical advice, diagnosis, treatment, or emergency care. Always consult a licensed healthcare professional for clinical decisions.

## Features

- Streaming AI chat over server-sent events
- Anonymous session-based conversation history
- Conversation list, rename, delete, edit, and resend flows
- Text-only chat input
- RAG-ready prompt pipeline with optional Qdrant retrieval
- OpenRouter LLM streaming via the OpenAI-compatible SDK
- Django admin ingestion tools for NAFDAC, OpenFDA, NEML, NHIA STG, WHO EML, NNMDA, and EMDEX source data

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, Vite, React Icons |
| Backend | Django 6, Django REST Framework |
| Sessions | Django sessions for anonymous chat ownership |
| AI | OpenRouter via the OpenAI-compatible SDK |
| RAG | Optional Qdrant Cloud retrieval with Qdrant Cloud Inference embeddings |
| Data ingestion | Django admin, management commands, django-q2 when installed |
| Database | SQLite by default, PostgreSQL via `DATABASE_URL` when configured |

## Repository Structure

```text
backend/
  config/              # single Django settings module, URLs, ASGI/WSGI
  rxchat/              # chat API, AI service, RAG ingestion, admin tools
  templates/           # generic error and admin ingestion templates
  manage.py
  requirements.txt
rxchat_frontend/
  public/              # RxChat static assets
  src/
    components/        # chat UI
    hooks/             # chat controller, audio/speech hooks
    pages/             # ChatPage
    utils/             # API and SSE helpers
```

## Backend Setup

Prerequisites:

- Python 3.11+
- SQLite for quick local use, or PostgreSQL via `DATABASE_URL`

Install and run:

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Local backend default: `http://localhost:8000`.

Create an admin user when you need the ingestion/admin surface:

```bash
python manage.py createsuperuser
```

## Frontend Setup

Prerequisites:

- Node.js 18+

Run the RxChat app:

```bash
cd rxchat_frontend
npm install
npm run dev
```

Local frontend default: `http://localhost:5173`.

On localhost, `VITE_API_BASE_URL` can be omitted; the app automatically uses `http://localhost:8000`. If the frontend is served from another host, set `VITE_API_BASE_URL` to the backend API origin.

## Environment Variables

Copy `backend/.env.sample` to `backend/.env` as needed. The project uses one normal Django settings module: `config.settings`.

Minimum useful backend variables:

```env
SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,[::1]
ALLOWED_ORIGINS=http://localhost:5173
DATABASE_URL=
```

AI:

```env
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_BACKUP_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_HTTP_REFERER=http://localhost:5173
OPENROUTER_MODEL=openai/gpt-oss-120b:free
OPENROUTER_TEXT_MAX_TOKENS=2048
OPENROUTER_REASONING_MAX_TOKENS=4096
```

Optional RAG retrieval:

```env
QDRANT_URL=https://your-cluster-id.region.cloud.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key
QDRANT_COLLECTION=rxchat
```

Optional OpenFDA pulls:

```env
OPENFDA_API_KEY=your_openfda_api_key
```

Frontend `.env` example:

```env
VITE_API_BASE_URL=https://your-backend.example.com
```

## API Overview

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/rxchat/send/` | Send a text message and stream the AI response |
| `GET` | `/rxchat/conversations/` | List conversations for the current browser session |
| `GET` | `/rxchat/conversations/<id>/` | Fetch a session-owned conversation with messages |
| `DELETE` | `/rxchat/conversations/<id>/delete/` | Delete a session-owned conversation |
| `PATCH` | `/rxchat/conversations/<id>/rename/` | Rename a session-owned conversation |
| `PUT` | `/rxchat/messages/<id>/` | Edit a user message and regenerate |
| `POST` | `/rxchat/messages/<id>/resend/` | Regenerate from a user message |
| `GET` | `/health/` | Health check |

`POST /rxchat/send/` accepts text only:

```json
{
  "message": "What are common side effects of metformin?",
  "conversation_id": "optional-existing-conversation-id"
}
```

## AI Behavior

The backend builds a safety-oriented RxChat prompt and streams responses through OpenRouter. Qdrant retrieval is optional: when matching knowledge-base chunks exist, they are provided as model-only background; when no chunks are available, the model is instructed to answer cautiously from general drug knowledge.

The prompt emphasizes:

- No fabrication when evidence or retrieval context is missing
- One clarifying question when key clinical details are needed
- Escalation for emergencies and high-risk situations
- Nigeria-aware medication and guideline context

Role prompt variants remain in the AI service for later use, but the public chat currently defaults to the patient/public role because there is no profile or role-selection flow.

## Data Ingestion

Django admin is staff-only and still uses Django's built-in admin authentication. Admin users can upload manual source files and queue ingestion tasks from `/admin/rxchat/ingestion/`. Management commands are also available for source scraping, OpenFDA pulls, ingestion, and schedule setup.

## Verification

Backend:

```bash
cd backend
python manage.py check
python manage.py test
```

Frontend:

```bash
cd rxchat_frontend
npm run lint
npm run build
```

## License

MIT
