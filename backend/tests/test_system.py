from __future__ import annotations

from pathlib import Path

import pytest

from app.ledger import Ledger
from app.models import EscortRequest, MissionCompleteRequest
from app.service import ApplicationService
from app.storage import MissionStorage


class DummyNetwork:
    async def propagate_transaction(self, _tx):
        return {}

    async def propagate_block(self, _block):
        return {}

    async def replicate_file(self, _mission_id, _encrypted_file):
        return {}


@pytest.fixture()
def anyio_backend():
    return "asyncio"


@pytest.fixture()
def service(tmp_path: Path) -> ApplicationService:
    ledger = Ledger("test-node", tmp_path / "ledger.json", difficulty=1)
    storage = MissionStorage(tmp_path / "storage")
    return ApplicationService(ledger, storage, DummyNetwork(), auto_mine=True)


def test_genesis_is_deterministic_and_balances_come_from_ledger(tmp_path: Path):
    first = Ledger("node-a", tmp_path / "a.json", difficulty=1)
    second = Ledger("node-b", tmp_path / "b.json", difficulty=1)
    assert first.chain[0].model_dump() == second.chain[0].model_dump()
    assert all(
        first.balance(wallet["wallet_address"]) == 100
        for wallet in first.wallets.values()
    )


@pytest.mark.anyio
async def test_double_spend_accepts_only_one(service: ApplicationService):
    result = await service.double_spend_demo()
    assert result["accepted_count"] == 1
    assert sum(item["accepted"] for item in result["results"]) == 1
    valid, error = service.ledger.validate_chain()
    assert valid, error


@pytest.mark.anyio
async def test_drone_race_allocates_once(service: ApplicationService):
    result = await service.drone_race_demo()
    assert result["accepted_count"] == 1
    active = service.ledger.active_drone_missions()
    assert list(active).count("DRONE-03") == 1


@pytest.mark.anyio
async def test_report_is_encrypted_and_owner_can_decrypt(service: ApplicationService):
    escort = await service.request_escort(
        EscortRequest(
            company_id="gulf",
            drone_id="DRONE-01",
            route_id="ROTA-ALFA",
            cost=20,
        )
    )
    mission_id = escort["mission_id"]
    await service.complete_mission(
        mission_id,
        MissionCompleteRequest(
            company_id="gulf",
            result="ROTA_SEGURA",
            description="Detalhes confidenciais da missão.",
            evidence=["radar-001"],
            strategic_notes="Nota reservada.",
            risk_classification="BAIXO",
        ),
    )
    encrypted = service.storage.read_encrypted(mission_id)
    assert "Detalhes confidenciais" not in encrypted
    decrypted = service.decrypt_mission(mission_id, "gulf")
    assert decrypted["valid"] is True
    assert decrypted["report"]["description"] == "Detalhes confidenciais da missão."
    with pytest.raises(PermissionError):
        service.decrypt_mission(mission_id, "atlas")


@pytest.mark.anyio
async def test_tampering_is_detected(service: ApplicationService):
    escort = await service.request_escort(
        EscortRequest(
            company_id="orion",
            drone_id="DRONE-02",
            route_id="ROTA-BRAVO",
            cost=10,
        )
    )
    mission_id = escort["mission_id"]
    await service.complete_mission(
        mission_id,
        MissionCompleteRequest(
            company_id="orion",
            result="OBSTACULO_DETECTADO",
            description="Objeto detectado.",
            risk_classification="ALTO",
        ),
    )
    mission = service.mission(mission_id)
    assert service.storage.verify(mission_id, mission["encrypted_file_hash"])["valid"]
    service.storage.tamper(mission_id)
    assert not service.storage.verify(
        mission_id, mission["encrypted_file_hash"]
    )["valid"]
    service.ledger.chain[1].transactions[0].payload["tampered"] = True
    valid, details = service.ledger.validate_chain()
    assert valid is False
    assert details["block_index"] == 1
