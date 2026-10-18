import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.seed import seed_database
from app.db.session import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as db:
        seed_database(db)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health(client: TestClient):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_rules_reject_pay_severity_override(client: TestClient):
    current = client.get("/api/rules").json()
    current["severity_overrides"] = {"R02": "pay"}
    res = client.put("/api/rules", json=current)
    assert res.status_code == 422


def test_human_approval_and_409_guard(client: TestClient):
    conv = client.post("/api/conversations", json={"title": "Test Factura"}).json()
    msg_res = client.post(
        f"/api/conversations/{conv['id']}/messages",
        data={
            "text": (
                "Factura No. ATS-991\n"
                "NIT: 901.022.366-3\n"
                "Total a pagar: USD 6000\n"
                "Cuenta: 81629733626"
            )
        },
    )
    assert msg_res.status_code == 200
    invoice_id = msg_res.json()["invoice"]["id"]

    # Aprobar como humano -> 200 OK
    app_res = client.post(
        f"/api/invoices/{invoice_id}/approve",
        json={"approver": "Ana Finanzas", "comment": "Autorizado por dirección"},
    )
    assert app_res.status_code == 200
    assert app_res.json()["actor"] == "human"
    assert app_res.json()["outcome"] == "pay"

    # Intentar aprobar de nuevo cuando ya está 'approved' -> 409 Conflict
    second_res = client.post(
        f"/api/invoices/{invoice_id}/approve",
        json={"approver": "Ana Finanzas", "comment": "Doble click"},
    )
    assert second_res.status_code == 409


def test_simultaneous_text_and_file_upload(client: TestClient):
    conv = client.post("/api/conversations", json={"title": "Email con Adjunto"}).json()
    files = {"file": ("factura.pdf", b"%PDF-1.4 sample content", "application/pdf")}
    data = {"text": "Correo: invoice.eml\nDe: vendor@example.com\nAsunto: Factura 001\n\nAdjunto factura"}

    res = client.post(
        f"/api/conversations/{conv['id']}/messages",
        data=data,
        files=files,
    )
    assert res.status_code == 200
    body = res.json()
    inv = body["invoice"]
    assert inv is not None
    assert inv["source_type"] == "pdf"
    assert inv["source_filename"] == "factura.pdf"
    assert "Correo: invoice.eml" in inv["raw_text"]


def test_rules_get_and_put_with_new_fields(client: TestClient):
    current = client.get("/api/rules").json()
    assert current["period_days"] == 7
    assert current["per_vendor_period_limit"] == "20000.00"
    assert current["require_verified_beneficiary"] is True
    assert current["block_sanctioned"] is True
    assert "KP" in current["sanctioned_countries"]
    assert current["review_on_vendor_changes"] is True
    assert "invoice_number" in current["required_fields"]
    assert current["retention_years"] == 5

    # Update with new values
    current["period_days"] = 14
    current["per_vendor_period_limit"] = "15000.00"
    current["retention_years"] = 7
    put_res = client.put("/api/rules", json=current)
    assert put_res.status_code == 200
    saved = put_res.json()
    assert saved["version"] == current["version"] + 1
    assert saved["period_days"] == 14
    assert saved["per_vendor_period_limit"] == "15000.00"
    assert saved["retention_years"] == 7


def test_reevaluate_endpoint(client: TestClient):
    conv = client.post("/api/conversations", json={"title": "Reevaluate Test"}).json()
    msg_res = client.post(
        f"/api/conversations/{conv['id']}/messages",
        data={
            "text": (
                "Factura No. ATS-992\n"
                "NIT: 901.022.366-3\n"
                "Total a pagar: USD 6000\n"
                "Cuenta: 81629733626"
            )
        },
    )
    invoice_id = msg_res.json()["invoice"]["id"]

    reeval_res = client.post(f"/api/invoices/{invoice_id}/reevaluate")
    assert reeval_res.status_code == 200
    assert reeval_res.json()["invoice_id"] == invoice_id

    # Approve invoice
    app_res = client.post(
        f"/api/invoices/{invoice_id}/approve",
        json={"approver": "Auditor", "comment": "Aprobado"},
    )
    assert app_res.status_code == 200

    # Reevaluating approved invoice should now return 409 Conflict
    reeval_after_approval = client.post(f"/api/invoices/{invoice_id}/reevaluate")
    assert reeval_after_approval.status_code == 409


def test_reset_refuses_to_wipe_without_company_json(client: TestClient, monkeypatch):
    from app.api.routes import dev

    monkeypatch.setattr(dev, "find_company_json", lambda: None)
    before = client.get("/api/beneficiaries").json()
    res = client.post("/api/dev/reset")
    assert res.status_code == 503
    assert client.get("/api/beneficiaries").json() == before


def test_approve_rejects_missing_extracted_data(client: TestClient):
    conv = client.post("/api/conversations", json={"title": "Incompleta"}).json()
    msg_res = client.post(
        f"/api/conversations/{conv['id']}/messages",
        data={"text": "Factura sin datos legibles ni monto"},
    )
    invoice_id = msg_res.json()["invoice"]["id"]

    res = client.post(
        f"/api/invoices/{invoice_id}/approve",
        json={"approver": "Auditor", "comment": "Aprobando a ciegas"},
    )
    assert res.status_code == 409
    assert "No se puede aprobar la factura" in res.json()["detail"] or "datos extraídos" in res.json()["detail"]


def test_approve_rejects_duplicate_invoice(client: TestClient):
    conv = client.post("/api/conversations", json={"title": "Duplicados"}).json()
    invoice_text = (
        "Factura No. ATS-777\n"
        "NIT: 901.022.366-3\n"
        "Total a pagar: USD 6000\n"
        "Cuenta: 81629733626"
    )
    # Configurar R02 como escalate para que la segunda factura quede en pending_approval y pruebe el guard R02 en /approve
    rules = client.get("/api/rules").json()
    rules["severity_overrides"] = {"R02": "escalate"}
    client.put("/api/rules", json=rules)

    # Primera factura
    res1 = client.post(f"/api/conversations/{conv['id']}/messages", data={"text": invoice_text})
    inv1_id = res1.json()["invoice"]["id"]

    # Segunda factura con los mismos datos
    res2 = client.post(f"/api/conversations/{conv['id']}/messages", data={"text": invoice_text})
    inv2_id = res2.json()["invoice"]["id"]

    # Aprobar la primera -> 200 OK
    app1 = client.post(
        f"/api/invoices/{inv1_id}/approve",
        json={"approver": "Auditor 1", "comment": "Primera aprobada"},
    )
    assert app1.status_code == 200

    # Intentar aprobar la segunda (duplicada de la primera) -> 409 Conflict por R02
    app2 = client.post(
        f"/api/invoices/{inv2_id}/approve",
        json={"approver": "Auditor 2", "comment": "Intento de pagar duplicada"},
    )
    assert app2.status_code == 409
    assert "Duplicada" in app2.json()["detail"]


def test_admin_token_protection(client: TestClient, monkeypatch):
    from app.api.routes import dev
    from app.config import settings

    monkeypatch.setattr(settings, "ADMIN_TOKEN", "secret-key-123")
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(dev, "_check_rate_limit", lambda req: None)

    # Llamar sin header -> 401
    res_unauth = client.post("/api/dev/reset")
    assert res_unauth.status_code == 401
    assert "Token de administración inválido" in res_unauth.json()["detail"]

    # Llamar con token incorrecto -> 401
    res_bad = client.post("/api/dev/reset", headers={"X-Admin-Token": "wrong-key"})
    assert res_bad.status_code == 401

    # Llamar con token correcto -> 200
    res_ok = client.post("/api/dev/reset", headers={"X-Admin-Token": "secret-key-123"})
    assert res_ok.status_code == 200


def test_dev_endpoints_blocked_in_production_without_admin_token(client: TestClient, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "ADMIN_TOKEN", "")

    res = client.post("/api/dev/reset")
    assert res.status_code == 403
    assert "Endpoints de desarrollo deshabilitados en producción" in res.json()["detail"]


def _pending_invoice(client: TestClient) -> str:
    conv = client.post("/api/conversations", json={"title": "Pendiente"}).json()
    res = client.post(f"/api/conversations/{conv['id']}/messages", data={"text": "Factura FAC-9 total US$10.00"})
    invoice = res.json()["invoice"]
    assert invoice["status"] == "pending_approval"
    return invoice["id"]


def test_human_decisions_do_not_need_the_admin_token(client: TestClient, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ADMIN_TOKEN", "secret-key-123")
    monkeypatch.setattr(settings, "APP_ENV", "production")
    invoice_id = _pending_invoice(client)
    res = client.post(f"/api/invoices/{invoice_id}/reject", json={"approver": "Ana", "comment": "No reconocida"})
    assert res.status_code == 200 and res.json()["outcome"] == "block"


def test_failed_decision_record_leaves_the_invoice_pending(client: TestClient, monkeypatch):
    from app.db.repositories import SqlDecisionRepository

    invoice_id = _pending_invoice(client)
    original_add = SqlDecisionRepository.add

    def broken_add(self, decision):
        if decision.actor.value == "human":
            self.db.rollback()
            raise RuntimeError("db down")
        return original_add(self, decision)

    monkeypatch.setattr(SqlDecisionRepository, "add", broken_add)
    with pytest.raises(RuntimeError):
        client.post(f"/api/invoices/{invoice_id}/reject", json={"approver": "Ana", "comment": "x"})
    monkeypatch.setattr(SqlDecisionRepository, "add", original_add)
    assert client.get(f"/api/invoices/{invoice_id}").json()["status"] == "pending_approval"
