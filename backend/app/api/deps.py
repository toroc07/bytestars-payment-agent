import os

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import settings
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


def require_admin_token(request: Request) -> None:
    """Security check for sensitive admin operations and demo endpoints.

    - If ADMIN_TOKEN is configured: requires 'X-Admin-Token' header matching ADMIN_TOKEN.
    - If ADMIN_TOKEN is not configured:
      - In development and test environments: allowed without credentials.
      - In production (or Vercel): rejects destructive /api/dev/* calls with 403 Forbidden.
    """
    token = request.headers.get("X-Admin-Token")
    if settings.ADMIN_TOKEN:
        if not token or token.strip() != settings.ADMIN_TOKEN.strip():
            raise HTTPException(
                status_code=401,
                detail="Token de administración inválido o ausente en el encabezado 'X-Admin-Token'.",
            )
        return

    # In production without an explicit ADMIN_TOKEN, dev endpoints are disabled to prevent abuse
    is_prod = settings.APP_ENV == "production" or bool(os.environ.get("VERCEL"))
    if is_prod and settings.APP_ENV not in ("test", "testing") and request.url.path.startswith("/api/dev"):
        raise HTTPException(
            status_code=403,
            detail="Endpoints de desarrollo deshabilitados en producción sin ADMIN_TOKEN configurado.",
        )
