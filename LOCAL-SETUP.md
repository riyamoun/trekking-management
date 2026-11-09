# TrekManage — complete local setup (your laptop)

Do this on **your computer** (not the Cursor cloud agent).  
When it works, your instructor opens `http://127.0.0.1:3847/` in a browser on **your** device.

---

## 0. Open a terminal on your machine

| Your OS | What to open |
|---------|----------------|
| **Windows** | Install [WSL2 Ubuntu](https://learn.microsoft.com/en-us/windows/wsl/install), then open **Ubuntu** from the Start menu. Run all commands below inside WSL. |
| **macOS** | **Terminal** app |
| **Ubuntu / Debian Linux** | normal Terminal |

Check you are not inside the Cursor cloud `/workspace` agent unless that *is* your intended demo machine.

```bash
pwd
whoami
```

---

## 1. Install Git, Python, and venv

### Ubuntu / Debian / Windows WSL

Copy-paste **one block at a time**, press Enter, wait until it finishes:

```bash
sudo apt-get update
```

```bash
sudo apt-get install -y git python3 python3-pip python3.12-venv python3-venv
```

```bash
python3 --version
git --version
```

You want Python **3.10 or newer**.

### macOS

```bash
# Install Homebrew if you do not have it: https://brew.sh
brew install git python
python3 --version
git --version
```

---

## 2. Install Redis (optional but recommended for full MAD-2 demo)

UI and dashboards work **without** Redis.  
Install Redis if you want trek caching + Celery (CSV export / reminders / monthly report).

### Ubuntu / Debian / WSL

```bash
sudo apt-get install -y redis-server
```

```bash
sudo service redis-server start
```

```bash
redis-cli ping
```

Expected reply: `PONG`

### macOS

```bash
brew install redis
brew services start redis
redis-cli ping
```

If Redis install fails, **skip it** and continue. You can still show the website and login dashboards.

---

## 3. Download the project from GitHub

Pick a folder on **your** machine (example: home directory):

```bash
cd ~
```

```bash
git clone https://github.com/riyamoun/trekking-management.git
```

```bash
cd trekking-management
```

```bash
git fetch origin
```

```bash
git checkout cursor/trekking-management-github-a742
```

```bash
git pull origin cursor/trekking-management-github-a742
```

```bash
pwd
ls
```

You should see `run.py`, `backend/`, `frontend/`, `requirements.txt`, `go.sh`.

---

## 4. Create a Python virtual environment and install packages

If an old broken `.venv` exists, remove it first:

```bash
rm -rf .venv
```

Create the venv:

```bash
python3 -m venv .venv
```

Activate it:

```bash
# Ubuntu / WSL / macOS / Linux
source .venv/bin/activate
```

Your prompt should show `(.venv)`.

Upgrade pip and install dependencies:

```bash
python -m pip install --upgrade pip
```

```bash
pip install -r requirements.txt
```

```bash
python -c "import flask; print('Flask OK')"
```

---

## 5. Create your local `.env` (lab passwords)

```bash
python3 scripts/write-lab-env.py
```

That copies `.env.example` → `.env` and fills viva passwords. Never commit `.env`.

Manual alternative:

```bash
cp .env.example .env
nano .env
```

Set these lines:

```env
ADMIN_PASSWORD=TrekLab#Admin9x
DEMO_STAFF_PASSWORD=TrekLab#Staff9x
DEMO_USER_PASSWORD=TrekLab#User9x
SEED_DEMO_DATA=true
SHOW_LAB_HINTS=true
PORT=3847
```

---

## 6. Start the app

Stay in the project folder with `(.venv)` active:

```bash
cd ~/trekking-management
source .venv/bin/activate
python run.py
```

**Leave this terminal open.** You should see Flask listening on port **3847**.

### Alternative (same folder, no activate needed)

```bash
bash go.sh
```

or:

```bash
python3 scripts/start-local.py
```

---

## 7. Open it in your browser (on the same computer)

Open a browser on **that same machine** and go to:

**http://127.0.0.1:3847/**

or

**http://localhost:3847/**

### What to click

1. Public home — hero, stickers, video  
2. **Explore treks**  
3. **Sign in** with the accounts below  

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@trekmanage.local` | `TrekLab#Admin9x` |
| Staff | `staff1@trekmanage.local` | `TrekLab#Staff9x` |
| Trekker | `trekker1@example.com` | `TrekLab#User9x` |

---

## 8. Optional — Celery (full job demo)

Need Redis running (`redis-cli ping` → `PONG`).

**Terminal 2** (new window):

```bash
cd ~/trekking-management
source .venv/bin/activate
celery -A celery_app.celery_config.celery worker --loglevel=INFO
```

**Terminal 3:**

```bash
cd ~/trekking-management
source .venv/bin/activate
celery -A celery_app.celery_config.celery beat --loglevel=INFO
```

Keep Terminal 1 (`python run.py`) running too.

---

## 9. Stop the app

In the Flask terminal press:

```text
Ctrl+C
```

---

## 10. Next time you want to run it again

```bash
cd ~/trekking-management
source .venv/bin/activate
python run.py
```

Then open http://127.0.0.1:3847/

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `redis-server: command not found` | Skip Redis; UI still works. |
| `ensurepip is not available` / venv failed | `sudo apt-get install -y python3.12-venv python3-venv` then `rm -rf .venv` and recreate. |
| `No module named 'flask'` | `source .venv/bin/activate` then `pip install -r requirements.txt` |
| `python: command not found` | Use `python3` or `.venv/bin/python run.py` |
| Browser **refused to connect** | Flask is not running on **this** PC. Start `python run.py` first, then open the URL on the **same** PC. |
| Port already in use | `PORT=3850 python run.py` then open `http://127.0.0.1:3850/` |
| Wrong folder / nested clone mess | Stay in `~/trekking-management` (the clone). Do **not** clone again inside Cursor cloud `/workspace` unless you mean to. |

---

## One-page copy list (experienced users)

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-pip python3.12-venv redis-server
sudo service redis-server start
cd ~
git clone https://github.com/riyamoun/trekking-management.git
cd trekking-management
git checkout cursor/trekking-management-github-a742
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# set ADMIN_PASSWORD / DEMO_* / SEED_DEMO_DATA=true in .env (see table above)
python run.py
# browser → http://127.0.0.1:3847/
```
