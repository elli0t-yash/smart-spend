import re
from datetime import datetime
from email.utils import parsedate_to_datetime


def parse_email(
    body: str,
    snippet: str,
    date_header: str,
    from_header: str = "",
) -> dict | None:
    text = (body or snippet or "").replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()

    date = _parse_date(date_header)
    from_lower = from_header.lower()

    result = None

    # ── Sender-based routing (e-commerce / subscriptions) ──────────────────────
    if "swiggy" in from_lower:
        result = _swiggy(text)
    elif "zomato" in from_lower:
        result = _zomato(text)
    elif "amazon" in from_lower:
        result = _amazon(text)
    elif "flipkart" in from_lower:
        result = _flipkart(text)
    elif "netflix" in from_lower or "spotify" in from_lower:
        result = _subscription(text, from_lower)

    # ── Fall through to bank parsers ───────────────────────────────────────────
    if result is None:
        for parser in [_hdfc, _icici, _axis, _sbi, _kotak, _generic]:
            result = parser(text)
            if result:
                result["email_type"] = "bank"
                result.setdefault("items", [])
                break

    if result:
        result["date"] = date
        result["narration"] = text[:150]

    return result


# ── E-commerce parsers ─────────────────────────────────────────────────────────

def _swiggy(text: str) -> dict | None:
    m = re.search(
        r"(?:order total|total amount|grand total|amount paid|total)[:\s]*[₹Rs\.]*\s*([\d,]+\.?\d*)",
        text, re.I,
    )
    if not m:
        m = re.search(r"₹\s*([\d,]+\.?\d*)", text)
    if not m:
        return None
    amount = _safe_amount(m.group(1))
    if amount is None:
        return None
    return {
        "amount": amount,
        "type": "debit",
        "merchant": "Swiggy",
        "email_type": "ecommerce",
        "items": _extract_food_items(text),
    }


def _zomato(text: str) -> dict | None:
    m = re.search(
        r"(?:order total|total|bill amount|amount)[:\s]*[₹Rs\.]*\s*([\d,]+\.?\d*)",
        text, re.I,
    )
    if not m:
        m = re.search(r"₹\s*([\d,]+\.?\d*)", text)
    if not m:
        return None
    amount = _safe_amount(m.group(1))
    if amount is None:
        return None
    return {
        "amount": amount,
        "type": "debit",
        "merchant": "Zomato",
        "email_type": "ecommerce",
        "items": _extract_food_items(text),
    }


def _amazon(text: str) -> dict | None:
    m = re.search(
        r"(?:order total|total amount|grand total|amount charged)[:\s]*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d*)",
        text, re.I,
    )
    if not m:
        return None
    amount = _safe_amount(m.group(1))
    if amount is None:
        return None
    return {
        "amount": amount,
        "type": "debit",
        "merchant": "Amazon",
        "email_type": "ecommerce",
        "items": [],
    }


def _flipkart(text: str) -> dict | None:
    m = re.search(
        r"(?:order total|total amount|you paid|amount)[:\s]*[₹Rs\.]*\s*([\d,]+\.?\d*)",
        text, re.I,
    )
    if not m:
        m = re.search(r"₹\s*([\d,]+\.?\d*)", text)
    if not m:
        return None
    amount = _safe_amount(m.group(1))
    if amount is None:
        return None
    return {
        "amount": amount,
        "type": "debit",
        "merchant": "Flipkart",
        "email_type": "ecommerce",
        "items": [],
    }


def _subscription(text: str, from_lower: str) -> dict | None:
    m = re.search(r"(?:INR|Rs\.?|₹)\s*([\d,]+\.?\d*)", text, re.I)
    if not m:
        return None
    amount = _safe_amount(m.group(1))
    if amount is None:
        return None

    if "netflix" in from_lower:
        merchant = "Netflix"
    elif "spotify" in from_lower:
        merchant = "Spotify"
    else:
        merchant = "Subscription"

    return {
        "amount": amount,
        "type": "debit",
        "merchant": merchant,
        "email_type": "subscription",
        "items": [],
        "frequency": "monthly",
    }


# ── Bank-specific parsers ──────────────────────────────────────────────────────

def _hdfc(text: str) -> dict | None:
    m = re.search(r"Rs\.?\s*([\d,]+\.?\d*)\s+(?:has been\s+)?(debited|credited)", text, re.I)
    if not m:
        return None
    return _build(m.group(1), m.group(2), _merchant_after(text, m.end()))


def _icici(text: str) -> dict | None:
    m = re.search(
        r"(?:debited|credited)\s+for\s+(?:Rs\.?|INR)\s*([\d,]+\.?\d*)", text, re.I
    )
    if not m:
        m = re.search(
            r"(?:Rs\.?|INR)\s*([\d,]+\.?\d*)\s+(?:has been\s+)?(debited|credited)", text, re.I
        )
    if not m:
        return None
    txn_type = "credit" if re.search(r"credit", text[: m.start() + 30], re.I) else "debit"
    return _build(m.group(1), txn_type, _merchant_after(text, m.end()))


def _axis(text: str) -> dict | None:
    m = re.search(r"INR\s*([\d,]+\.?\d*)\s+has been\s+(debited|credited)", text, re.I)
    if not m:
        return None
    return _build(m.group(1), m.group(2), _merchant_after(text, m.end()))


def _sbi(text: str) -> dict | None:
    m = re.search(r"(?:debited|credited)\s+by\s+Rs\.?\s*([\d,]+\.?\d*)", text, re.I)
    if not m:
        return None
    txn_type = "credit" if "credited" in m.group(0).lower() else "debit"
    return _build(m.group(1), txn_type, _merchant_after(text, m.end()))


def _kotak(text: str) -> dict | None:
    m = re.search(r"INR\s*([\d,]+\.?\d*)\s+(debited|credited)", text, re.I)
    if not m:
        return None
    return _build(m.group(1), m.group(2), _merchant_after(text, m.end()))


def _generic(text: str) -> dict | None:
    if not re.search(r"(debit|credit|spent|paid|payment|transaction)", text, re.I):
        return None
    m = re.search(r"(?:INR|Rs\.?|₹)\s*([\d,]+\.?\d*)", text, re.I)
    if not m:
        return None
    txn_type = "credit" if re.search(r"(credited|received|refund)", text, re.I) else "debit"
    return _build(m.group(1), txn_type, _merchant_after(text, m.end()))


# ── Helpers ────────────────────────────────────────────────────────────────────

def _build(amount_str: str, txn_type_raw: str, merchant: str) -> dict:
    txn_type = "credit" if "credit" in txn_type_raw.lower() else "debit"
    return {
        "amount": float(amount_str.replace(",", "")),
        "type": txn_type,
        "merchant": merchant,
    }


def _safe_amount(raw: str) -> float | None:
    try:
        val = float(raw.replace(",", ""))
        return val if 1 <= val <= 500_000 else None
    except ValueError:
        return None


def _merchant_after(text: str, pos: int) -> str:
    tail = text[pos : pos + 120]
    for pat in [
        r"\bat\s+([A-Z][A-Z0-9 \-&'.]{2,35})",
        r"\bto\s+([A-Z][A-Z0-9 \-&'.]{2,35})",
        r"\bfor\s+([A-Z][A-Z0-9 \-&'.]{2,35})",
        r"\btowards\s+([A-Z][A-Z0-9 \-&'.]{2,35})",
        r"\bvia\s+([A-Z][A-Z0-9 \-&'.]{2,35})",
    ]:
        m = re.search(pat, tail)
        if m:
            return m.group(1).strip().rstrip(".").title()[:40]
    m = re.search(r"([A-Z][A-Z0-9 ]{3,})", tail)
    if m:
        return m.group(1).strip().title()[:40]
    return "Unknown"


def _extract_food_items(text: str) -> list[str]:
    items: set[str] = set()
    for m in re.finditer(r"\b(\d+)\s*[xX]\s+([A-Za-z][A-Za-z\s&',\-]{2,35})", text):
        name = m.group(2).strip().rstrip(",.").strip()
        if len(name) > 3:
            items.add(name)
    for m in re.finditer(r"([A-Za-z][A-Za-z\s&',\-]{2,35})\s+[xX]\s*(\d+)\b", text):
        name = m.group(1).strip().rstrip(",.").strip()
        if len(name) > 3:
            items.add(name)
    return list(items)[:8]


def _parse_date(date_header: str) -> str:
    try:
        return parsedate_to_datetime(date_header).date().isoformat()
    except Exception:
        return datetime.today().date().isoformat()
