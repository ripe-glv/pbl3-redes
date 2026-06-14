from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ["NODE_ID"] = "auth-test-node"
os.environ["LEDGER_FILE"] = str(
    Path(tempfile.mkdtemp(prefix="sentinel-auth-")) / "ledger.json"
)
os.environ["STORAGE_DIR"] = tempfile.mkdtemp(prefix="sentinel-storage-")
os.environ["POW_DIFFICULTY"] = "1"
os.environ["PEERS"] = ""
os.environ["AUTH_SECRET"] = "test-shared-secret"

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def login(company_id: str, password: str) -> str:
    response = client.post(
        "/auth/login",
        json={"company_id": company_id, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_login_rejects_invalid_password_and_accepts_valid_credentials():
    rejected = client.post(
        "/auth/login",
        json={"company_id": "gulf", "password": "senha-errada"},
    )
    assert rejected.status_code == 401

    token = login("gulf", "Gulf@2026")
    profile = client.get("/auth/me", headers=bearer(token))
    assert profile.status_code == 200
    assert profile.json()["company_id"] == "gulf"


def test_private_operations_require_matching_authenticated_company():
    gulf_token = login("gulf", "Gulf@2026")
    atlas_token = login("atlas", "Atlas@2026")

    forbidden_transfer = client.post(
        "/credits/transfer",
        headers=bearer(atlas_token),
        json={
            "sender_company_id": "gulf",
            "recipient_company_id": "orion",
            "amount": 1,
        },
    )
    assert forbidden_transfer.status_code == 403

    escort = client.post(
        "/escort/request",
        headers=bearer(gulf_token),
        json={
            "company_id": "gulf",
            "drone_id": "DRONE-01",
            "route_id": "ROTA-ALFA",
            "cost": 10,
        },
    )
    assert escort.status_code == 200
    mission_id = escort.json()["mission_id"]

    completed = client.post(
        f"/missions/{mission_id}/complete",
        headers=bearer(gulf_token),
        json={
            "company_id": "gulf",
            "result": "ROTA_SEGURA",
            "description": "Conteúdo confidencial.",
            "evidence": ["radar"],
            "strategic_notes": "Reservado.",
            "risk_classification": "BAIXO",
        },
    )
    assert completed.status_code == 200

    owner_details = client.post(
        f"/missions/{mission_id}/decrypt",
        headers=bearer(gulf_token),
        json={},
    )
    assert owner_details.status_code == 200
    assert owner_details.json()["report"]["description"] == "Conteúdo confidencial."

    foreign_details = client.post(
        f"/missions/{mission_id}/decrypt",
        headers=bearer(atlas_token),
        json={},
    )
    assert foreign_details.status_code == 403
    assert "não possui a chave" in foreign_details.json()["detail"]
