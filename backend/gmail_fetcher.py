import base64
import re

import requests

from categorizer import categorize
from gmail_parser import parse_email

BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

BANK_QUERY = (
    "(debited OR credited OR \"transaction alert\" OR \"spent on\" OR \"payment of\") "
    "newer_than:60d"
)
ECOMMERCE_QUERY = (
    "from:(swiggy.in OR zomato.com OR amazon.in OR flipkart.com "
    "OR netflix.com OR spotify.com) newer_than:60d"
)
MAX_RESULTS = 100


def fetch_transactions(access_token: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {access_token}"}

    message_ids: set[str] = set()
    for query in [BANK_QUERY, ECOMMERCE_QUERY]:
        resp = requests.get(
            f"{BASE}/messages",
            headers=headers,
            params={"q": query, "maxResults": MAX_RESULTS},
            timeout=15,
        )
        resp.raise_for_status()
        for m in resp.json().get("messages", []):
            message_ids.add(m["id"])

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
    headers_dict = {h["name"]: h["value"] for h in payload.get("headers", [])}

    body = _extract_body(payload) or msg.get("snippet", "")
    snippet = msg.get("snippet", "")
    date_header = headers_dict.get("Date", "")
    from_header = headers_dict.get("From", "")

    txn = parse_email(body, snippet, date_header, from_header)
    if not txn:
        return None

    txn["category"] = categorize(txn["merchant"], txn["narration"])
    return txn


def _extract_body(payload: dict) -> str:
    # Prefer plain text; fall back to HTML (stripped)
    return _find_body(payload, "text/plain") or _find_body(payload, "text/html")


def _find_body(payload: dict, target_mime: str) -> str:
    mime = payload.get("mimeType", "")

    if mime == target_mime:
        data = payload.get("body", {}).get("data", "")
        if data:
            raw = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")
            return raw if target_mime == "text/plain" else _strip_html(raw)

    for part in payload.get("parts", []):
        text = _find_body(part, target_mime)
        if text:
            return text

    return ""


def _strip_html(html: str) -> str:
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.S | re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    html = (
        html.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&#39;", "'")
        .replace("&quot;", '"')
    )
    return re.sub(r"\s+", " ", html).strip()
