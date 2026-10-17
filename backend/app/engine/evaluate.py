"""Deterministic decision engine (docs/DECISION_ENGINE.md).

- Pure: no I/O, no DB, no LLM, no clock (the date arrives in ctx.today).
- Fail-closed: any exception or missing invoice ends in `escalate`, never `pay`.
- Aggregation: a failed `block` rule wins over a failed `escalate` rule; `pay` only with zero failures.
- `severity_overrides` may swap a rule between block and escalate; nothing turns a failure into pay.
"""

from app.engine.rules import RULES, Facts, money, to_base
from app.schemas import CheckStatus, EngineResult, EvaluationContext, ExtractedInvoice, Outcome, RuleCheck, RuleSet


def _apply_override(check: RuleCheck, rules: RuleSet) -> RuleCheck:
    override = rules.severity_overrides.get(check.rule_id)
    if override in ("block", "escalate") and override != check.outcome_if_failed:
        return check.model_copy(update={"outcome_if_failed": override})
    return check


def _summary(outcome: Outcome, failed: list[RuleCheck], invoice: ExtractedInvoice, amount_text: str) -> str:
    who = invoice.vendor_name or "el proveedor"
    if outcome == Outcome.pay:
        return f"Pagar {amount_text} a {who}: se cumplen todas las reglas."
    reasons = " ".join(c.message for c in failed)
    if outcome == Outcome.block:
        return f"Rechazada: {reasons}"
    return f"Escalada a una persona: {reasons}"


def _fail_closed(reason: str) -> EngineResult:
    return EngineResult(
        outcome=Outcome.escalate,
        checks=[
            RuleCheck(
                rule_id="R00",
                rule_name="ENGINE_ERROR",
                status=CheckStatus.failed,
                outcome_if_failed="escalate",
                observed=reason,
                expected="evaluación completa",
                message="El motor no pudo evaluar la factura; se escala por seguridad.",
            )
        ],
        summary="Escalada a una persona: el motor no pudo evaluar la factura.",
        amount_base_currency=None,
    )


def evaluate(invoice: ExtractedInvoice | None, rules: RuleSet, ctx: EvaluationContext) -> EngineResult:
    if invoice is None:
        invoice = ExtractedInvoice()  # nothing extracted: R01 fails and the invoice escalates
    try:
        amount_base = to_base(invoice.amount, invoice.currency, rules)
        facts = Facts(invoice=invoice, rules=rules, ctx=ctx, amount_base=amount_base)
        checks = [_apply_override(rule(facts), rules) for rule in RULES]

        failed = [c for c in checks if c.status == CheckStatus.failed]
        if any(c.outcome_if_failed == "block" for c in failed):
            outcome = Outcome.block
        elif failed:
            outcome = Outcome.escalate
        else:
            outcome = Outcome.pay

        # Rules whose failure decides the outcome lead the explanation.
        deciding = [c for c in failed if c.outcome_if_failed == outcome.value] or failed
        amount_text = money(invoice.amount, invoice.currency)
        return EngineResult(
            outcome=outcome,
            checks=checks,
            summary=_summary(outcome, deciding, invoice, amount_text),
            amount_base_currency=amount_base,
        )
    except Exception as exc:  # noqa: BLE001 - fail-closed by design
        return _fail_closed(f"{type(exc).__name__}: {exc}")
