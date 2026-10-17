from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator, model_validator

MoneyStr = Annotated[
    Decimal,
    PlainSerializer(lambda v: f"{v:.2f}" if v is not None else None, return_type=str, when_used="json"),
]

PositiveMoneyStr = Annotated[
    Decimal,
    Field(gt=Decimal(0)),
    PlainSerializer(lambda v: f"{v:.2f}" if v is not None else None, return_type=str, when_used="json"),
]


class Outcome(str, Enum):
    pay = "pay"
    block = "block"
    escalate = "escalate"


class InvoiceStatus(str, Enum):
    received = "received"
    paid = "paid"
    blocked = "blocked"
    pending_approval = "pending_approval"
    approved = "approved"
    rejected = "rejected"


class SourceType(str, Enum):
    pdf = "pdf"
    image = "image"
    text = "text"


class CheckStatus(str, Enum):
    passed = "passed"
    failed = "failed"
    skipped = "skipped"


class Actor(str, Enum):
    agent = "agent"
    human = "human"


class ExtractedInvoice(BaseModel):
    invoice_number: str | None = None
    vendor_name: str | None = None
    vendor_tax_id: str | None = None
    beneficiary_account: str | None = None
    amount: PositiveMoneyStr | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    issue_date: date | None = None
    due_date: date | None = None
    description: str | None = None
    po_reference: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class Invoice(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_type: SourceType
    source_filename: str | None = None
    raw_text: str | None = None
    extracted: ExtractedInvoice | None = None
    status: InvoiceStatus
    received_at: datetime


class RuleSet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version: int = 1
    company_name: str
    base_currency: str = Field(default="USD", min_length=3, max_length=3)
    fx_rates: dict[str, Decimal]
    allowed_currencies: list[str]
    approval_threshold: PositiveMoneyStr
    per_payment_limit: PositiveMoneyStr
    period: Literal["weekly", "monthly"]
    period_limit: PositiveMoneyStr
    period_budget: PositiveMoneyStr
    duplicate_window_days: int = Field(ge=0)
    agreement_tolerance_pct: Decimal = Field(ge=Decimal(0))
    min_extraction_confidence: float = Field(ge=0.0, le=1.0)
    require_allowlisted_beneficiary: bool = True
    severity_overrides: dict[str, Literal["block", "escalate"]] = Field(default_factory=dict)

    @field_validator("severity_overrides", mode="before")
    @classmethod
    def reject_pay_override(cls, v: dict) -> dict:
        if isinstance(v, dict):
            for rule_id, outcome in v.items():
                if outcome == "pay":
                    raise ValueError(f"severity_overrides cannot set '{rule_id}' to 'pay'")
        return v


class Beneficiary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    tax_id: str | None = None
    account: str | None = None
    country: str | None = None
    allowed: bool = True


class Agreement(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    beneficiary_id: str
    description: str
    expected_amount: PositiveMoneyStr
    currency: str = Field(min_length=3, max_length=3)
    po_reference: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None


class RuleCheck(BaseModel):
    rule_id: str
    rule_name: str
    status: CheckStatus
    outcome_if_failed: Literal["block", "escalate"]
    observed: str | None = None
    expected: str | None = None
    message: str


class EvaluationContext(BaseModel):
    today: date
    beneficiary: Beneficiary | None = None
    agreement: Agreement | None = None
    previous_invoices: list[ExtractedInvoice] = Field(default_factory=list)
    spent_in_period: MoneyStr = Decimal("0.00")


class EngineResult(BaseModel):
    outcome: Outcome
    checks: list[RuleCheck]
    summary: str
    amount_base_currency: MoneyStr | None = None

    @model_validator(mode="after")
    def verify_pay_invariant(self) -> "EngineResult":
        if self.outcome == Outcome.pay and any(c.status == CheckStatus.failed for c in self.checks):
            raise ValueError("Invariant violation: outcome cannot be 'pay' when any check failed")
        return self


class Decision(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    invoice_id: str
    outcome: Outcome
    actor: Actor
    checks: list[RuleCheck]
    summary: str
    explanation: str | None = None
    rule_set_version: int
    amount_base_currency: MoneyStr | None = None
    approver: str | None = None
    comment: str | None = None
    created_at: datetime


class ApprovalRequest(BaseModel):
    approver: str = Field(min_length=1)
    comment: str | None = None

    @field_validator("approver")
    @classmethod
    def strip_approver(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("approver cannot be blank")
        return v.strip()


class ChatMessage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: Literal["user", "assistant"]
    content: str
    invoice_id: str | None = None
    decision: Decision | None = None
    created_at: datetime


class ConversationSummary(BaseModel):
    id: str
    title: str
    invoice_id: str | None = None
    invoice_status: InvoiceStatus | None = None
    last_outcome: Outcome | None = None
    updated_at: datetime


class CreateConversationRequest(BaseModel):
    title: str | None = None


class SendMessageResponse(BaseModel):
    user_message: ChatMessage
    assistant_message: ChatMessage
    invoice: Invoice | None = None


class SummaryResponse(BaseModel):
    paid_count: int
    blocked_count: int
    pending_count: int
    spent_in_period: MoneyStr
    period_limit: MoneyStr
    period_budget: MoneyStr
