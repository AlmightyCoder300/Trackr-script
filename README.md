# Trackr UK Finance Internship Monitor

Runs every weekday at 07:30 UTC via GitHub Actions.
Scrapes `https://app.the-trackr.com/uk-finance/summer-internships`, diffs against the previous day's snapshot, and emails you if new listings appear or a previously-closed role opens.

---

## Setup (one-time, ~5 minutes)

### 1. Create a Gmail App Password

You must send from a Gmail account with **2-Step Verification** enabled.

1. Go to your Google Account → **Security** → **2-Step Verification** → scroll to **App passwords**
   (direct link: https://myaccount.google.com/apppasswords)
2. Click **Create** → give it any name (e.g. "Trackr monitor")
3. Copy the 16-character password Google shows you — you won't see it again

### 2. Add GitHub Secrets to your repo

In your GitHub repo go to **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret name | Value |
|---|---|
| `GMAIL_USER` | your Gmail address, e.g. `you@gmail.com` |
| `GMAIL_APP_PASSWORD` | the 16-character App Password from step 1 |
| `RECIPIENT_EMAIL` | email address to send alerts to (can be same as `GMAIL_USER`) |

### 3. Push this repo to GitHub

```bash
git init
git add .
git commit -m "init"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### 4. Enable GitHub Actions

If Actions are not already enabled, go to the **Actions** tab in your repo and click **"I understand my workflows, go ahead and enable them"**.

---

## How it works

| File | Purpose |
|---|---|
| `monitor.py` | Playwright scraper + diff logic + Gmail sender |
| `snapshot.json` | Auto-committed daily snapshot (don't edit manually) |
| `.github/workflows/monitor.yml` | Cron schedule + CI steps |
| `requirements.txt` | Python dependencies |

**First run:** saves a baseline snapshot with no email (nothing to diff against yet).  
**Subsequent runs:** diffs current listings against the saved snapshot and emails only if something changed.

### Change detection

- **New listing** — a company/programme pair that wasn't in yesterday's snapshot
- **Newly opened** — a listing that previously had no opening date but now does

---

## Manual run

Trigger a run any time from the **Actions** tab → select **"Internship Monitor"** → **"Run workflow"**.

---

## Local testing

```bash
export GMAIL_USER="you@gmail.com"
export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
export RECIPIENT_EMAIL="you@gmail.com"

pip install -r requirements.txt
python -m playwright install chromium
python monitor.py
```
