"""Offline reader on an English invoice (fictional data): it must read it, and the engine still decides."""

from datetime import date
from decimal import Decimal

from app.agent.local_reader import read_text

EMAIL = """Correo: 06_email_invoice_software.eml
De: billing@northstar-cloud.example
Asunto: Invoice NSCT-2026-445 from Northstar Cloud Tools LLC - USD 132.30

NORTHSTAR CLOUD TOOLS LLC (FICTIONAL)
200 Demo Parkway, Austin, TX 00000, United States
Federal Tax ID (fictional): 00-0000000

INVOICE NUMBER: NSCT-2026-445
Invoice date: 2026-10-10
Due date: 2026-10-25
Bill to: Laboratorio Delta UTB (fictional), Cartagena, Colombia
Currency: USD

DESCRIPTION                                      QTY     UNIT PRICE       LINE TOTAL
Cloud analytics seats - monthly subscription       3         49.00 USD       147.00 USD

Subtotal:                                                        147.00 USD
Discount:                                                        -14.70 USD (10%)
TOTAL DUE:                                                       132.30 USD

Payment instructions: NO-REAL-ACCOUNT-0000. TEST BANK - NOT OPERATIONAL.
"""


def test_english_invoice_is_read_offline():
    inv = read_text([EMAIL], "Distribuciones Andinas S.A.S.")
    assert inv.invoice_number == "NSCT-2026-445"
    assert inv.vendor_name is not None and "NORTHSTAR CLOUD TOOLS LLC" in inv.vendor_name.upper()
    assert inv.vendor_tax_id == "00-0000000"
    assert inv.amount == Decimal("132.30")
    assert inv.currency == "USD"
    assert inv.issue_date == date(2026, 10, 10)
    assert inv.due_date == date(2026, 10, 25)
    assert inv.description == "Cloud analytics seats - monthly subscription"
    assert inv.beneficiary_account is None  # placeholder account is not invented
    assert inv.confidence >= 0.8
