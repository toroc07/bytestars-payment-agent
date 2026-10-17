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
    assert current_rules.company_name == "Nimbus Labs Inc."

    ben_repo = SqlBeneficiaryRepository(db_session)
    bens = ben_repo.list_all()
    assert len(bens) >= 8

    agr_repo = SqlAgreementRepository(db_session)
    agrs = agr_repo.list_all()
    assert len(agrs) >= 8

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
