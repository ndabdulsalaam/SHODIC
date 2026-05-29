# SHODIC

SHODIC is a free, anonymous-session AI pharmacy chat app with text-only chat, streaming responses, and optional RAG retrieval over drug information sources.

> SHODIC provides general health and medication information only. It is not a substitute for professional medical advice, diagnosis, treatment, or emergency care.

## Prerequisites

- Python 3.11+
- Node.js 18+
- SQLite for quick setup, or PostgreSQL through `DATABASE_URL`

## Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.sample .env
python manage.py migrate
python manage.py runserver
```

Backend default: `http://localhost:8000`.

Create an admin user for source ingestion and admin management:

```bash
python manage.py createsuperuser
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend default: `http://localhost:5173`. On localhost, `VITE_API_BASE_URL` can be omitted and the app uses `http://localhost:8000`.

## Environment

Minimum backend `.env` values:

```env
SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,[::1]
ALLOWED_ORIGINS=http://localhost:5173
DATABASE_URL=
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=openrouter/free
QDRANT_URL=
QDRANT_API_KEY=
QDRANT_COLLECTION=shodic
OPENFDA_API_KEY=
```

Frontend `.env` is only needed when the API is not on localhost:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## API

The chat API lives under `/shodic/`:

- `POST /shodic/send/`
- `GET /shodic/conversations/`
- `GET /shodic/conversations/<id>/`
- `PATCH /shodic/conversations/<id>/rename/`
- `DELETE /shodic/conversations/<id>/delete/`
- `PUT /shodic/messages/<id>/`
- `POST /shodic/messages/<id>/resend/`

## Checks

```bash
cd backend
python manage.py check
python manage.py test

cd ../frontend
npm run lint
npm run build
```

## License

MIT
