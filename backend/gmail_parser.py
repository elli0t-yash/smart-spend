import re
from datetime import datetime
from email.utils import parsedate_to_datetime


def parse_email(body: str, snippet: str, date_header: str) -> dict | None:
    text = (body or snippet or "").replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()

    date = _parse_date(date_header)

    for parser in [_hdfc, _icici, _axis, _sbi, _kotak, _generic]:
        result = parser(text)
        if result:
            result["date"] = date
            result["narration"] = text[:150]
            return result

    return None


# ── bank-specific patterns ─────────────────────────────────────────────────────

def _hdfc(text: str) -> dict | None:
    # "Rs.450.00 debited from a/c XX1234 at SWIGGY"
    m = re.search(r"Rs\.?\s*([\d,]+\.?\d*)\s+(?:has been\s+)?(debited|credited)", text, re.I)
    if not m:
        return None
    return _build(m.group(1), m.group(2), _merchant_after(text, m.end()))


def _icici(text: str) -> dict | None:
    # "ICICI Bank account XX1234 debited for Rs 450.00"
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
    # "INR 450.00 has been debited from your Axis Bank account"
    m = re.search(r"INR\s*([\d,]+\.?\d*)\s+has been\s+(debited|credited)", text, re.I)
    if not m:
        return None
    return _build(m.group(1), m.group(2), _merchant_after(text, m.end()))


def _sbi(text: str) -> dict | None:
    # "Your a/c XX1234 is debited by Rs.450.00 on 15Jan24"
    m = re.search(r"(?:debited|credited)\s+by\s+Rs\.?\s*([\d,]+\.?\d*)", text, re.I)
    if not m:
        return None
    txn_type = "credit" if "credited" in m.group(0).lower() else "debit"
    return _build(m.group(1), txn_type, _merchant_after(text, m.end()))


def _kotak(text: str) -> dict | None:
    # "Kotak Bank: INR 450.00 debited"
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


# ── helpers ────────────────────────────────────────────────────────────────────

def _build(amount_str: str, txn_type_raw: str, merchant: str) -> dict:
    txn_type = "credit" if "credit" in txn_type_raw.lower() else "debit"
    return {
        "amount": float(amount_str.replace(",", "")),
        "type": txn_type,
        "merchant": merchant,
    }


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
    # fallback: first ALL-CAPS word group
    m = re.search(r"([A-Z][A-Z0-9 ]{3,})", tail)
    if m:
        return m.group(1).strip().title()[:40]
    return "Unknown"


def _parse_date(date_header: str) -> str:
    try:
        return parsedate_to_datetime(date_header).date().isoformat()
    except Exception:
        return datetime.today().date().isoformat()
