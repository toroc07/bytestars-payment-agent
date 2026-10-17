import email
import sys
from datetime import date
from email import policy
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agent.extraction import extract_invoice_data
from app.db.models import Base
from app.db.repositories import (
    SqlAgreementRepository,
    SqlBeneficiaryRepository,
    SqlDecisionRepository,
    SqlInvoiceRepository,
    SqlRuleSetRepository,
)
from app.db.seed import seed_database
from app.engine import evaluate
from app.schemas import EvaluationContext, Outcome, SourceType


def parse_eml_file(path: Path) -> tuple[str, bytes | None, str | None, SourceType]:
    msg = email.message_from_bytes(path.read_bytes(), policy=policy.default)
    headers = [
        f"Correo: {path.name}",
        f"De: {msg.get('From', '')}",
        f"Asunto: {msg.get('Subject', '')}",
        f"Fecha: {msg.get('Date', '')}",
    ]
    body_parts: list[str] = []
    att_bytes: bytes | None = None
    att_name: str | None = None
    source_type = SourceType.text

    for part in msg.walk():
        ctype = part.get_content_type()
        disp = str(part.get_content_disposition() or "")
        if ctype == "text/plain" and "attachment" not in disp:
            payload = part.get_content()
            if isinstance(payload, str):
                body_parts.append(payload.strip())
        elif ctype in ("application/pdf", "image/png", "image/jpeg") and att_bytes is None:
            att_bytes = part.get_payload(decode=True)
            att_name = part.get_filename() or path.stem
            source_type = SourceType.pdf if ctype == "application/pdf" else SourceType.image

    full_text = "\n".join(headers) + "\n\n" + "\n\n".join(body_parts)
    return full_text.strip(), att_bytes, att_name, source_type


def main() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as db:
        seed_database(db)
        rule_repo = SqlRuleSetRepository(db)
        ben_repo = SqlBeneficiaryRepository(db)
        agr_repo = SqlAgreementRepository(db)
        inv_repo = SqlInvoiceRepository(db)
        dec_repo = SqlDecisionRepository(db)

        rules = rule_repo.get_current()
        dataset_dir = REPO_ROOT / "dataset"
        files = sorted(
            list((dataset_dir / "Correos").glob("*.eml"))
            + list((dataset_dir / "PDFS").glob("*.pdf"))
            + list((dataset_dir / "Imagenes").glob("*.*"))
        )

        if not files:
            print("No se encontraron archivos en dataset/")
            return

        counts = {Outcome.pay: 0, Outcome.escalate: 0, Outcome.block: 0}
        unsafe_pays = 0

        print(f"Evaluando {len(files)} archivos del dataset con reglas v{rules.version}...\n")
        print(f"{'Archivo':<25} | {'Resultado':<10} | {'Monto Base':<12} | {'Reglas Fallidas'}")
        print("-" * 80)

        for fpath in files:
            if fpath.suffix.lower() == ".eml":
                text, file_bytes, filename, stype = parse_eml_file(fpath)
            elif fpath.suffix.lower() == ".pdf":
                text, file_bytes, filename, stype = None, fpath.read_bytes(), fpath.name, SourceType.pdf
            else:
                text, file_bytes, filename, stype = None, fpath.read_bytes(), fpath.name, SourceType.image

            extracted = extract_invoice_data(
                text=text,
                file_bytes=file_bytes,
                filename=filename,
                source_type=stype,
            )
            matched_ben = (
                ben_repo.find_match(
                    tax_id=extracted.vendor_tax_id,
                    account=extracted.beneficiary_account,
                    name=extracted.vendor_name,
                )
                if extracted
                else None
            )
            agreements = agr_repo.find_by_beneficiary(matched_ben.id) if matched_ben else []

            ctx = EvaluationContext(
                today=date.today(),
                beneficiary=matched_ben,
                agreement=agreements[0] if agreements else None,
                previous_invoices=inv_repo.list_previous_extractions(),
                spent_in_period=dec_repo.sum_spent_between(),
            )
            result = evaluate(extracted, rules, ctx)
            counts[result.outcome] += 1

            failed_ids = [c.rule_id for c in result.checks if c.status.value == "failed"]
            if result.outcome == Outcome.pay and failed_ids:
                unsafe_pays += 1

            amt_str = f"{result.amount_base_currency:.2f}" if result.amount_base_currency is not None else "N/A"
            print(f"{fpath.name:<25} | {result.outcome.value:<10} | {amt_str:<12} | {', '.join(failed_ids) or 'Ninguna'}")

        print("-" * 80)
        print(
            f"Resumen: PAY={counts[Outcome.pay]} | ESCALATE={counts[Outcome.escalate]} | BLOCK={counts[Outcome.block]}"
        )
        print(f"Violaciones de invariante I1 (Pagos con reglas fallidas): {unsafe_pays}")
        if unsafe_pays > 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
