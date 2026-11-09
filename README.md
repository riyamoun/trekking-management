# TrekManage — Trekking Management Application V2

IIT Madras BS Degree · App Development II (MAD-2).

Public marketing site plus role dashboards (admin / staff / trekker), JWT authentication, trail photography, SVG stickers, atmosphere video, and Chart.js analytics — built on Flask + Vue.js (CDN) + Bootstrap + SQLite + Redis + Celery.

## Run on your laptop (instructor / viva)

**Full line-by-line guide:** see [`LOCAL-SETUP.md`](./LOCAL-SETUP.md) (install → clone → venv → `.env` → run → browser → accounts).

Short path (Ubuntu / WSL) after reading that file:

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-pip python3.12-venv redis-server
sudo service redis-server start   # optional for UI-only demo
cd ~
git clone https://github.com/riyamoun/trekking-management.git
cd trekking-management
git checkout cursor/trekking-management-github-a742
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# set ADMIN_PASSWORD=TrekLab#Admin9x, DEMO_* passwords, SEED_DEMO_DATA=true
python run.py
# open http://127.0.0.1:3847/
```

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@trekmanage.local` | `TrekLab#Admin9x` |
| Staff | `staff1@trekmanage.local` | `TrekLab#Staff9x` |
| Trekker | `trekker1@example.com` | `TrekLab#User9x` |

## Architecture (viva-ready)

| Layer | Technology | Notes |
|------|------------|--------|
| API | Flask + Flask-JWT-Extended | Unified `User` model (`admin` / `staff` / `user`) |
| UI | Vue 3 CDN + Bootstrap 5 | Public site + role dashboards, Chart.js |
| DB | SQLite via SQLAlchemy | Created only by `db.create_all()` + seed |
| Cache | Redis | Open-trek listing TTL + invalidation on mutations |
| Jobs | Celery + Redis | Daily reminders, monthly HTML/PDF report, CSV export |
| Secrets | Env or `instance/runtime_secrets.json` | No hardcoded signing keys in source |

**Security posture**

- Signing keys: from env, else cryptographically generated under `instance/` (gitignored)
- Authorization uses **database role**, not JWT claim alone
- Public trek APIs expose only `Open` / `Approved`
- CORS allowlist (empty = same-origin only); Flask debug off unless `FLASK_DEBUG=1`
- Password policy: ≥10 chars, upper, lower, digit, symbol

## Features

| Role | Capabilities |
|------|----------------|
| **Admin** | Dashboard, trek CRUD, staff lifecycle, assignments, search, deactivate/blacklist, bookings, Chart.js reports, monthly report trigger |
| **Trek Staff** | Assigned treks only — slots/status, participants, mark started/completed |
| **Trekker** | Register, filter/book Open treks, history, profile, async CSV export |

**Domain rules:** no overbooking, no duplicate active bookings, book only when `Open`, staff may manage only assigned treks.

## Project structure

```
├── backend/           # Flask factory, models, APIs, seed, cache, security
├── celery_app/        # worker/beat + tasks
├── frontend/          # Vue CDN SPA + Bootstrap + assets
├── scripts/           # start-local.py (laptop launcher)
├── instance/          # DB + runtime secrets (gitignored)
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
