from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class RuleSetModel(Base):
    __tablename__ = "rule_sets"

    version: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    fx_rates: Mapped[dict] = mapped_column(JSON, nullable=False)
    allowed_currencies: Mapped[list] = mapped_column(JSON, nullable=False)
    approval_threshold: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    per_payment_limit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    period_limit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    period_budget: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    duplicate_window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    agreement_tolerance_pct: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    min_extraction_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    require_allowlisted_beneficiary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    severity_overrides: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BeneficiaryModel(Base):
    __tablename__ = "beneficiaries"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tax_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    account: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    country: Mapped[str | None] = mapped_column(String(10), nullable=True)
    allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AgreementModel(Base):
    __tablename__ = "agreements"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    beneficiary_id: Mapped[str] = mapped_column(String(64), ForeignKey("beneficiaries.id"), index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    po_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)


class InvoiceModel(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DecisionModel(Base):
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    invoice_id: Mapped[str] = mapped_column(String(64), ForeignKey("invoices.id"), index=True)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(20), nullable=False)
    checks: Mapped[list] = mapped_column(JSON, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_set_version: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_base_currency: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    approver: Mapped[str | None] = mapped_column(String(255), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ConversationModel(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    invoice_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("invoices.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class MessageModel(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(64), ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    invoice_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decision_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("decisions.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
