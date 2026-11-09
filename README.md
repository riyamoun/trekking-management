# TrekManage — Trekking Management Application V2

IIT Madras BS Degree · App Development II (MAD-2).

Public marketing site plus role dashboards (admin / staff / trekker), JWT authentication, trail photography, SVG stickers, atmosphere video, and Chart.js analytics — built on Flask + Vue.js (CDN) + Bootstrap + SQLite + Redis + Celery.

## Run on your laptop (instructor / viva)

The cloud agent preview is **not** on your machine. Clone the repo and start it locally so your instructor opens a normal browser tab on **your** device.

### Prerequisites

- Python 3.10+
- Redis (needed for trek cache + Celery; UI still boots if Redis is down)

```bash
# Ubuntu / WSL
sudo apt-get install -y redis-server
redis-server --daemonize yes

# macOS
brew install redis && brew services start redis
```

### One-command start

```bash
git clone https://github.com/riyamoun/trekking-management.git
cd trekking-management
git checkout cursor/trekking-management-github-a742   # or main after merge

python3 scripts/start-local.py
```

That script creates `.venv`, copies `.env.example` → `.env` if needed, starts Flask, and opens:

**http://127.0.0.1:3847/**

Press `Ctrl+C` in that terminal to stop.

### Manual start (same result)

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # first time only
python run.py
# then open http://127.0.0.1:3847/
```

### Optional Celery (reminders / CSV / monthly report)

In two extra terminals (venv activated, Redis up):

```bash
celery -A celery_app.celery_config.celery worker --loglevel=INFO
celery -A celery_app.celery_config.celery beat --loglevel=INFO
```

### Lab accounts (from `.env.example` when `SEED_DEMO_DATA=true`)

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@trekmanage.local` | `TrekLab#Admin9x` |
| Staff | `staff1@trekmanage.local` | `TrekLab#Staff9x` |
| Trekker | `trekker1@example.com` | `TrekLab#User9x` |

Change these in `.env` before first boot if you prefer. Never commit `.env` or `instance/`.

### What to show the instructor

1. Public home `#/` — hero, stickers, video, portals  
2. Explore `#/explore` — trek cards with photos  
3. Sign in as each role — admin / staff / trekker dashboards  
4. Optional: trigger CSV export / monthly report with Celery running  

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
