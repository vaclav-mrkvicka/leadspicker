---
name: lp-report
description: >
  Generates and delivers Leadspicker weekly activity reports for client accounts.
  Use when the user wants to: run a Leadspicker report, generate a weekly outreach
  summary for a client, add a new reporting account, set up Leadspicker reporting
  for a new client, create Gmail drafts for Leadspicker weekly reports, or onboard
  a new account into the reporting pipeline. Also triggers on: "run the Leadspicker
  report", "generate the weekly report", "add a new client to the report", "set up
  reporting for X", "create a report draft", "send the weekly summary to X".
---

# Leadspicker Weekly Report

Generates weekly outreach activity reports (emails, LinkedIn, sentiment, project breakdown)
for one or more Leadspicker accounts and delivers them via Gmail draft (or another configured
delivery method). The report structure is identical across all accounts and delivery methods.

Two primary workflows:
- **Onboard a new client** — add their API key, display name, and email address to the config, then run a test report
- **Run an existing report** — execute the report for one or all configured accounts

---

## Required Information

### Onboarding a new client

Always collect the following before making any changes:

| Field | Description | Example |
|-------|-------------|---------|
| Leadspicker API key | From the client's Leadspicker account settings | `73c6e0c59fe9...` |
| Account key name | Short ALLCAPS identifier, no spaces or hyphens | `STARTUPGRIND` |
| Display name | Real client name — used in subject line and report header | `Startup Grind` |
| Recipient email(s) | Comma-separated list of who receives the report | `naman@startupgrind.com` |
| Delivery method | How the report is delivered | Gmail draft (default) |

### Running an existing report

| Field | Description | Default |
|-------|-------------|---------|
| Account | Account key name or partial match | All accounts |
| Date range | Week to report on | Current week Mon–today (Mon = previous week) |
| Create draft | Whether to create a delivery draft | No (terminal only) |

---

## Workflow A: Onboard New Client

### Step 1 — Collect credentials

Ask the user for all fields from the Required Information table above. Do not proceed until you have all of them.

### Step 2 — Add API key to .env

Append to `.env` at the repo root:

```
LEADSPICKER_API_KEY_<ACCOUNTKEY>_REPORT=<api_key>
```

Example:
```
LEADSPICKER_API_KEY_STARTUPGRIND_REPORT=73c6e0c59fe9e53a3da01fe679d6d6b7...
```

### Step 3 — Add client config to gmail_draft.py

Open `leadspicker-report/gmail_draft.py` and add an entry to the `CLIENT_CONFIG` dict:

```python
"ACCOUNTKEY": {"name": "Display Name", "to": "email@client.com"},
```

For multiple recipients, comma-separate them in the `to` string:
```python
"INFOSHARE": {"name": "Infoshare", "to": "agnieszka@infoshare.pl, todd.benson@leadspicker.com"},
```

### Step 4 — Set up Gmail API access

**Gmail (default):** Two sub-steps — first create OAuth credentials in Google Cloud Console,
then run the local auth script to exchange them for tokens.

#### 4a — Google Cloud Console setup (one-time per Google account)

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or select an existing one)
3. Navigate to **APIs & Services → Library**, search for **Gmail API**, and enable it
4. Navigate to **APIs & Services → OAuth consent screen**
   - Choose **External** user type
   - Fill in app name (e.g. "Leadspicker Report"), support email, developer email
   - Add scope: `https://www.googleapis.com/auth/gmail.compose`
   - Add the Gmail address that will send drafts as a **Test user**
5. Navigate to **APIs & Services → Credentials → Create Credentials → OAuth client ID**
   - Application type: **Desktop app**
   - Name it anything (e.g. "Leadspicker Report Desktop")
6. Click **Download JSON** and save the file as:
   ```
   leadspicker-report/gmail_credentials.json
   ```
   This file is the prerequisite for the next step. Without it, `gmail_auth.py` will fail.

#### 4b — Run the local OAuth flow

Once `gmail_credentials.json` is in place, verify `.env` contains all three Gmail OAuth variables:
```
GMAIL_REFRESH_TOKEN=...
GMAIL_CLIENT_ID=...
GMAIL_CLIENT_SECRET=...
```
If any are missing, run:
```bash
python3 leadspicker-report/gmail_auth.py
```
This opens a browser for OAuth consent and writes `GMAIL_REFRESH_TOKEN`, `GMAIL_CLIENT_ID`,
and `GMAIL_CLIENT_SECRET` to `.env` automatically. Only needs to be done once per Google account.

### Step 5 — Verify (dry run, no draft)

```bash
python3 leadspicker-report/report.py --account <ACCOUNTKEY>
```

Confirm the terminal output shows stats for the correct account with no API errors.

### Step 6 — Verify draft creation

```bash
python3 leadspicker-report/report.py --account <ACCOUNTKEY> --draft
```

Confirm the output line: `Gmail draft created: Leadspicker Weekly — <Display Name> — w/c <date>`
Open Gmail Drafts to verify the To address and subject line are correct.

---

## Workflow B: Run Existing Report

### Single account

```bash
python3 leadspicker-report/report.py --account startupgrind
```
Account name matching is case-insensitive and partial (e.g. `ovhcee` matches `OVHCEESTARTUPS`).

### All accounts

```bash
python3 leadspicker-report/report.py
```

### With Gmail drafts

Add `--draft` to either command:
```bash
python3 leadspicker-report/report.py --draft
python3 leadspicker-report/report.py --account startupgrind --draft
```

### Custom date range

```bash
python3 leadspicker-report/report.py --from 2026-03-09 --to 2026-03-15
```

### Date logic (no flags)

- **Any day except Monday**: Reports Mon–today of the current week
- **Monday**: Automatically reports the previous completed Mon–Sun week

---

## Delivery Methods

### Gmail (current default)

Driven by `leadspicker-report/gmail_draft.py`.

**Required .env variables:**
```
GMAIL_REFRESH_TOKEN=...
GMAIL_CLIENT_ID=...
GMAIL_CLIENT_SECRET=...
```

**One-time setup:** Google Cloud Console OAuth credentials → download as `leadspicker-report/gmail_credentials.json` → run `python3 leadspicker-report/gmail_auth.py`

Creates a draft (not sent) in the authenticated Gmail account. Subject format:
`Leadspicker Weekly — {Display Name} — w/c {week_start_date}`

### Adding a new delivery method

The report data structure is fixed and delivery-agnostic. To add a new delivery method (Slack, SMTP, Notion, etc.):

1. Create a new module, e.g. `leadspicker-report/slack_draft.py`
2. Implement the same function signature as `create_draft()` in `gmail_draft.py`:

```python
def create_draft(
    account_name,       # str — raw account key (e.g. "STARTUPGRIND")
    week_start,         # str — ISO date (e.g. "2026-03-09")
    week_end,           # str — ISO date (e.g. "2026-03-15")
    day,                # dict — daily stats (emails_sent, linkedin_connections_sent, ...)
    week,               # dict — weekly stats (same keys as day)
    inbox_total,        # int — total replies in the week
    sentiments,         # dict — sentiment label → count
    channels,           # dict — {"email": int, "linkedin": int}
    recent_replies,     # list[dict] — up to 10 recent messages with full_name, sentiment, channel, project_name
    project_breakdown=None  # list[dict] — per-project stats (name, total_sent, total_replies, reply_rate, ...)
) -> tuple[str, str]:   # returns (draft_id_or_identifier, subject_line)
```

3. In `leadspicker-report/report.py`, import and call the new module alongside or instead of `gmail_draft`:

```python
from slack_draft import create_draft
```

The `CLIENT_CONFIG` lookup and display name resolution in `gmail_draft.py` should be replicated in the new module, or extracted to a shared `client_config.py`.

---

## Key Files

| File | Purpose |
|------|---------|
| `leadspicker-report/report.py` | Main entry point — CLI flags, account loading, stats rendering |
| `leadspicker-report/gmail_draft.py` | Gmail delivery module + `CLIENT_CONFIG` (display names + emails) |
| `leadspicker-report/api.py` | `LeadsPickerClient` — all Leadspicker API calls |
| `leadspicker-report/gmail_auth.py` | One-time Gmail OAuth2 setup |
| `.env` | `LEADSPICKER_API_KEY_*_REPORT` keys + Gmail OAuth credentials |

---

## Scheduled Automation

The report runs automatically every **Monday at 8:00 AM** via a macOS LaunchAgent, creating Gmail drafts for all configured accounts.

| File | Purpose |
|------|---------|
| `/Users/fallengemini/Library/LaunchAgents/com.leadspicker.weeklyreport.plist` | LaunchAgent definition |
| `leadspicker-report/cron.log` | stdout + stderr from scheduled runs |

**Check last run:**
```bash
tail -50 /Users/fallengemini/Desktop/VSCode/leadspicker-report/cron.log
```

**Reload after editing the plist:**
```bash
launchctl unload ~/Library/LaunchAgents/com.leadspicker.weeklyreport.plist
launchctl load ~/Library/LaunchAgents/com.leadspicker.weeklyreport.plist
```

**Manage:** Enable/disable via `launchctl load`/`unload`, or edit `StartCalendarInterval` in the plist to change the schedule.

---

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `No Leadspicker API keys found in .env` | Key not in .env or wrong pattern | Check key follows `LEADSPICKER_API_KEY_<NAME>_REPORT=<key>` exactly |
| `No account matching 'X'` | Account key not in .env | Add the key to .env or check spelling |
| `ERROR fetching daily stats` | Invalid or expired API key | Get a fresh key from the client's Leadspicker account |
| Draft To address is empty | Account not in `CLIENT_CONFIG` | Add entry to `CLIENT_CONFIG` in `gmail_draft.py` |
| Gmail auth error | Missing or expired OAuth tokens | Re-run `python3 leadspicker-report/gmail_auth.py` |
| Monday drafts not appearing | LaunchAgent not loaded or failed | Check `cron.log`; reload the plist if needed |
