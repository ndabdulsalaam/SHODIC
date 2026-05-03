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

Use the env files in `backend/` for local/private configuration:

- `.env.dev` for `dev`
- `.env.staging` for `staging`
- `.env.prod` as a local reference mirror of Render production variables
- `.env.old` as a private recycle bin that Django must never load
- `.env.sample` as the only tracked env template

Do not reuse the production `DATABASE_URL` in `dev` or `staging`.
The backend selects env files from the current branch: `dev` uses `.env.dev`,
`staging` uses `.env.staging`, and feature branches use `.env.dev`. The `main`
branch refuses to run locally. Run local commands with `ENV_FILE=.env.dev` or
`ENV_FILE=.env.staging` only when you want an explicit debugging override.

## Branch Flow

Use `main` as the production branch, `staging` as the pre-production branch,
`dev` as the local integration branch, and short-lived feature branches for new
work.

Recommended flow:

```bash
git checkout dev
git pull
git checkout -b feature/my-change
```

Develop locally, commit code and migrations together, then merge through
`dev -> staging -> main`. Do not push work directly to `main`.

## Neon Branch Commands

```bash
PROJECT_ID=your-neon-project-id
DB_NAME=your_database_name
ROLE_NAME=your_role_name

neon auth
neon branches list --project-id "$PROJECT_ID"

# One-time setup
neon branches create --name staging --parent main --project-id "$PROJECT_ID"
neon branches create --name dev --parent staging --project-id "$PROJECT_ID"

# Put these into backend/.env.staging and backend/.env.dev.
neon connection-string staging --project-id "$PROJECT_ID" --database-name "$DB_NAME" --role-name "$ROLE_NAME"
neon connection-string dev --project-id "$PROJECT_ID" --database-name "$DB_NAME" --role-name "$ROLE_NAME"

# Before a staging test cycle
neon branches reset staging --parent --project-id "$PROJECT_ID"

# At the start of a feature
neon branches reset dev --parent --project-id "$PROJECT_ID"

# Optional schema review before production
neon branches schema-diff main staging --project-id "$PROJECT_ID" --database "$DB_NAME"
```

## Local Dev Checklist

Backend:

```bash
cd backend
# Fill .env.dev with the dev Neon and Qdrant values first.
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py setup_qdrant
python manage.py seed_dev
python manage.py test
```

Frontend:

```bash
cd fildah_frontend
npm install
npm run lint
npm run build
cd ..
cd rxchat_frontend
npm install
npm run lint
npm run build
```

For schema work, use a dev Postgres database or Neon/Postgres branch instead of
SQLite so migrations are tested against the same database family as production.
When the dev branch has just been reset from staging and you want fake-only
data, run `ENV_FILE=.env.dev python manage.py seed_dev --flush --reset-qdrant`
after migrations.

## Staging Release Checklist

1. Merge or deploy the feature branch to `staging`.
2. Use the `staging` branch or run explicit checks with `ENV_FILE=.env.staging`.
3. Use a staging database, never production.
4. Let startup run:

   ```bash
   python manage.py collectstatic --noinput
   python manage.py migrate
   gunicorn config.wsgi:application
   ```

5. Rebuild the staging vector sample after migrations:

   ```bash
   ENV_FILE=.env.staging python manage.py reseed_staging --limit 250
   ```

6. Smoke-test login, registration, chat send/edit/resend/delete, admin access,
   static files, and frontend/backend session cookies.
7. Check logs and confirm migrations are applied.

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
