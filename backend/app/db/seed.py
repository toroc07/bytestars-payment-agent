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

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent
# In the repo the company lives in dataset/. On Vercel only backend/ is deployed, so the build step
# (scripts/vercel_build.py) copies it to backend/seed_data/.
COMPANY_JSON_CANDIDATES = [REPO_ROOT / "dataset" / "company.json", BACKEND_ROOT / "seed_data" / "company.json"]


def find_company_json() -> Path | None:
    return next((path for path in COMPANY_JSON_CANDIDATES if path.exists()), None)


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
    company_json = find_company_json()
    if company_json is None:
        return 0

    data = json.loads(company_json.read_text(encoding="utf-8"))
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
