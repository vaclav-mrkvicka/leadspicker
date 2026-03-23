"""
Leadspicker Daily Report
========================
Prints a daily + weekly activity summary across one or more accounts.

Usage:
  python3 report.py                            # today's report (terminal)
  python3 report.py --from 2026-03-09 --to 2026-03-15  # specific week
  python3 report.py --account startupgrind     # single account
  python3 report.py --draft                    # also create Gmail drafts

Account setup in .env:
  LEADSPICKER_API_KEY_<NAME>_REPORT=<key>

Run from repo root or leadspicker-report/:
  python3 leadspicker-report/report.py
"""

import sys
import os
import argparse
from datetime import date, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(__file__))
from api import LeadsPickerClient
from dotenv import dotenv_values

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
CET = ZoneInfo("Europe/Prague")

# ── Sentiment display config ───────────────────────────────────────────────
SENTIMENT_LABELS = {
    "positive":       "Positive",
    "maybe":          "Maybe / Interested",
    "not_interested": "Not interested",
    "negative":       "Negative",
    "out_of_office":  "Out of office",
    "unknown":        "Unknown",
    "bounced":        "Bounced",
    "limit_reached":  "Limit reached",
}


# ── Env loading ────────────────────────────────────────────────────────────
def load_accounts() -> list[LeadsPickerClient]:
    """
    Reads .env and returns one client per reporting account.
    Keys must follow the pattern: LEADSPICKER_API_KEY_<NAME>_REPORT=<key>
    Account name is derived from <NAME> (e.g. STARTUPGRIND).
    """
    env = dotenv_values(ENV_PATH)
    clients = []

    for key, value in env.items():
        if key.startswith("LEADSPICKER_API_KEY_") and key.endswith("_REPORT"):
            name = key[len("LEADSPICKER_API_KEY_"):-len("_REPORT")]
            clients.append(LeadsPickerClient(value, account_name=name))

    return clients


# ── Stats extraction helpers ───────────────────────────────────────────────
def extract_stat(data: dict, *keys, default=0):
    """Safely dig into nested dicts."""
    for k in keys:
        if isinstance(data, dict):
            data = data.get(k, default)
        else:
            return default
    return data if data is not None else default


def parse_dashboard(stats: dict) -> dict:
    """Extract the metrics we care about from dashboard/stats response."""
    return {
        "emails_sent":                  extract_stat(stats, "emails_sent"),
        "emails_replied":               extract_stat(stats, "emails_replied"),
        "linkedin_connections_sent":    extract_stat(stats, "linkedin_connections_sent"),
        "linkedin_connections_accepted": extract_stat(stats, "linkedin_connections_accepted"),
        "linkedin_messages_sent":       extract_stat(stats, "linkedin_messages_sent"),
        "linkedin_messages_replied":    extract_stat(stats, "linkedin_messages_replied"),
        "linkedin_inmails_sent":        extract_stat(stats, "linkedin_inmails_sent"),
        "linkedin_inmails_replied":     extract_stat(stats, "linkedin_inmails_replied"),
        "total_replies":                extract_stat(stats, "total_replies"),
        "total_messages_sent":          extract_stat(stats, "total_messages_sent"),
        "total_reply_rate":             extract_stat(stats, "total_reply_rate"),
    }


def parse_sentiments(inbox: dict) -> tuple[dict, int]:
    """Count sentiments from first page of inbox (approximate — use client.get_sentiment_counts for accuracy)."""
    counts = {k: 0 for k in SENTIMENT_LABELS}
    items = inbox.get("items", [])
    for msg in items:
        sentiment = msg.get("sentiment") or "unknown"
        counts[sentiment] = counts.get(sentiment, 0) + 1
    return counts, inbox.get("count", len(items))


def _channel(msg: dict) -> str:
    if msg.get("linkedin_messages"):
        return "LinkedIn"
    if msg.get("from_email") or msg.get("to_email"):
        return "Email"
    history = msg.get("history", [])
    if history:
        return history[0].get("step_type", "?").capitalize()
    return "?"


def _recent_cutoff() -> str:
    """ISO date 14 days ago from today."""
    return (date.today() - timedelta(days=14)).isoformat()


def filter_recent_items(items: list, limit: int = 10) -> list:
    """Return up to `limit` items received within the last 14 days."""
    cutoff = _recent_cutoff()
    return [m for m in items if (m.get("received") or "")[:10] >= cutoff][:limit]


def format_recent_replies(inbox: dict) -> list[str]:
    """Returns terminal-formatted lines for replies in the last 14 days (max 10)."""
    items = filter_recent_items(inbox.get("items", []))
    lines = []
    for msg in items:
        name = (msg.get("full_name") or "Unknown")[:28]
        sentiment = msg.get("sentiment") or "unknown"
        channel = _channel(msg)
        received = (msg.get("received") or "")[:10]
        project = (msg.get("project_name") or "")[:30]
        label = SENTIMENT_LABELS.get(sentiment, sentiment)
        lines.append(f"  {received}  {name:<28}  {channel:<9}  {label:<22}  {project}")
    return lines


# ── Report rendering ───────────────────────────────────────────────────────
def render_account_report(client: LeadsPickerClient, today_str: str, week_start_str: str,
                          debug: bool = False, date_filtered: bool = False) -> dict:
    print(f"\n{'═' * 60}")
    print(f"  Account: {client.account_name.upper()}")
    print(f"{'═' * 60}")

    # --- Daily stats ---
    try:
        day_raw = client.get_dashboard_stats(today_str, today_str)
        if debug:
            print(f"\n[DEBUG] dashboard/stats today: {day_raw}\n")
        day = parse_dashboard(day_raw)
    except Exception as e:
        print(f"  ERROR fetching daily stats: {e}")
        day = {}

    # --- Weekly stats ---
    try:
        week_raw = client.get_dashboard_stats(week_start_str, today_str)
        if debug:
            print(f"\n[DEBUG] dashboard/stats week: {week_raw}\n")
        week = parse_dashboard(week_raw)
    except Exception as e:
        print(f"  ERROR fetching weekly stats: {e}")
        week = {}

    # --- Per-project breakdown ---
    project_breakdown = []
    try:
        project_breakdown = client.get_project_breakdown(week_start_str, today_str)
    except Exception as e:
        print(f"  ERROR fetching project breakdown: {e}")

    # --- Inbox / replies (always date-scoped) ---
    inbox_total = 0
    sentiments  = {}
    channels    = {"email": 0, "linkedin": 0}
    recent      = []
    recent_raw  = []
    try:
        inbox_raw = client.get_inbound_messages()
        if debug:
            items_sample = inbox_raw.get("items", [])
            print(f"\n[DEBUG] inbox count={inbox_raw.get('count')} | first keys: {list(items_sample[0].keys()) if items_sample else 'empty'}\n")
        inbox_counts = client.get_inbox_counts(week_start_str, today_str)
        sentiments   = inbox_counts["sentiments"]
        inbox_total  = inbox_counts["total"]
        channels     = inbox_counts["channels"]
        recent = format_recent_replies(inbox_raw)
        recent_raw = [{**m, "channel": _channel(m)} for m in filter_recent_items(inbox_raw.get("items", []))]
    except Exception as e:
        print(f"  ERROR fetching inbox: {e}")

    # --- Render ---
    if date_filtered:
        # Historical range: single value column (week total only)
        def row(label, _today_val, week_val):
            print(f"  {label:<36}  {str(week_val):>6}")
    else:
        # Live/daily view: show today vs week
        def row(label, today_val, week_val):
            print(f"  {label:<36}  Today: {str(today_val):>6}   Week: {str(week_val):>6}")

    def wrow(label, val):
        print(f"  {label:<36}  {str(val)}")

    email_sent        = week.get("emails_sent", 0)
    li_conn_sent      = week.get("linkedin_connections_sent", 0)
    li_conn_accepted  = week.get("linkedin_connections_accepted", 0)
    li_msg_sent       = week.get("linkedin_messages_sent", 0)
    email_reply_rate  = round(channels["email"]   / email_sent   * 100, 1) if email_sent   else 0
    li_reply_rate     = round(channels["linkedin"] / li_msg_sent  * 100, 1) if li_msg_sent  else 0
    li_accept_rate    = round(li_conn_accepted      / li_conn_sent * 100, 1) if li_conn_sent else 0

    print()
    print("  EMAILS")
    row("Sent",        day.get("emails_sent", "—"), email_sent)
    row("Replies",     "—",                         channels["email"])
    row("Reply rate",  "—",                         f"{email_reply_rate}%")

    print()
    print("  LINKEDIN")
    row("Connection requests sent",  day.get("linkedin_connections_sent", "—"),    li_conn_sent)
    row("Connections accepted",      day.get("linkedin_connections_accepted", "—"), li_conn_accepted)
    row("Acceptance rate",           "—",                                            f"{li_accept_rate}%")
    row("Messages sent",             day.get("linkedin_messages_sent", "—"),        li_msg_sent)
    row("Message replies",           "—",                                            channels["linkedin"])
    row("Reply rate",                "—",                                            f"{li_reply_rate}%")
    if week.get("linkedin_inmails_sent", 0):
        row("InMails sent",          day.get("linkedin_inmails_sent", "—"),         week.get("linkedin_inmails_sent", "—"))

    # Compute totals from dashboard (sent) + inbox (replies)
    total_sent    = week.get("total_messages_sent", 0)
    reply_rate    = round(inbox_total / total_sent * 100, 1) if total_sent else 0

    print()
    print("  TOTALS")
    wrow("Total outreach sent",  total_sent)
    wrow("Total replies (inbox)", inbox_total)
    wrow("Response rate",        f"{reply_rate}%")

    if sentiments:
        print()
        print(f"  INBOX SENTIMENT  ({week_start_str} to {today_str})")
        for key, label in SENTIMENT_LABELS.items():
            count = sentiments.get(key, 0)
            if count:
                pct = round(count / inbox_total * 100) if inbox_total else 0
                bar = "█" * min(count // 3 + 1, 24)
                print(f"    {label:<24}  {count:>4}  ({pct:>2}%)  {bar}")

    if project_breakdown:
        print()
        print("  BY PROJECT")
        print(f"  {'Project':<34}  {'Sent':>5}  {'Replies':>7}  {'Rate':>5}  {'Email':>5}  {'LI Conn':>7}  {'LI Msg':>6}")
        print(f"  {'-'*34}  {'-'*5}  {'-'*7}  {'-'*5}  {'-'*5}  {'-'*7}  {'-'*6}")
        for p in project_breakdown:
            print(f"  {p['name'][:34]:<34}  {p['total_sent']:>5}  {p['total_replies']:>7}  {p['reply_rate']:>4.1f}%  {p['emails_sent']:>5}  {p['li_connections']:>7}  {p['li_messages']:>6}")

    if recent:
        print()
        print("  RECENT REPLIES (last 14 days, max 10)")
        print(f"  {'Date':<10}  {'Name':<28}  {'Channel':<9}  {'Sentiment':<22}  Project")
        print(f"  {'-'*9}  {'-'*28}  {'-'*9}  {'-'*22}  {'-'*25}")
        for line in recent:
            print(line)

    return {
        "day": day, "week": week,
        "inbox_total": inbox_total, "sentiments": sentiments,
        "channels": channels,
        "recent_raw": recent_raw,
        "project_breakdown": project_breakdown,
    }


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Leadspicker daily activity report")
    parser.add_argument("--date", default=None, help="Report date / week-end YYYY-MM-DD (default: today)")
    parser.add_argument("--from", dest="from_date", default=None, metavar="YYYY-MM-DD", help="Explicit week start date")
    parser.add_argument("--to", dest="to_date", default=None, metavar="YYYY-MM-DD", help="Explicit week end date")
    parser.add_argument("--account", default=None, help="Run for a single account (partial name match, case-insensitive)")
    parser.add_argument("--draft", action="store_true", help="Create a Gmail draft for each account")
    parser.add_argument("--debug", action="store_true", help="Print raw API responses")
    args = parser.parse_args()

    if args.from_date and args.to_date:
        week_start_str = args.from_date
        today_str      = args.to_date
        date_filtered  = True
    else:
        report_date = date.fromisoformat(args.date) if args.date else date.today()
        if report_date.weekday() == 0 and not args.date:
            # Monday default: report on the previous completed Mon–Sun week
            week_end   = report_date - timedelta(days=1)   # last Sunday
            week_start = week_end - timedelta(days=6)       # previous Monday
        else:
            # Explicit date or mid-week manual run: Mon–that date
            week_start = report_date - timedelta(days=report_date.weekday())
            week_end   = report_date
        today_str      = week_end.isoformat()
        week_start_str = week_start.isoformat()
        date_filtered  = True  # always show weekly totals, no "Today" column

    clients = load_accounts()
    if not clients:
        print("No Leadspicker API keys found in .env.")
        print("Add LEADSPICKER_API_KEY_<NAME>_REPORT=<key> entries.")
        sys.exit(1)

    if args.account:
        needle = args.account.lower()
        clients = [c for c in clients if needle in c.account_name.lower()]
        if not clients:
            print(f"No account matching '{args.account}'. Available accounts:")
            for c in load_accounts():
                print(f"  {c.account_name}")
            sys.exit(1)

    w = 58  # inner width between ║ chars
    bar = "═" * w
    line1 = f"  LEADSPICKER REPORT  --  {today_str}"
    line2 = f"  Week: {week_start_str} to {today_str}"
    print()
    print(f"╔{bar}╗")
    print(f"║{line1:<{w}}║")
    print(f"║{line2:<{w}}║")
    print(f"╚{bar}╝")

    if args.draft:
        from gmail_draft import create_draft

    for client in clients:
        data = render_account_report(client, today_str, week_start_str,
                                     debug=args.debug, date_filtered=date_filtered)
        if args.draft:
            try:
                draft_id, subject = create_draft(
                    account_name      = client.account_name,
                    week_start        = week_start_str,
                    week_end          = today_str,
                    day               = data["day"],
                    week              = data["week"],
                    inbox_total       = data["inbox_total"],
                    sentiments        = data["sentiments"],
                    channels          = data["channels"],
                    recent_replies    = data["recent_raw"],
                    project_breakdown = data["project_breakdown"],
                )
                print(f"\n  Gmail draft created: {subject}")
            except Exception as e:
                print(f"\n  ERROR creating Gmail draft: {e}")

    print(f"\n{'─' * 60}")
    print(f"  {len(clients)} account(s) reported.")
    print()


if __name__ == "__main__":
    main()
