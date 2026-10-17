import json
from pathlib import Path

from sqlalchemy import delete
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
from app.db.repositories import (
    SqlAgreementRepository,
    SqlBeneficiaryRepository,
    SqlRuleSetRepository,
)
from app.schemas import Agreement, Beneficiary, RuleSet

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPANY_JSON = REPO_ROOT / "dataset" / "company.json"


def reset_database(db: Session) -> None:
    db.execute(delete(MessageModel))
    db.execute(delete(ConversationModel))
    db.execute(delete(DecisionModel))
    db.execute(delete(InvoiceModel))
    db.execute(delete(AgreementModel))
    db.execute(delete(BeneficiaryModel))
    db.execute(delete(RuleSetModel))
    db.commit()


def seed_database(db: Session) -> int:
    if not COMPANY_JSON.exists():
        return 0

    data = json.loads(COMPANY_JSON.read_text(encoding="utf-8"))
    rule_repo = SqlRuleSetRepository(db)
    ben_repo = SqlBeneficiaryRepository(db)
    agr_repo = SqlAgreementRepository(db)

    count = 0
    if "rule_set" in data:
        rule_repo.save_new_version(RuleSet.model_validate(data["rule_set"]))
        count += 1

    for b in data.get("beneficiaries", []):
        ben_repo.upsert(Beneficiary.model_validate(b))
        count += 1

    for a in data.get("agreements", []):
        agr_repo.upsert(Agreement.model_validate(a))
        count += 1

    return count
