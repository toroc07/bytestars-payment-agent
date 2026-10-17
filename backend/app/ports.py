from datetime import datetime
from decimal import Decimal
from typing import Protocol

from app.schemas import (
    Agreement,
    Beneficiary,
    ChatMessage,
    ConversationSummary,
    Decision,
    ExtractedInvoice,
    Invoice,
    InvoiceStatus,
    Outcome,
    RuleSet,
)


class RuleSetRepository(Protocol):
    def get_current(self) -> RuleSet: ...
    def save_new_version(self, rule_set: RuleSet) -> RuleSet: ...


class BeneficiaryRepository(Protocol):
    def list_all(self) -> list[Beneficiary]: ...
    def find_match(
        self,
        tax_id: str | None = None,
        account: str | None = None,
        name: str | None = None,
    ) -> Beneficiary | None: ...
    def upsert(self, beneficiary: Beneficiary) -> Beneficiary: ...
    def delete(self, beneficiary_id: str) -> bool: ...


class AgreementRepository(Protocol):
    def list_all(self) -> list[Agreement]: ...
    def find_by_beneficiary(self, beneficiary_id: str) -> list[Agreement]: ...
    def upsert(self, agreement: Agreement) -> Agreement: ...


class InvoiceRepository(Protocol):
    def add(self, invoice: Invoice) -> Invoice: ...
    def get(self, invoice_id: str) -> Invoice | None: ...
    def list_all(self, status: InvoiceStatus | None = None) -> list[Invoice]: ...
    def update(self, invoice: Invoice) -> Invoice: ...
    def list_previous_extractions(self, exclude_invoice_id: str | None = None) -> list[ExtractedInvoice]: ...
    def get_last_paid_for_vendor(
        self,
        vendor_name: str | None = None,
        vendor_tax_id: str | None = None,
        exclude_invoice_id: str | None = None,
    ) -> ExtractedInvoice | None: ...


class DecisionRepository(Protocol):
    """Append-only repository: no update or delete methods allowed."""
    def add(self, decision: Decision) -> Decision: ...
    def get(self, decision_id: str) -> Decision | None: ...
    def list_by_invoice(self, invoice_id: str) -> list[Decision]: ...
    def list_all(
        self,
        outcome: Outcome | None = None,
        status: InvoiceStatus | None = None,
    ) -> list[Decision]: ...
    def sum_spent_between(
        self,
        start_dt: datetime | None = None,
        end_dt: datetime | None = None,
        vendor_name: str | None = None,
        vendor_tax_id: str | None = None,
    ) -> Decimal: ...


class ConversationRepository(Protocol):
    def create(self, title: str | None = None) -> ConversationSummary: ...
    def list_all(self) -> list[ConversationSummary]: ...
    def get(self, conversation_id: str) -> ConversationSummary | None: ...
    def update_metadata(
        self,
        conversation_id: str,
        title: str | None = None,
        invoice_id: str | None = None,
    ) -> None: ...
    def get_messages(self, conversation_id: str) -> list[ChatMessage]: ...
    def add_message(self, message: ChatMessage) -> ChatMessage: ...

