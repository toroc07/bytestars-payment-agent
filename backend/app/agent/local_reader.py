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
NIT = re.compile(r"\bNIT\b[:\s]*(?:es\s+)?(\d[\d.]{4,}\d-\d)", re.IGNORECASE)
NUMBER_PATTERNS = [
    re.compile(r"factura(?:\s+electr[oó]nica)?(?:\s+de\s+venta)?\s+No\.?\s*([A-Z]{2,5}-\d+)", re.IGNORECASE),
    re.compile(r"factura\s+([A-Z]{2,5}-\d+)", re.IGNORECASE),
]
TOTAL_PATTERNS = [
    re.compile(r"TOTAL A PAGAR" + AMOUNT, re.IGNORECASE),
    re.compile(r"\bTotal\b:?" + AMOUNT),
    re.compile(r"=" + AMOUNT),
    re.compile(r"por valor de" + AMOUNT, re.IGNORECASE),
]
ACCOUNT = re.compile(r"(?:\bcuenta\b|\bconsignar\b)[^\d\n]{0,60}?(\d{8,})", re.IGNORECASE)
ISSUE = [re.compile(r"Fecha de emisi[oó]n:?\s*(\d{2}/\d{2}/\d{4})", re.IGNORECASE),
         re.compile(r"emitida el\s+(\d{2}/\d{2}/\d{4})", re.IGNORECASE)]
DUE = [re.compile(r"Fecha de vencimiento:?\s*(\d{2}/\d{2}/\d{4})", re.IGNORECASE),
       re.compile(r"vence el\s+(\d{2}/\d{2}/\d{4})", re.IGNORECASE)]
PO = re.compile(r"\b(OC-\d{4}-\d{3,})\b", re.IGNORECASE)
CHAT_SENDER = re.compile(r"\]\s*[^()\n\]]+\(([^)]+)\):")
COMPANY_LINE = re.compile(r"^\s*([^\n|:]{3,80}?\b(?:S\.A\.S\.?|S\.A\.|Ltda\.?|SAS))\s*$", re.MULTILINE)
ITEM_PATTERNS = [
    re.compile(r"^\d+\s+(.+?)\s+(?:US\$|\$)", re.MULTILINE),  # PDF table row
    re.compile(r"-\s*\d+\s*x\s*(.+?)\s*\(a\s", re.IGNORECASE),  # chat with detail
    re.compile(r"[:,]\s*\d+\s+(.+?)\s+a\s+(?:US\$|\$)"),  # one-line chat
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
    return None


def _vendor_name(text: str, company_name: str) -> str | None:
    company = company_name.casefold()
    candidates = [m.group(1) for m in CHAT_SENDER.finditer(text)] + [m.group(1) for m in COMPANY_LINE.finditer(text)]
    for candidate in candidates:
        if candidate.strip().casefold() != company:
            return candidate.strip()
    return None


def _currency(symbol: str) -> str:
    return "USD" if symbol.upper() in ("US$", "USD") else "COP"


def read_text(sources: list[str], company_name: str) -> ExtractedInvoice:
    """`sources` in reading order: the message (chat/email body) first, then the document text."""
    message = sources[0] if sources else ""
    document = "\n".join(s for s in sources[1:] if s)
    full = "\n".join(s for s in sources if s)
    primary = document or full  # the invoice itself wins for its own data

    number = _first(NUMBER_PATTERNS, primary) or _first(NUMBER_PATTERNS, full)
    total = _first(TOTAL_PATTERNS, primary) or _first(TOTAL_PATTERNS, full)
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
        amount=parse_money(total.group(2)) if total else None,
        currency=_currency(total.group(1)) if total else None,
        issue_date=parse_date(issue.group(1) if issue else None),
        due_date=parse_date(due.group(1) if due else None),
        description=item.group(1).strip() if item else None,
        po_reference=po.group(1).upper() if po else None,
    )
    essentials = (invoice.invoice_number, invoice.vendor_name or invoice.vendor_tax_id, invoice.amount,
                  invoice.issue_date)
    return invoice.model_copy(update={"confidence": 0.9 if all(essentials) else 0.5})
