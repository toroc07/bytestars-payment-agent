"""Offline invoice reader for text (chat, email body, PDF text layer). Used when no LLM answers.

It only copies what it finds with fixed patterns of Colombian invoices; anything it cannot find stays
None and its confidence drops, so the engine escalates. Images need the LLM.
"""

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from app.schemas import ExtractedInvoice

CURRENCY = r"(US\$|USD|COP|\$)"
AMOUNT = r"\s*" + CURRENCY + r"\s*(\d[\d.,]*\d|\d)"
NIT = re.compile(r"\bNIT(?:\s+SIMULADO)?[:\s]*(?:es\s+)?(\d[\d.]{4,}\d-\d)", re.IGNORECASE)
TAX_ID = re.compile(r"\bTax\s+ID\b[^:\n]{0,30}:\s*(\d[\d-]{4,}\d)", re.IGNORECASE)
NUMBER_PATTERNS = [
    re.compile(
        r"\b(?:factura(?:\s+electr[oó]nica)?(?:\s+de\s+venta)?\s+No\.?|invoice\s+(?:number|no\.?|#)|N[uú\ufffd]?mero|Number|No\.)\s*[:.]?\s*([A-Z0-9]{2,8}(?:-[A-Z0-9]+)+|\b[A-Z]{2,5}-\d+\b)",
        re.IGNORECASE,
    ),
    re.compile(r"\bfactura\s+([A-Z]{2,5}-\d+)", re.IGNORECASE),
    re.compile(r"\binvoice\s+([A-Z]{2,6}(?:-[A-Z0-9]+)+)", re.IGNORECASE),
]
# English layout: the currency code comes after the amount ("TOTAL DUE: 132.30 USD").
TOTAL_SUFFIX_PATTERNS = [
    re.compile(r"\bTOTAL(?:\s+DUE|\s+AMOUNT)?\b\s*[:=]?\s*(\d[\d.,]*\d|\d)\s*(USD|COP)\b", re.IGNORECASE),
    re.compile(r"\bAMOUNT\s+DUE\b\s*[:=]?\s*(\d[\d.,]*\d|\d)\s*(USD|COP)\b", re.IGNORECASE),
]
TOTAL_PATTERNS = [
    re.compile(
        r"\bTOTAL\s+A\s+PAGAR(?:\s*/\s*AMOUNT\s+DUE)?\s*[:=]?\s*"
        r"(?:(US\$|USD|COP|EUR|GBP|MXN|\$)\s*)?"
        r"(\d[\d.,]*\d|\d)"
        r"(?:\s*(USD|COP|EUR|GBP|MXN))?",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:(US\$|USD|COP|EUR|GBP|MXN|\$)\s*)?"
        r"(\d[\d.,]*\d|\d)"
        r"(?:\s*(USD|COP|EUR|GBP|MXN))?"
        r"(?:\s*\n\s*[^\n\d$]{1,5})*\s*\n\s*TOTAL\s+A\s+PAGAR",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:\bTotal\b\s*[:=]|por\s+valor\s+de|=)\s*"
        r"(?:(US\$|USD|COP|EUR|GBP|MXN|\$)\s*)?"
        r"(\d[\d.,]*\d|\d)"
        r"(?:\s*(USD|COP|EUR|GBP|MXN))?",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:TOTAL\s+(?:DUE|AMOUNT)|AMOUNT\s+DUE)\b\s*[:=]?\s*"
        r"(?:(US\$|USD|COP|EUR|GBP|MXN|\$)\s*)?"
        r"(\d[\d.,]*\d|\d)"
        r"(?:\s*(USD|COP|EUR|GBP|MXN))?",
        re.IGNORECASE,
    ),
]
CURRENCY_HEADER = re.compile(r"\b(?:Moneda|Currency)\s*[:.]?\s*([A-Z]{3})\b", re.IGNORECASE)
ACCOUNT = re.compile(r"(?:\bcuenta\b|\bconsignar\b)[^\d\n]{0,60}?(\d{8,})", re.IGNORECASE)
ISSUE = [
    re.compile(r"(?:Fecha(?:\s+de\s+emisi[oó]n)?|emitida\s+el|Date)\s*:?\s*(\d{2}/\d{2}/\d{4})", re.IGNORECASE),
    re.compile(r"(?:Invoice|Issue)\s+date:?\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE),
]
DUE = [
    re.compile(r"(?:Fecha\s+de\s+vencimiento|vence\s+el|Vencimiento|Due\s+date)\s*:?\s*(\d{2}/\d{2}/\d{4})", re.IGNORECASE),
    re.compile(r"Due\s+date:?\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE),
]
PO = re.compile(r"\b(OC-\d{4}-\d{3,})\b", re.IGNORECASE)
CHAT_SENDER = re.compile(r"\]\s*[^()\n\]]+\(([^)]+)\):")
COMPANY_LINE = re.compile(
    r"^\s*([^\n|:]{3,80}?(?:\bS\.A\.S\.?|\bS\.A\.|\bLtda\.?|\bSAS|\bLLC|\bInc\.?|\bLtd\.?|\bCorp\.?))"
    r"\s*(?:\([^)\n]*\))?\s*$",
    re.MULTILINE | re.IGNORECASE,
)
INLINE_COMPANY = re.compile(
    r"([A-Za-zÁ-ú0-9 \t]{3,60}?(?:\bS\.A\.S\.?|\bS\.A\.|\bLtda\.?|\bSAS|\bLLC|\bInc\.?|\bLtd\.?|\bCorp\.?))(?:\s*\([^)]*\))?",
    re.IGNORECASE,
)
ITEM_PATTERNS = [
    re.compile(r"Descripci[oó\ufffd]n[^\n]*\n([A-Za-zÁ-ú\ufffd][^\n]{3,80}?)(?:\s+\d+\s+(?:licencia|hora|servicio|unidad|mes|paquete|c/u)|\s{2,}|\$)", re.IGNORECASE),
    re.compile(r"Descripci[oó\ufffd]n[^\n]*\n([A-Za-zÁ-ú\ufffd][^\n]{3,80})", re.IGNORECASE),  # table header follow
    re.compile(r"^\d+\s+([A-Za-zÁ-ú][^\n$]+?)\s+(?:US\$|\$)", re.MULTILINE),  # PDF table row
    re.compile(r"-\s*\d+\s*x\s*(.+?)\s*\(a\s", re.IGNORECASE),  # chat with detail
    re.compile(r"[:,]\s*\d+\s+(.+?)\s+a\s+(?:US\$|\$)"),  # one-line chat
    # English table row: description, quantity, unit price with the currency after it.
    re.compile(r"^([A-Za-z][^\n]{2,80}?)\s{2,}\d+\s{2,}\d[\d.,]*\s*(?:USD|COP)\b", re.MULTILINE),
]


def parse_money(raw: str) -> Decimal | None:
    """'1,487.50' (US) and '1.487.500' / '1.487,50' (CO) -> Decimal."""
    text = raw.strip()
    if "," in text and "." in text:
        decimal_sep = "," if text.rfind(",") > text.rfind(".") else "."
        thousands = "." if decimal_sep == "," else ","
        text = text.replace(thousands, "").replace(decimal_sep, ".")
    elif "." in text:
        parts = text.split(".")
        if len(parts) > 2 or len(parts[-1]) == 3:
            text = text.replace(".", "")
    elif "," in text:
        parts = text.split(",")
        text = text.replace(",", ".") if len(parts) == 2 and len(parts[-1]) == 2 else text.replace(",", "")
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None
    return value if value > 0 else None


def parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        try:
            return date.fromisoformat(raw)
        except ValueError:
            return None
    try:
        day, month, year = (int(p) for p in raw.split("/"))
        return date(year, month, day)
    except ValueError:
        return None


def _first(patterns: list[re.Pattern[str]], text: str) -> re.Match[str] | None:
    for pattern in patterns:
        if match := pattern.search(text):
            return match
    return None


def _vendor_tax_id(text: str, company_name: str) -> str | None:
    company = company_name.casefold()
    for match in NIT.finditer(text):
        before = text[max(0, match.start() - 80):match.start()].casefold()
        if company and company in before:
            continue  # the buyer's NIT, printed next to its name
        return match.group(1)
    match = TAX_ID.search(text)
    return match.group(1) if match else None


def _vendor_name(text: str, company_name: str) -> str | None:
    company = company_name.casefold()
    candidates = (
        [m.group(1) for m in CHAT_SENDER.finditer(text)]
        + [m.group(1) for m in COMPANY_LINE.finditer(text)]
        + [m.group(1) for m in INLINE_COMPANY.finditer(text)]
    )
    for candidate in candidates:
        cand = candidate.strip()
        if cand.casefold() != company and not cand.casefold().startswith(company):
            return cand
    return None


def _currency(raw: str, full_text: str = "") -> str | None:
    s = raw.strip().upper()
    if s in ("US$", "USD"):
        return "USD"
    if s in ("COP", "EUR", "GBP", "MXN"):
        return s
    if s == "$":
        # A bare "$" is pesos in Colombia and dollars elsewhere: only the text can say which. Guessing
        # wrong pays thousands of times the amount ($4.500 COP read as US$4,500), so unknown stays None.
        if re.search(r"\b(?:COP|PESOS?)\b", full_text, re.IGNORECASE):
            return "COP"
        if re.search(r"\bUSD\b|US\$|\bd[oó]lar(?:es)?\b", full_text, re.IGNORECASE):
            return "USD"
        return None
    return s


def read_text(sources: list[str], company_name: str) -> ExtractedInvoice:
    """`sources` in reading order: the message (chat/email body) first, then the document text."""
    message = sources[0] if sources else ""
    document = "\n".join(s for s in sources[1:] if s)
    full = "\n".join(s for s in sources if s)
    primary = document or full  # the invoice itself wins for its own data

    number = _first(NUMBER_PATTERNS, primary) or _first(NUMBER_PATTERNS, full)
    total = _first(TOTAL_PATTERNS, primary) or _first(TOTAL_PATTERNS, full)
    amount, currency = None, None
    if total:
        prefix = total.group(1) if len(total.groups()) >= 1 else None
        val = total.group(2) if len(total.groups()) >= 2 else None
        suffix = total.group(3) if len(total.groups()) >= 3 else None
        if val:
            amount = parse_money(val)
        raw_curr = suffix or prefix
        if raw_curr:
            currency = _currency(raw_curr, full)
    if amount is None and (suffix := _first(TOTAL_SUFFIX_PATTERNS, primary) or _first(TOTAL_SUFFIX_PATTERNS, full)):
        amount, currency = parse_money(suffix.group(1)), suffix.group(2).upper()
    if currency is None and (cm := (CURRENCY_HEADER.search(primary) or CURRENCY_HEADER.search(full))):
        currency = _currency(cm.group(1), full)
    if currency is None:
        if re.search(r"\b(?:USD|US\$)\b", full):
            currency = "USD"
        elif re.search(r"\bCOP\b", full):
            currency = "COP"
    # Money goes where the sender asks: an account written in the message beats the document's.
    message_accounts = ACCOUNT.findall(message) if document else []
    account = message_accounts[-1] if message_accounts else (m.group(1) if (m := ACCOUNT.search(primary)) else None)
    po = PO.search(primary) or PO.search(full)
    item = _first(ITEM_PATTERNS, primary)
    issue = _first(ISSUE, primary)
    due = _first(DUE, primary)

    invoice = ExtractedInvoice(
        invoice_number=number.group(1).upper() if number else None,
        vendor_name=_vendor_name(document, company_name) or _vendor_name(full, company_name),
        vendor_tax_id=_vendor_tax_id(primary, company_name) or _vendor_tax_id(full, company_name),
        beneficiary_account=account,
        amount=amount,
        currency=currency,
        issue_date=parse_date(issue.group(1) if issue else None),
        due_date=parse_date(due.group(1) if due else None),
        description=item.group(1).strip() if item else None,
        po_reference=po.group(1).upper() if po else None,
    )
    essentials = (invoice.invoice_number, invoice.vendor_name or invoice.vendor_tax_id, invoice.amount,
                  invoice.issue_date)
    return invoice.model_copy(update={"confidence": 0.9 if all(essentials) else 0.5})
