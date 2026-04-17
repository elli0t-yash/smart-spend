import base64

import requests

from categorizer import categorize
from gmail_parser import parse_email

BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
QUERY = (
    "(debited OR credited OR \"transaction alert\" OR \"spent on\" OR \"payment of\") "
    "newer_than:60d"
)
MAX_RESULTS = 50


def fetch_transactions(access_token: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {access_token}"}

    resp = requests.get(
        f"{BASE}/messages",
        headers=headers,
        params={"q": QUERY, "maxResults": MAX_RESULTS},
        timeout=15,
    )
    resp.raise_for_status()

    message_ids = [m["id"] for m in resp.json().get("messages", [])]

    transactions = []
    for msg_id in message_ids:
        try:
            detail = requests.get(
                f"{BASE}/messages/{msg_id}",
                headers=headers,
                params={"format": "full"},
                timeout=10,
            ).json()
            txn = _process(detail)
            if txn:
                transactions.append(txn)
        except Exception:
            continue

    return transactions


def _process(msg: dict) -> dict | None:
    payload = msg.get("payload", {})
    headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

    body = _extract_body(payload) or msg.get("snippet", "")
    snippet = msg.get("snippet", "")
    date_header = headers.get("Date", "")

    txn = parse_email(body, snippet, date_header)
    if not txn:
        return None

    txn["category"] = categorize(txn["merchant"], txn["narration"])
    return txn


def _extract_body(payload: dict) -> str:
    mime = payload.get("mimeType", "")
    if mime == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")

    for part in payload.get("parts", []):
        text = _extract_body(part)
        if text:
            return text

    return ""
