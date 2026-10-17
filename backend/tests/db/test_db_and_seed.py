from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base
from app.db.repositories import (
    SqlAgreementRepository,
    SqlBeneficiaryRepository,
    SqlDecisionRepository,
    SqlInvoiceRepository,
    SqlRuleSetRepository,
)
from app.db.seed import reset_database, seed_database
from app.schemas import (
    Actor,
    Beneficiary,
    Decision,
    Invoice,
    InvoiceStatus,
    Outcome,
    SourceType,
)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_seed_and_reset(db_session):
    loaded = seed_database(db_session)
    assert loaded > 0

    rule_repo = SqlRuleSetRepository(db_session)
    current_rules = rule_repo.get_current()
    assert current_rules.company_name == "Distribuciones Andinas S.A.S."

    ben_repo = SqlBeneficiaryRepository(db_session)
    bens = ben_repo.list_all()
    assert len(bens) == 8
    assert all(b.verified and b.allowed and not b.sanctioned for b in bens)

    agr_repo = SqlAgreementRepository(db_session)

    # Test reset
    reset_database(db_session)
    assert len(ben_repo.list_all()) == 0
    assert len(agr_repo.list_all()) == 0


def test_decision_repo_sum_spent(db_session):
    inv_repo = SqlInvoiceRepository(db_session)
    dec_repo = SqlDecisionRepository(db_session)
    import datetime

    now = datetime.datetime.now(datetime.UTC)
    inv = inv_repo.add(
        Invoice(
            id="inv-test-1",
            source_type=SourceType.text,
            status=InvoiceStatus.approved,
            received_at=now,
        )
    )

    dec_repo.add(
        Decision(
            id="dec-test-1",
            invoice_id=inv.id,
            outcome=Outcome.pay,
            actor=Actor.human,
            checks=[],
            summary="Approved",
            rule_set_version=1,
            amount_base_currency=Decimal("1500.00"),
            created_at=now,
        )
    )

    total = dec_repo.sum_spent_between()
    assert total == Decimal("1500.00")


def test_beneficiary_match_by_legal_name_and_attributes(db_session):
    ben_repo = SqlBeneficiaryRepository(db_session)
    ben = Beneficiary(
        id="ben-test-legal",
        name="Estudio Diseno",
        legal_name="Estudio Diseno Legal S.A. de C.V.",
        tax_id="MX-123456",
        account="MX-ACC-111",
        country="MX",
        allowed=True,
        verified=True,
        sanctioned=False,
        owners=["Juan Perez (100%)"],
    )
    ben_repo.upsert(ben)

    # Match by legal name
    matched = ben_repo.find_match(name="Estudio Diseno Legal S.A. de C.V.")
    assert matched is not None
    assert matched.id == "ben-test-legal"
    assert matched.verified is True
    assert matched.sanctioned is False
    assert matched.owners == ["Juan Perez (100%)"]


def test_last_paid_for_vendor_and_vendor_sum(db_session):
    inv_repo = SqlInvoiceRepository(db_session)
    dec_repo = SqlDecisionRepository(db_session)
    import datetime

    from app.schemas import ExtractedInvoice

    t1 = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=2)
    t2 = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1)

    inv1 = inv_repo.add(
        Invoice(
            id="inv-paid-1",
            source_type=SourceType.pdf,
            source_filename="inv1.pdf",
            extracted=ExtractedInvoice(
                invoice_number="INV-001",
                vendor_name="Acme Corp",
                vendor_tax_id="TAX-ACME",
                amount=Decimal("1000.00"),
                currency="USD",
            ),
            status=InvoiceStatus.paid,
            received_at=t1,
        )
    )
    dec_repo.add(
        Decision(
            id="dec-1",
            invoice_id=inv1.id,
            outcome=Outcome.pay,
            actor=Actor.agent,
            checks=[],
            summary="Paid",
            rule_set_version=1,
            amount_base_currency=Decimal("1000.00"),
            created_at=t1,
        )
    )

    inv2 = inv_repo.add(
        Invoice(
            id="inv-paid-2",
            source_type=SourceType.pdf,
            source_filename="inv2.pdf",
            extracted=ExtractedInvoice(
                invoice_number="INV-002",
                vendor_name="Acme Corp",
                vendor_tax_id="TAX-ACME",
                amount=Decimal("2000.00"),
                currency="USD",
            ),
            status=InvoiceStatus.paid,
            received_at=t2,
        )
    )
    dec_repo.add(
        Decision(
            id="dec-2",
            invoice_id=inv2.id,
            outcome=Outcome.pay,
            actor=Actor.agent,
            checks=[],
            summary="Paid",
            rule_set_version=1,
            amount_base_currency=Decimal("2000.00"),
            created_at=t2,
        )
    )

    # Latest invoice for Acme Corp is inv2
    latest = inv_repo.get_last_paid_for_vendor(vendor_name="Acme Corp")
    assert latest is not None
    assert latest.invoice_number == "INV-002"

    # Excluding inv2 returns inv1
    prev = inv_repo.get_last_paid_for_vendor(vendor_name="Acme Corp", exclude_invoice_id="inv-paid-2")
    assert prev is not None
    assert prev.invoice_number == "INV-001"

    # Sum spent for vendor
    vendor_spent = dec_repo.sum_spent_between(vendor_name="Acme Corp")
    assert vendor_spent == Decimal("3000.00")

    # Sum spent with other vendor name returns 0
    other_spent = dec_repo.sum_spent_between(vendor_name="Other Vendor")
    assert other_spent == Decimal("0.00")

