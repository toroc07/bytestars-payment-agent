from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_decision_repo, get_invoice_repo, get_rule_repo
from app.ports import DecisionRepository, InvoiceRepository, RuleSetRepository
from app.schemas import Decision, Invoice, InvoiceStatus, Outcome, SummaryResponse

router = APIRouter(prefix="/api", tags=["invoices"])


@router.get("/invoices", response_model=list[Invoice])
def list_invoices(
    status: InvoiceStatus | None = Query(default=None),
    repo: InvoiceRepository = Depends(get_invoice_repo),
) -> list[Invoice]:
    return repo.list_all(status=status)


@router.get("/invoices/{invoice_id}", response_model=Invoice)
def get_invoice(
    invoice_id: str,
    repo: InvoiceRepository = Depends(get_invoice_repo),
) -> Invoice:
    invoice = repo.get(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return invoice


@router.get("/invoices/{invoice_id}/decisions", response_model=list[Decision])
def list_invoice_decisions(
    invoice_id: str,
    inv_repo: InvoiceRepository = Depends(get_invoice_repo),
    dec_repo: DecisionRepository = Depends(get_decision_repo),
) -> list[Decision]:
    if not inv_repo.get(invoice_id):
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return dec_repo.list_by_invoice(invoice_id)


@router.get("/decisions", response_model=list[Decision])
def list_decisions(
    outcome: Outcome | None = Query(default=None),
    status: InvoiceStatus | None = Query(default=None),
    dec_repo: DecisionRepository = Depends(get_decision_repo),
) -> list[Decision]:
    return dec_repo.list_all(outcome=outcome, status=status)


@router.get("/summary", response_model=SummaryResponse)
def get_summary(
    inv_repo: InvoiceRepository = Depends(get_invoice_repo),
    dec_repo: DecisionRepository = Depends(get_decision_repo),
    rule_repo: RuleSetRepository = Depends(get_rule_repo),
) -> SummaryResponse:
    invoices = inv_repo.list_all()
    rules = rule_repo.get_current()
    window_start = datetime.now(timezone.utc) - timedelta(days=rules.period_days)
    spent = dec_repo.sum_spent_between(start_dt=window_start)

    paid_count = sum(1 for i in invoices if i.status in (InvoiceStatus.paid, InvoiceStatus.approved))
    blocked_count = sum(1 for i in invoices if i.status in (InvoiceStatus.blocked, InvoiceStatus.rejected))
    pending_count = sum(1 for i in invoices if i.status == InvoiceStatus.pending_approval)

    return SummaryResponse(
        paid_count=paid_count,
        blocked_count=blocked_count,
        pending_count=pending_count,
        spent_in_period=spent,
        period_limit=rules.period_limit,
        period_budget=rules.period_budget,
    )
