"""In-memory repositories and a fake LLM provider (no network, no database) for agent tests."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from app.llm import LLMChain, LLMError, LLMRequest
from app.schemas import (
    Agreement,
    Beneficiary,
    ChatMessage,
    Decision,
    ExtractedInvoice,
    Invoice,
    InvoiceStatus,
    RuleSet,
)

PAID = (InvoiceStatus.paid, InvoiceStatus.approved)


class FakeProvider:
    def __init__(self, name: str = "fake", answer: dict[str, Any] | None = None, files: bool = True):
        self.name = name
        self.answer = answer
        self.files = files
        self.requests: list[LLMRequest] = []

    def supports(self, request: LLMRequest) -> bool:
        return self.files or not request.has_file

    def generate_json(self, request: LLMRequest) -> dict[str, Any]:
        self.requests.append(request)
        if self.answer is None:
            raise LLMError(f"{self.name}: quota exceeded")
        return self.answer


def chain(*providers: FakeProvider) -> LLMChain:
    return LLMChain(list(providers), cache=None)


class Repos:
    """Implements every port the pipeline uses, keeping state in lists and dicts."""

    def __init__(self, rules: RuleSet, beneficiaries: list[Beneficiary], agreements: list[Agreement] | None = None):
        self.rules = rules
        self.beneficiaries = beneficiaries
        self.agreements = agreements or []
        self.invoices: dict[str, Invoice] = {}
        self.decisions: list[Decision] = []
        self.messages: list[ChatMessage] = []
        self.titles: dict[str, str] = {}

    # RuleSetRepository
    def get_current(self) -> RuleSet:
        return self.rules

    # BeneficiaryRepository
    def find_match(self, tax_id=None, account=None, name=None) -> Beneficiary | None:
        for key, value in (("tax_id", tax_id), ("account", account)):
            match = next((b for b in self.beneficiaries if value and getattr(b, key) == value.strip()), None)
            if match:
                return match
        return next((b for b in self.beneficiaries if name and b.name.lower() == name.strip().lower()), None)

    # AgreementRepository
    def find_by_beneficiary(self, beneficiary_id: str) -> list[Agreement]:
        return [a for a in self.agreements if a.beneficiary_id == beneficiary_id]

    # InvoiceRepository and DecisionRepository share `add`
    def add(self, item):
        if isinstance(item, Invoice):
            self.invoices[item.id] = item
        else:
            self.decisions.append(item)
        return item

    def get(self, invoice_id: str, for_update: bool = False) -> Invoice | None:
        return self.invoices.get(invoice_id)

    def update(self, invoice: Invoice) -> Invoice:
        self.invoices[invoice.id] = invoice
        return invoice

    def transition_status(self, invoice_id: str, from_status: InvoiceStatus, to_status: InvoiceStatus,
                          commit: bool = True) -> bool:
        inv = self.invoices.get(invoice_id)
        if not inv or inv.status != from_status:
            return False
        self.invoices[invoice_id] = inv.model_copy(update={"status": to_status})
        return True

    def list_previous_extractions(
        self,
        exclude_invoice_id=None,
        before_dt=None,
    ) -> list[ExtractedInvoice]:
        return [
            i.extracted
            for i in self.invoices.values()
            if i.extracted
            and i.id != exclude_invoice_id
            and (
                before_dt is None
                or i.received_at < before_dt
                or i.status in PAID
            )
        ]

    def get_last_paid_for_vendor(self, vendor_name=None, vendor_tax_id=None, exclude_invoice_id=None):
        paid = [i for i in self.invoices.values() if i.status in PAID and i.extracted and i.id != exclude_invoice_id
                and i.extracted.vendor_tax_id == vendor_tax_id]
        return paid[-1].extracted if paid else None

    def sum_spent_between(self, start_dt: datetime | None = None, end_dt=None, vendor_name=None, vendor_tax_id=None):
        total = Decimal("0.00")
        for invoice in self.invoices.values():
            if invoice.status not in PAID or (vendor_tax_id and invoice.extracted.vendor_tax_id != vendor_tax_id):
                continue
            last = [d for d in self.decisions if d.invoice_id == invoice.id][-1]
            total += last.amount_base_currency or Decimal(0)
        return total

    # ConversationRepository
    def add_message(self, message: ChatMessage) -> ChatMessage:
        self.messages.append(message)
        return message

    def update_metadata(self, conversation_id: str, title=None, invoice_id=None) -> None:
        if title:
            self.titles[conversation_id] = title
