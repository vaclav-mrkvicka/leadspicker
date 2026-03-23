"""
Leadspicker API client.
Docs: https://app.leadspicker.com/app/sb/api/openapi.json
Auth: X-Api-Key header
"""

import requests

BASE_URL = "https://app.leadspicker.com/app/sb/api"
REQUEST_TIMEOUT = 30  # seconds per request


class LeadsPickerClient:
    def __init__(self, api_key: str, account_name: str = "default"):
        self.api_key = api_key
        self.account_name = account_name
        self.session = requests.Session()
        self.session.headers.update({
            "X-Api-Key": api_key,
            "Accept": "application/json",
        })

    def _get(self, path: str, params: dict = None) -> dict:
        url = f"{BASE_URL}{path}"
        r = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.json()

    def get_dashboard_stats(self, start_date: str, end_date: str) -> dict:
        """Aggregated stats for a date range (YYYY-MM-DD)."""
        return self._get("/dashboard/stats", {
            "custom_start_date": start_date,
            "custom_end_date": end_date,
            "add_chart_data": False,
        })

    def get_projects(self) -> list:
        """All projects for this account."""
        return self._get("/projects")

    def get_inbound_messages(self, projects: list[int] = None, sentiment: str = None) -> dict:
        """Replies inbox. Optionally filter by sentiment to get accurate per-sentiment counts."""
        params = {"inbox_sort": "latest_received_first"}
        if projects:
            params["projects"] = projects
        if sentiment:
            params["sentiment"] = sentiment
        return self._get("/inbound-messages", params)

    def get_inbox_counts(self, start_date: str, end_date: str) -> dict:
        """
        Single pagination pass over the inbox for the date range.
        Returns sentiment counts, channel counts, and total — all from the same source.
        """
        sentiments = {}
        channels   = {"email": 0, "linkedin": 0}
        page = 1
        while True:
            data = self._get("/inbound-messages", {
                "inbox_sort": "latest_received_first",
                "limit": 100,
                "page": page,
            })
            items = data.get("items", [])
            if not items:
                break
            past_window = False
            for msg in items:
                received = (msg.get("received") or "")[:10]
                if received > end_date:
                    continue
                if received < start_date:
                    past_window = True
                    break
                sentiment = msg.get("sentiment") or "unknown"
                sentiments[sentiment] = sentiments.get(sentiment, 0) + 1
                if msg.get("linkedin_messages"):
                    channels["linkedin"] += 1
                else:
                    channels["email"] += 1
            if past_window:
                break
            page += 1
        total = sum(sentiments.values())
        return {"sentiments": sentiments, "channels": channels, "total": total}

    def get_sentiment_counts(self, start_date: str = None, end_date: str = None) -> tuple[dict, int]:
        """Kept for backwards compatibility — use get_inbox_counts for new code."""
        if start_date and end_date:
            result = self.get_inbox_counts(start_date, end_date)
            return result["sentiments"], result["total"]
        sentiments = ["positive", "maybe", "not_interested", "negative",
                      "out_of_office", "unknown", "bounced", "limit_reached"]
        total = self.get_inbound_messages().get("count", 0)
        counts = {}
        for s in sentiments:
            r = self.get_inbound_messages(sentiment=s)
            counts[s] = r.get("count", 0)
        return counts, total

    def get_projects(self, limit: int = 30) -> list:
        """Projects ordered by last active date."""
        data = self._get("/projects", {"order_by_field": "last_active", "order_direction": "desc", "limit": limit})
        return data if isinstance(data, list) else data.get("results", data.get("items", []))

    def get_project_breakdown(self, start_date: str, end_date: str) -> list[dict]:
        """
        Returns per-project stats for projects active in the date range.
        Fetches all projects then filters to those with activity — one API call per project.
        """
        projects = self.get_projects(limit=100)
        breakdown = []
        for p in projects:
            pid  = p.get("id")
            name = p.get("name", "Unknown")
            r = self._get("/dashboard/stats", {
                "custom_start_date": start_date,
                "custom_end_date":   end_date,
                "add_chart_data":    False,
                "projects":          pid,
            })
            total_sent = r.get("total_messages_sent", 0)
            if not total_sent:
                continue   # skip projects with no activity in this period
            breakdown.append({
                "name":           name,
                "emails_sent":    r.get("emails_sent", 0),
                "li_connections": r.get("linkedin_connections_sent", 0),
                "li_accepted":    r.get("linkedin_connections_accepted", 0),
                "li_messages":    r.get("linkedin_messages_sent", 0),
                "total_sent":     total_sent,
                "total_replies":  r.get("total_replies", 0),
                "reply_rate":     r.get("total_reply_rate", 0.0),
            })
        return sorted(breakdown, key=lambda x: x["total_sent"], reverse=True)

    def get_sequence_stats(self, project_id: int, start_date: str = None, end_date: str = None) -> dict:
        """Per-project sequence stats."""
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return self._get(f"/projects/{project_id}/sequence-stats", params)
