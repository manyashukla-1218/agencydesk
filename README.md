# AgencyDesk

Multi-tenant agency/client project-management platform. Stack: **React
(Vite)**, **Python (FastAPI + SQLAlchemy)**, **PostgreSQL (Alembic
migrations)**.

See [`DESIGN.md`](./DESIGN.md) for the schema/access-control write-up.

## Setup (under 10 minutes)

### 0. Prerequisites
- Python 3.11+
- Node 18+
- PostgreSQL 14+ running locally (or use the docker-compose snippet below)

```bash
# quickest way to get a local Postgres if you don't have one:
docker run --name agencydesk-db -e POSTGRES_USER=agencydesk \
  -e POSTGRES_PASSWORD=agencydesk -e POSTGRES_DB=agencydesk \
  -p 5432:5432 -d postgres:16
```

### 1. Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env   # defaults already match the docker command above

alembic upgrade head    # creates all tables + the invite-race unique index
python seed.py          # seeds 2 agencies, clients, mixed-visibility tasks

uvicorn app.main:app --reload --port 8000
```

API is now at `http://localhost:8000` (docs at `/docs`).

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

App is now at `http://localhost:5173`.

### 3. Log in

Seed data gives you three ready-made logins (all password `password123`):

| Email | What it is |
|---|---|
| `admin@northwind.test` | agency_admin @ Northwind Creative |
| `demo.person@example.com` | **two accounts, same email** — agency_member @ Northwind, client_user @ Beacon/Initech. Logging in shows a workspace picker. |
| `contact@acme.test` | client_user @ Northwind's client "Acme Corp" |

### 4. Run tests

```bash
cd backend
pytest
```

Tests run against an in-memory SQLite database (no Postgres needed to run
them) and specifically assert:
- cross-tenant reads/writes 404 rather than leak (`test_tenant_isolation.py`)
- internal tasks/comments/time-entries never reach a `client_user`, including
  through search/status filters and the dashboard aggregate (`test_client_visibility.py`)
- all four named edge cases: one-person-two-agencies, invite races, duplicate
  invite acceptance, and member removal mid-task (`test_edge_cases.py`)

## Project layout

```
backend/
  app/
    models.py       # SQLAlchemy schema
    deps.py          # TenantScope — the single source of truth for tenant/visibility filtering
    routers/         # one file per resource
  alembic/versions/  # 0001_initial.py — full schema + partial unique index for invites
  seed.py
  tests/
frontend/
  src/
    api/client.js    # fetch wrapper
    pages/           # Login, ProjectsList, ProjectBoard (+ task detail)
DESIGN.md
```

## Known simplifications (in scope per the brief, called out for the interview)

- File storage is local disk (`UPLOAD_DIR`), not S3 — fine for a take-home,
  swappable behind the same `storage_key` field in production.
- No Timeline/Gantt view, full CRM, or automations — explicitly out of
  scope per the assignment brief.
- Postgres Row-Level-Security is discussed as a defense-in-depth option in
  DESIGN.md but not implemented — the assignment's isolation requirement is
  met at the application layer (`TenantScope`) and covered by tests.
