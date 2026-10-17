import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException

from app.agent.pipeline import reevaluate
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
    Decision,
    InvoiceStatus,
    Outcome,
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

    return reevaluate(
        invoice, inv_repo=inv_repo, dec_repo=dec_repo, rule_repo=rule_repo, ben_repo=ben_repo, agr_repo=agr_repo
    )
