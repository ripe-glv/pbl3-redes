from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from web3 import Web3


EVENT_TYPES = {
    "GenesisCredit": "GENESIS_CREDIT",
    "CreditTransferred": "TRANSFER_CREDIT",
    "EscortRequested": "ESCORT_PAYMENT",
    "MissionCompleted": "MISSION_COMPLETE",
}


class EvmGateway:
    def __init__(self, rpc_url: str, artifact_path: Path, node_id: str = "ganache-evm"):
        self.rpc_url = rpc_url
        self.artifact_path = artifact_path
        self.node_id = node_id
        self.web3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
        self._wait_until_ready()
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        self.address = Web3.to_checksum_address(artifact["address"])
        self.company_addresses = {
            company_id: Web3.to_checksum_address(address)
            for company_id, address in artifact["companies"].items()
        }
        self.contract = self.web3.eth.contract(
            address=self.address, abi=artifact["abi"]
        )

    def _wait_until_ready(self) -> None:
        for _ in range(90):
            if self.web3.is_connected() and self.artifact_path.exists():
                return
            time.sleep(1)
        raise RuntimeError("Ganache ou artefato do contrato indisponível.")

    def balance(self, company_id: str) -> int:
        return int(
            self.contract.functions.credits(
                self.company_addresses[company_id]
            ).call()
        )

    def transfer(self, sender_id: str, recipient_id: str, amount: int) -> dict[str, Any]:
        function = self.contract.functions.transferCredits(
            self.company_addresses[recipient_id], amount
        )
        return self._send(function, sender_id)

    def request_escort(
        self, company_id: str, mission_id: str, drone_id: str, route_id: str, cost: int
    ) -> dict[str, Any]:
        function = self.contract.functions.requestEscort(
            mission_id, drone_id, route_id, cost
        )
        return self._send(function, company_id)

    def complete_mission(
        self,
        company_id: str,
        mission_id: str,
        result: str,
        risk_classification: str,
        storage_pointer: str,
        report_hash: str,
        encrypted_file_hash: str,
        encrypted_access_key: str,
    ) -> dict[str, Any]:
        function = self.contract.functions.completeMission(
            mission_id,
            result,
            risk_classification,
            storage_pointer,
            report_hash,
            encrypted_file_hash,
            encrypted_access_key,
        )
        return self._send(function, company_id)

    def _send(self, function: Any, company_id: str) -> dict[str, Any]:
        tx_hash = function.transact(
            {"from": self.company_addresses[company_id], "gas": 4_000_000}
        )
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
        if receipt.status != 1:
            raise ValueError("A transação Ethereum foi revertida pelo contrato.")
        return {
            "transaction_hash": receipt.transactionHash.hex(),
            "block_number": receipt.blockNumber,
            "gas_used": receipt.gasUsed,
            "status": "CONFIRMED",
        }

    def missions(self) -> list[dict[str, Any]]:
        count = int(self.contract.functions.getMissionCount().call())
        result = []
        for index in range(count):
            mission_id = self.contract.functions.getMissionId(index).call()
            raw = self.contract.functions.getMission(mission_id).call()
            result.append(
                {
                    "mission_id": raw[0],
                    "company_wallet_address": raw[1],
                    "company_id": raw[2],
                    "drone_id": raw[3],
                    "route_id": raw[4],
                    "cost": int(raw[5]),
                    "created_at": datetime.fromtimestamp(
                        int(raw[6]), timezone.utc
                    ).isoformat(),
                    "status": "COMPLETED" if raw[7] else "ACTIVE",
                    "result": raw[8] or None,
                    "risk_classification": raw[9] or None,
                    "storage_pointer": raw[10] or None,
                    "report_hash": raw[11] or None,
                    "encrypted_file_hash": raw[12] or None,
                    "encrypted_access_key": raw[13] or None,
                }
            )
        return sorted(result, key=lambda item: item["created_at"], reverse=True)

    def mission(self, mission_id: str) -> dict[str, Any]:
        for mission in self.missions():
            if mission["mission_id"] == mission_id:
                return mission
        raise ValueError("Missão não encontrada.")

    def drone_state(self, drone_id: str) -> tuple[bool, str | None]:
        busy = bool(self.contract.functions.droneBusy(drone_id).call())
        mission_id = self.contract.functions.droneMission(drone_id).call()
        return not busy, mission_id or None

    def transactions(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for event_name, tx_type in EVENT_TYPES.items():
            event = getattr(self.contract.events, event_name)
            for log in event.get_logs(from_block=0, to_block="latest"):
                args = dict(log["args"])
                records.append(self._event_transaction(tx_type, event_name, log, args))
        return sorted(
            records,
            key=lambda item: (item["_block_number"], item["_log_index"]),
            reverse=True,
        )

    def _event_transaction(
        self, tx_type: str, event_name: str, log: Any, args: dict[str, Any]
    ) -> dict[str, Any]:
        sender = args.get("sender") or args.get("company") or "SYSTEM"
        recipient = args.get("recipient") or self.address
        if event_name == "GenesisCredit":
            sender = "SYSTEM"
            recipient = args["company"]
        amount = int(args.get("amount") or args.get("cost") or 0)
        payload = {
            key: value
            for key, value in args.items()
            if key not in {"sender", "recipient", "company", "amount", "cost"}
        }
        if event_name == "EscortRequested":
            payload["status"] = "ACTIVE"
        block = self.web3.eth.get_block(log["blockNumber"])
        return {
            "id": log["transactionHash"].hex()
            + f":{int(log['logIndex'])}",
            "type": tx_type,
            "sender": str(sender),
            "recipient": str(recipient),
            "amount": amount,
            "timestamp": datetime.fromtimestamp(
                int(block["timestamp"]), timezone.utc
            ).isoformat(),
            "payload": payload,
            "signature": "Ethereum account signature",
            "public_key": "",
            "_block_number": int(log["blockNumber"]),
            "_log_index": int(log["logIndex"]),
        }

    def blocks(self) -> list[dict[str, Any]]:
        transactions = self.transactions()
        grouped: dict[int, list[dict[str, Any]]] = {}
        for tx in transactions:
            grouped.setdefault(tx["_block_number"], []).append(
                {key: value for key, value in tx.items() if not key.startswith("_")}
            )
        result = []
        for number in range(self.web3.eth.block_number, -1, -1):
            block = self.web3.eth.get_block(number)
            result.append(
                {
                    "index": number,
                    "timestamp": datetime.fromtimestamp(
                        int(block["timestamp"]), timezone.utc
                    ).isoformat(),
                    "previous_hash": block["parentHash"].hex(),
                    "hash": block["hash"].hex(),
                    "nonce": int.from_bytes(block["nonce"], "big"),
                    "transactions": grouped.get(number, []),
                    "node_id": "ganache",
                }
            )
        return result

    def status(self) -> dict[str, Any]:
        transactions = self.transactions()
        return {
            "node_id": self.node_id,
            "online": self.web3.is_connected(),
            "height": self.web3.eth.block_number,
            "transactions": len(transactions),
            "mempool": 0,
            "peers": 0,
            "chain_valid": self.web3.is_connected(),
            "chain_id": self.web3.eth.chain_id,
            "contract_address": self.address,
            "blockchain_mode": "ethereum-ganache",
        }
