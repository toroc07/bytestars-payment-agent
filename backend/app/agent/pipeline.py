"""Agent pipeline (docs/ARCHITECTURE.md §3): register -> extract -> context -> engine -> explain -> persist.

Called by api/routes/chat.py. The LLM only reads the invoice; the engine decides. Once the invoice is
registered, any failure ends in an `escalate` decision for that same invoice (fail-closed), never in an
exception, so the route does not register it twice.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.agent.explain import explain
from app.agent.extraction import Extraction, extract, looks_like_invoice
from app.agent.query import HELP_TEXT, answer_question, looks_like_question
from app.engine import evaluate
from app.llm import LLMChain, get_llm
from app.ports import (
    AgreementRepository,
    BeneficiaryRepository,
    ConversationRepository,
    DecisionRepository,
    InvoiceRepository,
    LlmCacheRepository,
    RuleSetRepository,
)
from app.schemas import (
    Actor,
    Agreement,
    Beneficiary,
    ChatMessage,
    CheckStatus,
    Decision,
    EngineResult,
    EvaluationContext,
    ExtractedInvoice,
    Invoice,
    InvoiceStatus,
    Outcome,
    RuleCheck,
    RuleSet,
    SendMessageResponse,
    SourceType,
)

log = logging.getLogger(__name__)

STATUS_BY_OUTCOME = {
    Outcome.pay: InvoiceStatus.paid,
    Outcome.block: InvoiceStatus.blocked,
    Outcome.escalate: InvoiceStatus.pending_approval,
}



def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def sniff_mime(data: bytes | None) -> str | None:
    if not data:
        return None
    if data.startswith(b"%PDF"):
        return "application/pdf"
    if data.startswith(b"\x89PNG"):
        return "image/png"
    if data.startswith(b"\xff\xd8"):
        return "image/jpeg"
    return None


def pick_agreement(agreements: list[Agreement], invoice: ExtractedInvoice) -> Agreement | None:
    """The agreement in force on the issue date; the one with the same purchase order first."""
    day = invoice.issue_date

    def in_force(a: Agreement) -> bool:
        return day is None or ((a.valid_from is None or a.valid_from <= day) and (a.valid_to is None or day <= a.valid_to))

    valid = [a for a in agreements if in_force(a)]
    po = (invoice.po_reference or "").strip().upper()
    return next((a for a in valid if po and (a.po_reference or "").strip().upper() == po), valid[0] if valid else None)


def build_context(
    invoice: ExtractedInvoice | None,
    invoice_id: str,
    rules: RuleSet,
    now: datetime,
    ben_repo: BeneficiaryRepository,
    agr_repo: AgreementRepository,
    inv_repo: InvoiceRepository,
    dec_repo: DecisionRepository,
) -> EvaluationContext:
    """Step 4: everything the engine needs, read from the repositories (no LLM)."""
    window_start = now - timedelta(days=rules.period_days)
    today = now.date()
    if invoice is None:
        return EvaluationContext(today=today, spent_in_period=dec_repo.sum_spent_between(start_dt=window_start))

    beneficiary: Beneficiary | None = ben_repo.find_match(
        tax_id=invoice.vendor_tax_id, account=invoice.beneficiary_account, name=invoice.vendor_name
    )
    agreement = pick_agreement(agr_repo.find_by_beneficiary(beneficiary.id), invoice) if beneficiary else None
    vendor_name = beneficiary.name if beneficiary else invoice.vendor_name
    vendor_tax_id = beneficiary.tax_id if beneficiary else invoice.vendor_tax_id
    has_vendor = bool(vendor_name or vendor_tax_id)
    return EvaluationContext(
        today=today,
        beneficiary=beneficiary,
        agreement=agreement,
        previous_invoices=inv_repo.list_previous_extractions(exclude_invoice_id=invoice_id),
        last_vendor_invoice=inv_repo.get_last_paid_for_vendor(
            vendor_name=vendor_name, vendor_tax_id=vendor_tax_id, exclude_invoice_id=invoice_id
        ) if has_vendor else None,
        spent_in_period=dec_repo.sum_spent_between(start_dt=window_start),
        vendor_spent_in_period=dec_repo.sum_spent_between(
            start_dt=window_start, vendor_name=vendor_name, vendor_tax_id=vendor_tax_id
        ) if has_vendor else Decimal("0.00"),
    )


def _pipeline_error(exc: Exception) -> EngineResult:
    return EngineResult(
        outcome=Outcome.escalate,
        checks=[RuleCheck(
            rule_id="R00", rule_name="ENGINE_ERROR", status=CheckStatus.failed, outcome_if_failed="escalate",
            observed=f"error del agente: {type(exc).__name__}", expected="procesamiento completo",
            message="El agente no pudo terminar de revisar la factura; queda para una persona (fail-closed).",
        )],
        summary="Escalada a una persona: el agente no pudo terminar la revisión.",
    )


def _with_cache(llm: LLMChain, cache_repo: LlmCacheRepository | None) -> LLMChain:
    """LLM readings also go to the database, so a reading survives restarts and serverless instances."""
    if cache_repo is None or llm.cache is None:  # LLM_CACHE=false disables every cache layer
        return llm
    return llm.with_store(cache_repo)


def _title(invoice: ExtractedInvoice | None, filename: str | None, text: str | None) -> str:
    if invoice and invoice.vendor_name and invoice.invoice_number:
        return f"{invoice.vendor_name} · {invoice.invoice_number}"[:80]
    return (filename or (text or "Factura").strip().splitlines()[0])[:80]


def handle_chat_turn(
    *,
    conversation_id: str,
    user_message: ChatMessage,
    text: str | None,
    file_bytes: bytes | None,
    filename: str | None,
    source_type: SourceType,
    conv_repo: ConversationRepository,
    inv_repo: InvoiceRepository,
    dec_repo: DecisionRepository,
    rule_repo: RuleSetRepository,
    ben_repo: BeneficiaryRepository,
    agr_repo: AgreementRepository,
    llm: LLMChain | None = None,
    cache_repo: LlmCacheRepository | None = None,
    clock=lambda: datetime.now(UTC),
) -> SendMessageResponse:
    question = file_bytes is None and looks_like_question(text)
    if question or (file_bytes is None and not looks_like_invoice(text)):
        # Read-only answer (or help): nothing is registered and nothing can be approved from here.
        content = answer_question(text or "", inv_repo=inv_repo, dec_repo=dec_repo, rule_repo=rule_repo,
                                  now=clock()) if question else HELP_TEXT
        reply = ChatMessage(id=_new_id("msg"), conversation_id=conversation_id, role="assistant",
                            content=content, created_at=clock())
        conv_repo.add_message(reply)
        return SendMessageResponse(user_message=user_message, assistant_message=reply, invoice=None)

    rules = rule_repo.get_current()
    now = clock()
    invoice = inv_repo.add(Invoice(
        id=_new_id("inv"), source_type=source_type, source_filename=filename, raw_text=text,
        extracted=None, status=InvoiceStatus.received, received_at=now,
    ))

    extraction = Extraction(None, "none")
    try:
        extraction = extract(text=text, file_bytes=file_bytes, mime_type=sniff_mime(file_bytes),
                             company_name=rules.company_name, llm=_with_cache(llm or get_llm(), cache_repo))
        if extraction.invoice is not None:
            invoice = inv_repo.update(invoice.model_copy(update={"extracted": extraction.invoice}))
        context = build_context(extraction.invoice, invoice.id, rules, now, ben_repo, agr_repo, inv_repo, dec_repo)
        result = evaluate(extraction.invoice, rules, context)
    except Exception as exc:  # fail-closed: the invoice exists, so decide escalate on it
        log.exception("agent pipeline failed for invoice %s", invoice.id)
        result = _pipeline_error(exc)

    decision = dec_repo.add(Decision(
        id=_new_id("dec"),
        invoice_id=invoice.id,
        outcome=result.outcome,
        actor=Actor.agent,
        checks=result.checks,
        summary=result.summary,
        explanation=explain(result, extraction.invoice, extraction.source, extraction.error),
        rule_set_version=rules.version,
        amount_base_currency=result.amount_base_currency,
        created_at=clock(),
    ))
    invoice = inv_repo.update(invoice.model_copy(update={"status": STATUS_BY_OUTCOME[result.outcome]}))

    reply = conv_repo.add_message(ChatMessage(
        id=_new_id("msg"), conversation_id=conversation_id, role="assistant", content=result.summary,
        invoice_id=invoice.id, decision=decision, created_at=clock(),
    ))
    conv_repo.update_metadata(conversation_id=conversation_id, title=_title(extraction.invoice, filename, text),
                              invoice_id=invoice.id)
    return SendMessageResponse(user_message=user_message, assistant_message=reply, invoice=invoice)


def reevaluate(
    invoice: Invoice,
    *,
    inv_repo: InvoiceRepository,
    dec_repo: DecisionRepository,
    rule_repo: RuleSetRepository,
    ben_repo: BeneficiaryRepository,
    agr_repo: AgreementRepository,
    clock=lambda: datetime.now(UTC),
) -> Decision:
    """New agent decision for a stored invoice with the current rules and data (no new reading).

    Same context and failure handling as a chat turn; the previous decisions stay as they were.
    """
    rules = rule_repo.get_current()
    now = clock()
    try:
        context = build_context(invoice.extracted, invoice.id, rules, now, ben_repo, agr_repo, inv_repo, dec_repo)
        result = evaluate(invoice.extracted, rules, context)
    except Exception as exc:  # fail-closed: a broken re-evaluation leaves the invoice for a person
        log.exception("re-evaluation failed for invoice %s", invoice.id)
        result = _pipeline_error(exc)
    decision = dec_repo.add(Decision(
        id=_new_id("dec"),
        invoice_id=invoice.id,
        outcome=result.outcome,
        actor=Actor.agent,
        checks=result.checks,
        summary=result.summary,
        explanation=explain(result, invoice.extracted, "stored", None),
        rule_set_version=rules.version,
        amount_base_currency=result.amount_base_currency,
        created_at=clock(),
    ))
    inv_repo.update(invoice.model_copy(update={"status": STATUS_BY_OUTCOME[result.outcome]}))
    return decision
