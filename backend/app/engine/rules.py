"""Rule catalog R01-R11 (docs/DECISION_ENGINE.md). Each rule is a pure function returning one RuleCheck.

Rules never decide alone: `evaluate` aggregates them (block > escalate > pay). A rule that cannot
apply returns a `skipped` check, which stays visible in the decision log.
"""

import re
from dataclasses import dataclass
from decimal import Decimal

from app.schemas import CheckStatus, EvaluationContext, ExtractedInvoice, RuleCheck, RuleSet

FIELD_LABELS = {
    "invoice_number": "número de factura",
    "vendor_name": "proveedor",
    "vendor_tax_id": "NIT / identificación fiscal",
    "beneficiary_account": "cuenta bancaria",
    "amount": "monto",
    "currency": "moneda",
    "issue_date": "fecha de emisión",
    "due_date": "fecha de vencimiento",
    "description": "concepto",
    "po_reference": "orden de compra",
}

PASSED, FAILED, SKIPPED = CheckStatus.passed, CheckStatus.failed, CheckStatus.skipped


@dataclass(frozen=True)
class Facts:
    """What every rule may read, computed once per evaluation."""

    invoice: ExtractedInvoice
    rules: RuleSet
    ctx: EvaluationContext
    amount_base: Decimal | None  # amount in the base currency; None if it cannot be computed


def money(amount: Decimal | None, currency: str | None) -> str:
    if amount is None:
        return "—"
    return f"{currency or ''} {amount:,.2f}".strip()


def digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def norm_name(value: str | None) -> str:
    text = (value or "").casefold()
    text = re.sub(r"\b(s\.?\s?a\.?\s?s\.?|s\.?\s?a\.?|ltda\.?|inc\.?|llc|gmbh|kk)(?=\W|$)", "", text)
    return re.sub(r"[^a-z0-9áéíóúñü]", "", text)


def to_base(amount: Decimal | None, currency: str | None, rules: RuleSet) -> Decimal | None:
    if amount is None or not currency:
        return None
    currency = currency.upper()
    if currency == rules.base_currency.upper():
        return amount
    rate = rules.fx_rates.get(currency)
    return None if rate is None else (amount * Decimal(rate)).quantize(Decimal("0.01"))


def check(
    rule_id: str,
    name: str,
    status: CheckStatus,
    outcome: str,
    message: str,
    observed: str | None = None,
    expected: str | None = None,
) -> RuleCheck:
    return RuleCheck(
        rule_id=rule_id,
        rule_name=name,
        status=status,
        outcome_if_failed=outcome,  # type: ignore[arg-type]
        observed=observed,
        expected=expected,
        message=message,
    )


def r01_required_fields(f: Facts) -> RuleCheck:
    missing = [k for k in f.rules.required_fields if getattr(f.invoice, k, None) in (None, "")]
    low_confidence = f.invoice.confidence < f.rules.min_extraction_confidence
    if missing or low_confidence:
        parts = []
        if missing:
            parts.append("falta " + ", ".join(FIELD_LABELS.get(k, k) for k in missing))
        if low_confidence:
            parts.append(f"la lectura es poco confiable ({f.invoice.confidence:.0%})")
        observed = ", ".join(FIELD_LABELS.get(k, k) for k in missing) or f"confianza {f.invoice.confidence:.0%}"
        return check(
            "R01", "REQUIRED_FIELDS", FAILED, "escalate",
            "Factura incompleta: " + " y ".join(parts) + ".",
            observed=observed,
            expected=f"todos los datos obligatorios y confianza ≥ {f.rules.min_extraction_confidence:.0%}",
        )
    return check("R01", "REQUIRED_FIELDS", PASSED, "escalate", "La factura trae todos los datos obligatorios.")


def _same_vendor(a: ExtractedInvoice, b: ExtractedInvoice) -> bool:
    if a.vendor_tax_id and b.vendor_tax_id:
        return digits(a.vendor_tax_id) == digits(b.vendor_tax_id)
    return bool(a.vendor_name and b.vendor_name and norm_name(a.vendor_name) == norm_name(b.vendor_name))


def _po_key(value: str | None) -> str:
    """Normalized purchase-order reference; empty when it carries no number (e.g. "No aplica")."""
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper()) if digits(value) else ""


def _same_charge(a: ExtractedInvoice, b: ExtractedInvoice) -> bool:
    """Same purchase order, amount and currency: the same charge re-sent under another number."""
    po = _po_key(a.po_reference)
    return bool(
        po and po == _po_key(b.po_reference)
        and a.amount is not None and a.amount == b.amount
        and (a.currency or "").upper() == (b.currency or "").upper()
    )


def r02_not_duplicate(f: Facts) -> RuleCheck:
    inv = f.invoice
    if not inv.invoice_number or not (inv.vendor_name or inv.vendor_tax_id):
        return check("R02", "NOT_DUPLICATE", SKIPPED, "block",
                     "No se puede comprobar si es duplicada: falta número de factura o proveedor.")
    number = inv.invoice_number.strip().upper()
    who = inv.vendor_name or inv.vendor_tax_id
    for prev in f.ctx.previous_invoices:
        if not _same_vendor(inv, prev):
            continue
        if prev.invoice_number and prev.invoice_number.strip().upper() == number:
            return check(
                "R02", "NOT_DUPLICATE", FAILED, "block",
                f"Duplicada: la factura {inv.invoice_number} de {who} ya fue registrada.",
                observed=f"{inv.invoice_number} ya registrada",
                expected="factura no registrada antes",
            )
        if _same_charge(inv, prev):
            return check(
                "R02", "NOT_DUPLICATE", FAILED, "block",
                f"Duplicada: {who} ya cobró {money(inv.amount, inv.currency)} por la orden {inv.po_reference} "
                f"en la factura {prev.invoice_number or 'anterior'}; esta repite el cobro con otro número.",
                observed=f"{inv.invoice_number} = {prev.invoice_number} (misma orden y monto)",
                expected="un solo cobro por orden de compra y monto",
            )
    return check("R02", "NOT_DUPLICATE", PASSED, "block",
                 "No hay otra factura registrada con ese número, ni con la misma orden y monto.")


def r03_beneficiary_allowed(f: Facts) -> RuleCheck:
    if not f.rules.require_allowlisted_beneficiary:
        return check("R03", "BENEFICIARY_ALLOWED", SKIPPED, "block", "La lista de permitidos no está activada.")
    b = f.ctx.beneficiary
    if b is None and not (f.invoice.vendor_name or f.invoice.vendor_tax_id):
        # Unreadable vendor is not the same as an unknown one: a person must look, so escalate.
        return check("R03", "BENEFICIARY_ALLOWED", FAILED, "escalate",
                     "No se identificó al proveedor: una persona debe revisar a quién se paga.",
                     observed="proveedor no identificado", expected="proveedor en la lista de permitidos")
    if b is None or not b.allowed:
        who = f.invoice.vendor_name or f.invoice.vendor_tax_id or "el proveedor"
        reason = "no está en la lista de beneficiarios permitidos" if b is None else "está marcado como no permitido"
        return check("R03", "BENEFICIARY_ALLOWED", FAILED, "block", f"Proveedor no permitido: {who} {reason}.",
                     observed=who, expected="proveedor en la lista de permitidos")
    return check("R03", "BENEFICIARY_ALLOWED", PASSED, "block", f"{b.name} está en la lista de beneficiarios permitidos.")


def r04_beneficiary_verified(f: Facts) -> RuleCheck:
    b = f.ctx.beneficiary
    if not f.rules.require_verified_beneficiary or b is None:
        return check("R04", "BENEFICIARY_VERIFIED", SKIPPED, "block",
                     "No aplica: verificación desactivada o proveedor no identificado.")
    if not b.verified:
        return check(
            "R04", "BENEFICIARY_VERIFIED", FAILED, "block",
            f"{b.name} no está verificado (razón social, país, datos bancarios y dueños con 25 % o más).",
            observed="sin verificar", expected="proveedor verificado",
        )
    return check("R04", "BENEFICIARY_VERIFIED", PASSED, "block", f"{b.name} está verificado.")


def r05_not_sanctioned(f: Facts) -> RuleCheck:
    if not f.rules.block_sanctioned:
        return check("R05", "NOT_SANCTIONED", SKIPPED, "block", "El control de sanciones no está activado.")
    b = f.ctx.beneficiary
    sanctioned_countries = {c.upper() for c in f.rules.sanctioned_countries}
    countries = {c.upper() for c in (f.invoice.vendor_country, b.country if b else None) if c}
    hit = sorted(countries & sanctioned_countries)
    if (b is not None and b.sanctioned) or hit:
        reason = f"país sancionado ({', '.join(hit)})" if hit else f"{b.name} está marcado como sancionado"  # type: ignore[union-attr]
        return check("R05", "NOT_SANCTIONED", FAILED, "block", f"No se paga: {reason}.",
                     observed=", ".join(hit) or "proveedor sancionado", expected="sin sanciones")
    if not countries and b is None:
        return check("R05", "NOT_SANCTIONED", SKIPPED, "block",
                     "No hay país ni proveedor identificado para comprobar sanciones.")
    return check("R05", "NOT_SANCTIONED", PASSED, "block", "Ni el proveedor ni su país están sancionados.")


def r06_currency_convertible(f: Facts) -> RuleCheck:
    cur = (f.invoice.currency or "").upper()
    if not cur:
        # Without a currency there is no amount in USD, so every limit (R07-R10) would be skipped: fail-closed.
        return check("R06", "CURRENCY_CONVERTIBLE", FAILED, "escalate",
                     "No se sabe en qué moneda está la factura: no se pueden comprobar los límites.",
                     observed="moneda desconocida", expected=f"una de {', '.join(sorted(f.rules.allowed_currencies))}")
    allowed = {c.upper() for c in f.rules.allowed_currencies}
    no_rate = f.invoice.amount is not None and f.amount_base is None
    if cur not in allowed or no_rate:
        return check(
            "R06", "CURRENCY_CONVERTIBLE", FAILED, "escalate",
            f"La moneda {cur} no está permitida o no tiene tasa: no se pueden comprobar los límites.",
            observed=cur, expected=f"una de {', '.join(sorted(allowed))} con tasa de cambio",
        )
    return check("R06", "CURRENCY_CONVERTIBLE", PASSED, "escalate", f"La moneda {cur} está permitida.")


def _limit(rule_id: str, name: str, outcome: str, value: Decimal | None, limit: Decimal | None,
           f: Facts, over: str, ok: str) -> RuleCheck:
    base = f.rules.base_currency
    if value is None or limit is None:
        return check(rule_id, name, SKIPPED, outcome, "No se puede comprobar: falta el monto en la moneda base.")
    observed, expected = money(value, base), f"≤ {money(limit, base)}"
    text = (over if value > limit else ok).format(value=observed, limit=money(limit, base))
    return check(rule_id, name, FAILED if value > limit else PASSED, outcome, text, observed=observed, expected=expected)


def r07_per_payment_limit(f: Facts) -> RuleCheck:
    return _limit("R07", "PER_PAYMENT_LIMIT", "block", f.amount_base, f.rules.per_payment_limit, f,
                  "{value} supera el límite por pago de {limit}.",
                  "{value} está dentro del límite por pago de {limit}.")


def r08_approval_threshold(f: Facts) -> RuleCheck:
    return _limit("R08", "APPROVAL_THRESHOLD", "escalate", f.amount_base, f.rules.approval_threshold, f,
                  "{value} supera el umbral de {limit}: requiere aprobación de una persona.",
                  "{value} no supera el umbral de aprobación de {limit}.")


def r09_period_limit(f: Facts) -> RuleCheck:
    days = f.rules.period_days
    total = None if f.amount_base is None else f.ctx.spent_in_period + f.amount_base
    return _limit("R09", "PERIOD_LIMIT", "escalate", total, f.rules.period_limit, f,
                  f"Con esta factura se pagarían {{value}} en {days} días y el tope es {{limit}}: queda para revisión.",
                  f"Lo pagado en {days} días con esta factura ({{value}}) está dentro del tope de {{limit}}.")


def r10_vendor_period_limit(f: Facts) -> RuleCheck:
    if f.rules.per_vendor_period_limit is None:
        return check("R10", "VENDOR_PERIOD_LIMIT", SKIPPED, "escalate", "No hay límite por proveedor configurado.")
    total = None if f.amount_base is None else f.ctx.vendor_spent_in_period + f.amount_base
    return _limit("R10", "VENDOR_PERIOD_LIMIT", "escalate", total, f.rules.per_vendor_period_limit, f,
                  "Este proveedor recibiría {value} en el periodo y el límite es {limit}: requiere revisión.",
                  "Lo pagado a este proveedor en el periodo ({value}) está dentro del límite de {limit}.")


def r11_vendor_changes(f: Facts) -> RuleCheck:
    if not f.rules.review_on_vendor_changes:
        return check("R11", "VENDOR_CHANGES", SKIPPED, "escalate",
                     "La revisión por cambios del proveedor no está activada.")
    inv, b, last = f.invoice, f.ctx.beneficiary, f.ctx.last_vendor_invoice
    changes: list[str] = []
    # Against the vendor's registered data: catches impersonation (known name, other NIT or account).
    if b and inv.vendor_tax_id and b.tax_id and digits(inv.vendor_tax_id) != digits(b.tax_id):
        changes.append(f"el NIT {inv.vendor_tax_id} no coincide con el registrado ({b.tax_id})")
    if b and inv.beneficiary_account and b.account and digits(inv.beneficiary_account) != digits(b.account):
        changes.append("la cuenta bancaria no coincide con la registrada")
    # Against the last payment to the same vendor.
    if last and (inv.beneficiary_account and last.beneficiary_account
                 and digits(inv.beneficiary_account) != digits(last.beneficiary_account)):
        changes.append("la cuenta bancaria cambió respecto al último pago")
    # Amount against what was agreed (ADR-017): vendors bill varying amounts, so comparing with the
    # last payment would send every recurring invoice to a person.
    agreement = f.ctx.agreement
    agreed = to_base(agreement.expected_amount, agreement.currency, f.rules) if agreement else None
    if agreed is not None and f.amount_base is not None:
        deviation = abs(f.amount_base - agreed) * 100 / agreed
        if deviation > f.rules.agreement_tolerance_pct:
            changes.append(
                f"el monto no cuadra con lo acordado ({money(agreed, f.rules.base_currency)}, "
                f"diferencia {deviation:.1f} % > {f.rules.agreement_tolerance_pct} %)"
            )
    if changes:
        unique = list(dict.fromkeys(changes))
        return check("R11", "VENDOR_CHANGES", FAILED, "escalate", "Revisión humana: " + "; ".join(unique) + ".",
                     observed="; ".join(unique),
                     expected="mismos datos que el registro, el último pago y lo acordado")
    if b is None and last is None and agreed is None:
        return check("R11", "VENDOR_CHANGES", SKIPPED, "escalate",
                     "No hay datos registrados, pagos previos ni acuerdo para comparar.")
    return check("R11", "VENDOR_CHANGES", PASSED, "escalate",
                 "Los datos del proveedor coinciden con lo registrado, el último pago y lo acordado.")


RULES = [
    r01_required_fields,
    r02_not_duplicate,
    r03_beneficiary_allowed,
    r04_beneficiary_verified,
    r05_not_sanctioned,
    r06_currency_convertible,
    r07_per_payment_limit,
    r08_approval_threshold,
    r09_period_limit,
    r10_vendor_period_limit,
    r11_vendor_changes,
]
