from __future__ import annotations

import json
import urllib.error
import urllib.request


BASE_URL = "http://localhost:8011"


def request(
    method: str,
    path: str,
    body: dict | None = None,
    token: str | None = None,
) -> dict | list:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()
        raise RuntimeError(f"{method} {path}: HTTP {exc.code}: {detail}") from exc


def main() -> None:
    login = request(
        "POST",
        "/auth/login",
        {"company_id": "gulf", "password": "Gulf@2026"},
    )
    token = login["access_token"]
    transfer = request(
        "POST",
        "/credits/transfer",
        {
            "sender_company_id": "gulf",
            "recipient_company_id": "atlas",
            "amount": 5,
        },
        token,
    )
    escort = request(
        "POST",
        "/escort/request",
        {
            "company_id": "gulf",
            "drone_id": "DRONE-01",
            "route_id": "ROTA-ALFA",
            "cost": 10,
        },
        token,
    )
    mission_id = escort["mission_id"]
    completed = request(
        "POST",
        f"/missions/{mission_id}/complete",
        {
            "company_id": "gulf",
            "result": "ROTA_SEGURA",
            "description": "Teste de integração EVM.",
            "evidence": ["smoke-test"],
            "strategic_notes": "Ambiente Ganache.",
            "risk_classification": "BAIXO",
        },
        token,
    )
    decrypted = request(
        "POST", f"/missions/{mission_id}/decrypt", {}, token
    )
    integrity = request(
        "GET", f"/missions/{mission_id}/verify-file-integrity"
    )
    status = request("GET", "/node/status")
    assert transfer["status"] == "CONFIRMED"
    assert completed["status"] == "CONFIRMED"
    assert decrypted["valid"] is True
    assert integrity["valid"] is True
    assert status["blockchain_mode"] == "ethereum-ganache"
    print(
        json.dumps(
            {
                "mission_id": mission_id,
                "height": status["height"],
                "contract_address": status["contract_address"],
                "report_valid": decrypted["valid"],
                "file_valid": integrity["valid"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
