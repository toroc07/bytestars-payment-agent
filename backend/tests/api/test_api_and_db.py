import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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
    # Crear conversación y enviar texto (creará factura en pending_approval por fail-closed)
    conv = client.post("/api/conversations", json={"title": "Test Factura"}).json()
    msg_res = client.post(
        f"/api/conversations/{conv['id']}/messages",
        data={"text": "Factura de prueba USD 6000"},
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
        data={"text": "Factura simple"},
    )
    invoice_id = msg_res.json()["invoice"]["id"]

    reeval_res = client.post(f"/api/invoices/{invoice_id}/reevaluate")
    assert reeval_res.status_code == 200
    assert reeval_res.json()["invoice_id"] == invoice_id

    # Approve invoice
    client.post(
        f"/api/invoices/{invoice_id}/approve",
        json={"approver": "Auditor", "comment": "Aprobado"},
    )
    # Reevaluating approved invoice should now return 409 Conflict
    reeval_after_approval = client.post(f"/api/invoices/{invoice_id}/reevaluate")
    assert reeval_after_approval.status_code == 409


