from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from cryptography.exceptions import InvalidTag

from .data import DRONES, ROUTES
from .ledger import ESCROW_ADDRESS, Ledger, now_iso
from .models import Block, EscortRequest, MissionCompleteRequest, Transaction
from .network import PeerNetwork
from .storage import MissionStorage


class ApplicationService:
    def __init__(
        self, ledger: Ledger, storage: MissionStorage, network: PeerNetwork, auto_mine: bool
    ):
        self.ledger = ledger
        self.storage = storage
        self.network = network
        self.auto_mine = auto_mine
        self.operation_lock = asyncio.Lock()

    async def submit(self, tx: Transaction, mine: bool | None = None) -> dict[str, Any]:
        accepted, message = self.ledger.add_transaction(tx)
        if not accepted:
            raise ValueError(message)
        propagation = await self.network.propagate_transaction(tx)
        result: dict[str, Any] = {
            "accepted": True,
            "transaction": tx.model_dump(),
            "propagation": propagation,
        }
        should_mine = self.auto_mine if mine is None else mine
        if should_mine:
            block = self.ledger.mine()
            result["block"] = block.model_dump()
            result["block_propagation"] = await self.network.propagate_block(block)
        return result

    async def transfer(self, sender_id: str, recipient_id: str, amount: int) -> dict:
        if sender_id == recipient_id:
            raise ValueError("Remetente e destinatário devem ser diferentes.")
        if sender_id not in self.ledger.wallets or recipient_id not in self.ledger.wallets:
            raise ValueError("Companhia não encontrada.")
        recipient = self.ledger.wallets[recipient_id]["wallet_address"]
        tx = self.ledger.create_signed_transaction(
            sender_id,
            "TRANSFER_CREDIT",
            recipient,
            amount,
            {"currency": "OC", "recipient_company_id": recipient_id},
        )
        return await self.submit(tx)

    async def request_escort(self, request: EscortRequest) -> dict[str, Any]:
        if request.company_id not in self.ledger.wallets:
            raise ValueError("Companhia não encontrada.")
        if request.route_id not in ROUTES:
            raise ValueError("Rota não encontrada.")
        mission_id = f"MISSION-{uuid.uuid4().hex[:8].upper()}"
        payload = {
            "mission_id": mission_id,
            "company_id": request.company_id,
            "company_wallet_address": self.ledger.wallets[request.company_id][
                "wallet_address"
            ],
            "drone_id": request.drone_id,
            "route_id": request.route_id,
            "status": "ACTIVE",
        }
        tx = self.ledger.create_signed_transaction(
            request.company_id,
            "ESCORT_PAYMENT",
            ESCROW_ADDRESS,
            request.cost,
            payload,
        )
        async with self.operation_lock:
            accepted, message = self.ledger.add_transaction(tx)
            if not accepted:
                raise ValueError(message)
            dispatch_tx = self.ledger.create_signed_transaction(
                request.company_id,
                "DRONE_DISPATCH",
                ESCROW_ADDRESS,
                0,
                {
                    **payload,
                    "payment_tx_id": tx.id,
                    "dispatch_rule": "atomic-with-confirmed-payment",
                },
            )
            accepted, message = self.ledger.add_transaction(dispatch_tx)
            if not accepted:
                raise ValueError(message)
            tx_propagation, dispatch_propagation = await asyncio.gather(
                self.network.propagate_transaction(tx),
                self.network.propagate_transaction(dispatch_tx),
            )
            block = self.ledger.mine()
            block_propagation = await self.network.propagate_block(block)
            result = {
                "accepted": True,
                "transaction": tx.model_dump(),
                "dispatch_transaction": dispatch_tx.model_dump(),
                "propagation": tx_propagation,
                "dispatch_propagation": dispatch_propagation,
                "block": block.model_dump(),
                "block_propagation": block_propagation,
            }
        result["mission_id"] = mission_id
        result["dispatch"] = {
            "payment_tx_id": tx.id,
            "dispatch_tx_id": dispatch_tx.id,
            "drone_id": request.drone_id,
            "status": "DISPATCHED",
        }
        return result

    def missions(self) -> list[dict[str, Any]]:
        missions: dict[str, dict[str, Any]] = {}
        for block in self.ledger.chain:
            for tx in block.transactions:
                mission_id = tx.payload.get("mission_id")
                if not mission_id:
                    continue
                if tx.type == "ESCORT_PAYMENT":
                    missions[mission_id] = {
                        **tx.payload,
                        "payment_tx_id": tx.id,
                        "cost": tx.amount,
                        "created_at": tx.timestamp,
                        "status": "ACTIVE",
                    }
                elif tx.type == "MISSION_COMPLETE" and mission_id in missions:
                    missions[mission_id].update(
                        {
                            "status": "COMPLETED",
                            "result": tx.payload["result"],
                            "completed_at": tx.timestamp,
                        }
                    )
                elif tx.type == "MISSION_REPORT_PROOF" and mission_id in missions:
                    missions[mission_id].update(tx.payload)
        return sorted(missions.values(), key=lambda item: item["created_at"], reverse=True)

    def mission(self, mission_id: str) -> dict[str, Any]:
        for mission in self.missions():
            if mission["mission_id"] == mission_id:
                return mission
        raise ValueError("Missão não encontrada.")

    async def complete_mission(
        self, mission_id: str, request: MissionCompleteRequest
    ) -> dict[str, Any]:
        mission = self.mission(mission_id)
        if mission["status"] != "ACTIVE":
            raise ValueError("A missão já foi concluída.")
        if mission["company_id"] != request.company_id:
            raise PermissionError("Somente a companhia dona pode concluir esta missão.")
        wallet = self.ledger.wallets[request.company_id]
        report = {
            "mission_id": mission_id,
            "company_id": request.company_id,
            "company_wallet_address": wallet["wallet_address"],
            "drone_id": mission["drone_id"],
            "route_id": mission["route_id"],
            "detailed_route": ROUTES[mission["route_id"]],
            "result": request.result,
            "description": request.description,
            "evidence": request.evidence,
            "strategic_notes": request.strategic_notes,
            "risk_classification": request.risk_classification,
            "timestamp": now_iso(),
        }
        stored = self.storage.save(
            mission_id, report, wallet["encryption_public_key"]
        )
        await self.network.replicate_file(mission_id, stored["encrypted_file"])
        complete_tx = self.ledger.create_signed_transaction(
            request.company_id,
            "MISSION_COMPLETE",
            ESCROW_ADDRESS,
            0,
            {
                "mission_id": mission_id,
                "result": request.result,
                "risk_classification": request.risk_classification,
            },
        )
        proof_tx = self.ledger.create_signed_transaction(
            request.company_id,
            "MISSION_REPORT_PROOF",
            ESCROW_ADDRESS,
            0,
            {
                "mission_id": mission_id,
                "company_wallet_address": wallet["wallet_address"],
                "drone_id": mission["drone_id"],
                "route_id": mission["route_id"],
                "result": request.result,
                "storage_pointer": mission_id,
                "report_hash": stored["report_hash"],
                "encrypted_file_hash": stored["encrypted_file_hash"],
                "encrypted_access_key": stored["encrypted_access_key"],
            },
        )
        async with self.operation_lock:
            accepted, error = self.ledger.add_transaction(complete_tx)
            if not accepted:
                raise ValueError(error)
            accepted, error = self.ledger.add_transaction(proof_tx)
            if not accepted:
                raise ValueError(error)
            await self.network.propagate_transaction(complete_tx)
            await self.network.propagate_transaction(proof_tx)
            block = self.ledger.mine()
            await self.network.propagate_block(block)
        return {
            "mission_id": mission_id,
            "status": "COMPLETED",
            "public_proof": proof_tx.payload,
            "block": block.model_dump(),
        }

    def decrypt_mission(self, mission_id: str, company_id: str) -> dict[str, Any]:
        mission = self.mission(mission_id)
        if mission["company_id"] != company_id:
            raise PermissionError(
                "Você consegue auditar a existência e integridade desta missão, "
                "mas não possui a chave para visualizar os detalhes confidenciais."
            )
        wallet = self.ledger.wallets[company_id]
        try:
            report = self.storage.decrypt(
                mission_id, wallet["encryption_private_key"]
            )
        except (InvalidTag, json.JSONDecodeError, ValueError) as exc:
            raise ValueError("O arquivo não pôde ser descriptografado; pode estar adulterado.") from exc
        from .crypto import canonical_json, sha256_hex

        calculated = sha256_hex(canonical_json(report))
        return {
            "report": report,
            "calculated_hash": calculated,
            "registered_hash": mission["report_hash"],
            "valid": calculated == mission["report_hash"],
        }

    async def double_spend_demo(self, company_id: str = "gulf") -> dict[str, Any]:
        balance = self.ledger.balance(
            self.ledger.wallets[company_id]["wallet_address"]
        )
        amount = max(1, balance)
        tx1 = self.ledger.create_signed_transaction(
            company_id, "TRANSFER_CREDIT", self.ledger.wallets["atlas"]["wallet_address"],
            amount, {"demo": "double-spend", "attempt": 1}
        )
        tx2 = self.ledger.create_signed_transaction(
            company_id, "TRANSFER_CREDIT", self.ledger.wallets["orion"]["wallet_address"],
            amount, {"demo": "double-spend", "attempt": 2}
        )

        async def attempt(tx: Transaction) -> dict[str, Any]:
            accepted, message = await asyncio.to_thread(self.ledger.add_transaction, tx)
            return {"transaction_id": tx.id, "accepted": accepted, "message": message}

        results = await asyncio.gather(attempt(tx1), attempt(tx2))
        accepted = [item for item in results if item["accepted"]]
        if accepted:
            block = self.ledger.mine()
            await self.network.propagate_block(block)
        return {
            "initial_balance": balance,
            "attempted_amount_each": amount,
            "results": results,
            "accepted_count": len(accepted),
            "expected": "Apenas uma transação aceita.",
        }

    async def drone_race_demo(self, drone_id: str = "DRONE-03") -> dict[str, Any]:
        requests = [
            EscortRequest(company_id="atlas", drone_id=drone_id, route_id="ROTA-ALFA", cost=10),
            EscortRequest(company_id="orion", drone_id=drone_id, route_id="ROTA-BRAVO", cost=10),
        ]

        async def attempt(request: EscortRequest) -> dict[str, Any]:
            try:
                result = await self.request_escort(request)
                return {"company_id": request.company_id, "accepted": True, "mission_id": result["mission_id"]}
            except ValueError as exc:
                return {"company_id": request.company_id, "accepted": False, "message": str(exc)}

        results = await asyncio.gather(*(attempt(item) for item in requests))
        return {
            "drone_id": drone_id,
            "results": results,
            "accepted_count": sum(1 for item in results if item["accepted"]),
            "expected": "Uma missão confirmada e outra rejeitada.",
        }
