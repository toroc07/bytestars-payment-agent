"""Replays dataset/expected.json through the engine: outcomes must match and no trap may be paid.

It feeds the engine the expected extraction (not the LLM), so it checks the rules, not the reading.
"""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.engine import evaluate
from app.schemas import Beneficiary, EvaluationContext, ExtractedInvoice, Outcome, RuleSet

DATASET = Path(__file__).resolve().parents[3] / "dataset"
pytestmark = pytest.mark.skipif(not (DATASET / "expected.json").exists(), reason="dataset/expected.json missing")


def find_beneficiary(inv: ExtractedInvoice, beneficiaries: list[Beneficiary]) -> Beneficiary | None:
    """Same order as SqlBeneficiaryRepository.find_match: tax id, account, then name."""
    for key, value in (("tax_id", inv.vendor_tax_id), ("account", inv.beneficiary_account)):
        match = next((b for b in beneficiaries if value and getattr(b, key) == value.strip()), None)
        if match:
            return match
    name = " ".join((inv.vendor_name or "").lower().split())
    return next((b for b in beneficiaries if name and " ".join(b.name.lower().split()) == name), None)


def test_engine_matches_expected_results():
    company = json.loads((DATASET / "company.json").read_text(encoding="utf-8"))
    expected = json.loads((DATASET / "expected.json").read_text(encoding="utf-8"))
    rules = RuleSet.model_validate(company["rule_set"])
    beneficiaries = [Beneficiary.model_validate(b) for b in company["beneficiaries"]]

    registered: list[ExtractedInvoice] = []
    paid: list[ExtractedInvoice] = []
    mismatches = []
    for case in expected["invoices"]:
        inv = ExtractedInvoice(**case["expected_extraction"], vendor_country="CO", confidence=0.95)
        vendor_paid = [p for p in paid if p.vendor_tax_id == inv.vendor_tax_id]
        result = evaluate(inv, rules, EvaluationContext(
            today=date(2026, 10, 17),
            beneficiary=find_beneficiary(inv, beneficiaries),
            previous_invoices=list(registered),
            last_vendor_invoice=vendor_paid[-1] if vendor_paid else None,
            spent_in_period=sum((p.amount for p in paid), Decimal(0)),
            vendor_spent_in_period=sum((p.amount for p in vendor_paid), Decimal(0)),
        ))
        registered.append(inv)
        if result.outcome == Outcome.pay:
            paid.append(inv)
        assert not (case["case"] != "normal" and result.outcome == Outcome.pay), f"{case['file']}: trap paid"
        if result.outcome.value != case["expected_outcome"]:
            mismatches.append((case["file"], case["expected_outcome"], result.outcome.value))

    assert mismatches == []
