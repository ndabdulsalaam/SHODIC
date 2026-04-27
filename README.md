# RxChat

RxChat is an AI pharmacy chat application for medication questions, drug
interaction support, OTC guidance, and healthcare decision support, with a
Nigeria-first product direction.

The app currently provides a ChatGPT-style pharmacy assistant with streaming
responses, session-based anonymous conversations, account-based chat history,
role-aware prompting, OTP authentication, and profile settings. The longer-term
plan is to ground answers in curated Nigerian and international drug data using
a retrieval pipeline.

> Medical disclaimer: RxChat provides general health and medication information
> for educational purposes only. It is not a substitute for professional medical
> advice, diagnosis, treatment, or emergency care. Always consult a licensed
> healthcare professional for clinical decisions.

## Current Features

- Streaming AI chat over server-sent events
- Anonymous session chats without registration
- Registered-user chat history
- Conversation list, rename, delete, edit, and resend flows
- Role-aware responses for patients, pharmacists, physicians, nurses, and other
  health professionals
- Email OTP registration
- Trusted-device OTP login
- Password reset via OTP
- Google OAuth setup path
- User profile and email update flow
- Subscription and organization data models for future paid/team features

## Product Direction

RxChat is being built toward a safer pharmacy assistant that can answer from
curated sources such as:

- Nigeria Essential Medicines List
- NAFDAC Greenbook
- NHIA Standard Treatment Guidelines
- WHO Essential Medicines List
- OpenFDA drug labels
- DrugBank or other licensed data where permitted

The current AI layer already has RAG prompt structure, source formatting helpers,
and role-specific safety instructions. Retrieval and ingestion are still roadmap
work.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, Vite, React Router, React Icons |
| Backend | Django 6, Django REST Framework |
| Auth | Django sessions, email OTP, trusted-device cookie, Google OAuth |
| AI | OpenRouter via the OpenAI-compatible SDK |
| Database | SQLite for local dev, PostgreSQL via `DATABASE_URL` for production |
| Email | Brevo HTTP API, Django console fallback for local dev |
| RAG | Optional Qdrant Cloud retrieval with Qdrant Cloud Inference embeddings |
| Deployment target | Vercel frontend, Render backend |

## Repository Structure

```text
rxchat/
  backend/
    accounts/          # auth, OTPs, profiles, subscriptions, organizations
    chat/              # conversations, messages, streaming chat API, AI service
    config/            # Django settings, URLs, auth config
    templates/         # error templates
    manage.py
    requirements.txt
  frontend/
    public/            # static assets
    src/
      components/      # chat, auth, sidebar, settings UI
      pages/           # ChatPage and AuthPage
    package.json
  TODO.md              # implementation roadmap and data-source plan
```

## Backend Setup

Prerequisites:

- Python 3.11+
- PostgreSQL if using `DATABASE_URL`; otherwise SQLite is used locally

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

## Frontend Setup

Prerequisites:

- Node.js 18+

Install and run:

```bash
cd frontend
npm install
npm run dev
```

Local frontend default: `http://localhost:5173`.

For local development, `VITE_API_BASE_URL` can be omitted; the app automatically uses
`http://localhost:8000/api` when opened on `localhost` or `127.0.0.1`. Set
`VITE_API_BASE_URL` to the deployed backend API origin before building the remote frontend.

## Environment Variables

Create `backend/.env` for backend configuration.

Minimum setup for local and remote access:

```env
SECRET_KEY=change-me
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,[::1],rxchat.onrender.com
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,https://rxchat.vercel.app
```

AI:

```env
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=openai/gpt-oss-120b:free
OPENROUTER_TEXT_MAX_TOKENS=2048
OPENROUTER_REASONING_MAX_TOKENS=4096
```

Optional RAG retrieval:

```env
QDRANT_URL=https://your-cluster-id.region.cloud.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key
QDRANT_COLLECTION=rxchat_drugs
```

Database:

```env
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

If `DATABASE_URL` is omitted, Django uses local SQLite.

Email OTP delivery:

```env
BREVO_API_KEY=your_brevo_api_key
BREVO_SENDER_EMAIL=verified-sender@example.com
BREVO_SENDER_NAME=RxChat
```

If Brevo is not configured, OTP emails are sent through Django's console email
backend in local development.

Google OAuth:

```env
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

The backend derives the Google callback URL from the request host. Add the
actual backend callbacks to Google Cloud Console under Authorized redirect URIs,
for example `http://localhost:8000/api/auth/google/callback/` and
`https://rxchat.onrender.com/api/auth/google/callback/`.

Frontend environment variables can be added in `frontend/.env`:

```env
VITE_API_BASE_URL=https://rxchat.onrender.com/api
```

Omit `VITE_API_BASE_URL` locally unless you want to point the local frontend at
a remote backend.

## API Overview

Chat endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/chat/send/` | Send a message and stream the AI response |
| `GET` | `/api/chat/conversations/` | List current user's or session's conversations |
| `GET` | `/api/chat/conversations/<id>/` | Fetch a conversation with messages |
| `DELETE` | `/api/chat/conversations/<id>/delete/` | Delete a conversation |
| `PATCH` | `/api/chat/conversations/<id>/rename/` | Rename a conversation |
| `PUT` | `/api/chat/messages/<id>/` | Edit a user message and regenerate |
| `POST` | `/api/chat/messages/<id>/resend/` | Regenerate from a user message |

Auth endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/auth/register/` | Start email OTP registration |
| `POST` | `/api/auth/verify-otp/` | Verify registration OTP |
| `POST` | `/api/auth/complete-setup/` | Create account after OTP verification |
| `POST` | `/api/auth/login/` | Login or request device OTP |
| `POST` | `/api/auth/verify-device/` | Verify new device OTP |
| `POST` | `/api/auth/resend-otp/` | Resend OTP |
| `POST` | `/api/auth/forgot-password/` | Start password reset |
| `POST` | `/api/auth/verify-reset-otp/` | Verify password reset OTP |
| `POST` | `/api/auth/reset-password/` | Set a new password |
| `GET` | `/api/auth/google/login/` | Start Google OAuth |
| `GET` | `/api/auth/google/callback/` | Google OAuth callback |
| `POST` | `/api/auth/google/complete-setup/` | Complete Google account setup |
| `GET` | `/api/auth/me/` | Get current session user |
| `POST` | `/api/auth/logout/` | Logout |
| `PATCH` | `/api/auth/profile/` | Update profile fields |
| `POST` | `/api/auth/email/add/` | Start verified email change |
| `POST` | `/api/auth/email/verify/` | Verify and set new email |
| `POST` | `/api/auth/email/remove/` | Remove a non-primary email |

## AI Behavior

The backend builds a role-aware prompt and streams responses through OpenRouter.
Qdrant retrieval is optional: when matching knowledge-base chunks exist, the
answer is instructed to stay grounded in those chunks; when no chunks are
available, the answer must say it is relying on general model knowledge and be
extra cautious for dosing, interactions, and high-risk populations.

The prompt emphasizes:

- No fabrication when evidence or retrieval context is missing
- One clarifying question when key clinical details are needed
- Escalation for emergencies and high-risk situations
- Different response depth for patients and healthcare professionals
- Nigeria-aware medication and guideline context

## Roadmap

Near-term engineering work:

- Expand backend tests for auth, chat ownership, edit/resend, and profile roles
- Keep README/code/deployment config aligned as implementation evolves
- Add usage limits based on subscription plan
- Build ingestion for the Qdrant-backed knowledge base

RAG and data work:

- Create ingestion pipeline for Nigerian drug and guideline sources
- Store chunk metadata with source, license, revision date, and removal flags
- Add Qdrant ingestion and source-aware retrieval controls
- Add source-aware answer controls and audit logs
- Keep non-commercial or licensed datasets removable before monetization

Planned product features:

- Medication reminders
- Symptom triage
- Prescription image scanning
- Live pharmacist escalation
- Multi-language support
- Team and enterprise workspaces

## Deployment Notes

Frontend deployment target:

- Vercel
- Root directory: `frontend/`
- Build command: `npm run build`

Backend deployment target:

- Render or another Django-compatible host
- Root directory: `backend/`
- Start command: typically `gunicorn config.wsgi:application`
- Configure `SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS`,
  `ALLOWED_ORIGINS`, OpenRouter, optional Qdrant, and email keys in the host
  environment

Manual provider connectivity checks can be run from `backend/` with:

```bash
python check_apis.py
```

## License

MIT
