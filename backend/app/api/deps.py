import os
import secrets

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
    """Guards /api/dev/* (seed and reset reload or wipe the whole demo). ADR-024.

    - With ADMIN_TOKEN set: the 'X-Admin-Token' header must match (constant-time comparison). The web app
      sends it from Configuración → Demo.
    - Without ADMIN_TOKEN: allowed in development and tests; refused in production (APP_ENV=production or
      on Vercel), so a visitor cannot wipe a public demo.
    Approving or rejecting an invoice does not use this token: a person does it with name and reason.
    """
    if settings.ADMIN_TOKEN:
        token = (request.headers.get("X-Admin-Token") or "").strip()
        if not secrets.compare_digest(token.encode(), settings.ADMIN_TOKEN.strip().encode()):
            raise HTTPException(status_code=401, detail="Token de administración inválido o ausente en el encabezado 'X-Admin-Token'.")
        return
    if settings.APP_ENV in ("test", "testing"):
        return
    if settings.APP_ENV == "production" or os.environ.get("VERCEL"):
        raise HTTPException(
            status_code=403,
            detail="Endpoints de desarrollo deshabilitados en producción sin ADMIN_TOKEN configurado.",
        )
