# TrekManage — Trekking Management Application V2

IIT Madras BS Degree · App Development II (MAD-2) project.

Flask API + Vue.js (CDN) SPA + Bootstrap UI + SQLite + Redis cache + Celery batch jobs.

## Features

| Role | Capabilities |
|------|----------------|
| **Admin** | Dashboard stats, trek CRUD, staff create/manage, assign staff, search users/staff/treks, deactivate/blacklist, all bookings, ChartJS analytics, trigger monthly report |
| **Trek Staff** | Dashboard of assigned treks, update slots/status, participant list, mark started/completed (assigned treks only) |
| **Trekker** | Self-register, browse/filter Open & Approved treks, book (Open only), cancel, history, profile, async CSV export |

**Domain rules:** no overbooking, no duplicate active bookings, book only when status is `Open`, staff may manage only assigned treks.

**Celery jobs:** daily trek reminders · monthly HTML+PDF admin report (1st of month) · user-triggered booking CSV export with completion alert.

**Recommended extras included:** ChartJS admin analytics, responsive Bootstrap UI, HTML+PDF monthly report, frontend+backend validation, booking confirmation/cancellation notifications (email/webhook with local mock fallback).

## Stack (MAD-2 mandatory)

- Flask (API)
- Vue.js 3 via CDN (Jinja2 not used for UI pages)
- Bootstrap 5 only (no other CSS frameworks)
- SQLite created programmatically (`db.create_all` + seed)
- Redis for caching frequently accessed open treks (TTL)
- Redis + Celery for batch jobs

## Quick start (local)

### 1. Prerequisites

- Python 3.10+
- Redis server running locally (`redis-server`)

```bash
# Ubuntu/Debian
sudo apt-get install -y redis-server
redis-server --daemonize yes
redis-cli ping   # expect PONG
```

### 2. Setup

```bash
cd <project-root>
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # optional — defaults work for local demo
```

### 3. Run services (4 terminals)

**Terminal A — Flask (API + Vue SPA)**

```bash
source .venv/bin/activate
python run.py
# App: http://127.0.0.1:3847
```

**Terminal B — Celery worker**

```bash
source .venv/bin/activate
celery -A celery_app.celery_config.celery worker --loglevel=INFO
```

**Terminal C — Celery beat (schedules)**

```bash
source .venv/bin/activate
celery -A celery_app.celery_config.celery beat --loglevel=INFO
```

**Terminal D — Redis** (if not already a service)

```bash
redis-server
```

### 4. Demo logins (seeded automatically on first boot)

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@trekmanage.local` | `Admin@123` |
| Staff | `staff1@trekmanage.local` | `Staff@123` |
| Staff | `staff2@trekmanage.local` | `Staff@123` |
| User | `trekker1@example.com` | `User@123` |
| User | `trekker2@example.com` | `User@123` |

Admin is created programmatically after DB init — there is **no admin registration**.

## Project structure

```
├── backend/           # Flask app factory, models, APIs, seed, cache, notifications
│   ├── api/           # auth, admin, staff, user, treks blueprints
│   ├── models.py      # Unified User + Trek + Booking + ExportJob
│   └── seed.py        # Admin + demo data
├── celery_app/        # Celery worker/beat + tasks
├── frontend/          # Vue CDN SPA + Bootstrap
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── instance/          # SQLite DB (gitignored, created at runtime)
├── exports/           # CSV exports (gitignored)
├── reports/           # Monthly reports + notification mock log
├── run.py
├── requirements.txt
└── .env.example
```

## API overview

- `POST /api/auth/register` — trekker self-register
- `POST /api/auth/login` — all roles
- `GET  /api/auth/me`
- `GET  /api/treks` — public/open listing (Redis-cached)
- `GET|POST|PUT|DELETE /api/admin/treks` — admin trek CRUD
- `POST /api/admin/staff` · `POST /api/admin/treks/:id/assign-staff`
- `GET  /api/admin/search` · `PATCH /api/admin/people/:id/status`
- `GET  /api/admin/dashboard` · `/reports/summary` · `POST /reports/monthly/run`
- `GET|PATCH /api/staff/...` — assigned-trek management
- `POST /api/user/bookings` · cancel · history · profile
- `POST /api/user/exports/bookings` — Celery CSV job

JWT: send `Authorization: Bearer <token>` on protected routes.

## Notifications / secrets

If `MAIL_*` or `WEBHOOK_URL` are empty, notifications are written to:

- `reports/notifications.log`
- `notification_logs` DB table (visible on Admin → Reports)

No secrets are committed. Copy `.env.example` → `.env` for local overrides.

## Manual job triggers (viva)

- Admin UI → **Reports** → “Generate monthly report”
- User UI → **My bookings** → “Export CSV (async)”
- Celery beat runs daily reminders at 08:00 IST and monthly report on the 1st at 09:00 IST

```bash
# Optional one-shot from Python shell
source .venv/bin/activate
python -c "from celery_app.tasks import send_daily_reminders; print(send_daily_reminders.delay().id)"
```

## Notes for evaluation / viva

- Database is **never** created manually — Flask `db.create_all()` + seed on startup.
- Redis caches the open-treks listing (`treks:open`) with configurable TTL.
- Only Bootstrap is used for styling; ChartJS is used only for admin charts (allowed recommended option).
