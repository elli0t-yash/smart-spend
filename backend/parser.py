import re
from datetime import date, datetime
from typing import Optional
import pdfplumber
from nlp_extractor import ner_extract_merchant


# ── Utilities ──────────────────────────────────────────────────────────────────

def parse_amount(val: str) -> float:
    return float(val.replace(",", "").strip()) if val and val.strip() not in ("0.00", "") else 0.0


_DATE_FMTS = ["%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d-%b-%Y", "%d %B %Y", "%d/%b/%Y"]

def parse_date(val: str) -> Optional[date]:
    val = re.sub(r"\s+", " ", val.strip())
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


# ── Merchant extraction ────────────────────────────────────────────────────────

def _extract_hdfc_merchant(narration: str) -> str:
    clean = re.split(r"Value Dt \d{2}/\d{2}/\d{4}", narration)[0].strip()

    if re.match(r"UPI-", clean, re.IGNORECASE):
        rest = clean[4:]
        if "@" in rest:
            pre_at = rest[: rest.index("@")]
            segments = pre_at.split("-")
            for i, seg in enumerate(segments):
                s = seg.strip()
                is_vpa = (
                    (s and s[0].islower())
                    or (s and s[0].isdigit())
                    or (len(s) >= 8 and any(c.isdigit() for c in s) and any(c.isalpha() for c in s))
                )
                if is_vpa:
                    name = "-".join(segments[:i]).strip()
                    if name:
                        return name.title()
            return pre_at.title()
        m = re.search(r"-(?!remark\b|paid\b|payment\b)([a-z]{3,})", rest)
        if m:
            return rest[: m.start()].strip().title()
        m = re.search(r"-\d{9,}", rest)
        if m:
            return rest[: m.start()].strip().title()
        parts = rest.split()
        return " ".join(parts[:2]).strip().title() or "UPI Payment"

    if re.match(r"POS\s", clean):
        parts = clean.split()
        idx = next((i for i, p in enumerate(parts) if re.match(r"\d{6}X", p)), None)
        if idx is not None and idx + 1 < len(parts):
            return " ".join(parts[idx + 1:]).title()
        return "POS Purchase"

    if "ME DC SI" in clean:
        parts = clean.split()
        idx = next((i for i, p in enumerate(parts) if re.match(r"\d{6}X", p)), None)
        if idx is not None and idx + 1 < len(parts):
            return " ".join(parts[idx + 1:]).replace("RAZ*", "").title()
        return "Card Payment"

    if re.search(r"BAJAJ FINANCE|A2AINT01", clean, re.IGNORECASE):
        return "Bajaj Finance (Salary)"
    if re.search(r"IB FD|FD PREMAT|FD through", clean, re.IGNORECASE):
        return "Fixed Deposit"
    if re.search(r"Interest paid", clean, re.IGNORECASE):
        return "Interest Income"

    return clean[:40].strip().title()


def _extract_generic_merchant(narration: str) -> str:
    clean = narration.strip()

    # Strip SBI transfer prefix: "TO TRANSFER-..." / "BY TRANSFER-..."
    clean = re.sub(r"^(?:TO|BY)\s+TRANSFER[- ]+", "", clean, flags=re.IGNORECASE).strip()

    # UPI: "UPI/P2P/REF/NAME@bank", "UPI/REF/NAME", "UPI-NAME@bank"
    m = re.match(
        r"UPI[/\-](?:P2[PM][/\-]|DR[/\-]|CR[/\-])?\d*[/\-]?([^/@\n,]+?)(?:[@/]|$)",
        clean, re.IGNORECASE,
    )
    if m:
        merchant = m.group(1).strip().rstrip("-").strip()
        if merchant and len(merchant) > 1 and not merchant.isdigit():
            return merchant.title()

    # NEFT/IMPS/RTGS: "NEFT/REF/NAME", "NEFT-REF-NAME"
    m = re.search(r"(?:NEFT|IMPS|RTGS)[/\-\s]+\S+[/\-\s]+(.+?)(?:\s{2,}|[/|]|$)", clean, re.IGNORECASE)
    if m:
        name = m.group(1).strip()[:40]
        if name:
            return name.title()

    # POS: "POS/TERMINAL/MERCHANT"
    m = re.search(r"\bPOS[/\s]+\S*[/\s]+(.+?)(?:\s{2,}|$)", clean, re.IGNORECASE)
    if m:
        name = m.group(1).strip()[:40]
        if name:
            return name.title()

    if re.search(r"ATM|CDMS WDL", clean, re.IGNORECASE):
        return "ATM Withdrawal"

    return clean[:40].strip().title()


def extract_merchant(narration: str, bank: str = "hdfc") -> str:
    result = _extract_hdfc_merchant(narration) if bank == "hdfc" else _extract_generic_merchant(narration)

    # Phase 1: NER fallback — if regex produced a noisy long string, try spaCy
    _looks_weak = len(result) > 35 or result.isupper() or "/" in result
    if _looks_weak:
        ner_result = ner_extract_merchant(narration)
        if ner_result:
            return ner_result

    return result


# ── Bank detection ─────────────────────────────────────────────────────────────

_BANK_SIGNATURES = [
    ("hdfc",  ["HDFC BANK", "HDFCBANK"]),
    ("sbi",   ["STATE BANK OF INDIA"]),
    ("icici", ["ICICI BANK"]),
    ("axis",  ["AXIS BANK"]),
    ("kotak", ["KOTAK MAHINDRA BANK", "KOTAK BANK"]),
]

SUPPORTED_BANKS = {
    "hdfc":  "HDFC Bank",
    "sbi":   "State Bank of India",
    "icici": "ICICI Bank",
    "axis":  "Axis Bank",
    "kotak": "Kotak Mahindra Bank",
}


def detect_bank(file_path: str, password: str = "") -> str:
    with pdfplumber.open(file_path, password=password) as pdf:
        text = ""
        for page in pdf.pages[:2]:
            text += (page.extract_text() or "").upper()
    for bank_id, sigs in _BANK_SIGNATURES:
        if any(sig in text for sig in sigs):
            return bank_id
    return "unknown"


# ── HDFC parser (handles packed multi-txn rows) ────────────────────────────────

def _split_narrations(narration_cell: str) -> list[str]:
    text = " ".join(line.strip() for line in narration_cell.split("\n") if line.strip())
    pattern = r"(Value Dt \d{2}/\d{2}/\d{4}(?:\s+Ref\s+\d+)?)"
    parts = re.split(pattern, text)
    transactions = []
    i = 0
    while i < len(parts):
        body = parts[i].strip()
        if i + 1 < len(parts) and re.match(r"Value Dt \d{2}/\d{2}/\d{4}", parts[i + 1]):
            full = (body + " " + parts[i + 1]).strip()
            if body:
                transactions.append(full)
            i += 2
        else:
            if body:
                transactions.append(body)
            i += 1
    return transactions


_HDFC_SKIP = re.compile(r"FD through MOBILE|IB FD PREMAT|FD through\s", re.IGNORECASE)


def parse_hdfc_pdf(file_path: str, password: str = "") -> list[dict]:
    transactions = []
    with pdfplumber.open(file_path, password=password) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if not tables:
                continue
            table = tables[0]
            if not table or (table[0][0] or "").strip() != "Txn Date":
                continue
            for row in table[1:]:
                if len(row) < 5:
                    continue
                dates = [d.strip() for d in (row[0] or "").split("\n") if re.match(r"\d{2}/\d{2}/\d{4}", d.strip())]
                narrations = _split_narrations(row[1] or "")
                withdrawals = [v.strip() for v in (row[2] or "").split("\n") if v.strip()]
                deposits = [v.strip() for v in (row[3] or "").split("\n") if v.strip()]
                count = min(len(dates), len(narrations), len(withdrawals), len(deposits))
                for i in range(count):
                    narr = narrations[i]
                    if _HDFC_SKIP.search(narr):
                        continue
                    withdrawal = parse_amount(withdrawals[i]) if i < len(withdrawals) else 0.0
                    deposit = parse_amount(deposits[i]) if i < len(deposits) else 0.0
                    try:
                        txn_date = datetime.strptime(dates[i], "%d/%m/%Y").date()
                    except ValueError:
                        continue
                    transactions.append({
                        "date":       txn_date.isoformat(),
                        "narration":  narr,
                        "merchant":   extract_merchant(narr, "hdfc"),
                        "amount":     withdrawal if withdrawal > 0 else deposit,
                        "type":       "debit" if withdrawal > 0 else "credit",
                        "withdrawal": withdrawal,
                        "deposit":    deposit,
                    })
    return transactions


# ── Generic single-row-per-transaction parser ──────────────────────────────────

# Column header aliases per bank
_BANK_HEADERS: dict[str, dict[str, list[str]]] = {
    "sbi": {
        "date":      ["txn date", "transaction date", "date"],
        "narration": ["description", "particulars", "narration"],
        "debit":     ["debit", "withdrawal", "dr"],
        "credit":    ["credit", "deposit", "cr"],
    },
    "icici": {
        "date":      ["transaction date", "date", "value date"],
        "narration": ["description", "transaction remarks", "particulars", "narration"],
        "debit":     ["withdrawal", "debit", "dr"],
        "credit":    ["deposit", "credit", "cr"],
        # ICICI sometimes has a single amount col + dr/cr indicator
        "amount":    ["amount (inr)", "amount"],
        "dr_cr":     ["dr/cr", "type", "cr/dr"],
    },
    "axis": {
        "date":      ["tran date", "transaction date", "date"],
        "narration": ["particulars", "description", "narration"],
        "debit":     ["dr", "debit", "withdrawal"],
        "credit":    ["cr", "credit", "deposit"],
    },
    "kotak": {
        "date":      ["transaction date", "date", "txn date"],
        "narration": ["description", "particulars", "narration"],
        "debit":     ["debit", "dr", "withdrawal"],
        "credit":    ["credit", "cr", "deposit"],
    },
}


def _find_col(header_row: list, aliases: list[str]) -> Optional[int]:
    for j, cell in enumerate(header_row):
        cell_lower = (cell or "").lower().strip()
        if any(alias in cell_lower for alias in aliases):
            return j
    return None


def _parse_generic_pdf(file_path: str, password: str, bank: str) -> list[dict]:
    header_map = _BANK_HEADERS[bank]
    transactions = []

    with pdfplumber.open(file_path, password=password) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if not tables:
                continue
            for table in tables:
                if not table or len(table) < 2:
                    continue

                # Find the header row (check first 5 rows)
                header_row = None
                data_start = 0
                for i, row in enumerate(table[:5]):
                    if row and _find_col(row, header_map["date"]) is not None:
                        header_row = row
                        data_start = i + 1
                        break
                if header_row is None:
                    continue

                date_col   = _find_col(header_row, header_map["date"])
                narr_col   = _find_col(header_row, header_map["narration"])
                debit_col  = _find_col(header_row, header_map.get("debit", []))
                credit_col = _find_col(header_row, header_map.get("credit", []))
                amount_col = _find_col(header_row, header_map.get("amount", []))
                dr_cr_col  = _find_col(header_row, header_map.get("dr_cr", []))

                if date_col is None or narr_col is None:
                    continue

                known_cols = [c for c in [date_col, narr_col, debit_col, credit_col, amount_col, dr_cr_col] if c is not None]

                for row in table[data_start:]:
                    if not row or len(row) <= max(known_cols):
                        continue

                    date_val  = (row[date_col] or "").strip()
                    narration = " ".join((row[narr_col] or "").split())
                    if not date_val or not narration:
                        continue

                    txn_date = parse_date(date_val)
                    if not txn_date:
                        continue

                    debit = credit = 0.0

                    if debit_col is not None and credit_col is not None:
                        debit  = parse_amount(row[debit_col]  or "")
                        credit = parse_amount(row[credit_col] or "")
                    elif amount_col is not None and dr_cr_col is not None:
                        amt = parse_amount(row[amount_col] or "")
                        indicator = (row[dr_cr_col] or "").strip().upper()
                        if indicator.startswith("D"):
                            debit = amt
                        else:
                            credit = amt

                    if debit == 0.0 and credit == 0.0:
                        continue

                    transactions.append({
                        "date":       txn_date.isoformat(),
                        "narration":  narration,
                        "merchant":   extract_merchant(narration, bank),
                        "amount":     debit if debit > 0 else credit,
                        "type":       "debit" if debit > 0 else "credit",
                        "withdrawal": debit,
                        "deposit":    credit,
                    })

    return transactions


# ── Public entry point ─────────────────────────────────────────────────────────

def parse_statement(
    file_path: str,
    password: str = "",
    bank: Optional[str] = None,
) -> tuple[list[dict], str]:
    """
    Parse a bank statement PDF.
    Auto-detects the bank when bank is None or "auto".
    Returns (transactions, bank_id).
    """
    if not bank or bank == "auto":
        bank = detect_bank(file_path, password)

    if bank == "hdfc":
        return parse_hdfc_pdf(file_path, password), "hdfc"

    if bank in _BANK_HEADERS:
        return _parse_generic_pdf(file_path, password, bank), bank

    # Unknown: try HDFC format, then each generic bank
    txns = parse_hdfc_pdf(file_path, password)
    if txns:
        return txns, "hdfc"
    for b in ("sbi", "icici", "axis", "kotak"):
        txns = _parse_generic_pdf(file_path, password, b)
        if txns:
            return txns, b
    return [], "unknown"
