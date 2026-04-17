import re
from datetime import datetime
import pdfplumber


def parse_amount(val: str) -> float:
    return float(val.replace(",", "").strip()) if val and val.strip() not in ("0.00", "") else 0.0


def extract_merchant(narration: str) -> str:
    # Strip "Value Dt ..." suffix to work on the meaningful part
    clean = re.split(r"Value Dt \d{2}/\d{2}/\d{4}", narration)[0].strip()

    if re.match(r"UPI-", clean, re.IGNORECASE):
        rest = clean[4:]
        # UPI format: DisplayName-vpahandle@bankcode-BANKIFSC-refnum-remark
        # Display name ends where the VPA handle begins (before the @ sign).
        if "@" in rest:
            pre_at = rest[:rest.index("@")]
            segments = pre_at.split("-")
            for i, seg in enumerate(segments):
                s = seg.strip()
                # VPA segment: starts lowercase, starts with a digit, or is 8+ chars mixing letters+digits
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

        # No @ sign (old UPI format): find boundary via lowercase handle or phone number.
        # Check lowercase-starting handle first (exclude common remark words at end)
        m = re.search(r"-(?!remark\b|paid\b|payment\b)([a-z]{3,})", rest)
        if m:
            return rest[:m.start()].strip().title()
        # Phone number in handle (9+ digits)
        m = re.search(r"-\d{9,}", rest)
        if m:
            return rest[:m.start()].strip().title()
        # Fallback: first two words
        parts = rest.split()
        return " ".join(parts[:2]).strip().title() or "UPI Payment"

    if re.match(r"POS\s", clean):
        parts = clean.split()
        # "POS CARDNUM MERCHANT" — skip card number
        idx = next((i for i, p in enumerate(parts) if re.match(r"\d{6}X", p)), None)
        if idx is not None and idx + 1 < len(parts):
            return " ".join(parts[idx + 1:]).title()
        return "POS Purchase"

    if "ME DC SI" in clean:
        # "ME DC SI CARDNUM MERCHANT"
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


def _split_narrations(narration_cell: str) -> list[str]:
    """Split a packed narration cell into individual transaction narrations."""
    # Flatten multi-line cell to single string
    text = " ".join(line.strip() for line in narration_cell.split("\n") if line.strip())

    # Split on "Value Dt DD/MM/YYYY Ref REFNUM" (Ref number optional for some entries)
    # Using capturing group so delimiters are kept
    pattern = r"(Value Dt \d{2}/\d{2}/\d{4}(?:\s+Ref\s+\d+)?)"
    parts = re.split(pattern, text)

    # parts = [body1, delim1, body2, delim2, ...]
    transactions = []
    i = 0
    while i < len(parts):
        body = parts[i].strip()
        if i + 1 < len(parts) and re.match(r"Value Dt \d{2}/\d{2}/\d{4}", parts[i + 1]):
            full = (body + " " + parts[i + 1]).strip()
            if body:  # only add if there's actual narration content
                transactions.append(full)
            i += 2
        else:
            if body:
                transactions.append(body)
            i += 1

    return transactions


# Transactions to skip (internal bank operations, not real spend)
_SKIP_PATTERNS = re.compile(
    r"FD through MOBILE|IB FD PREMAT|FD through\s",
    re.IGNORECASE,
)


def parse_hdfc_pdf(file_path: str, password: str = "") -> list[dict]:
    transactions = []

    with pdfplumber.open(file_path, password=password) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if not tables:
                continue
            table = tables[0]
            if not table or table[0][0] != "Txn Date":
                continue

            for row in table[1:]:
                if len(row) < 5:
                    continue

                dates = [d.strip() for d in row[0].split("\n") if re.match(r"\d{2}/\d{2}/\d{4}", d.strip())]
                narrations = _split_narrations(row[1])
                withdrawals = [v.strip() for v in row[2].split("\n") if v.strip()]
                deposits = [v.strip() for v in row[3].split("\n") if v.strip()]

                count = min(len(dates), len(narrations), len(withdrawals), len(deposits))

                for i in range(count):
                    narr = narrations[i]

                    if _SKIP_PATTERNS.search(narr):
                        continue

                    withdrawal = parse_amount(withdrawals[i]) if i < len(withdrawals) else 0.0
                    deposit = parse_amount(deposits[i]) if i < len(deposits) else 0.0

                    try:
                        date = datetime.strptime(dates[i], "%d/%m/%Y").date()
                    except ValueError:
                        continue

                    transactions.append({
                        "date": date.isoformat(),
                        "narration": narr,
                        "merchant": extract_merchant(narr),
                        "amount": withdrawal if withdrawal > 0 else deposit,
                        "type": "debit" if withdrawal > 0 else "credit",
                        "withdrawal": withdrawal,
                        "deposit": deposit,
                    })

    return transactions
