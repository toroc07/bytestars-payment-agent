"""Evaluates the agent on the dataset against dataset/expected.json (docs/PROJECT.md, "Cómo se evalúa").

Runs the real pipeline (extraction -> context -> engine -> persistence) over the 100 invoices in canonical
order (factura_001..100) on a freshly seeded in-memory SQLite, feeding each file the way the frontend sends it:
.txt as text, .eml as headers + body text with the PDF attached, PDF and images as files.

Usage (from backend/):
    python -m scripts.evaluate_dataset            # uses the LLM keys in .env
    python -m scripts.evaluate_dataset --offline  # no LLM: offline reader only (images escalate)

Exit code 1 if a trap (duplicate, unknown vendor, impersonation, account change) was paid. Invoices
expected to escalate only because the 7-day cap was reached ("tope_semanal") are reported apart: whether the
cap is reached depends on what was paid before them, and the engine checks the real spend every time.
"""

import argparse
import email
import json
import sys
import time
from collections import Counter
from datetime import UTC, datetime, timedelta
from email import policy
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agent.pipeline import handle_chat_turn
from app.db.models import Base
from app.db.repositories import (
    SqlAgreementRepository,
    SqlBeneficiaryRepository,
    SqlConversationRepository,
    SqlDecisionRepository,
    SqlInvoiceRepository,
    SqlRuleSetRepository,
)
from app.db.seed import seed_database
from app.llm import LLMChain, get_llm
from app.schemas import ChatMessage, SourceType

DATASET = Path(__file__).resolve().parents[2] / "dataset"
FIELDS = ("invoice_number", "vendor_tax_id", "beneficiary_account", "amount", "currency", "issue_date",
          "po_reference")


def as_frontend_input(path: Path) -> tuple[str | None, bytes | None, str | None, SourceType]:
    """(text, file bytes, filename, source type) as the web app would send this file."""
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8"), None, None, SourceType.text
    if suffix == ".eml":
        msg = email.message_from_bytes(path.read_bytes(), policy=policy.default)
        body = msg.get_body(preferencelist=("plain",))
        attachment = next(msg.iter_attachments(), None)
        text = f"Correo: {path.name}\nDe: {msg['from']}\nAsunto: {msg['subject']}\n\n"
        text += body.get_content() if body else ""
        if attachment is None:
            return text, None, None, SourceType.text
        source = SourceType.pdf if attachment.get_content_type() == "application/pdf" else SourceType.image
        return text, attachment.get_content(), attachment.get_filename(), source
    source = SourceType.pdf if suffix == ".pdf" else SourceType.image
    return None, path.read_bytes(), path.name, source


def extraction_diffs(expected: dict, got: dict | None) -> dict:
    got = got or {}
    diffs = {}
    for field in FIELDS:
        want, have = expected.get(field), got.get(field)
        if field == "po_reference" and want == "No aplica":
            want = None
        if field == "amount" and want and have and float(want) == float(have):
            continue
        if (want or None) != (have or None):
            diffs[field] = (want, have)
    return diffs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--offline", action="store_true", help="no LLM: only the offline reader")
    parser.add_argument("--limit", type=int, default=None, help="evaluate only the first N invoices")
    args = parser.parse_args()

    expected = json.loads((DATASET / "expected.json").read_text(encoding="utf-8"))
    cases = expected["invoices"][: args.limit]
    llm = LLMChain([], cache=None) if args.offline else get_llm()

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    seed_database(db)
    repos = dict(  # noqa: C408 - keyword names are the pipeline parameters
        conv_repo=SqlConversationRepository(db), inv_repo=SqlInvoiceRepository(db),
        dec_repo=SqlDecisionRepository(db), rule_repo=SqlRuleSetRepository(db),
        ben_repo=SqlBeneficiaryRepository(db), agr_repo=SqlAgreementRepository(db),
    )

    print(f"Evaluando {len(cases)} facturas · LLM: {', '.join(llm.available) or 'ninguno (lector local)'}\n")
    outcomes: Counter = Counter()
    sources: Counter = Counter()
    mismatches, improper_pays, cap_dependent, reading_errors = [], [], [], []
    clock_start = datetime.now(UTC)
    started = time.monotonic()
    for index, case in enumerate(cases):
        text, file_bytes, filename, source_type = as_frontend_input(DATASET / case["file"])
        conversation = repos["conv_repo"].create(title=case["file"])
        now = clock_start + timedelta(seconds=index)  # strictly increasing, all inside one 7-day window
        user = ChatMessage(id=f"msg-eval-{index}", conversation_id=conversation.id, role="user",
                           content=text or filename or "", created_at=now)
        response = handle_chat_turn(conversation_id=conversation.id, user_message=user, text=text,
                                    file_bytes=file_bytes, filename=filename, source_type=source_type,
                                    llm=llm, clock=lambda now=now: now, **repos)
        decision = response.assistant_message.decision
        got = decision.outcome.value
        explanation = decision.explanation or ""
        source = explanation.split("Datos leídos con ", 1)[-1].split(".\n", 1)[0] if "Datos leídos con" in explanation \
            else "sin lectura"
        sources[source] += 1
        outcomes[(case["expected_outcome"], got)] += 1

        failed = [c.rule_id for c in decision.checks if c.status == "failed"]
        mark = "OK " if got == case["expected_outcome"] else "XX "
        print(f"{mark}{case['file']:<28} esperado {case['expected_outcome']:<8} obtuvo {got:<8} {','.join(failed)}")
        if got != case["expected_outcome"]:
            mismatches.append(case["file"])
        if got == "pay" and case["expected_outcome"] != "pay":
            (cap_dependent if case["case"] == "tope_semanal" else improper_pays).append(case["file"])
        extracted = response.invoice.extracted.model_dump(mode="json") if response.invoice.extracted else None
        if diffs := extraction_diffs(case["expected_extraction"], extracted):
            reading_errors.append((case["file"], diffs))

    total = len(cases)
    correct = total - len(mismatches)
    autonomous = sum(v for (want, got), v in outcomes.items() if want == got and got != "escalate")
    print("\n" + "-" * 80)
    print(f"Coinciden con expected.json: {correct}/{total} ({correct / total:.0%})")
    print(f"Autonomía (pagar o frenar correctamente, sin persona): {autonomous}/{total} ({autonomous / total:.0%})")
    print(f"Pagos indebidos (trampas pagadas): {len(improper_pays)} {improper_pays or ''}")
    print(f"Pagadas antes de llegar al tope semanal (dependen del orden): {len(cap_dependent)}")
    print(f"Lecturas: {dict(sources)}")
    print(f"Facturas con algún dato leído distinto: {len(reading_errors)}")
    for file, diffs in reading_errors:
        print(f"   {file}: {diffs}")
    print(f"Tiempo: {time.monotonic() - started:.0f} s")
    return 1 if improper_pays else 0


if __name__ == "__main__":
    sys.exit(main())
