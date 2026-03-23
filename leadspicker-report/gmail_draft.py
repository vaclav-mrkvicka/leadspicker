"""
Gmail draft creator for Leadspicker weekly reports.
Uses stored OAuth2 credentials — no browser interaction after initial setup.
"""

import os
import base64
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import dotenv_values

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]

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

SENTIMENT_COLORS = {
    "positive":       "#1a7f37",
    "maybe":          "#0969da",
    "not_interested": "#9a6700",
    "negative":       "#cf222e",
    "out_of_office":  "#6e7781",
    "unknown":        "#6e7781",
    "bounced":        "#6e7781",
    "limit_reached":  "#6e7781",
}

# Real client names and recipient email addresses per account key
CLIENT_CONFIG = {
    "STARTUPGRIND":        {"name": "Startup Grind",         "to": "naman@startupgrind.com"},
    "INFOSHARE":           {"name": "Infoshare",              "to": "agnieszka@infoshare.pl, todd.benson@leadspicker.com"},
    "OVHNESTARTUPS":       {"name": "OVH Startups NE",       "to": "cezary.skarzynski@ovhcloud.com, todd.benson@leadspicker.com"},
    "OVHAFRICASTARTUPS":   {"name": "OVH Startups Africa",   "to": "christopher.apedo-amah@ovhcloud.com, todd.benson@leadspicker.com"},
    "MASSCHALLENGE":       {"name": "MassChallenge Switzerland", "to": "Elodie@masschallenge.org, todd.benson@leadspicker.com"},
    "OVHSESTARTUPS":       {"name": "OVH Startups SE",       "to": "ilaria.navoni@ovhcloud.com, todd.benson@leadspicker.com"},
    "OVHFRANCESTARTUPS":   {"name": "OVH Startups France",   "to": "leonard.pommereau@ovhcloud.com, todd.benson@leadspicker.com"},
    "PWCGERMANY":          {"name": "PwC Germany",            "to": "jannis.grube@pwc.com, todd.benson@leadspicker.com"},
    "OVHCEESTARTUPS":      {"name": "OVH Startups CEE",      "to": "natalia.swirska@ovhcloud.com, todd.benson@leadspicker.com"},
    "SEYFOR":              {"name": "Seyfor",                 "to": "Filip.Naplava@seyfor.com"},
    "OVHAPACSTARTUPS":     {"name": "OVH Startups APAC",     "to": "satyam.santosh@ovhcloud.com, todd.benson@leadspicker.com"},
    "WAV":                 {"name": "WhatAVenture",           "to": "ipek.hizar@whataventure.com"},
    "OVHAPACPARTNERS":     {"name": "OVH Partners APAC",     "to": "jeff.lee@ovhcloud.com, todd.benson@leadspicker.com"},
    "PWCBELGIUM":          {"name": "PwC Belgium",            "to": "kato.de.wulf@pwc.com, todd.benson@leadspicker.com"},
    "IOVOX":               {"name": "Iovox",                  "to": "sonja@iovox.com, todd.benson@leadspicker.com"},
    "ALVAO":               {"name": "Alvao",                  "to": "michal.minarovic@alvao.com, petr.hlousek@alvao.com"},
    "VIENNABUSINESS":      {"name": "Vienna Business Agency", "to": "mwolf@wirtschaftsagentur.at"},
}


def _get_gmail_service():
    env = dotenv_values(ENV_PATH)
    creds = Credentials(
        token=None,
        refresh_token=env["GMAIL_REFRESH_TOKEN"],
        client_id=env["GMAIL_CLIENT_ID"],
        client_secret=env["GMAIL_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)


def _stat_row(label, value):
    return (
        '<tr>'
        '<td style="padding:6px 12px;color:#444;">' + label + '</td>'
        '<td style="padding:6px 12px;text-align:right;font-weight:600;">' + str(value) + '</td>'
        '</tr>'
    )


def _section_header(title):
    return (
        '<tr><td colspan="2" style="padding:16px 12px 4px;font-size:11px;font-weight:700;'
        'text-transform:uppercase;letter-spacing:0.08em;color:#888;">' + title + '</td></tr>'
    )


def build_html(account_name, week_start, week_end, day, week, inbox_total,
               sentiments, channels, recent_replies, project_breakdown=None):
    week_label = week_start + ' \u2013 ' + week_end
    total_sent = week.get("total_messages_sent", 0)
    reply_rate = round(inbox_total / total_sent * 100, 1) if total_sent else 0

    # ── Rate calculations ────────────────────────────────────────────
    email_sent       = week.get("emails_sent", 0)
    li_conn_sent     = week.get("linkedin_connections_sent", 0)
    li_conn_accepted = week.get("linkedin_connections_accepted", 0)
    li_msg_sent      = week.get("linkedin_messages_sent", 0)
    email_reply_rate = round(channels.get("email", 0)    / email_sent       * 100, 1) if email_sent       else 0
    li_reply_rate    = round(channels.get("linkedin", 0) / li_msg_sent      * 100, 1) if li_msg_sent      else 0
    li_accept_rate   = round(li_conn_accepted             / li_conn_sent     * 100, 1) if li_conn_sent     else 0

    # ── Activity table rows ──────────────────────────────────────────
    activity_rows = (
        _section_header("Emails")
        + _stat_row("Sent",       email_sent)
        + _stat_row("Replies",    channels.get("email", 0))
        + _stat_row("Reply rate", str(email_reply_rate) + "%")
        + _section_header("LinkedIn")
        + _stat_row("Connection requests sent", li_conn_sent)
        + _stat_row("Connections accepted",     li_conn_accepted)
        + _stat_row("Acceptance rate",          str(li_accept_rate) + "%")
        + _stat_row("Messages sent",            li_msg_sent)
        + _stat_row("Message replies",          channels.get("linkedin", 0))
        + _stat_row("Reply rate",               str(li_reply_rate) + "%")
    )
    if week.get("linkedin_inmails_sent", 0):
        activity_rows += _stat_row("InMails sent", week.get("linkedin_inmails_sent", "—"))

    activity_rows += (
        _section_header("Totals")
        + _stat_row("Total outreach sent",   total_sent)
        + _stat_row("Total replies (inbox)", inbox_total)
        + _stat_row("Response rate",         str(reply_rate) + "%")
    )

    # ── Project breakdown section ────────────────────────────────────
    project_section = ""
    if project_breakdown:
        rows = ""
        for p in project_breakdown:
            rate_color = "#1a7f37" if p["reply_rate"] >= 5 else ("#9a6700" if p["reply_rate"] >= 2 else "#6e7781")
            rows += (
                '<tr style="border-bottom:1px solid #f0f0f0;">'
                '<td style="padding:6px 12px;font-weight:500;">' + p["name"] + '</td>'
                '<td style="padding:6px 12px;text-align:right;">' + str(p["total_sent"]) + '</td>'
                '<td style="padding:6px 12px;text-align:right;">' + str(p["emails_sent"]) + '</td>'
                '<td style="padding:6px 12px;text-align:right;">' + str(p["li_connections"]) + '</td>'
                '<td style="padding:6px 12px;text-align:right;">' + str(p["li_accepted"]) + '</td>'
                '<td style="padding:6px 12px;text-align:right;">' + str(p["li_messages"]) + '</td>'
                '<td style="padding:6px 12px;text-align:right;">' + str(p["total_replies"]) + '</td>'
                '<td style="padding:6px 12px;text-align:right;font-weight:600;color:' + rate_color + ';">' + str(p["reply_rate"]) + '%</td>'
                '</tr>'
            )
        project_section = (
            '<h3 style="font-size:14px;font-weight:700;margin:0 0 8px;text-transform:uppercase;'
            'letter-spacing:0.06em;color:#888;">By Project</h3>'
            '<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;'
            'border:1px solid #e0e0e0;border-radius:8px;overflow:hidden;margin-bottom:24px;font-size:13px;">'
            '<thead><tr style="background:#f6f8fa;">'
            '<th style="padding:6px 12px;text-align:left;color:#666;">Project</th>'
            '<th style="padding:6px 12px;text-align:right;color:#666;">Sent</th>'
            '<th style="padding:6px 12px;text-align:right;color:#666;">Emails</th>'
            '<th style="padding:6px 12px;text-align:right;color:#666;">LI Conn</th>'
            '<th style="padding:6px 12px;text-align:right;color:#666;">Accepted</th>'
            '<th style="padding:6px 12px;text-align:right;color:#666;">LI Msg</th>'
            '<th style="padding:6px 12px;text-align:right;color:#666;">Replies</th>'
            '<th style="padding:6px 12px;text-align:right;color:#666;">Rate</th>'
            '</tr></thead>'
            '<tbody>' + rows + '</tbody>'
            '</table>'
        )

    # ── Sentiment section ────────────────────────────────────────────
    sentiment_section = ""
    if sentiments:
        rows = ""
        for key, label in SENTIMENT_LABELS.items():
            count = sentiments.get(key, 0)
            if not count:
                continue
            pct   = round(count / inbox_total * 100) if inbox_total else 0
            color = SENTIMENT_COLORS.get(key, "#6e7781")
            bar_w = max(4, min(pct * 2, 200))
            rows += (
                '<tr>'
                '<td style="padding:5px 12px;color:#444;">' + label + '</td>'
                '<td style="padding:5px 12px;text-align:right;font-weight:600;">' + str(count) + '</td>'
                '<td style="padding:5px 12px;">'
                '<div style="display:inline-block;width:' + str(bar_w) + 'px;height:10px;'
                'background:' + color + ';border-radius:3px;vertical-align:middle;"></div>'
                '<span style="font-size:11px;color:#888;margin-left:6px;">' + str(pct) + '%</span>'
                '</td>'
                '</tr>'
            )
        sentiment_section = (
            '<h3 style="font-size:14px;font-weight:700;margin:0 0 8px;text-transform:uppercase;'
            'letter-spacing:0.06em;color:#888;">Inbox Sentiment &nbsp;'
            '<span style="font-weight:400;font-size:12px;color:#aaa;">' + week_label + '</span></h3>'
            '<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;'
            'border:1px solid #e0e0e0;border-radius:8px;overflow:hidden;margin-bottom:24px;">'
            '<tbody>' + rows + '</tbody>'
            '</table>'
        )

    # ── Recent replies section ───────────────────────────────────────
    replies_section = ""
    if recent_replies:
        rows = ""
        for msg in recent_replies:
            sentiment_key = msg.get("sentiment") or "unknown"
            sentiment_lbl = SENTIMENT_LABELS.get(sentiment_key, sentiment_key)
            color = SENTIMENT_COLORS.get(sentiment_key, "#6e7781")
            rows += (
                '<tr style="border-bottom:1px solid #f0f0f0;">'
                '<td style="padding:6px 12px;color:#444;white-space:nowrap;">' + (msg.get("received") or "")[:10] + '</td>'
                '<td style="padding:6px 12px;font-weight:500;">' + (msg.get("full_name") or "—") + '</td>'
                '<td style="padding:6px 12px;color:#666;">' + msg.get("channel", "?") + '</td>'
                '<td style="padding:6px 12px;"><span style="color:' + color + ';font-weight:600;">' + sentiment_lbl + '</span></td>'
                '<td style="padding:6px 12px;color:#888;font-size:12px;">' + msg.get("project_name", "") + '</td>'
                '</tr>'
            )
        replies_section = (
            '<h3 style="font-size:14px;font-weight:700;margin:0 0 8px;text-transform:uppercase;'
            'letter-spacing:0.06em;color:#888;">Recent Replies</h3>'
            '<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;'
            'border:1px solid #e0e0e0;border-radius:8px;overflow:hidden;margin-bottom:24px;font-size:13px;">'
            '<thead><tr style="background:#f6f8fa;">'
            '<th style="padding:6px 12px;text-align:left;color:#666;">Date</th>'
            '<th style="padding:6px 12px;text-align:left;color:#666;">Name</th>'
            '<th style="padding:6px 12px;text-align:left;color:#666;">Channel</th>'
            '<th style="padding:6px 12px;text-align:left;color:#666;">Sentiment</th>'
            '<th style="padding:6px 12px;text-align:left;color:#666;">Project</th>'
            '</tr></thead>'
            '<tbody>' + rows + '</tbody>'
            '</table>'
        )

    # ── Assemble ─────────────────────────────────────────────────────
    return (
        '<!DOCTYPE html><html><body style="font-family:-apple-system,BlinkMacSystemFont,'
        '\'Segoe UI\',sans-serif;color:#1a1a1a;max-width:720px;margin:0 auto;padding:24px;">'

        '<h2 style="margin:0 0 4px;font-size:20px;">Leadspicker Weekly Report</h2>'
        '<p style="margin:0 0 24px;color:#666;font-size:14px;">'
        '<strong>' + account_name + '</strong> &nbsp;&middot;&nbsp; ' + week_label + '</p>'

        '<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;'
        'border:1px solid #e0e0e0;border-radius:8px;overflow:hidden;margin-bottom:24px;">'
        '<thead><tr style="background:#f6f8fa;">'
        '<th style="padding:8px 12px;text-align:left;font-size:12px;color:#666;">Metric</th>'
        '<th style="padding:8px 12px;text-align:right;font-size:12px;color:#666;">Week</th>'
        '</tr></thead>'
        '<tbody>' + activity_rows + '</tbody>'
        '</table>'

        + project_section
        + sentiment_section
        + replies_section

        + '<p style="font-size:11px;color:#aaa;margin-top:32px;">'
        'Generated automatically by Leadspicker Report &nbsp;&middot;&nbsp; '
        + str(datetime.date.today()) + '</p>'
        '</body></html>'
    )


def create_draft(account_name, week_start, week_end, day, week, inbox_total,
                 sentiments, channels, recent_replies, project_breakdown=None):
    service = _get_gmail_service()

    config     = CLIENT_CONFIG.get(account_name, {})
    real_name  = config.get("name", account_name)
    to_address = config.get("to", "")

    wc_label = datetime.datetime.strptime(week_start, "%Y-%m-%d").strftime("%-d %b")
    subject  = f"Leadspicker Weekly — {real_name} — w/c {wc_label}"

    html_body = build_html(real_name, week_start, week_end, day, week,
                           inbox_total, sentiments, channels, recent_replies, project_breakdown)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["To"]      = to_address
    msg.attach(MIMEText(html_body, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = service.users().drafts().create(
        userId="me",
        body={"message": {"raw": raw}}
    ).execute()

    return draft["id"], subject
