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
