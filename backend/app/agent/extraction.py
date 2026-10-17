"""Step 3 of the pipeline: document -> ExtractedInvoice. The LLM only reads; its output is re-validated here.

Order (ADR-019):
1. Text only (chat, email body, PDF with a text layer): the offline reader. If it finds every key field,
   that reading is used and no LLM quota is spent.
2. Otherwise the LLM chain (cache -> Gemini models -> Groq/OpenRouter). A PDF with text goes as text.
3. If no LLM answers, the offline reading (even if incomplete; the engine escalates what is missing).
"""

import io
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from app.agent.local_reader import parse_date, parse_money, read_text
from app.llm import LLMChain, LLMError, LLMRequest
from app.schemas import ExtractedInvoice

PROMPT = (Path(__file__).parent / "prompts" / "extraction.md").read_text(encoding="utf-8")
MAX_TEXT_CHARS = 20_000
MAX_FIELD_CHARS = 200
# What the offline reading must contain to be used without asking the LLM.
COMPLETE_FIELDS = ("invoice_number", "vendor_name", "vendor_tax_id", "beneficiary_account", "amount", "currency",
                   "issue_date", "description")
INVOICE_HINTS = re.compile(r"factura|\bNIT\b|total|US\$|\bUSD\b|\bCOP\b|\$\s?\d", re.IGNORECASE)


@dataclass(frozen=True)
class Extraction:
    invoice: ExtractedInvoice | None
    source: str  # provider name, "cache", "local" or "none"
    error: str | None = None


def is_complete(invoice: ExtractedInvoice) -> bool:
    return all(getattr(invoice, field) not in (None, "") for field in COMPLETE_FIELDS)


def looks_like_invoice(text: str | None) -> bool:
    return bool(text and INVOICE_HINTS.search(text))


def pdf_text(data: bytes) -> str:
    """Text layer of a PDF; empty when it is a scan or cannot be opened."""
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages_text = []
            for page in pdf.pages[:5]:
                try:
                    clean_page = page.filter(
                        lambda obj: obj.get("object_type") != "char"
                        or (obj.get("matrix") and obj["matrix"][1] == 0 and obj["matrix"][2] == 0)
                    )
                    txt = clean_page.extract_text()
                except Exception:  # noqa: BLE001 - pdfplumber filter can fail on unusual char dicts
                    txt = None
                txt = txt or page.extract_text() or ""
                if txt:
                    pages_text.append(txt)
            return "\n".join(pages_text).strip()
    except Exception:  # noqa: BLE001 - a broken PDF just has no text; the LLM may still read it
        return ""


def _document_block(message: str, document: str) -> str:
    parts = []
    if message.strip():
        parts.append("[Mensaje recibido]\n" + message.strip())
    if document.strip():
        parts.append("[Texto del archivo adjunto]\n" + document.strip())
    body = "\n\n".join(parts) or "[Sin texto: lee el archivo adjunto]"
    body = body.replace("</documento>", "")[:MAX_TEXT_CHARS]  # the data cannot close its own delimiter
    return f"<documento>\n{body}\n</documento>"


def _text(value: Any, limit: int = MAX_FIELD_CHARS) -> str | None:
    if value is None or isinstance(value, (dict, list)):
        return None
    text = str(value).strip()
    return text[:limit] if text and text.lower() not in ("null", "none", "n/a") else None


def _money(value: Any) -> Decimal | None:
    text = _text(value, 40)
    if text is None or "-" in text:  # a negative or ranged amount is not something to pay
        return None
    text = re.sub(r"[^\d.,]", "", text)
    try:
        amount = Decimal(text) if re.fullmatch(r"\d+(\.\d{1,2})?", text) else parse_money(text)
    except InvalidOperation:
        return None
    return amount if amount and amount > 0 else None


def _date(value: Any) -> date | None:
    text = _text(value, 20)
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return parse_date(text)


def _code(value: Any, length: int) -> str | None:
    text = (_text(value, 10) or "").upper()
    return text if re.fullmatch(rf"[A-Z]{{{length}}}", text) else None


def _currency_code(value: Any) -> str | None:
    text = (_text(value, 10) or "").upper().strip()
    if text in ("US$", "USD"):
        return "USD"
    if text in ("COP", "EUR", "GBP", "MXN"):
        return text
    if text == "$":
        return "USD"
    return text if re.fullmatch(r"[A-Z]{3}", text) else None


def coerce(data: dict[str, Any]) -> ExtractedInvoice:
    """Field by field: anything malformed becomes None (and the engine escalates), never an error."""
    account = re.sub(r"\D", "", _text(data.get("beneficiary_account"), 40) or "") or None
    po = _text(data.get("po_reference"), 60)
    try:
        confidence = min(max(float(data.get("confidence") or 0), 0.0), 1.0)
    except (TypeError, ValueError):
        confidence = 0.0
    return ExtractedInvoice(
        invoice_number=_text(data.get("invoice_number"), 60),
        vendor_name=_text(data.get("vendor_name")),
        vendor_tax_id=_text(data.get("vendor_tax_id"), 40),
        beneficiary_account=account,
        vendor_country=_code(data.get("vendor_country"), 2),
        amount=_money(data.get("amount")),
        currency=_currency_code(data.get("currency")),
        issue_date=_date(data.get("issue_date")),
        due_date=_date(data.get("due_date")),
        description=_text(data.get("description")),
        po_reference=None if po and po.lower() in ("no aplica", "n/a", "ninguna") else po,
        confidence=confidence,
    )


def extract(
    *,
    text: str | None,
    file_bytes: bytes | None,
    mime_type: str | None,
    company_name: str,
    llm: LLMChain,
) -> Extraction:
    message = text or ""
    document = pdf_text(file_bytes) if file_bytes and mime_type == "application/pdf" else ""
    send_file = file_bytes is not None and not document  # images and scanned PDFs go as files
    local = read_text([message, document], company_name) if (message.strip() or document) else None
    if local is not None and not send_file and is_complete(local):
        return Extraction(local, "local")
    request = LLMRequest(
        system=PROMPT.format(company_name=company_name),
        text=_document_block(message, document),
        file_bytes=file_bytes if send_file else None,
        mime_type=mime_type if send_file else None,
    )
    error = None
    try:
        data, provider = llm.generate_json(request)
        return Extraction(coerce(data), provider)
    except LLMError as exc:
        error = str(exc)
    except Exception as exc:  # noqa: BLE001 - fail-closed: fall back, the engine escalates what is missing
        error = f"{type(exc).__name__}"
    if local is not None:
        return Extraction(local, "local", error)
    return Extraction(None, "none", error)
