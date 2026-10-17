import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import (
    AgreementModel,
    BeneficiaryModel,
    ConversationModel,
    DecisionModel,
    InvoiceModel,
    MessageModel,
    RuleSetModel,
)
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
    RuleCheck,
    RuleSet,
)


def _normalize_name(value: str) -> str:
    return " ".join(value.lower().strip().split())


class SqlRuleSetRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_current(self) -> RuleSet:
        stmt = select(RuleSetModel).order_by(desc(RuleSetModel.version)).limit(1)
        row = self.db.execute(stmt).scalar_one_or_none()
        if not row:
            default_rules = RuleSet(
                version=1,
                company_name="Distribuciones Andinas S.A.S.",
                base_currency="USD",
                fx_rates={
                    "USD": Decimal("1.00"),
                    "EUR": Decimal("1.10"),
                    "COP": Decimal("0.00025"),
                    "MXN": Decimal("0.055"),
                    "BRL": Decimal("0.19"),
                },
                allowed_currencies=["USD", "EUR", "COP", "MXN", "BRL"],
                approval_threshold=Decimal("5000.00"),
                per_payment_limit=Decimal("10000.00"),
                period="weekly",
                period_days=7,
                period_limit=Decimal("50000.00"),
                per_vendor_period_limit=Decimal("20000.00"),
                period_budget=Decimal("50000.00"),
                duplicate_window_days=90,
                agreement_tolerance_pct=Decimal("5.00"),
                min_extraction_confidence=0.8,
                require_allowlisted_beneficiary=True,
                require_verified_beneficiary=True,
                block_sanctioned=True,
                sanctioned_countries=["KP", "IR", "SY", "CU", "RU"],
                review_on_vendor_changes=True,
                required_fields=["vendor_name", "invoice_number", "amount", "issue_date", "description"],
                retention_years=5,
                severity_overrides={},
            )
            return self.save_new_version(default_rules)
        return self._to_schema(row)

    def save_new_version(self, rule_set: RuleSet) -> RuleSet:
        stmt = select(RuleSetModel.version).order_by(desc(RuleSetModel.version)).limit(1)
        latest_version = self.db.execute(stmt).scalar_one_or_none()
        next_version = (latest_version or 0) + 1

        model = RuleSetModel(
            version=next_version,
            company_name=rule_set.company_name,
            base_currency=rule_set.base_currency,
            fx_rates={k: str(v) for k, v in rule_set.fx_rates.items()},
            allowed_currencies=rule_set.allowed_currencies,
            approval_threshold=rule_set.approval_threshold,
            per_payment_limit=rule_set.per_payment_limit,
            period=rule_set.period,
            period_days=rule_set.period_days,
            period_limit=rule_set.period_limit,
            per_vendor_period_limit=rule_set.per_vendor_period_limit,
            period_budget=rule_set.period_budget,
            duplicate_window_days=rule_set.duplicate_window_days,
            agreement_tolerance_pct=rule_set.agreement_tolerance_pct,
            min_extraction_confidence=rule_set.min_extraction_confidence,
            require_allowlisted_beneficiary=rule_set.require_allowlisted_beneficiary,
            require_verified_beneficiary=rule_set.require_verified_beneficiary,
            block_sanctioned=rule_set.block_sanctioned,
            sanctioned_countries=rule_set.sanctioned_countries,
            review_on_vendor_changes=rule_set.review_on_vendor_changes,
            required_fields=rule_set.required_fields,
            retention_years=rule_set.retention_years,
            severity_overrides=rule_set.severity_overrides,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._to_schema(model)

    @staticmethod
    def _to_schema(row: RuleSetModel) -> RuleSet:
        return RuleSet(
            version=row.version,
            company_name=row.company_name,
            base_currency=row.base_currency,
            fx_rates={k: Decimal(str(v)) for k, v in row.fx_rates.items()},
            allowed_currencies=row.allowed_currencies,
            approval_threshold=Decimal(str(row.approval_threshold)),
            per_payment_limit=Decimal(str(row.per_payment_limit)),
            period=row.period,
            period_days=row.period_days,
            period_limit=Decimal(str(row.period_limit)),
            per_vendor_period_limit=Decimal(str(row.per_vendor_period_limit)) if row.per_vendor_period_limit is not None else None,
            period_budget=Decimal(str(row.period_budget)),
            duplicate_window_days=row.duplicate_window_days,
            agreement_tolerance_pct=Decimal(str(row.agreement_tolerance_pct)),
            min_extraction_confidence=row.min_extraction_confidence,
            require_allowlisted_beneficiary=row.require_allowlisted_beneficiary,
            require_verified_beneficiary=row.require_verified_beneficiary,
            block_sanctioned=row.block_sanctioned,
            sanctioned_countries=row.sanctioned_countries or [],
            review_on_vendor_changes=row.review_on_vendor_changes,
            required_fields=row.required_fields or [],
            retention_years=row.retention_years,
            severity_overrides=row.severity_overrides or {},
        )


class SqlBeneficiaryRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self) -> list[Beneficiary]:
        rows = self.db.execute(select(BeneficiaryModel).order_by(BeneficiaryModel.name)).scalars().all()
        return [Beneficiary.model_validate(r) for r in rows]

    def find_match(
        self,
        tax_id: str | None = None,
        account: str | None = None,
        name: str | None = None,
    ) -> Beneficiary | None:
        if tax_id and tax_id.strip():
            row = self.db.execute(
                select(BeneficiaryModel).where(BeneficiaryModel.tax_id == tax_id.strip())
            ).scalar_one_or_none()
            if row:
                return Beneficiary.model_validate(row)

        if account and account.strip():
            row = self.db.execute(
                select(BeneficiaryModel).where(BeneficiaryModel.account == account.strip())
            ).scalar_one_or_none()
            if row:
                return Beneficiary.model_validate(row)

        if name and name.strip():
            target = _normalize_name(name)
            for row in self.db.execute(select(BeneficiaryModel)).scalars().all():
                if _normalize_name(row.name) == target or (row.legal_name and _normalize_name(row.legal_name) == target):
                    return Beneficiary.model_validate(row)
        return None

    def upsert(self, beneficiary: Beneficiary) -> Beneficiary:
        existing = self.db.get(BeneficiaryModel, beneficiary.id)
        if existing:
            existing.name = beneficiary.name
            existing.legal_name = beneficiary.legal_name
            existing.tax_id = beneficiary.tax_id
            existing.account = beneficiary.account
            existing.country = beneficiary.country
            existing.allowed = beneficiary.allowed
            existing.verified = beneficiary.verified
            existing.sanctioned = beneficiary.sanctioned
            existing.owners = beneficiary.owners
            model = existing
        else:
            model = BeneficiaryModel(**beneficiary.model_dump())
            self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return Beneficiary.model_validate(model)

    def delete(self, beneficiary_id: str) -> bool:
        existing = self.db.get(BeneficiaryModel, beneficiary_id)
        if not existing:
            return False
        self.db.delete(existing)
        self.db.commit()
        return True


class SqlAgreementRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self) -> list[Agreement]:
        rows = self.db.execute(select(AgreementModel)).scalars().all()
        return [Agreement.model_validate(r) for r in rows]

    def find_by_beneficiary(self, beneficiary_id: str) -> list[Agreement]:
        stmt = select(AgreementModel).where(AgreementModel.beneficiary_id == beneficiary_id)
        rows = self.db.execute(stmt).scalars().all()
        return [Agreement.model_validate(r) for r in rows]

    def upsert(self, agreement: Agreement) -> Agreement:
        existing = self.db.get(AgreementModel, agreement.id)
        if existing:
            existing.beneficiary_id = agreement.beneficiary_id
            existing.description = agreement.description
            existing.expected_amount = agreement.expected_amount
            existing.currency = agreement.currency
            existing.po_reference = agreement.po_reference
            existing.valid_from = agreement.valid_from
            existing.valid_to = agreement.valid_to
            model = existing
        else:
            model = AgreementModel(**agreement.model_dump())
            self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return Agreement.model_validate(model)


class SqlInvoiceRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, invoice: Invoice) -> Invoice:
        extracted_json = invoice.extracted.model_dump(mode="json") if invoice.extracted else None
        model = InvoiceModel(
            id=invoice.id,
            source_type=invoice.source_type.value,
            source_filename=invoice.source_filename,
            raw_text=invoice.raw_text,
            extracted=extracted_json,
            status=invoice.status.value,
            received_at=invoice.received_at,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._to_schema(model)

    def get(self, invoice_id: str) -> Invoice | None:
        row = self.db.get(InvoiceModel, invoice_id)
        return self._to_schema(row) if row else None

    def list_all(self, status: InvoiceStatus | None = None) -> list[Invoice]:
        stmt = select(InvoiceModel).order_by(desc(InvoiceModel.received_at))
        if status:
            stmt = stmt.where(InvoiceModel.status == status.value)
        rows = self.db.execute(stmt).scalars().all()
        return [self._to_schema(r) for r in rows]

    def update(self, invoice: Invoice) -> Invoice:
        row = self.db.get(InvoiceModel, invoice.id)
        if not row:
            raise ValueError(f"Invoice {invoice.id} not found")
        row.status = invoice.status.value
        row.raw_text = invoice.raw_text
        row.extracted = invoice.extracted.model_dump(mode="json") if invoice.extracted else None
        self.db.commit()
        self.db.refresh(row)
        return self._to_schema(row)

    def list_previous_extractions(self, exclude_invoice_id: str | None = None) -> list[ExtractedInvoice]:
        stmt = select(InvoiceModel).where(InvoiceModel.extracted.is_not(None))
        if exclude_invoice_id:
            stmt = stmt.where(InvoiceModel.id != exclude_invoice_id)
        rows = self.db.execute(stmt).scalars().all()
        return [ExtractedInvoice.model_validate(r.extracted) for r in rows if r.extracted]

    def get_last_paid_for_vendor(
        self,
        vendor_name: str | None = None,
        vendor_tax_id: str | None = None,
        exclude_invoice_id: str | None = None,
    ) -> ExtractedInvoice | None:
        stmt = (
            select(InvoiceModel)
            .where(InvoiceModel.status.in_([InvoiceStatus.paid.value, InvoiceStatus.approved.value]))
            .where(InvoiceModel.extracted.is_not(None))
            .order_by(desc(InvoiceModel.received_at))
        )
        if exclude_invoice_id:
            stmt = stmt.where(InvoiceModel.id != exclude_invoice_id)

        norm_name = _normalize_name(vendor_name) if vendor_name else None
        for row in self.db.execute(stmt).scalars().all():
            ext = ExtractedInvoice.model_validate(row.extracted)
            if vendor_tax_id and ext.vendor_tax_id and ext.vendor_tax_id.strip() == vendor_tax_id.strip():
                return ext
            if norm_name and ext.vendor_name and _normalize_name(ext.vendor_name) == norm_name:
                return ext
        return None

    @staticmethod
    def _to_schema(row: InvoiceModel) -> Invoice:
        return Invoice(
            id=row.id,
            source_type=row.source_type,
            source_filename=row.source_filename,
            raw_text=row.raw_text,
            extracted=ExtractedInvoice.model_validate(row.extracted) if row.extracted else None,
            status=row.status,
            received_at=row.received_at,
        )


class SqlDecisionRepository:
    """Append-only repository: strictly no update or delete methods."""

    def __init__(self, db: Session):
        self.db = db

    def add(self, decision: Decision) -> Decision:
        model = DecisionModel(
            id=decision.id,
            invoice_id=decision.invoice_id,
            outcome=decision.outcome.value,
            actor=decision.actor.value,
            checks=[c.model_dump(mode="json") for c in decision.checks],
            summary=decision.summary,
            explanation=decision.explanation,
            rule_set_version=decision.rule_set_version,
            amount_base_currency=decision.amount_base_currency,
            approver=decision.approver,
            comment=decision.comment,
            created_at=decision.created_at,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._to_schema(model)

    def get(self, decision_id: str) -> Decision | None:
        row = self.db.get(DecisionModel, decision_id)
        return self._to_schema(row) if row else None

    def list_by_invoice(self, invoice_id: str) -> list[Decision]:
        stmt = (
            select(DecisionModel)
            .where(DecisionModel.invoice_id == invoice_id)
            .order_by(desc(DecisionModel.created_at))
        )
        rows = self.db.execute(stmt).scalars().all()
        return [self._to_schema(r) for r in rows]

    def list_all(
        self,
        outcome: Outcome | None = None,
        status: InvoiceStatus | None = None,
    ) -> list[Decision]:
        stmt = select(DecisionModel).order_by(desc(DecisionModel.created_at))
        if outcome:
            stmt = stmt.where(DecisionModel.outcome == outcome.value)
        if status:
            stmt = stmt.join(InvoiceModel, DecisionModel.invoice_id == InvoiceModel.id).where(
                InvoiceModel.status == status.value
            )
        rows = self.db.execute(stmt).scalars().all()
        return [self._to_schema(r) for r in rows]

    def sum_spent_between(
        self,
        start_dt: datetime | None = None,
        end_dt: datetime | None = None,
        vendor_name: str | None = None,
        vendor_tax_id: str | None = None,
    ) -> Decimal:
        stmt = select(InvoiceModel).where(
            InvoiceModel.status.in_([InvoiceStatus.paid.value, InvoiceStatus.approved.value])
        )
        if start_dt:
            stmt = stmt.where(InvoiceModel.received_at >= start_dt)
        if end_dt:
            stmt = stmt.where(InvoiceModel.received_at <= end_dt)

        norm_name = _normalize_name(vendor_name) if vendor_name else None
        invoices = self.db.execute(stmt).scalars().all()
        total = Decimal("0.00")
        for inv in invoices:
            if vendor_name or vendor_tax_id:
                if not inv.extracted:
                    continue
                ext_tax = inv.extracted.get("vendor_tax_id")
                ext_name = inv.extracted.get("vendor_name")
                tax_match = bool(vendor_tax_id and ext_tax and ext_tax.strip() == vendor_tax_id.strip())
                name_match = bool(norm_name and ext_name and _normalize_name(ext_name) == norm_name)
                if not (tax_match or name_match):
                    continue

            latest_dec = self.db.execute(
                select(DecisionModel)
                .where(DecisionModel.invoice_id == inv.id)
                .order_by(desc(DecisionModel.created_at))
                .limit(1)
            ).scalar_one_or_none()
            if latest_dec and latest_dec.amount_base_currency is not None:
                total += Decimal(str(latest_dec.amount_base_currency))
        return total

    @staticmethod
    def _to_schema(row: DecisionModel) -> Decision:
        return Decision(
            id=row.id,
            invoice_id=row.invoice_id,
            outcome=row.outcome,
            actor=row.actor,
            checks=[RuleCheck.model_validate(c) for c in row.checks],
            summary=row.summary,
            explanation=row.explanation,
            rule_set_version=row.rule_set_version,
            amount_base_currency=Decimal(str(row.amount_base_currency)) if row.amount_base_currency is not None else None,
            approver=row.approver,
            comment=row.comment,
            created_at=row.created_at,
        )


class SqlConversationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, title: str | None = None) -> ConversationSummary:
        now = datetime.now(UTC)
        conv = ConversationModel(
            id=f"conv-{uuid.uuid4().hex[:10]}",
            title=title or "Nueva factura",
            invoice_id=None,
            updated_at=now,
        )
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return self._to_summary(conv)

    def list_all(self) -> list[ConversationSummary]:
        rows = (
            self.db.execute(select(ConversationModel).order_by(desc(ConversationModel.updated_at)))
            .scalars()
            .all()
        )
        return [self._to_summary(r) for r in rows]

    def get(self, conversation_id: str) -> ConversationSummary | None:
        row = self.db.get(ConversationModel, conversation_id)
        return self._to_summary(row) if row else None

    def update_metadata(
        self,
        conversation_id: str,
        title: str | None = None,
        invoice_id: str | None = None,
    ) -> None:
        row = self.db.get(ConversationModel, conversation_id)
        if not row:
            return
        if title:
            row.title = title
        if invoice_id:
            row.invoice_id = invoice_id
        row.updated_at = datetime.now(UTC)
        self.db.commit()

    def get_messages(self, conversation_id: str) -> list[ChatMessage]:
        stmt = (
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            .order_by(MessageModel.created_at)
        )
        rows = self.db.execute(stmt).scalars().all()
        dec_repo = SqlDecisionRepository(self.db)
        result = []
        for r in rows:
            decision = dec_repo.get(r.decision_id) if r.decision_id else None
            result.append(
                ChatMessage(
                    id=r.id,
                    conversation_id=r.conversation_id,
                    role=r.role,
                    content=r.content,
                    invoice_id=r.invoice_id,
                    decision=decision,
                    created_at=r.created_at,
                )
            )
        return result

    def add_message(self, message: ChatMessage) -> ChatMessage:
        model = MessageModel(
            id=message.id,
            conversation_id=message.conversation_id,
            role=message.role,
            content=message.content,
            invoice_id=message.invoice_id,
            decision_id=message.decision.id if message.decision else None,
            created_at=message.created_at,
        )
        self.db.add(model)
        conv = self.db.get(ConversationModel, message.conversation_id)
        if conv:
            conv.updated_at = datetime.now(UTC)
            if message.invoice_id:
                conv.invoice_id = message.invoice_id
        self.db.commit()
        return message

    def _to_summary(self, row: ConversationModel) -> ConversationSummary:
        inv_status = None
        last_outcome = None
        if row.invoice_id:
            inv = self.db.get(InvoiceModel, row.invoice_id)
            if inv:
                inv_status = InvoiceStatus(inv.status)
            latest_dec = self.db.execute(
                select(DecisionModel)
                .where(DecisionModel.invoice_id == row.invoice_id)
                .order_by(desc(DecisionModel.created_at))
                .limit(1)
            ).scalar_one_or_none()
            if latest_dec:
                last_outcome = Outcome(latest_dec.outcome)

        return ConversationSummary(
            id=row.id,
            title=row.title,
            invoice_id=row.invoice_id,
            invoice_status=inv_status,
            last_outcome=last_outcome,
            updated_at=row.updated_at,
        )
