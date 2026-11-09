# TrekManage — Windows PowerShell (simple)

Use **PowerShell on your Windows PC**. No Linux. No WSL. Redis is optional (skip it).

---

## 1. Install once (if you don’t have them)

1. **Python 3.12** — https://www.python.org/downloads/  
   During setup, tick **“Add python.exe to PATH”**, then Install.
2. **Git** — https://git-scm.com/download/win  

Close PowerShell and open a **new** PowerShell window.

Check:

```powershell
python --version
git --version
```

---

## 2. Download the project

```powershell
cd $HOME
git clone https://github.com/riyamoun/trekking-management.git
cd trekking-management
git checkout cursor/trekking-management-github-a742
git pull
```

---

## 3. Install Python packages

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 4. Lab passwords file

```powershell
.\.venv\Scripts\python.exe scripts\write-lab-env.py
```

---

## 5. Start the app

```powershell
.\.venv\Scripts\python.exe run.py
```

Leave this window open. Wait until it says it is running.

---

## 6. Open in Chrome / Edge

Go to:

**http://127.0.0.1:3847/**

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@trekmanage.local | TrekLab#Admin9x |
| Staff | staff1@trekmanage.local | TrekLab#Staff9x |
| Trekker | trekker1@example.com | TrekLab#User9x |

---

## Stop

In the PowerShell window that is running the app, press **Ctrl+C**.

## Next time

```powershell
cd $HOME\trekking-management
.\.venv\Scripts\python.exe run.py
```

Then open http://127.0.0.1:3847/

---

## If something fails

| Message | Fix |
|---------|-----|
| `python` not found | Reinstall Python and tick **Add to PATH**, open a **new** PowerShell |
| `Activate.ps1` blocked | Don’t use Activate — use `.\.venv\Scripts\python.exe` like above |
| refused to connect | App is not running — do step 5 first, same PC |
| `git` not found | Install Git, open a **new** PowerShell |
