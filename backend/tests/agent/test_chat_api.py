"""End to end through the HTTP route: seeded SQLite, real repositories, no LLM (tests/conftest.py)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.seed import seed_database
from app.db.session import Base, get_db
from app.main import app

DATASET = Path(__file__).resolve().parents[3] / "dataset"


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    with session_factory() as db:
        seed_database(db)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def post(client: TestClient, **kwargs) -> dict:
    conversation = client.post("/api/conversations", json={}).json()
    response = client.post(f"/api/conversations/{conversation['id']}/messages", **kwargs)
    assert response.status_code == 200, response.text
    return response.json()


def test_chat_invoice_is_decided_and_listed(client):
    text = (DATASET / "Textos" / "factura_010.txt").read_text(encoding="utf-8")
    first = post(client, data={"text": text})
    assert first["assistant_message"]["decision"]["outcome"] == "pay"
    assert first["invoice"]["status"] == "paid"

    again = post(client, data={"text": text})
    assert again["assistant_message"]["decision"]["outcome"] == "block"

    statuses = sorted(i["status"] for i in client.get("/api/invoices").json())
    assert statuses == ["blocked", "paid"]
    assert client.get("/api/summary").json()["spent_in_period"] == "1487.50"


def test_pdf_from_unknown_vendor_is_blocked(client):
    pdf = (DATASET / "PDFS" / "factura_015.pdf").read_bytes()
    body = post(client, files={"file": ("factura_015.pdf", pdf, "application/pdf")})
    decision = body["assistant_message"]["decision"]
    assert decision["outcome"] == "block"
    assert any(c["rule_id"] == "R03" and c["status"] == "failed" for c in decision["checks"])
