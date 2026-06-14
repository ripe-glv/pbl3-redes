from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import get_settings
from .crypto import sign
from .data import DRONES, ROUTES
from .auth import AuthSession, auth, require_session
from .ledger import Ledger, transaction_signing_body
from .models import (
    Block,
    CreditTransferRequest,
    EscortRequest,
    LoginRequest,
    MissionCompleteRequest,
    PeerRequest,
    SignRequest,
    TamperRequest,
    Transaction,
)
from .network import PeerNetwork
from .service import ApplicationService
from .storage import MissionStorage

settings = get_settings()
ledger = Ledger(settings.node_id, settings.ledger_file, settings.difficulty)
ledger.peers.update(settings.peers)
storage = MissionStorage(settings.storage_dir / "missions")
network = PeerNetwork(ledger)
service = ApplicationService(ledger, storage, network, settings.auto_mine)

app = FastAPI(
    title="Operational Credit Distributed Ledger",
    description="TEC502 - Problema 3: Economia e Auditoria de Guerra",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def fail(exc: Exception) -> HTTPException:
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@app.get("/")
def root() -> dict[str, str]:
    return {"name": app.title, "node_id": settings.node_id, "docs": "/docs"}


@app.post("/auth/login")
def login(request: LoginRequest) -> dict[str, Any]:
    if request.company_id not in ledger.wallets:
        raise HTTPException(401, "Companhia ou senha inválida.")
    if not auth.authenticate(request.company_id, request.password):
        raise HTTPException(401, "Companhia ou senha inválida.")
    token, expires_at = auth.issue(request.company_id)
    wallet = ledger.wallets[request.company_id]
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at,
        "company": {
            "company_id": request.company_id,
            "name": wallet["name"],
            "wallet_address": wallet["wallet_address"],
            "balance": ledger.balance(wallet["wallet_address"]),
        },
    }


@app.get("/auth/me")
def authenticated_company(
    session: AuthSession = Depends(require_session),
) -> dict[str, Any]:
    wallet = ledger.wallets[session.company_id]
    return {
        "company_id": session.company_id,
        "name": wallet["name"],
        "wallet_address": wallet["wallet_address"],
        "balance": ledger.balance(wallet["wallet_address"]),
        "expires_at": session.expires_at,
    }


@app.get("/node/status")
async def node_status() -> dict[str, Any]:
    valid, _ = ledger.validate_chain()
    return {
        "node_id": settings.node_id,
        "online": True,
        "height": len(ledger.chain) - 1,
        "transactions": len(ledger.confirmed_transactions()),
        "mempool": len(ledger.mempool),
        "peers": len(ledger.peers),
        "chain_valid": valid,
    }


@app.get("/node/network")
async def node_network() -> dict[str, Any]:
    return {"local": await node_status(), "peers": await network.peer_statuses()}


@app.get("/node/peers")
def list_peers() -> dict[str, list[str]]:
    return {"peers": sorted(ledger.peers)}


@app.post("/node/peers")
def add_peer(request: PeerRequest) -> dict[str, Any]:
    ledger.peers.add(request.url.rstrip("/"))
    ledger._save()
    return {"registered": request.url, "peers": sorted(ledger.peers)}


@app.post("/node/sync")
@app.post("/node/resolve-conflicts")
async def sync() -> dict[str, Any]:
    return await network.resolve_conflicts()


@app.get("/ledger")
def get_ledger() -> dict[str, Any]:
    return {
        "node_id": settings.node_id,
        "height": len(ledger.chain) - 1,
        "chain": [block.model_dump() for block in ledger.chain],
        "mempool": [tx.model_dump() for tx in ledger.mempool],
    }


@app.get("/blocks")
def get_blocks() -> list[dict[str, Any]]:
    return [block.model_dump() for block in reversed(ledger.chain)]


@app.get("/blocks/{index}")
def get_block(index: int) -> dict[str, Any]:
    try:
        return ledger.chain[index].model_dump()
    except IndexError as exc:
        raise HTTPException(404, "Bloco não encontrado.") from exc


@app.get("/transactions")
def get_transactions() -> list[dict[str, Any]]:
    return [tx.model_dump() for tx in reversed(ledger.confirmed_transactions())]


@app.get("/transactions/{transaction_id}")
def get_transaction(transaction_id: str) -> dict[str, Any]:
    for tx in ledger.confirmed_transactions() + ledger.mempool:
        if tx.id == transaction_id:
            return tx.model_dump()
    raise HTTPException(404, "Transação não encontrada.")


@app.post("/transactions")
async def post_transaction(tx: Transaction) -> dict[str, Any]:
    try:
        return await service.submit(tx, mine=False)
    except ValueError as exc:
        raise fail(exc)


@app.post("/receive-transaction")
def receive_transaction(tx: Transaction) -> dict[str, Any]:
    accepted, message = ledger.add_transaction(tx)
    if not accepted and message != "Transação duplicada.":
        raise HTTPException(400, message)
    return {"accepted": accepted, "message": message}


@app.post("/mine")
async def mine() -> dict[str, Any]:
    try:
        block = ledger.mine()
        return {
            "block": block.model_dump(),
            "propagation": await network.propagate_block(block),
        }
    except ValueError as exc:
        raise fail(exc)


@app.post("/receive-block")
async def receive_block(block: Block) -> dict[str, Any]:
    accepted, message = ledger.add_block(block)
    if not accepted and "sincronização" in message:
        resolution = await network.resolve_conflicts()
        return {"accepted": False, "message": message, "resolution": resolution}
    if not accepted:
        raise HTTPException(400, message)
    return {"accepted": True, "message": message}


@app.get("/companies")
def companies() -> list[dict[str, Any]]:
    return [
        {
            "company_id": wallet["company_id"],
            "name": wallet["name"],
            "wallet_address": wallet["wallet_address"],
            "balance": ledger.balance(wallet["wallet_address"]),
        }
        for wallet in ledger.wallets.values()
    ]


@app.get("/balances")
def balances() -> dict[str, int]:
    return {
        wallet["company_id"]: ledger.balance(wallet["wallet_address"])
        for wallet in ledger.wallets.values()
    }


@app.get("/companies/{company_id}/balance")
def company_balance(company_id: str) -> dict[str, Any]:
    if company_id not in ledger.wallets:
        raise HTTPException(404, "Companhia não encontrada.")
    wallet = ledger.wallets[company_id]
    return {
        "company_id": company_id,
        "wallet_address": wallet["wallet_address"],
        "balance": ledger.balance(wallet["wallet_address"]),
        "source": "confirmed ledger transactions",
    }


@app.get("/companies/{company_id}/history")
@app.get("/wallets/{company_id}/transactions")
def company_history(company_id: str) -> list[dict[str, Any]]:
    if company_id not in ledger.wallets:
        raise HTTPException(404, "Companhia não encontrada.")
    address = ledger.wallets[company_id]["wallet_address"]
    return [
        tx.model_dump()
        for tx in reversed(ledger.confirmed_transactions())
        if address in {tx.sender, tx.recipient}
        or tx.payload.get("company_wallet_address") == address
    ]


@app.post("/credits/transfer")
async def transfer(
    request: CreditTransferRequest,
    session: AuthSession = Depends(require_session),
) -> dict[str, Any]:
    if request.sender_company_id != session.company_id:
        raise HTTPException(403, "A sessão não pertence à carteira remetente.")
    try:
        return await service.transfer(
            request.sender_company_id, request.recipient_company_id, request.amount
        )
    except ValueError as exc:
        raise fail(exc)


@app.get("/wallets")
def wallets() -> list[dict[str, Any]]:
    return [public_wallet(company_id) for company_id in ledger.wallets]


@app.get("/wallets/{company_id}")
def public_wallet(company_id: str) -> dict[str, Any]:
    if company_id not in ledger.wallets:
        raise HTTPException(404, "Carteira não encontrada.")
    wallet = ledger.wallets[company_id]
    return {
        key: value
        for key, value in wallet.items()
        if key not in {"private_key", "encryption_private_key"}
    } | {"balance": ledger.balance(wallet["wallet_address"])}


@app.post("/wallets/{company_id}/sign")
def sign_message(
    company_id: str,
    request: SignRequest,
    session: AuthSession = Depends(require_session),
) -> dict[str, str]:
    if company_id not in ledger.wallets:
        raise HTTPException(404, "Carteira não encontrada.")
    if company_id != session.company_id:
        raise HTTPException(403, "A sessão não pertence a esta carteira.")
    return {
        "signature": sign(ledger.wallets[company_id]["private_key"], request.message)
    }


@app.get("/drones")
def drones() -> list[dict[str, Any]]:
    active = ledger.active_drone_missions()
    return [
        {
            "drone_id": drone_id,
            "available": drone_id not in active,
            "active_mission": active.get(drone_id),
        }
        for drone_id in DRONES
    ]


@app.get("/drones/{drone_id}/missions")
def drone_missions(drone_id: str) -> list[dict[str, Any]]:
    return [item for item in service.missions() if item["drone_id"] == drone_id]


@app.post("/escort/request")
async def escort(
    request: EscortRequest,
    session: AuthSession = Depends(require_session),
) -> dict[str, Any]:
    if request.company_id != session.company_id:
        raise HTTPException(403, "A sessão não pertence à companhia solicitante.")
    try:
        return await service.request_escort(request)
    except (ValueError, PermissionError) as exc:
        raise fail(exc)


@app.get("/missions")
def missions() -> list[dict[str, Any]]:
    return service.missions()


@app.get("/missions/{mission_id}/public")
def public_mission(mission_id: str) -> dict[str, Any]:
    try:
        return service.mission(mission_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/missions/{mission_id}/complete")
async def complete_mission(
    mission_id: str,
    request: MissionCompleteRequest,
    session: AuthSession = Depends(require_session),
) -> dict[str, Any]:
    if request.company_id != session.company_id:
        raise HTTPException(403, "A sessão não pertence à companhia informada.")
    try:
        return await service.complete_mission(mission_id, request)
    except (ValueError, PermissionError) as exc:
        raise fail(exc)


@app.post("/missions/{mission_id}/decrypt")
def decrypt_mission(
    mission_id: str,
    session: AuthSession = Depends(require_session),
) -> dict[str, Any]:
    try:
        return service.decrypt_mission(mission_id, session.company_id)
    except (ValueError, PermissionError, FileNotFoundError) as exc:
        raise fail(exc)


@app.get("/missions/{mission_id}/verify-file-integrity")
def verify_file(mission_id: str) -> dict[str, Any]:
    try:
        mission = service.mission(mission_id)
        if "encrypted_file_hash" not in mission:
            raise ValueError("A missão ainda não possui laudo.")
        return storage.verify(mission_id, mission["encrypted_file_hash"])
    except (ValueError, FileNotFoundError) as exc:
        raise fail(exc)


class StorageReplica(BaseModel):
    mission_id: str
    encrypted_file: str


class SaveEncryptedReport(BaseModel):
    mission_id: str
    company_id: str
    report: dict[str, Any]


@app.post("/storage/save-encrypted-report")
def save_encrypted_report(
    request: SaveEncryptedReport,
    session: AuthSession = Depends(require_session),
) -> dict[str, str]:
    if request.company_id not in ledger.wallets:
        raise HTTPException(404, "Companhia não encontrada.")
    if request.company_id != session.company_id:
        raise HTTPException(403, "A sessão não pertence à companhia informada.")
    try:
        mission = service.mission(request.mission_id)
        if mission["company_id"] != request.company_id:
            raise PermissionError("A carteira não é dona desta missão.")
        return storage.save(
            request.mission_id,
            request.report,
            ledger.wallets[request.company_id]["encryption_public_key"],
        )
    except (ValueError, PermissionError) as exc:
        raise fail(exc)


@app.post("/storage/replica")
def storage_replica(request: StorageReplica) -> dict[str, bool]:
    try:
        storage.save_replica(request.mission_id, request.encrypted_file)
        return {"saved": True}
    except ValueError as exc:
        raise fail(exc)


@app.get("/storage/{mission_id}")
def get_storage(mission_id: str) -> dict[str, str]:
    try:
        return {"mission_id": mission_id, "encrypted_file": storage.read_encrypted(mission_id)}
    except (ValueError, FileNotFoundError) as exc:
        raise fail(exc)


@app.post("/storage/{mission_id}/tamper")
def tamper_storage(mission_id: str) -> dict[str, str]:
    try:
        storage.tamper(mission_id)
        return {"message": "Arquivo off-chain adulterado propositalmente."}
    except (ValueError, FileNotFoundError) as exc:
        raise fail(exc)


@app.get("/audit/verify-chain")
def verify_chain() -> dict[str, Any]:
    valid, error = ledger.validate_chain()
    return {"valid": valid, "node_id": settings.node_id, "details": error}


@app.post("/audit/tamper-chain")
def tamper_chain() -> dict[str, Any]:
    if len(ledger.chain) < 2:
        raise HTTPException(400, "Mine ao menos um bloco antes do teste.")
    ledger.chain[1].transactions[0].payload["tampered"] = True
    ledger._save()
    return {"message": "Bloco local adulterado propositalmente.", "block_index": 1}


@app.post("/audit/tamper-storage")
def audit_tamper_storage(request: TamperRequest) -> dict[str, Any]:
    mission_id = request.mission_id
    if not mission_id:
        completed = [m for m in service.missions() if "encrypted_file_hash" in m]
        if not completed:
            raise HTTPException(400, "Não há missão concluída para adulterar.")
        mission_id = completed[0]["mission_id"]
    return tamper_storage(mission_id)


@app.post("/audit/repair")
async def repair() -> dict[str, Any]:
    return await network.resolve_conflicts()


@app.post("/demo/double-spend")
async def demo_double_spend() -> dict[str, Any]:
    return await service.double_spend_demo()


@app.post("/demo/drone-race")
async def demo_drone_race() -> dict[str, Any]:
    return await service.drone_race_demo()


@app.post("/demo/tamper")
def demo_tamper(request: TamperRequest) -> dict[str, Any]:
    if request.target == "storage":
        return audit_tamper_storage(request)
    return tamper_chain()


@app.get("/demo/compare-nodes")
async def compare_nodes() -> dict[str, Any]:
    return {
        "local": {
            "node_id": settings.node_id,
            "height": len(ledger.chain) - 1,
            "balances": balances(),
            "tip_hash": ledger.chain[-1].hash,
        },
        "peers": await network.peer_statuses(),
    }


@app.post("/demo/decrypt-correct-wallet")
def demo_decrypt_correct(
    session: AuthSession = Depends(require_session),
) -> dict[str, Any]:
    completed = [m for m in service.missions() if "report_hash" in m]
    if not completed:
        raise HTTPException(400, "Não há missão concluída.")
    owned = [item for item in completed if item["company_id"] == session.company_id]
    if not owned:
        raise HTTPException(403, "A companhia autenticada não possui laudo concluído.")
    return service.decrypt_mission(owned[0]["mission_id"], session.company_id)


@app.post("/demo/decrypt-wrong-wallet")
def demo_decrypt_wrong(
    session: AuthSession = Depends(require_session),
) -> dict[str, Any]:
    completed = [m for m in service.missions() if "report_hash" in m]
    if not completed:
        raise HTTPException(400, "Não há missão concluída.")
    foreign = [item for item in completed if item["company_id"] != session.company_id]
    if not foreign:
        raise HTTPException(400, "Não há laudo de outra companhia para testar.")
    mission = foreign[0]
    try:
        service.decrypt_mission(mission["mission_id"], session.company_id)
    except PermissionError as exc:
        return {"rejected": True, "message": str(exc)}
    return {"rejected": False}
