import uuid
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import (
    get_agreement_repo,
    get_beneficiary_repo,
    get_decision_repo,
    get_invoice_repo,
    get_rule_repo,
)
from app.ports import (
    AgreementRepository,
    BeneficiaryRepository,
    DecisionRepository,
    InvoiceRepository,
    RuleSetRepository,
)
from app.schemas import (
    Actor,
    ApprovalRequest,
    CheckStatus,
    Decision,
    EvaluationContext,
    InvoiceStatus,
    Outcome,
    RuleCheck,
)

router = APIRouter(prefix="/api/invoices", tags=["approvals"])


@router.post("/{invoice_id}/approve", response_model=Decision)
def approve_invoice(
    invoice_id: str,
    payload: ApprovalRequest,
    inv_repo: InvoiceRepository = Depends(get_invoice_repo),
    dec_repo: DecisionRepository = Depends(get_decision_repo),
    rule_repo: RuleSetRepository = Depends(get_rule_repo),
) -> Decision:
    invoice = inv_repo.get(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if invoice.status != InvoiceStatus.pending_approval:
        raise HTTPException(
            status_code=409,
            detail=f"Solo se pueden aprobar facturas en estado 'pending_approval' (estado actual: '{invoice.status.value}')",
        )

    prev_decisions = dec_repo.list_by_invoice(invoice_id)
    last_decision = prev_decisions[0] if prev_decisions else None
    rules = rule_repo.get_current()

    new_decision = Decision(
        id=f"dec-{uuid.uuid4().hex[:10]}",
        invoice_id=invoice.id,
        outcome=Outcome.pay,
        actor=Actor.human,
        checks=last_decision.checks if last_decision else [],
        summary=f"Aprobada manualmente por {payload.approver}.",
        explanation=payload.comment,
        rule_set_version=rules.version,
        amount_base_currency=last_decision.amount_base_currency if last_decision else None,
        approver=payload.approver,
        comment=payload.comment,
        created_at=datetime.now(UTC),
    )
    dec_repo.add(new_decision)

    invoice.status = InvoiceStatus.approved
    inv_repo.update(invoice)
    return new_decision


@router.post("/{invoice_id}/reject", response_model=Decision)
def reject_invoice(
    invoice_id: str,
    payload: ApprovalRequest,
    inv_repo: InvoiceRepository = Depends(get_invoice_repo),
    dec_repo: DecisionRepository = Depends(get_decision_repo),
    rule_repo: RuleSetRepository = Depends(get_rule_repo),
) -> Decision:
    invoice = inv_repo.get(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if invoice.status != InvoiceStatus.pending_approval:
        raise HTTPException(
            status_code=409,
            detail=f"Solo se pueden rechazar facturas en estado 'pending_approval' (estado actual: '{invoice.status.value}')",
        )

    prev_decisions = dec_repo.list_by_invoice(invoice_id)
    last_decision = prev_decisions[0] if prev_decisions else None
    rules = rule_repo.get_current()

    new_decision = Decision(
        id=f"dec-{uuid.uuid4().hex[:10]}",
        invoice_id=invoice.id,
        outcome=Outcome.block,
        actor=Actor.human,
        checks=last_decision.checks if last_decision else [],
        summary=f"Rechazada manualmente por {payload.approver}.",
        explanation=payload.comment,
        rule_set_version=rules.version,
        amount_base_currency=last_decision.amount_base_currency if last_decision else None,
        approver=payload.approver,
        comment=payload.comment,
        created_at=datetime.now(UTC),
    )
    dec_repo.add(new_decision)

    invoice.status = InvoiceStatus.rejected
    inv_repo.update(invoice)
    return new_decision


@router.post("/{invoice_id}/reevaluate", response_model=Decision)
def reevaluate_invoice(
    invoice_id: str,
    inv_repo: InvoiceRepository = Depends(get_invoice_repo),
    dec_repo: DecisionRepository = Depends(get_decision_repo),
    rule_repo: RuleSetRepository = Depends(get_rule_repo),
    ben_repo: BeneficiaryRepository = Depends(get_beneficiary_repo),
    agr_repo: AgreementRepository = Depends(get_agreement_repo),
) -> Decision:
    invoice = inv_repo.get(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if invoice.status not in (InvoiceStatus.blocked, InvoiceStatus.pending_approval):
        raise HTTPException(
            status_code=409,
            detail=f"Solo se pueden reevaluar facturas en estado 'blocked' o 'pending_approval' (estado actual: '{invoice.status.value}')",
        )

    rules = rule_repo.get_current()
    extracted = invoice.extracted

    try:
        from app.engine import evaluate  # Implementado por Dev A

        matched_ben = (
            ben_repo.find_match(
                tax_id=extracted.vendor_tax_id if extracted else None,
                account=extracted.beneficiary_account if extracted else None,
                name=extracted.vendor_name if extracted else None,
            )
            if extracted
            else None
        )
        agreements = agr_repo.find_by_beneficiary(matched_ben.id) if matched_ben else []
        window_start = datetime.now(timezone.utc) - timedelta(days=rules.period_days)
        v_name = matched_ben.name if matched_ben else (extracted.vendor_name if extracted else None)
        v_tax = matched_ben.tax_id if matched_ben else (extracted.vendor_tax_id if extracted else None)

        ctx = EvaluationContext(
            today=date.today(),
            beneficiary=matched_ben,
            agreement=agreements[0] if agreements else None,
            previous_invoices=inv_repo.list_previous_extractions(exclude_invoice_id=invoice.id),
            last_vendor_invoice=inv_repo.get_last_paid_for_vendor(
                vendor_name=v_name, vendor_tax_id=v_tax, exclude_invoice_id=invoice.id
            ),
            spent_in_period=dec_repo.sum_spent_between(start_dt=window_start),
            vendor_spent_in_period=dec_repo.sum_spent_between(
                start_dt=window_start, vendor_name=v_name, vendor_tax_id=v_tax
            )
            if (v_name or v_tax)
            else Decimal("0.00"),
        )

        engine_res = evaluate(extracted, rules, ctx)
        outcome = engine_res.outcome
        checks = engine_res.checks
        summary = engine_res.summary
        amount_base = engine_res.amount_base_currency
    except Exception as exc:  # noqa: BLE001
        outcome = Outcome.escalate
        checks = [
            RuleCheck(
                rule_id="R01",
                rule_name="EXTRACTION_COMPLETE",
                status=CheckStatus.failed,
                outcome_if_failed="escalate",
                observed=str(exc),
                expected="Motor de reglas disponible y extracción válida",
                message="Se escaló por precaución (fail-closed) al re-evaluar la factura.",
            )
        ]
        summary = "Re-evaluación escalada a revisión humana (fail-closed)."
        amount_base = Decimal("0.00")

    status_map = {
        Outcome.pay: InvoiceStatus.paid,
        Outcome.block: InvoiceStatus.blocked,
        Outcome.escalate: InvoiceStatus.pending_approval,
    }
    invoice.status = status_map[outcome]
    inv_repo.update(invoice)

    decision = Decision(
        id=f"dec-{uuid.uuid4().hex[:10]}",
        invoice_id=invoice.id,
        outcome=outcome,
        actor=Actor.agent,
        checks=checks,
        summary=summary,
        rule_set_version=rules.version,
        amount_base_currency=amount_base,
        created_at=datetime.now(UTC),
    )
    return dec_repo.add(decision)
