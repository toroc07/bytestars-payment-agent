from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.repositories import (
    SqlAgreementRepository,
    SqlBeneficiaryRepository,
    SqlConversationRepository,
    SqlDecisionRepository,
    SqlInvoiceRepository,
    SqlLlmCacheRepository,
    SqlRuleSetRepository,
)
from app.db.session import get_db


def get_rule_repo(db: Session = Depends(get_db)) -> SqlRuleSetRepository:
    return SqlRuleSetRepository(db)


def get_beneficiary_repo(db: Session = Depends(get_db)) -> SqlBeneficiaryRepository:
    return SqlBeneficiaryRepository(db)


def get_agreement_repo(db: Session = Depends(get_db)) -> SqlAgreementRepository:
    return SqlAgreementRepository(db)


def get_invoice_repo(db: Session = Depends(get_db)) -> SqlInvoiceRepository:
    return SqlInvoiceRepository(db)


def get_decision_repo(db: Session = Depends(get_db)) -> SqlDecisionRepository:
    return SqlDecisionRepository(db)


def get_conversation_repo(db: Session = Depends(get_db)) -> SqlConversationRepository:
    return SqlConversationRepository(db)


def get_llm_cache_repo(db: Session = Depends(get_db)) -> SqlLlmCacheRepository:
    return SqlLlmCacheRepository(db)
