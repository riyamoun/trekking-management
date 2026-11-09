# TrekManage — Trekking Management Application V2

IIT Madras BS Degree · App Development II (MAD-2).

Public marketing site plus role dashboards (admin / staff / trekker), JWT authentication, trail photography, SVG stickers, atmosphere video, and Chart.js analytics — built on Flask + Vue.js (CDN) + Bootstrap + SQLite + Redis + Celery.

## Architecture (viva-ready)

| Layer | Technology | Notes |
|------|------------|--------|
| API | Flask + Flask-JWT-Extended | Unified `User` model (`admin` / `staff` / `user`) |
| UI | Vue 3 CDN + Bootstrap 5 | Role dashboards, Chart.js analytics |
| DB | SQLite via SQLAlchemy | Created only by `db.create_all()` + seed |
| Cache | Redis | Open-trek listing TTL + invalidation on mutations |
| Jobs | Celery + Redis | Daily reminders, monthly HTML/PDF report, CSV export |
| Secrets | Env or `instance/runtime_secrets.json` | No hardcoded signing keys or demo passwords in source |

**Security posture**

- Signing keys: from env, else cryptographically generated and persisted under `instance/` (gitignored)
- Admin bootstrap password: from `ADMIN_PASSWORD` or one-time random → `instance/BOOTSTRAP_ADMIN.txt`
- Lab fixtures (`SEED_DEMO_DATA`) off by default; published UI never shows credentials
- Authorization uses **database role**, not JWT claim alone
- Public trek APIs expose only `Open` / `Approved`; other statuses require proper access
- CORS allowlist (empty = same-origin only); Flask debug off unless `FLASK_DEBUG=1`
- Password policy: ≥10 chars, upper, lower, digit, symbol

## Features

| Role | Capabilities |
|------|----------------|
| **Admin** | Dashboard, trek CRUD, staff lifecycle, assignments, search, deactivate/blacklist, bookings, Chart.js reports, monthly report trigger |
| **Trek Staff** | Assigned treks only — slots/status, participants, mark started/completed |
| **Trekker** | Register, filter/book Open treks, history, profile, async CSV export |

**Domain rules:** no overbooking, no duplicate active bookings, book only when `Open`, staff may manage only assigned treks.

## Quick start (local lab)

### Prerequisites

- Python 3.10+
- Redis (`redis-server`)

```bash
sudo apt-get install -y redis-server   # if needed
redis-server --daemonize yes
redis-cli ping
```

### Setup

```bash
cd <project-root>
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env:
#   ADMIN_PASSWORD=<strong password>
#   SEED_DEMO_DATA=true          # optional viva fixtures
#   DEMO_STAFF_PASSWORD=...
#   DEMO_USER_PASSWORD=...
#   SHOW_LAB_HINTS=true          # optional UI hint (no passwords shown)
```

If `ADMIN_PASSWORD` is omitted, the first boot writes credentials to `instance/BOOTSTRAP_ADMIN.txt`.

### Run (4 processes)

```bash
python run.py
# http://127.0.0.1:3847

celery -A celery_app.celery_config.celery worker --loglevel=INFO
celery -A celery_app.celery_config.celery beat --loglevel=INFO
redis-server   # if not already running
```

### Lab accounts (only when `SEED_DEMO_DATA=true`)

Passwords come from your `.env` (`DEMO_*`) or `instance/DEMO_CREDENTIALS.txt` — **never commit them**.

| Role | Email (when seeded) |
|------|---------------------|
| Admin | value of `ADMIN_EMAIL_SEED` |
| Staff | `staff1@trekmanage.local`, `staff2@trekmanage.local` |
| User | `trekker1@example.com`, … |

## Project structure

```
├── backend/           # Flask factory, models, APIs, seed, cache, security
│   ├── api/           # auth, admin, staff, user, treks
│   ├── security.py    # runtime secrets + password policy
│   └── seed.py        # admin bootstrap + optional lab fixtures
├── celery_app/        # worker/beat + tasks
├── frontend/          # Vue CDN SPA + Bootstrap
├── instance/          # DB + runtime secrets (gitignored)
├── exports/ · reports/
├── run.py
└── requirements.txt
```

## API overview

- `GET  /api/meta` · `GET /api/health`
- `POST /api/auth/register` · `POST /api/auth/login` · `GET /api/auth/me`
- `GET  /api/treks` (public Open/Approved, Redis-cached)
- Admin / staff / user blueprints under `/api/admin`, `/api/staff`, `/api/user`
- JWT: `Authorization: Bearer <token>`

## Celery jobs

1. **Daily reminders** (08:00 IST) — upcoming bookings via email/webhook (mock if unset)
2. **Monthly report** (1st, 09:00 IST) — HTML + PDF for admin; also triggerable from UI
3. **CSV export** — user-triggered; completion notification + download

## Notifications / secrets

Empty `MAIL_*` / `WEBHOOK_URL` → `reports/notifications.log` + DB `notification_logs`.  
Published deploys should set `SECRET_KEY`, `JWT_SECRET_KEY`, and `ADMIN_PASSWORD` via host secrets; otherwise strong values are auto-generated into `instance/`.
