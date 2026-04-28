# Safe Growth Workflow

This project uses three isolated environments: `dev`, `staging`, and
`production`. Each environment must have its own Django settings module,
database, frontend API URL, and external-service configuration.

## Environments

| Environment | Django settings module | Purpose | Database |
| --- | --- | --- | --- |
| `dev` | `config.settings.dev` | Local feature work | Local/dev Postgres preferred; SQLite fallback allowed |
| `staging` | `config.settings.staging` | Pre-production release testing | Staging Postgres or Neon/Postgres branch |
| `production` | `config.settings.production` | Live users | Production Postgres only |

Use the sample files in `backend/` as templates:

- `.env.sample` for `dev`
- `.env.staging.sample` for `staging`
- `.env.production.sample` for `production`

Do not reuse the production `DATABASE_URL` in `dev` or `staging`.

## Branch Flow

Use `main` as the production branch, `staging` as the pre-production branch, and
short-lived `feature/...` branches for new work.

Recommended flow:

```bash
git checkout main
git pull
git checkout -b feature/my-change
```

Develop locally, commit code and migrations together, then open a pull request
into `staging`. After staging passes testing, merge the same approved work into
`main` for production.

## Local Dev Checklist

Backend:

```bash
cd backend
cp .env.sample .env
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py test
```

Frontend:

```bash
cd rxchat_frontend
npm install
npm run lint
npm run build
```

For schema work, use a dev Postgres database or Neon/Postgres branch instead of
SQLite so migrations are tested against the same database family as production.

## Staging Release Checklist

1. Merge or deploy the feature branch to `staging`.
2. Use `DJANGO_SETTINGS_MODULE=config.settings.staging`.
3. Use a staging database, never production.
4. Let startup run:

   ```bash
   python manage.py collectstatic --noinput
   python manage.py migrate
   gunicorn config.wsgi:application
   ```

5. Smoke-test login, registration, chat send/edit/resend/delete, admin access,
   static files, and frontend/backend session cookies.
6. Check logs and confirm migrations are applied.

Staging must catch migration and deployment issues before production.

## Production Release Checklist

1. Confirm the exact code and migrations already passed staging.
2. Create a fresh production database backup.
3. Merge the approved work into `main`.
4. Deploy production with `DJANGO_SETTINGS_MODULE=config.settings.production`.
5. Let startup run `collectstatic`, `migrate`, and Gunicorn.
6. Smoke-test production immediately.
7. Check logs and migration state.

If a release fails before destructive data changes, roll back the code deploy. If
data was changed destructively, restore from the verified backup or ship a
forward-fix migration, depending on which is safer.

## Migration Rules

- New table: create and test normally.
- New column: add nullable or with a safe default first; enforce stricter
  constraints in a later migration if needed.
- Rename column: add the new column, copy data, update code, verify, then remove
  the old column in a later release.
- Remove column: stop using it in code first, deploy, verify, then remove it in
  a later release.
- Relationship changes: add the new relationship beside the old one, backfill,
  update code, enforce constraints, then remove the old relationship.
- Data migrations: use Django `RunPython`, keep them idempotent where possible,
  and test them against staging data before production.

## Database Copying

Prefer provider-native branching or snapshots when available. For generic
Postgres-compatible providers, use `pg_dump` and `pg_restore` into a non-production
database.

Example shape:

```bash
pg_dump "$PRODUCTION_DATABASE_URL" --format=custom --no-owner --no-acl --file=prod.dump
pg_restore --dbname="$STAGING_DATABASE_URL" --clean --if-exists --no-owner --no-acl prod.dump
```

Scrub sensitive user data before using copied production data for broad dev
work. Never run restore commands against production unless the goal is an
intentional disaster recovery restore.
