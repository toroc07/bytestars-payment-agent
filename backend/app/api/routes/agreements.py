from fastapi import APIRouter, Depends

from app.api.deps import get_agreement_repo
from app.ports import AgreementRepository
from app.schemas import Agreement

router = APIRouter(prefix="/api/agreements", tags=["agreements"])


@router.get("", response_model=list[Agreement])
def list_agreements(
    repo: AgreementRepository = Depends(get_agreement_repo),
) -> list[Agreement]:
    return repo.list_all()


@router.post("", response_model=Agreement)
def upsert_agreement(
    payload: Agreement,
    repo: AgreementRepository = Depends(get_agreement_repo),
) -> Agreement:
    return repo.upsert(payload)
