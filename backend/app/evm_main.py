from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidTag
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .auth import AuthSession, auth, require_session
from .crypto import canonical_json, sha256_hex
from .data import DRONES, ROUTES, build_wallets
from .evm import EvmGateway
from .models import (
    CreditTransferRequest,
    EscortRequest,
    LoginRequest,
    MissionCompleteRequest,
    TamperRequest,
)
from .storage import MissionStorage


gateway = EvmGateway(
    os.getenv("EVM_RPC_URL", "http://ganache:8545"),
    Path(os.getenv("EVM_ARTIFACT_PATH", "/evm/SentinelLedger.json")),
    os.getenv("NODE_ID", "node-a"),
)
wallets = build_wallets()
for company_id, address in gateway.company_addresses.items():
    wallets[company_id]["wallet_address"] = address
storage = MissionStorage(
    Path(os.getenv("STORAGE_DIR", "storage/evm")) / "missions"
)

app = FastAPI(
    title="Sentinel Ledger EVM",
    description="Versão Ethereum local executada em Ganache",
    version="2.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def fail(exc: Exception) -> HTTPException:
    message = str(exc)
    if "revert" in message.lower():
        message = message.split("revert", 1)[-1].strip(" :\"'")
    status = 403 if isinstance(exc, PermissionError) else 400
    return HTTPException(status, message)


def public_company(company_id: str) -> dict[str, Any]:
    wallet = wallets[company_id]
    return {
        "company_id": company_id,
        "name": wallet["name"],
        "wallet_address": wallet["wallet_address"],
        "balance": gateway.balance(company_id),
    }


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": app.title,
        "node_id": gateway.node_id,
        "blockchain_mode": "ethereum-ganache",
        "docs": "/docs",
    }


@app.post("/auth/login")
def login(request: LoginRequest) -> dict[str, Any]:
    if request.company_id not in wallets or not auth.authenticate(
        request.company_id, request.password
    ):
        raise HTTPException(401, "Companhia ou senha inválida.")
    token, expires_at = auth.issue(request.company_id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at,
        "company": public_company(request.company_id),
    }


@app.get("/auth/me")
def authenticated_company(
    session: AuthSession = Depends(require_session),
) -> dict[str, Any]:
    return public_company(session.company_id) | {"expires_at": session.expires_at}


@app.get("/node/status")
def node_status() -> dict[str, Any]:
    return gateway.status()


@app.get("/node/network")
def node_network() -> dict[str, Any]:
    return {"local": gateway.status(), "peers": []}


@app.get("/node/peers")
def peers() -> dict[str, list[str]]:
    return {"peers": []}


@app.get("/ledger")
def ledger() -> dict[str, Any]:
    blocks = list(reversed(gateway.blocks()))
    return {
        "node_id": gateway.node_id,
        "height": gateway.web3.eth.block_number,
        "chain": blocks,
        "mempool": [],
    }


@app.get("/blocks")
def blocks() -> list[dict[str, Any]]:
    return gateway.blocks()


@app.get("/transactions")
def transactions() -> list[dict[str, Any]]:
    return [
        {key: value for key, value in tx.items() if not key.startswith("_")}
        for tx in gateway.transactions()
    ]


@app.get("/companies")
def companies() -> list[dict[str, Any]]:
    return [public_company(company_id) for company_id in wallets]


@app.get("/balances")
def balances() -> dict[str, int]:
    return {company_id: gateway.balance(company_id) for company_id in wallets}


@app.get("/wallets")
def all_wallets() -> list[dict[str, Any]]:
    return [wallet(company_id) for company_id in wallets]


@app.get("/wallets/{company_id}")
def wallet(company_id: str) -> dict[str, Any]:
    if company_id not in wallets:
        raise HTTPException(404, "Carteira não encontrada.")
    return {
        key: value
        for key, value in wallets[company_id].items()
        if key not in {"private_key", "encryption_private_key"}
    } | {"balance": gateway.balance(company_id)}


@app.post("/credits/transfer")
def transfer(
    request: CreditTransferRequest,
    session: AuthSession = Depends(require_session),
) -> dict[str, Any]:
    if request.sender_company_id != session.company_id:
        raise HTTPException(403, "A sessão não pertence à carteira remetente.")
    try:
        receipt = gateway.transfer(
            request.sender_company_id,
            request.recipient_company_id,
            request.amount,
        )
        return {"accepted": True, **receipt}
    except Exception as exc:
        raise fail(exc) from exc


@app.get("/drones")
def drones() -> list[dict[str, Any]]:
    result = []
    for drone_id in DRONES:
        available, mission_id = gateway.drone_state(drone_id)
        result.append(
            {
                "drone_id": drone_id,
                "available": available,
                "active_mission": mission_id,
            }
        )
    return result


@app.post("/escort/request")
def request_escort(
    request: EscortRequest,
    session: AuthSession = Depends(require_session),
) -> dict[str, Any]:
    if request.company_id != session.company_id:
        raise HTTPException(403, "A sessão não pertence à companhia solicitante.")
    if request.route_id not in ROUTES or request.drone_id not in DRONES:
        raise HTTPException(400, "Rota ou drone inválido.")
    mission_id = f"MISSION-{uuid.uuid4().hex[:8].upper()}"
    try:
        receipt = gateway.request_escort(
            request.company_id,
            mission_id,
            request.drone_id,
            request.route_id,
            request.cost,
        )
        return {
            "accepted": True,
            "mission_id": mission_id,
            "dispatch": {
                "drone_id": request.drone_id,
                "status": "DISPATCHED",
            },
            **receipt,
        }
    except Exception as exc:
        raise fail(exc) from exc


@app.get("/missions")
def missions() -> list[dict[str, Any]]:
    return gateway.missions()


@app.get("/missions/{mission_id}/public")
def mission(mission_id: str) -> dict[str, Any]:
    try:
        return gateway.mission(mission_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/missions/{mission_id}/complete")
def complete_mission(
    mission_id: str,
    request: MissionCompleteRequest,
    session: AuthSession = Depends(require_session),
) -> dict[str, Any]:
    if request.company_id != session.company_id:
        raise HTTPException(403, "A sessão não pertence à companhia informada.")
    try:
        current = gateway.mission(mission_id)
        if current["company_id"] != request.company_id:
            raise PermissionError("Somente a companhia dona pode concluir esta missão.")
        report = {
            "mission_id": mission_id,
            "company_id": request.company_id,
            "company_wallet_address": wallets[request.company_id]["wallet_address"],
            "drone_id": current["drone_id"],
            "route_id": current["route_id"],
            "detailed_route": ROUTES[current["route_id"]],
            "result": request.result,
            "description": request.description,
            "evidence": request.evidence,
            "strategic_notes": request.strategic_notes,
            "risk_classification": request.risk_classification,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        stored = storage.save(
            mission_id,
            report,
            wallets[request.company_id]["encryption_public_key"],
        )
        receipt = gateway.complete_mission(
            request.company_id,
            mission_id,
            request.result,
            request.risk_classification,
            stored["storage_pointer"],
            stored["report_hash"],
            stored["encrypted_file_hash"],
            stored["encrypted_access_key"],
        )
        return {
            "mission_id": mission_id,
            "status": "COMPLETED",
            "public_proof": {
                key: stored[key]
                for key in (
                    "storage_pointer",
                    "report_hash",
                    "encrypted_file_hash",
                    "encrypted_access_key",
                )
            },
            **receipt,
        }
    except Exception as exc:
        raise fail(exc) from exc


@app.post("/missions/{mission_id}/decrypt")
def decrypt_mission(
    mission_id: str,
    session: AuthSession = Depends(require_session),
) -> dict[str, Any]:
    try:
        current = gateway.mission(mission_id)
        if current["company_id"] != session.company_id:
            raise PermissionError(
                "Você consegue auditar a prova, mas não possui a chave do laudo."
            )
        report = storage.decrypt(
            mission_id, wallets[session.company_id]["encryption_private_key"]
        )
        calculated = sha256_hex(canonical_json(report))
        return {
            "report": report,
            "calculated_hash": calculated,
            "registered_hash": current["report_hash"],
            "valid": calculated == current["report_hash"],
        }
    except (ValueError, PermissionError, FileNotFoundError, InvalidTag) as exc:
        raise fail(exc) from exc


@app.get("/missions/{mission_id}/verify-file-integrity")
def verify_file(mission_id: str) -> dict[str, Any]:
    try:
        current = gateway.mission(mission_id)
        if not current["encrypted_file_hash"]:
            raise ValueError("A missão ainda não possui laudo.")
        return storage.verify(mission_id, current["encrypted_file_hash"])
    except (ValueError, FileNotFoundError) as exc:
        raise fail(exc) from exc


@app.get("/audit/verify-chain")
def verify_chain() -> dict[str, Any]:
    return {
        "valid": gateway.web3.is_connected(),
        "node_id": gateway.node_id,
        "details": {
            "message": "Integridade e consenso são validados pelo cliente Ethereum.",
            "contract_address": gateway.address,
        },
    }


@app.post("/audit/tamper-chain")
def tamper_chain() -> None:
    raise HTTPException(
        409,
        "Ganache não permite editar um bloco confirmado pela API da aplicação.",
    )


@app.post("/audit/tamper-storage")
def tamper_storage(request: TamperRequest) -> dict[str, Any]:
    mission_id = request.mission_id
    if not mission_id:
        completed = [
            item for item in gateway.missions() if item["encrypted_file_hash"]
        ]
        if not completed:
            raise HTTPException(400, "Não há missão concluída para adulterar.")
        mission_id = completed[0]["mission_id"]
    try:
        storage.tamper(mission_id)
        return {"message": "Arquivo off-chain adulterado propositalmente."}
    except (ValueError, FileNotFoundError) as exc:
        raise fail(exc) from exc


@app.post("/audit/repair")
def repair() -> dict[str, Any]:
    return {
        "replaced": False,
        "message": "No modo Ganache, consenso e persistência pertencem ao nó Ethereum.",
        "height": gateway.web3.eth.block_number,
    }


@app.post("/demo/double-spend")
def double_spend_demo() -> dict[str, Any]:
    company_id = "gulf"
    initial = gateway.balance(company_id)
    results = []
    for recipient_id in ("atlas", "orion"):
        try:
            receipt = gateway.transfer(company_id, recipient_id, initial)
            results.append({"recipient": recipient_id, "accepted": True, **receipt})
        except Exception as exc:
            results.append(
                {"recipient": recipient_id, "accepted": False, "message": str(exc)}
            )
    return {
        "initial_balance": initial,
        "attempted_amount_each": initial,
        "results": results,
        "accepted_count": sum(item["accepted"] for item in results),
        "expected": "Apenas uma transação aceita pelo smart contract.",
    }


@app.post("/demo/drone-race")
def drone_race_demo() -> dict[str, Any]:
    drone_id = "DRONE-03"
    results = []
    for company_id, route_id in (
        ("atlas", "ROTA-ALFA"),
        ("orion", "ROTA-BRAVO"),
    ):
        mission_id = f"MISSION-{uuid.uuid4().hex[:8].upper()}"
        try:
            receipt = gateway.request_escort(
                company_id, mission_id, drone_id, route_id, 10
            )
            results.append(
                {
                    "company_id": company_id,
                    "mission_id": mission_id,
                    "accepted": True,
                    **receipt,
                }
            )
        except Exception as exc:
            results.append(
                {"company_id": company_id, "accepted": False, "message": str(exc)}
            )
    return {
        "drone_id": drone_id,
        "results": results,
        "accepted_count": sum(item["accepted"] for item in results),
        "expected": "Uma missão confirmada e outra revertida.",
    }


@app.get("/demo/compare-nodes")
def compare_nodes() -> dict[str, Any]:
    return {
        "local": gateway.status() | {"balances": balances()},
        "peers": [],
        "message": "Ganache representa uma única rede Ethereum local.",
    }


def _completed_missions() -> list[dict[str, Any]]:
    return [item for item in gateway.missions() if item["report_hash"]]


@app.post("/demo/decrypt-correct-wallet")
def demo_decrypt_correct(
    session: AuthSession = Depends(require_session),
) -> dict[str, Any]:
    owned = [
        item
        for item in _completed_missions()
        if item["company_id"] == session.company_id
    ]
    if not owned:
        raise HTTPException(400, "A companhia não possui laudo concluído.")
    return decrypt_mission(owned[0]["mission_id"], session)


@app.post("/demo/decrypt-wrong-wallet")
def demo_decrypt_wrong(
    session: AuthSession = Depends(require_session),
) -> dict[str, Any]:
    foreign = [
        item
        for item in _completed_missions()
        if item["company_id"] != session.company_id
    ]
    if not foreign:
        raise HTTPException(400, "Não há laudo de outra companhia.")
    return {
        "rejected": True,
        "message": "A carteira autenticada não possui a chave privada do laudo.",
        "mission_id": foreign[0]["mission_id"],
    }
