from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import get_beneficiary_repo
from app.ports import BeneficiaryRepository
from app.schemas import Beneficiary

router = APIRouter(prefix="/api/beneficiaries", tags=["beneficiaries"])


@router.get("", response_model=list[Beneficiary])
def list_beneficiaries(
    repo: BeneficiaryRepository = Depends(get_beneficiary_repo),
) -> list[Beneficiary]:
    return repo.list_all()


@router.post("", response_model=Beneficiary)
def upsert_beneficiary(
    payload: Beneficiary,
    repo: BeneficiaryRepository = Depends(get_beneficiary_repo),
) -> Beneficiary:
    return repo.upsert(payload)


@router.delete("/{beneficiary_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_beneficiary(
    beneficiary_id: str,
    repo: BeneficiaryRepository = Depends(get_beneficiary_repo),
) -> Response:
    deleted = repo.delete(beneficiary_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Beneficiario no encontrado")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
