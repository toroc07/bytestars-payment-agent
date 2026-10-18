from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, PlainSerializer, field_validator, model_validator


def _as_utc(value: datetime) -> datetime:
    """SQLite drops the offset: read naive timestamps as UTC so the API always sends one."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


UtcDatetime = Annotated[datetime, AfterValidator(_as_utc)]

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
    vendor_country: str | None = Field(default=None, min_length=2, max_length=2)
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
    received_at: UtcDatetime


class RuleSet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version: int = 1
    company_name: str
    base_currency: str = Field(default="USD", min_length=3, max_length=3)
    fx_rates: dict[str, Decimal]
    allowed_currencies: list[str]
    approval_threshold: PositiveMoneyStr
    per_payment_limit: PositiveMoneyStr
    period: Literal["weekly", "monthly"] = "weekly"
    period_days: int = Field(default=7, ge=1)
    period_limit: PositiveMoneyStr
    per_vendor_period_limit: PositiveMoneyStr | None = Field(default=Decimal("20000.00"))
    period_budget: PositiveMoneyStr
    duplicate_window_days: int = Field(default=90, ge=0)
    agreement_tolerance_pct: Decimal = Field(default=Decimal("5.00"), ge=Decimal(0))
    min_extraction_confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    require_allowlisted_beneficiary: bool = True
    require_verified_beneficiary: bool = True
    block_sanctioned: bool = True
    sanctioned_countries: list[str] = Field(default_factory=lambda: ["KP", "IR", "SY", "CU", "RU"])
    review_on_vendor_changes: bool = True
    required_fields: list[str] = Field(
        default_factory=lambda: ["vendor_name", "invoice_number", "amount", "issue_date", "description"]
    )
    retention_years: int = Field(default=5, ge=1)
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
    legal_name: str | None = None
    tax_id: str | None = None
    account: str | None = None
    country: str | None = Field(default=None, min_length=2, max_length=2)
    allowed: bool = True
    # Verification is a human step (rule R04): a new vendor starts unverified.
    verified: bool = False
    sanctioned: bool = False
    owners: list[str] = Field(default_factory=list)


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
    last_vendor_invoice: ExtractedInvoice | None = None
    spent_in_period: MoneyStr = Decimal("0.00")
    vendor_spent_in_period: MoneyStr = Decimal("0.00")


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
    created_at: UtcDatetime


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
    created_at: UtcDatetime


class ConversationSummary(BaseModel):
    id: str
    title: str
    invoice_id: str | None = None
    invoice_status: InvoiceStatus | None = None
    last_outcome: Outcome | None = None
    updated_at: UtcDatetime


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
    spent_by_agent: MoneyStr = Decimal("0.00")  # paid by the engine, inside the rules
    spent_by_people: MoneyStr = Decimal("0.00")  # exceptions a person approved
    period_limit: MoneyStr
    period_budget: MoneyStr

