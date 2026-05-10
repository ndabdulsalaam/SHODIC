# Fildah

Fildah is the parent company and brand platform for focused health technology
products. It owns the company website, product directory, documentation,
support intake, account hub, and shared backend API.

RxChat is the first product under Fildah: an AI pharmacy chat application for
medication questions, drug interaction support, OTC guidance, and healthcare
decision support, with a Nigeria-first product direction.

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

- Fildah parent brand website APIs backed by Django admin-managed content
- Product catalog with RxChat as the first live product
- Documentation, blog/update, page, and contact/support model(s)
- Shared account hub API for product access, organizations, and subscription summary
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
| Database | PostgreSQL per environment; SQLite fallback for quick dev only |
| Email | Brevo HTTP API, Django console fallback for local dev |
| RAG | Optional Qdrant Cloud retrieval with Qdrant Cloud Inference embeddings |
| Deployment target | Vercel frontend, Render backend |

## Repository Structure

```text
fildah/
  backend/
    fildah/           # parent brand CMS, products, docs, blog, support, account hub API
    accounts/          # auth, OTPs, profiles, subscriptions, organizations
    rxchat/            # conversations, messages, streaming RxChat API, AI service
    config/            # Django settings, URLs, auth config
    templates/         # error templates
    manage.py
    requirements.txt
  fildah_frontend/
    public/            # Fildah parent-site static assets
    src/
      components/      # parent-site layout and reusable UI
      pages/           # home, products, docs, blog, support, account hub
    package.json
  rxchat_frontend/
    public/            # RxChat frontend static assets
    src/
      config/          # RxChat product config for API namespace/domain
      components/      # chat, auth, sidebar, settings UI
      pages/           # ChatPage and AuthPage
    package.json
  plans/               # implementation roadmaps and data-source notes
```

## Backend Setup

Prerequisites:

- Python 3.11+
- PostgreSQL for serious dev/staging/production schema work; SQLite fallback is
  available only when `DATABASE_URL` is omitted in `dev`

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

Run the Fildah parent website:

```bash
cd fildah_frontend
npm install
npm run dev
```

Local Fildah frontend default: `http://localhost:5174`.

Run the RxChat product app:

```bash
cd rxchat_frontend
npm install
npm run dev
```

Local frontend default: `http://localhost:5173`.

The `fildah_frontend/` directory is the parent brand website. The
`rxchat_frontend/` directory is the RxChat product frontend. Future Fildah
products should use their own frontend app/deployment and call the shared API at
`https://api.fildah.com`.

For local development, `VITE_API_BASE_URL` can be omitted; the app automatically uses
`http://localhost:8000` when opened on `localhost` or `127.0.0.1`. Set
`VITE_API_BASE_URL` to the deployed backend API origin before building the remote frontend.

## Environment Variables

The backend does not use a plain `backend/.env` file. Local env selection is
branch-aware:

- `dev` branch loads `backend/.env.dev`
- `staging` branch loads `backend/.env.staging`
- other local branches load `backend/.env.dev`
- `main` refuses to run locally

Use `ENV_FILE=.env.dev` or `ENV_FILE=.env.staging` only when you need an
explicit debugging override. `backend/.env.old` is a private recycle bin and is
never loaded. Production on Render is controlled by host-managed variables with
`DJANGO_ENV=production`; `backend/.env.prod` is only a local reference copy.

Every backend env file should carry the same key list as `backend/.env.sample`.
Example local setup:

```env
DJANGO_SETTINGS_MODULE=config.settings.dev
DJANGO_ENV=dev
SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,[::1]
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:3000
DATABASE_URL=
DATABASE_SSL_REQUIRE=False
```

AI:

```env
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_BACKUP_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=openai/gpt-oss-120b:free
OPENROUTER_VISION_MODEL=google/gemma-4-31b-it:free
OPENROUTER_VISION_MODEL_FALLBACK=baidu/qianfan-ocr-fast:free
OPENROUTER_TEXT_MAX_TOKENS=2048
OPENROUTER_REASONING_MAX_TOKENS=4096
```

Optional RAG retrieval:

```env
QDRANT_URL=https://your-cluster-id.region.cloud.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key
QDRANT_COLLECTION=rxchat_dev
QDRANT_INFERENCE_MODEL=intfloat/multilingual-e5-small
QDRANT_SPARSE_MODEL=qdrant/bm25
QDRANT_DENSE_VECTOR_NAME=dense
QDRANT_SPARSE_VECTOR_NAME=sparse
QDRANT_VECTOR_SIZE=384
QDRANT_DISTANCE=Cosine
```

Database:

```env
DATABASE_URL=postgresql://user:password@host:5432/dev_db
```

If `DATABASE_URL` is omitted in `dev`, Django uses local SQLite. Staging and
production require `DATABASE_URL`.

Email OTP delivery:

```env
BREVO_API_KEY=your_brevo_api_key
BREVO_SENDER_EMAIL=verified-sender@example.com
BREVO_SENDER_NAME_RXCHAT=RxChat
BREVO_SENDER_NAME=RxChat
DEFAULT_FROM_EMAIL=RxChat <noreply@rxchat.dev>
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
for example `http://localhost:8000/auth/google/callback/` and
`https://api.fildah.com/auth/google/callback/`.

Frontend environment variables can be added in `fildah_frontend/.env` and
`rxchat_frontend/.env`:

```env
VITE_API_BASE_URL=https://api.fildah.com
```

Omit `VITE_API_BASE_URL` locally unless you want to point the local frontend at
a remote backend.

## API Overview

Fildah parent endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/home/` | Parent-site homepage metadata, featured products, trust points, updates |
| `GET` | `/products/` | Product catalog |
| `GET` | `/products/<slug>/` | Product detail, starting with RxChat |
| `GET` | `/pages/<slug>/` | Published company pages such as About |
| `GET` | `/docs/` | Published documentation sections |
| `GET` | `/docs/<slug>/` | Documentation detail |
| `GET` | `/blog/` | Published blog/news posts |
| `GET` | `/blog/<slug>/` | Blog/news detail |
| `POST` | `/contact/` | Contact/support intake |
| `GET` | `/account/products/` | Authenticated account hub summary |

Chat endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/rxchat/send/` | Send a message and stream the AI response |
| `GET` | `/rxchat/conversations/` | List current user's or session's conversations |
| `GET` | `/rxchat/conversations/<id>/` | Fetch a conversation with messages |
| `DELETE` | `/rxchat/conversations/<id>/delete/` | Delete a conversation |
| `PATCH` | `/rxchat/conversations/<id>/rename/` | Rename a conversation |
| `PUT` | `/rxchat/messages/<id>/` | Edit a user message and regenerate |
| `POST` | `/rxchat/messages/<id>/resend/` | Regenerate from a user message |

Auth endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/auth/register/` | Start email OTP registration |
| `POST` | `/auth/verify-otp/` | Verify registration OTP |
| `POST` | `/auth/complete-setup/` | Create account after OTP verification |
| `POST` | `/auth/login/` | Login or request device OTP |
| `POST` | `/auth/verify-device/` | Verify new device OTP |
| `POST` | `/auth/resend-otp/` | Resend OTP |
| `POST` | `/auth/forgot-password/` | Start password reset |
| `POST` | `/auth/verify-reset-otp/` | Verify password reset OTP |
| `POST` | `/auth/reset-password/` | Set a new password |
| `GET` | `/auth/google/login/` | Start Google OAuth |
| `GET` | `/auth/google/callback/` | Google OAuth callback |
| `POST` | `/auth/google/complete-setup/` | Complete Google account setup |
| `GET` | `/auth/me/` | Get current session user |
| `POST` | `/auth/logout/` | Logout |
| `PATCH` | `/auth/profile/` | Update profile fields |
| `POST` | `/auth/email/add/` | Start verified email change |
| `POST` | `/auth/email/verify/` | Verify and set new email |
| `POST` | `/auth/email/remove/` | Remove a non-primary email |

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

Frontend deployment targets:

- Fildah parent site: Vercel project with root directory `fildah_frontend/`
- RxChat product app: Vercel project with root directory `rxchat_frontend/`
- Build command for both: `npm run build`

Backend deployment target:

- Render or another Django-compatible host
- Root directory: `backend/`
- Build command: `./build.sh`
- Start command: `python manage.py collectstatic --noinput && python manage.py migrate && gunicorn config.wsgi:application`
- Configure `DJANGO_SETTINGS_MODULE`, `DJANGO_ENV`, `SECRET_KEY`,
  `DATABASE_URL`, `ALLOWED_HOSTS`, `ALLOWED_ORIGINS`, OpenRouter, optional
  Qdrant, and email keys in the host environment.
- Use `config.settings.staging` for staging and `config.settings.production`
  for production.

For the full branch, database, migration, and release workflow, see
[`docs/safe-growth-workflow.md`](docs/safe-growth-workflow.md).

Manual provider connectivity checks can be run from `backend/` with:

```bash
python check_apis.py
```

Django admin:

- `/admin/?project=fildah` shows the all-products Fildah admin view.
- `/admin/?project=rxchat` filters the admin index to RxChat sections.
- Direct admin URLs still rely on Django model permissions for access control.

## License

MIT
