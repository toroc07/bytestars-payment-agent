"""Engine tests: one scenario per rule, aggregation, overrides and the safety invariants (I1-I4)."""

from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.engine import evaluate
from app.schemas import Agreement, Beneficiary, CheckStatus, EvaluationContext, ExtractedInvoice, Outcome, RuleSet

RULES = RuleSet(
    company_name="Distribuciones Andinas S.A.S.",
    base_currency="USD",
    fx_rates={"USD": Decimal(1), "COP": Decimal("0.00025")},
    allowed_currencies=["USD", "COP"],
    approval_threshold=Decimal(5000),
    per_payment_limit=Decimal(10000),
    period_days=7,
    period_limit=Decimal(50000),
    per_vendor_period_limit=Decimal(20000),
    period_budget=Decimal(50000),
    required_fields=["vendor_name", "invoice_number", "amount", "issue_date", "description"],
    sanctioned_countries=["KP", "IR", "SY", "CU", "RU"],
)

VENDOR = Beneficiary(
    id="ben-aseo", name="Aseo Total Servicios S.A.S.", tax_id="901.022.366-3",
    account="81629733626", country="CO", allowed=True, verified=True, sanctioned=False,
)


def invoice(**overrides) -> ExtractedInvoice:
    data = {
        "invoice_number": "ATS-818", "vendor_name": "Aseo Total Servicios S.A.S.", "vendor_tax_id": "901.022.366-3",
        "beneficiary_account": "81629733626", "vendor_country": "CO", "amount": Decimal(780), "currency": "USD",
        "issue_date": date(2026, 9, 16), "due_date": date(2026, 10, 16), "description": "Insumos de limpieza",
        "confidence": 0.95,
    }
    data.update(overrides)
    return ExtractedInvoice(**data)


def ctx(**overrides) -> EvaluationContext:
    data = {"today": date(2026, 10, 1), "beneficiary": VENDOR}
    data.update(overrides)
    return EvaluationContext(**data)


def failed_ids(result) -> list[str]:
    return [c.rule_id for c in result.checks if c.status == CheckStatus.failed]


def test_clean_invoice_is_paid():
    result = evaluate(invoice(), RULES, ctx())
    assert result.outcome == Outcome.pay
    assert failed_ids(result) == []
    assert result.amount_base_currency == Decimal(780)


def test_missing_required_field_escalates():
    result = evaluate(invoice(description=None), RULES, ctx())
    assert result.outcome == Outcome.escalate and failed_ids(result) == ["R01"]


def test_low_confidence_escalates():
    assert failed_ids(evaluate(invoice(confidence=0.4), RULES, ctx())) == ["R01"]


def test_duplicate_is_rejected():
    result = evaluate(invoice(), RULES, ctx(previous_invoices=[invoice(beneficiary_account=None)]))
    assert result.outcome == Outcome.block and "R02" in failed_ids(result)


def test_same_charge_with_new_number_is_rejected():
    first = invoice(invoice_number="ATS-700", po_reference="OC-2026-0408")
    result = evaluate(invoice(po_reference="oc 2026 0408"), RULES, ctx(previous_invoices=[first]))
    assert result.outcome == Outcome.block and "R02" in failed_ids(result)


def test_same_po_with_other_amount_or_no_po_is_not_duplicate():
    other_amount = invoice(invoice_number="ATS-700", po_reference="OC-2026-0408", amount=Decimal(100))
    no_po = invoice(invoice_number="ATS-701", po_reference="No aplica")
    result = evaluate(invoice(po_reference="OC-2026-0408"), RULES, ctx(previous_invoices=[other_amount]))
    assert "R02" not in failed_ids(result)
    assert "R02" not in failed_ids(evaluate(invoice(po_reference="No aplica"), RULES, ctx(previous_invoices=[no_po])))


def test_unknown_vendor_is_rejected():
    result = evaluate(invoice(vendor_name="Proveedor Nuevo SAS", vendor_tax_id="999"), RULES, ctx(beneficiary=None))
    assert result.outcome == Outcome.block and "R03" in failed_ids(result)


def test_unverified_vendor_is_rejected():
    result = evaluate(invoice(), RULES, ctx(beneficiary=VENDOR.model_copy(update={"verified": False})))
    assert result.outcome == Outcome.block and "R04" in failed_ids(result)


def test_sanctioned_country_is_rejected_even_without_beneficiary():
    result = evaluate(invoice(vendor_country="IR"), RULES, ctx(beneficiary=None))
    assert result.outcome == Outcome.block and {"R03", "R05"} <= set(failed_ids(result))


def test_unknown_currency_escalates():
    result = evaluate(invoice(currency="JPY"), RULES, ctx())
    assert result.outcome == Outcome.escalate and failed_ids(result) == ["R06"]


def test_cop_is_converted_to_base_currency():
    result = evaluate(invoice(amount=Decimal(3105900), currency="COP"), RULES, ctx())
    assert result.amount_base_currency == Decimal("776.48")
    assert result.outcome == Outcome.pay


def test_over_per_payment_limit_is_rejected():
    result = evaluate(invoice(amount=Decimal(12000)), RULES, ctx())
    assert result.outcome == Outcome.block
    assert {"R07", "R08"} <= set(failed_ids(result))


def test_over_approval_threshold_escalates():
    result = evaluate(invoice(amount=Decimal(6000)), RULES, ctx())
    assert result.outcome == Outcome.escalate and failed_ids(result) == ["R08"]


def test_period_limit_escalates():
    result = evaluate(invoice(amount=Decimal(1000)), RULES, ctx(spent_in_period=Decimal(49500)))
    assert result.outcome == Outcome.escalate and "R09" in failed_ids(result)


def test_vendor_period_limit_escalates():
    result = evaluate(invoice(amount=Decimal(1000)), RULES, ctx(vendor_spent_in_period=Decimal(19500)))
    assert result.outcome == Outcome.escalate and failed_ids(result) == ["R10"]


def test_bank_account_change_escalates():
    result = evaluate(invoice(beneficiary_account="111"), RULES, ctx())
    assert result.outcome == Outcome.escalate and failed_ids(result) == ["R11"]


def test_impersonation_with_other_tax_id_escalates():
    result = evaluate(invoice(vendor_tax_id="901.233.780-5"), RULES, ctx())
    assert "R11" in failed_ids(result) and result.outcome == Outcome.escalate


def test_account_change_against_last_payment_escalates():
    last = invoice(invoice_number="ATS-700", beneficiary_account="222")
    unregistered = VENDOR.model_copy(update={"account": None})
    result = evaluate(invoice(), RULES, ctx(beneficiary=unregistered, last_vendor_invoice=last))
    assert failed_ids(result) == ["R11"]


def test_varying_amount_against_last_payment_is_paid():
    last = invoice(invoice_number="ATS-700", amount=Decimal(500))
    assert evaluate(invoice(), RULES, ctx(last_vendor_invoice=last)).outcome == Outcome.pay


def test_amount_outside_agreement_tolerance_escalates():
    agreed = Agreement(id="agr-1", beneficiary_id="ben-aseo", description="Aseo", expected_amount=Decimal(700),
                       currency="USD")
    assert failed_ids(evaluate(invoice(), RULES, ctx(agreement=agreed))) == ["R11"]  # 780 vs 700 = 11.4 %
    within = agreed.model_copy(update={"expected_amount": Decimal(760)})
    assert evaluate(invoice(), RULES, ctx(agreement=within)).outcome == Outcome.pay  # 2.6 %


def test_block_wins_over_escalate():
    result = evaluate(invoice(amount=Decimal(6000), beneficiary_account="111"), RULES, ctx(beneficiary=None))
    assert result.outcome == Outcome.block


def test_override_can_soften_block_to_escalate_but_never_pay():
    rules = RULES.model_copy(update={"severity_overrides": {"R03": "escalate"}})
    result = evaluate(invoice(vendor_tax_id="999", vendor_name="Otro SAS"), rules, ctx(beneficiary=None))
    assert result.outcome == Outcome.escalate
    with pytest.raises(ValueError):
        RuleSet(**{**RULES.model_dump(), "severity_overrides": {"R03": "pay"}})


def test_no_invoice_escalates():
    result = evaluate(None, RULES, ctx())
    assert result.outcome == Outcome.escalate and "R01" in failed_ids(result)


def test_every_rule_reports_a_check_with_a_message():
    result = evaluate(invoice(), RULES, ctx())
    assert [c.rule_id for c in result.checks] == [f"R{n:02d}" for n in range(1, 12)]
    assert all(c.message for c in result.checks)


# ---- Safety invariants over random inputs ------------------------------------------------------

money = st.one_of(st.none(), st.decimals(min_value=Decimal("0.01"), max_value=Decimal(100000), places=2))
maybe_text = st.one_of(st.none(), st.sampled_from(["", "ATS-818", "X-1", "Aseo Total Servicios S.A.S."]))


@st.composite
def random_invoices(draw):
    return ExtractedInvoice(
        invoice_number=draw(maybe_text),
        vendor_name=draw(maybe_text),
        vendor_tax_id=draw(st.one_of(st.none(), st.sampled_from(["901.022.366-3", "123"]))),
        beneficiary_account=draw(st.one_of(st.none(), st.sampled_from(["81629733626", "111"]))),
        vendor_country=draw(st.one_of(st.none(), st.sampled_from(["CO", "IR", "US"]))),
        amount=draw(money),
        currency=draw(st.one_of(st.none(), st.sampled_from(["USD", "COP", "JPY"]))),
        issue_date=draw(st.one_of(st.none(), st.just(date(2026, 9, 16)))),
        description=draw(st.one_of(st.none(), st.just("Servicio"))),
        confidence=draw(st.floats(min_value=0, max_value=1)),
    )


@st.composite
def random_contexts(draw):
    beneficiary = draw(st.one_of(st.none(), st.builds(
        lambda allowed, verified, sanctioned: VENDOR.model_copy(
            update={"allowed": allowed, "verified": verified, "sanctioned": sanctioned}),
        st.booleans(), st.booleans(), st.booleans())))
    return EvaluationContext(
        today=date(2026, 10, 1),
        beneficiary=beneficiary,
        spent_in_period=draw(st.decimals(min_value=Decimal(0), max_value=Decimal(60000), places=2)),
        vendor_spent_in_period=draw(st.decimals(min_value=Decimal(0), max_value=Decimal(25000), places=2)),
    )


@settings(max_examples=300, deadline=None)
@given(random_invoices(), random_contexts())
def test_pay_never_with_a_failed_rule(inv, context):
    result = evaluate(inv, RULES, context)
    if result.outcome == Outcome.pay:
        assert not any(c.status == CheckStatus.failed for c in result.checks)  # I1


@settings(max_examples=300, deadline=None)
@given(random_invoices(), random_contexts())
def test_missing_essentials_never_pay(inv, context):
    result = evaluate(inv, RULES, context)
    if inv.amount is None or not inv.currency or context.beneficiary is None:
        assert result.outcome != Outcome.pay  # I4


@settings(max_examples=200, deadline=None)
@given(random_invoices(), random_contexts())
def test_deterministic(inv, context):
    assert evaluate(inv, RULES, context) == evaluate(inv, RULES, context)  # I2


def test_unreadable_vendor_escalates_instead_of_rejecting():
    result = evaluate(invoice(vendor_name=None, vendor_tax_id=None), RULES, ctx(beneficiary=None))
    assert result.outcome == Outcome.escalate and {"R01", "R03"} <= set(failed_ids(result))


def test_internal_error_escalates(monkeypatch):
    import importlib

    engine = importlib.import_module("app.engine.evaluate")

    def boom(_facts):
        raise RuntimeError("bug")

    monkeypatch.setattr(engine, "RULES", [boom])
    result = engine.evaluate(invoice(), RULES, ctx())
    assert result.outcome == Outcome.escalate and result.checks[0].rule_id == "R00"  # I3
