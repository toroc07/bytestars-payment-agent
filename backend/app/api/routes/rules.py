from fastapi import APIRouter, Depends

from app.api.deps import get_rule_repo
from app.ports import RuleSetRepository
from app.schemas import RuleSet

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("", response_model=RuleSet)
def get_rules(repo: RuleSetRepository = Depends(get_rule_repo)) -> RuleSet:
    return repo.get_current()


@router.put("", response_model=RuleSet)
def update_rules(
    payload: RuleSet,
    repo: RuleSetRepository = Depends(get_rule_repo),
) -> RuleSet:
    return repo.save_new_version(payload)
