import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException

from app.agent.pipeline import reevaluate
from app.api.deps import (
    get_agreement_repo,
    get_beneficiary_repo,
    get_decision_repo,
    get_invoice_repo,
    get_rule_repo,
)
from app.engine.rules import Facts, r02_not_duplicate, r05_not_sanctioned, to_base
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
    invoice = inv_repo.get(invoice_id, for_update=True)
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if invoice.status != InvoiceStatus.pending_approval:
        raise HTTPException(
            status_code=409,
            detail=f"Solo se pueden aprobar facturas en estado 'pending_approval' (estado actual: '{invoice.status.value}')",
        )

    # 1. Validación crítica de extracción de datos antes de permitir pago humano
    if not invoice.extracted:
        raise HTTPException(
            status_code=409,
            detail="No se puede aprobar una factura sin datos extraídos.",
        )
    ext = invoice.extracted
    if ext.amount is None or ext.amount <= Decimal("0.00"):
        raise HTTPException(
            status_code=409,
            detail="No se puede aprobar la factura: el monto es inválido o no fue extraído.",
        )
    if not (ext.currency and ext.currency.strip()):
        raise HTTPException(
            status_code=409,
            detail="No se puede aprobar la factura: la moneda no está especificada.",
        )
    if not (ext.vendor_name or ext.vendor_tax_id):
        raise HTTPException(
            status_code=409,
            detail="No se puede aprobar la factura: falta el proveedor o beneficiario (nombre o NIT).",
        )

    # 2. Re-comprobación de reglas duras: R02 (duplicados) y R05 (sancionados)
    rules = rule_repo.get_current()
    amount_base = to_base(ext.amount, ext.currency, rules)
    facts = Facts(
        invoice=ext,
        rules=rules,
        ctx=EvaluationContext(
            today=datetime.now(UTC).date(),
            previous_invoices=inv_repo.list_previous_extractions(
                exclude_invoice_id=invoice.id,
                before_dt=invoice.received_at,
            ),
        ),
        amount_base=amount_base,
    )
    r02_check = r02_not_duplicate(facts)
    if r02_check.status == CheckStatus.failed:
        raise HTTPException(
            status_code=409,
            detail=f"No se puede aprobar la factura: {r02_check.message}",
        )
    if rules.block_sanctioned:
        r05_check = r05_not_sanctioned(facts)
        if r05_check.status == CheckStatus.failed:
            raise HTTPException(
                status_code=409,
                detail=f"No se puede aprobar la factura: {r05_check.message}",
            )

    # 3. Transición atómica de estado: evita race conditions si llegan dos solicitudes simultáneas
    transitioned = inv_repo.transition_status(
        invoice_id=invoice.id,
        from_status=InvoiceStatus.pending_approval,
        to_status=InvoiceStatus.approved,
        commit=False,  # committed together with the decision below: never a status change without its record
    )
    if not transitioned:
        raise HTTPException(
            status_code=409,
            detail="Conflicto de concurrencia: la factura ya fue procesada o cambió de estado.",
        )

    prev_decisions = dec_repo.list_by_invoice(invoice_id)
    last_decision = prev_decisions[0] if prev_decisions else None
    amount_base = last_decision.amount_base_currency if last_decision else None
    if amount_base is None and ext.amount and (ext.currency or "").upper() == rules.base_currency.upper():
        amount_base = ext.amount

    new_decision = Decision(
        id=f"dec-{uuid.uuid4().hex[:10]}",
        invoice_id=invoice.id,
        outcome=Outcome.pay,
        actor=Actor.human,
        checks=last_decision.checks if last_decision else [],
        summary=f"Aprobada manualmente por {payload.approver}.",
        explanation=payload.comment,
        rule_set_version=rules.version,
        amount_base_currency=amount_base,
        approver=payload.approver,
        comment=payload.comment,
        created_at=datetime.now(UTC),
    )
    dec_repo.add(new_decision)
    return new_decision


@router.post("/{invoice_id}/reject", response_model=Decision)
def reject_invoice(
    invoice_id: str,
    payload: ApprovalRequest,
    inv_repo: InvoiceRepository = Depends(get_invoice_repo),
    dec_repo: DecisionRepository = Depends(get_decision_repo),
    rule_repo: RuleSetRepository = Depends(get_rule_repo),
) -> Decision:
    invoice = inv_repo.get(invoice_id, for_update=True)
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if invoice.status != InvoiceStatus.pending_approval:
        raise HTTPException(
            status_code=409,
            detail=f"Solo se pueden rechazar facturas en estado 'pending_approval' (estado actual: '{invoice.status.value}')",
        )

    # Transición atómica de estado
    transitioned = inv_repo.transition_status(
        invoice_id=invoice.id,
        from_status=InvoiceStatus.pending_approval,
        to_status=InvoiceStatus.rejected,
        commit=False,  # committed together with the decision below: never a status change without its record
    )
    if not transitioned:
        raise HTTPException(
            status_code=409,
            detail="Conflicto de concurrencia: la factura ya fue procesada o cambió de estado.",
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
