"""Read-only chat (docs/ARCHITECTURE.md §3, "Chat de consulta"): answers questions about stored decisions.

No LLM: questions are matched with fixed patterns and answers are built from the repositories, so nothing
here can approve, change or invent anything, and a question cannot carry a prompt injection.
"""

import re
import unicodedata
from datetime import datetime, timedelta

from app.ports import DecisionRepository, InvoiceRepository, RuleSetRepository
from app.schemas import CheckStatus, Decision, Invoice, InvoiceStatus

MAX_LISTED = 8
MONEY_IN_TEXT = re.compile(r"US\$\s?\d|\$\s?\d|\bUSD\s?\d|\bCOP\b|\btotal\b\s*[:=]", re.IGNORECASE)
QUESTION_START = re.compile(
    r"^\s*(?:¿|por\s?que|que|cual|cuales|cuanto|cuantos|cuantas|cuando|como|quien|donde|muestrame|muestra|"
    r"lista|listame|dime|explica|explicame|hay|tengo|resumen|estado)\b",
)
INVOICE_NUMBER = re.compile(r"\b([A-Z]{2,5}-\d{2,})\b", re.IGNORECASE)
FILE_NUMBER = re.compile(r"\b(?:factura[_\s]?|la\s|el\s)(\d{3})\b", re.IGNORECASE)

STATUS_LABEL = {
    InvoiceStatus.paid: "pagada",
    InvoiceStatus.approved: "aprobada por una persona",
    InvoiceStatus.pending_approval: "pendiente de aprobación",
    InvoiceStatus.blocked: "rechazada por el agente",
    InvoiceStatus.rejected: "rechazada por una persona",
    InvoiceStatus.received: "recibida, sin decisión",
}

HELP_TEXT = (
    "Envíame una factura para revisarla: adjunta un PDF o una imagen (PNG o JPG), o pega el texto del mensaje o "
    "correo con la factura. Te digo si se paga, se frena o queda pendiente de aprobación, y por qué.\n"
    "También puedes preguntarme por lo ya decidido, por ejemplo: «¿por qué frenaste la SIG-497?», "
    "«¿qué facturas están pendientes?», «¿cuánto se ha pagado esta semana?» o «facturas de Tecnoredes»."
)


def _plain(text: str) -> str:
    """Lower case without accents, for matching only."""
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def looks_like_question(text: str | None) -> bool:
    """A question about past decisions, not an invoice: asks something and carries no amounts."""
    if not text or len(text) > 400 or MONEY_IN_TEXT.search(text):
        return False
    plain = _plain(text)
    return "?" in text or bool(QUESTION_START.match(plain))


def _money(amount, currency: str | None) -> str:
    return "—" if amount is None else f"{currency or ''} {amount:,.2f}".strip()


def _label(invoice: Invoice) -> str:
    e = invoice.extracted
    if e is None:
        return f"la factura {invoice.source_filename or invoice.id} (sin datos leídos)"
    number = e.invoice_number or invoice.source_filename or invoice.id
    vendor = e.vendor_name or e.vendor_tax_id or "proveedor sin identificar"
    return f"la factura {number} de {vendor} ({_money(e.amount, e.currency)})"


def _failed(decision: Decision) -> str:
    rules = [c for c in decision.checks if c.status == CheckStatus.failed]
    return "; ".join(f"{c.rule_id} · {c.message.rstrip('. ')}" for c in rules)


def _explain_invoice(invoice: Invoice, dec_repo: DecisionRepository) -> str:
    history = sorted(dec_repo.list_by_invoice(invoice.id), key=lambda d: d.created_at)
    agent = [d for d in history if d.actor.value == "agent"]
    human = [d for d in history if d.actor.value == "human"]
    label = _label(invoice)
    lines = [f"{label[0].upper()}{label[1:]} está {STATUS_LABEL.get(invoice.status, invoice.status.value)}."]
    if agent:
        last = agent[-1]
        reasons = _failed(last)
        lines.append(f"Reglas que no se cumplieron: {reasons}." if reasons else f"El agente decidió: {last.summary}")
        if len(agent) > 1:
            lines.append(f"Se evaluó {len(agent)} veces (la última con las reglas v{last.rule_set_version}).")
    for d in human:
        verb = "aprobó" if d.outcome.value == "pay" else "rechazó"
        lines.append(f"{d.approver or 'Una persona'} la {verb}" + (f": «{d.comment}»." if d.comment else "."))
    return "\n".join(lines)


def _find_invoices(text: str, invoices: list[Invoice]) -> list[Invoice]:
    found: list[Invoice] = []
    for number in {m.upper() for m in INVOICE_NUMBER.findall(text)}:
        found += [i for i in invoices if i.extracted and (i.extracted.invoice_number or "").upper() == number]
    for number in FILE_NUMBER.findall(text):
        tag = f"factura_{number}"
        found += [i for i in invoices if tag in (i.source_filename or "") or tag in (i.raw_text or "")]
    return list({i.id: i for i in found}.values())


# Words too common in company names to identify a vendor on their own.
GENERIC_WORDS = {"comercializadora", "servicios", "colombia", "integral", "industrial", "total", "sociedad",
                 "suministros", "bogota", "facturas", "factura"}


def _vendor_words(name: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]{4,}", _plain(name)) if w not in GENERIC_WORDS}


def _vendor_invoices(text: str, invoices: list[Invoice]) -> tuple[str, list[Invoice]] | None:
    asked = set(re.findall(r"[a-z0-9]{4,}", _plain(text)))
    for invoice in invoices:
        name = invoice.extracted.vendor_name if invoice.extracted else None
        if name and (_vendor_words(name) & asked):
            key = _vendor_words(name) & asked
            same = [i for i in invoices
                    if i.extracted and i.extracted.vendor_name and key & _vendor_words(i.extracted.vendor_name)]
            return name, same
    return None


def _listing(title: str, invoices: list[Invoice], dec_repo: DecisionRepository, with_reason: bool) -> str:
    if not invoices:
        return f"{title}: ninguna."
    lines = [f"{title}: {len(invoices)}."]
    for invoice in invoices[:MAX_LISTED]:
        reason = ""
        if with_reason:
            latest = dec_repo.list_by_invoice(invoice.id)
            reason = f" — {_failed(latest[0])}" if latest and _failed(latest[0]) else ""
        lines.append(f"• {_label(invoice)}, {STATUS_LABEL.get(invoice.status, invoice.status.value)}{reason}")
    if len(invoices) > MAX_LISTED:
        lines.append(f"…y {len(invoices) - MAX_LISTED} más (todas están en el Registro de decisiones).")
    return "\n".join(lines)


def answer_question(
    text: str,
    *,
    inv_repo: InvoiceRepository,
    dec_repo: DecisionRepository,
    rule_repo: RuleSetRepository,
    now: datetime,
) -> str:
    plain = _plain(text)
    invoices = inv_repo.list_all()

    named = _find_invoices(text, invoices)
    if named:
        return "\n\n".join(_explain_invoice(i, dec_repo) for i in named[:3])

    if re.search(r"cuanto|gasto|gastado|pagado|presupuesto|tope|limite", plain):
        rules = rule_repo.get_current()
        spent = dec_repo.sum_spent_between(start_dt=now - timedelta(days=rules.period_days))
        counts = {s: sum(1 for i in invoices if i.status == s) for s in InvoiceStatus}
        paid = counts[InvoiceStatus.paid] + counts[InvoiceStatus.approved]
        return (f"En los últimos {rules.period_days} días se han pagado {_money(spent, rules.base_currency)} de un "
                f"límite de {_money(rules.period_limit, rules.base_currency)}. Facturas: {paid} pagadas, "
                f"{counts[InvoiceStatus.pending_approval]} pendientes de aprobación y "
                f"{counts[InvoiceStatus.blocked] + counts[InvoiceStatus.rejected]} rechazadas.")

    if re.search(r"pendiente|aprobar|aprobacion|escalad|revisar", plain):
        pending = [i for i in invoices if i.status == InvoiceStatus.pending_approval]
        return _listing("Facturas pendientes de aprobación", pending, dec_repo, with_reason=True)

    if re.search(r"rechaz|frenad|bloquead|frenaste|rechazaste", plain):
        blocked = [i for i in invoices if i.status in (InvoiceStatus.blocked, InvoiceStatus.rejected)]
        return _listing("Facturas rechazadas", blocked, dec_repo, with_reason=True)

    if re.search(r"pagad|pagaste", plain):
        paid = [i for i in invoices if i.status in (InvoiceStatus.paid, InvoiceStatus.approved)]
        return _listing("Facturas pagadas", paid, dec_repo, with_reason=False)

    vendor = _vendor_invoices(text, invoices)
    if vendor:
        name, same = vendor
        return _listing(f"Facturas de {name}", same, dec_repo, with_reason=True)

    if not invoices:
        return "Todavía no hay facturas revisadas. " + HELP_TEXT
    return "No encontré esa factura ni entendí la pregunta.\n" + HELP_TEXT
