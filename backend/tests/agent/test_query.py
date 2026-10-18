"""Read-only chat: questions about stored decisions are answered from the repositories, never registered."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.agent.pipeline import handle_chat_turn
from app.agent.query import looks_like_question
from app.schemas import Actor, Beneficiary, ChatMessage, Decision, Outcome, RuleSet, SourceType
from tests.agent.fakes import FakeProvider, Repos, chain

COMPANY = json.loads((Path(__file__).resolve().parents[3] / "dataset" / "company.json").read_text(encoding="utf-8"))
NOW = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)
ASEO = {
    "invoice_number": "ATS-842", "vendor_name": "Aseo Total Servicios S.A.S.", "vendor_tax_id": "901.022.366-3",
    "beneficiary_account": "81629733626", "vendor_country": "CO", "amount": "1487.50", "currency": "USD",
    "issue_date": "2026-08-27", "description": "Fumigación de instalaciones", "confidence": 0.95,
}


def repos_for() -> Repos:
    return Repos(RuleSet.model_validate(COMPANY["rule_set"]),
                 [Beneficiary.model_validate(b) for b in COMPANY["beneficiaries"]])


def chain_with(overrides: dict):
    return chain(FakeProvider(answer={**ASEO, **overrides}))


def send(repos: Repos, text: str, llm=None):
    user = ChatMessage(id="msg-user", conversation_id="conv-1", role="user", content=text, created_at=NOW)
    return handle_chat_turn(
        conversation_id="conv-1", user_message=user, text=text, file_bytes=None, filename=None,
        source_type=SourceType.text, conv_repo=repos, inv_repo=repos, dec_repo=repos, rule_repo=repos,
        ben_repo=repos, agr_repo=repos, llm=llm or chain(), clock=lambda: NOW,
    )

DELTA = {"invoice_number": "CDE-107", "vendor_name": "Comercializadora Delta Express S.A.S.",
         "vendor_tax_id": "901.587.432-6", "beneficiary_account": "62690944157"}


def test_questions_and_invoices_are_told_apart():
    assert looks_like_question("¿por qué frenaste la SIG-497?")
    assert looks_like_question("qué facturas están pendientes")
    assert looks_like_question("cuánto se ha pagado esta semana")
    assert not looks_like_question("Factura No. ATS-842 por US$1,487.50")
    assert not looks_like_question("[29/08/2026, 10:43] Sandra (Aseo Total): Factura No. ATS-842\nTotal: US$1,487.50")


def test_why_was_an_invoice_blocked():
    repos = repos_for()
    send(repos, "Factura CDE-107", llm=chain_with(DELTA))
    reply = send(repos, "¿por qué rechazaste la CDE-107?")
    assert reply.invoice is None and reply.assistant_message.decision is None
    text = reply.assistant_message.content
    assert "CDE-107" in text and "rechazada por el agente" in text and "R03" in text
    assert len(repos.invoices) == 1  # the question registered nothing


def test_human_endorsement_is_told():
    repos = repos_for()
    first = send(repos, "Factura No. ATS-842 por US$1,487.50", llm=chain_with({"amount": "6000.00"}))
    invoice = first.invoice
    repos.add(Decision(id="dec-h", invoice_id=invoice.id, outcome=Outcome.pay, actor=Actor.human, checks=[],
                       summary="Aprobada", rule_set_version=1, approver="Ana", comment="Contrato firmado",
                       created_at=NOW + timedelta(minutes=1)))
    text = send(repos, "¿qué pasó con la ATS-842?").assistant_message.content
    assert "R08" in text and "Ana la aprobó: «Contrato firmado»" in text


def test_pending_list_and_spend_summary():
    repos = repos_for()
    send(repos, "Factura No. ATS-842 por US$1,487.50", llm=chain_with({}))
    send(repos, "Factura No. ATS-900 por US$6,000.00", llm=chain_with({"invoice_number": "ATS-900", "amount": "6000.00"}))
    pending = send(repos, "¿qué facturas están pendientes?").assistant_message.content
    assert "Facturas por aprobar: 1." in pending and "ATS-900" in pending and "R08" in pending
    spend = send(repos, "¿cuánto se ha pagado esta semana?").assistant_message.content
    assert "USD 1,487.50" in spend and "USD 50,000.00" in spend and "1 pagada," in spend and "umbral de revisión" in spend


def test_vendor_listing_and_unknown_question():
    repos = repos_for()
    send(repos, "Factura CDE-107", llm=chain_with(DELTA))
    assert "Facturas de Comercializadora Delta Express" in send(repos, "facturas de delta?").assistant_message.content
    assert "No encontré esa factura" in send(repos, "¿qué opinas del clima?").assistant_message.content


LAO_KAO = {"invoice_number": "WL2141486", "vendor_name": "LAO KAO S.A.", "vendor_tax_id": "900.111.222-3",
           "beneficiary_account": "12345678901", "amount": "130200.00", "currency": "COP"}


def test_questions_inside_an_invoice_conversation_are_about_that_invoice():
    repos = repos_for()
    send(repos, "Factura No. ATS-842 por US$1,487.50", llm=chain_with({}))  # another invoice, paid
    send(repos, "Factura WL2141486", llm=chain_with(LAO_KAO))  # same conversation now holds the LAO KAO invoice

    why = send(repos, "por que fue rechazada?").assistant_message.content
    assert why.startswith("La factura WL2141486 de LAO KAO S.A.") and "R03" in why

    fix = send(repos, "que puedo hacer para que no sea rechazada?").assistant_message.content
    assert "Configuración → Beneficiarios" in fix and "Reevaluar" in fix and "R03" in fix
    assert "nunca paga algo que incumple una regla" in fix

    others = send(repos, "que otra factura hay?").assistant_message.content
    assert others.startswith("Hay 2 facturas: 1 pagada, 0 por aprobar") and "ATS-842" in others and "WL2141486" in others


def test_remedy_for_an_escalation_points_to_human_approval():
    repos = repos_for()
    send(repos, "Factura ATS-900", llm=chain_with({"invoice_number": "ATS-900", "amount": "6000.00"}))
    fix = send(repos, "¿qué hago para pagar la ATS-900?").assistant_message.content
    assert "R08" in fix and "«Aprobar pago»" in fix
