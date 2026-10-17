import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.deps import (
    get_agreement_repo,
    get_beneficiary_repo,
    get_conversation_repo,
    get_decision_repo,
    get_invoice_repo,
    get_rule_repo,
)
from app.config import settings
from app.ports import (
    AgreementRepository,
    BeneficiaryRepository,
    ConversationRepository,
    DecisionRepository,
    InvoiceRepository,
    RuleSetRepository,
)
from app.schemas import (
    Actor,
    ChatMessage,
    CheckStatus,
    ConversationSummary,
    CreateConversationRequest,
    Decision,
    Invoice,
    InvoiceStatus,
    Outcome,
    RuleCheck,
    SendMessageResponse,
    SourceType,
)

router = APIRouter(prefix="/api/conversations", tags=["chat"])

ALLOWED_MIME_TYPES = {
    "application/pdf": SourceType.pdf,
    "image/png": SourceType.image,
    "image/jpeg": SourceType.image,
    "image/jpg": SourceType.image,
}


@router.get("", response_model=list[ConversationSummary])
def list_conversations(
    repo: ConversationRepository = Depends(get_conversation_repo),
) -> list[ConversationSummary]:
    return repo.list_all()


@router.post("", response_model=ConversationSummary)
def create_conversation(
    payload: CreateConversationRequest | None = None,
    repo: ConversationRepository = Depends(get_conversation_repo),
) -> ConversationSummary:
    title = payload.title if payload else None
    return repo.create(title=title)


@router.get("/{conversation_id}/messages", response_model=list[ChatMessage])
def get_messages(
    conversation_id: str,
    repo: ConversationRepository = Depends(get_conversation_repo),
) -> list[ChatMessage]:
    if not repo.get(conversation_id):
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return repo.get_messages(conversation_id)


@router.post("/{conversation_id}/messages", response_model=SendMessageResponse)
def send_message(
    conversation_id: str,
    text: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    conv_repo: ConversationRepository = Depends(get_conversation_repo),
    inv_repo: InvoiceRepository = Depends(get_invoice_repo),
    dec_repo: DecisionRepository = Depends(get_decision_repo),
    rule_repo: RuleSetRepository = Depends(get_rule_repo),
    ben_repo: BeneficiaryRepository = Depends(get_beneficiary_repo),
    agr_repo: AgreementRepository = Depends(get_agreement_repo),
) -> SendMessageResponse:
    conv = conv_repo.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    if not text and not file:
        raise HTTPException(status_code=400, detail="Debes enviar texto o adjuntar un archivo.")

    file_bytes: bytes | None = None
    source_type = SourceType.text
    filename: str | None = None

    if file:
        if file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=422,
                detail="Formato de archivo no soportado. Usa PDF, PNG o JPG.",
            )
        file_bytes = file.file.read()
        max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
        if len(file_bytes) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"El archivo supera el límite máximo de {settings.MAX_UPLOAD_MB} MB.",
            )
        source_type = ALLOWED_MIME_TYPES[file.content_type]
        filename = file.filename

    now = datetime.now(UTC)
    user_msg = ChatMessage(
        id=f"msg-{uuid.uuid4().hex[:10]}",
        conversation_id=conversation_id,
        role="user",
        content=text or f"Archivo adjunto: {filename}",
        created_at=now,
    )
    conv_repo.add_message(user_msg)

    # Intenta delegar en el pipeline del agente (Dev A). Si falla o no existe, fail-closed a escalate.
    try:
        from app.agent.pipeline import handle_chat_turn  # Implementado por Dev A

        return handle_chat_turn(
            conversation_id=conversation_id,
            user_message=user_msg,
            text=text,
            file_bytes=file_bytes,
            filename=filename,
            source_type=source_type,
            conv_repo=conv_repo,
            inv_repo=inv_repo,
            dec_repo=dec_repo,
            rule_repo=rule_repo,
            ben_repo=ben_repo,
            agr_repo=agr_repo,
        )
    except Exception as exc:  # noqa: BLE001
        rules = rule_repo.get_current()
        inv = Invoice(
            id=f"inv-{uuid.uuid4().hex[:10]}",
            source_type=source_type,
            source_filename=filename,
            raw_text=text,
            extracted=None,
            status=InvoiceStatus.pending_approval,
            received_at=now,
        )
        inv_repo.add(inv)

        fallback_decision = Decision(
            id=f"dec-{uuid.uuid4().hex[:10]}",
            invoice_id=inv.id,
            outcome=Outcome.escalate,
            actor=Actor.agent,
            checks=[
                RuleCheck(
                    rule_id="R01",
                    rule_name="EXTRACTION_COMPLETE",
                    status=CheckStatus.failed,
                    outcome_if_failed="escalate",
                    observed=f"Excepción o pipeline pendiente: {type(exc).__name__}",
                    expected="Extracción y evaluación completas",
                    message="No se pudo procesar automáticamente la factura; se escala a revisión humana por seguridad (fail-closed).",
                )
            ],
            summary="Factura escalada a aprobación humana por seguridad (fail-closed).",
            explanation="El agente encontró un problema al extraer o evaluar los datos y aplicó la política fail-closed.",
            rule_set_version=rules.version,
            amount_base_currency=None,
            created_at=now,
        )
        dec_repo.add(fallback_decision)

        assistant_msg = ChatMessage(
            id=f"msg-{uuid.uuid4().hex[:10]}",
            conversation_id=conversation_id,
            role="assistant",
            content=fallback_decision.summary,
            invoice_id=inv.id,
            decision=fallback_decision,
            created_at=datetime.now(UTC),
        )
        conv_repo.add_message(assistant_msg)
        conv_repo.update_metadata(
            conversation_id=conversation_id,
            title=filename or (text[:40] if text else "Factura escalada"),
            invoice_id=inv.id,
        )
        return SendMessageResponse(
            user_message=user_msg,
            assistant_message=assistant_msg,
            invoice=inv,
        )
