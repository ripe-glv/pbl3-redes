from __future__ import annotations

import copy
import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .crypto import canonical_json, sha256_hex, sign, verify, wallet_address
from .data import DRONES, build_wallets
from .models import Block, Transaction

SYSTEM_ADDRESS = "SYSTEM"
ESCROW_ADDRESS = "ESCORT_NETWORK"
GENESIS_TIMESTAMP = "2026-05-26T00:00:00+00:00"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def transaction_signing_body(tx: Transaction | dict[str, Any]) -> dict[str, Any]:
    data = tx.model_dump() if isinstance(tx, Transaction) else copy.deepcopy(tx)
    data.pop("signature", None)
    return data


def block_hash(block: Block | dict[str, Any]) -> str:
    data = block.model_dump() if isinstance(block, Block) else copy.deepcopy(block)
    data.pop("hash", None)
    return sha256_hex(canonical_json(data))


class Ledger:
    def __init__(self, node_id: str, path: Path, difficulty: int = 3):
        self.node_id = node_id
        self.path = path
        self.difficulty = difficulty
        self.lock = threading.RLock()
        self.wallets = build_wallets()
        self.chain: list[Block] = []
        self.mempool: list[Transaction] = []
        self.peers: set[str] = set()
        self._load_or_initialize()

    def _genesis_block(self) -> Block:
        transactions = []
        for company_id in sorted(self.wallets):
            wallet = self.wallets[company_id]
            transactions.append(
                Transaction(
                    id=f"genesis-{company_id}",
                    type="GENESIS_CREDIT",
                    sender=SYSTEM_ADDRESS,
                    recipient=wallet["wallet_address"],
                    amount=100,
                    timestamp=GENESIS_TIMESTAMP,
                    payload={"company_id": company_id, "currency": "OC"},
                )
            )
        candidate = Block(
            index=0,
            timestamp=GENESIS_TIMESTAMP,
            previous_hash="0" * 64,
            hash="",
            nonce=0,
            transactions=transactions,
            node_id="genesis",
        )
        return self._proof_of_work(candidate)

    def _load_or_initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.chain = [Block.model_validate(block) for block in data["chain"]]
            self.mempool = [
                Transaction.model_validate(tx) for tx in data.get("mempool", [])
            ]
            self.peers = set(data.get("peers", []))
        else:
            self.chain = [self._genesis_block()]
            self._save()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(
            json.dumps(
                {
                    "chain": [block.model_dump() for block in self.chain],
                    "mempool": [tx.model_dump() for tx in self.mempool],
                    "peers": sorted(self.peers),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        temp.replace(self.path)

    def confirmed_transactions(self) -> list[Transaction]:
        return [tx for block in self.chain for tx in block.transactions]

    def transaction_ids(self, include_pending: bool = True) -> set[str]:
        ids = {tx.id for tx in self.confirmed_transactions()}
        if include_pending:
            ids.update(tx.id for tx in self.mempool)
        return ids

    def balance(self, address: str, include_pending: bool = False) -> int:
        balance = 0
        transactions = self.confirmed_transactions()
        if include_pending:
            transactions += self.mempool
        for tx in transactions:
            if tx.recipient == address:
                balance += tx.amount
            if tx.sender == address:
                balance -= tx.amount
        return balance

    def active_drone_missions(
        self, include_pending: bool = True, extra: list[Transaction] | None = None
    ) -> dict[str, str]:
        active: dict[str, str] = {}
        transactions = self.confirmed_transactions()
        if include_pending:
            transactions += self.mempool
        transactions += extra or []
        for tx in transactions:
            if tx.type == "ESCORT_PAYMENT":
                active[tx.payload["drone_id"]] = tx.payload["mission_id"]
            elif tx.type == "MISSION_COMPLETE":
                mission_id = tx.payload["mission_id"]
                for drone_id, active_id in list(active.items()):
                    if active_id == mission_id:
                        active.pop(drone_id)
        return active

    def _mission_transactions(
        self, mission_id: str, include_mempool: bool, prior: list[Transaction]
    ) -> list[Transaction]:
        transactions = self.confirmed_transactions()
        if include_mempool:
            transactions += self.mempool
        transactions += prior
        return [
            tx for tx in transactions if tx.payload.get("mission_id") == mission_id
        ]

    def _validate_signature(self, tx: Transaction) -> tuple[bool, str]:
        if tx.type == "GENESIS_CREDIT":
            return False, "Créditos de gênese só podem existir no bloco gênese."
        if not tx.public_key or not tx.signature:
            return False, "Assinatura e chave pública são obrigatórias."
        if wallet_address(tx.public_key) != tx.sender:
            return False, "A chave pública não corresponde à carteira remetente."
        if not verify(tx.public_key, tx.signature, transaction_signing_body(tx)):
            return False, "Assinatura digital inválida."
        return True, ""

    def validate_transaction(
        self,
        tx: Transaction,
        *,
        include_mempool: bool = True,
        prior_in_block: list[Transaction] | None = None,
    ) -> tuple[bool, str]:
        if tx.id in self.transaction_ids(include_pending=include_mempool):
            return False, "Transação duplicada."
        valid, error = self._validate_signature(tx)
        if not valid:
            return valid, error
        prior = prior_in_block or []
        if tx.type in {"TRANSFER_CREDIT", "ESCORT_PAYMENT"}:
            available = self.balance(tx.sender, include_pending=include_mempool)
            for item in prior:
                if item.sender == tx.sender:
                    available -= item.amount
                if item.recipient == tx.sender:
                    available += item.amount
            if available < tx.amount:
                return (
                    False,
                    "Saldo insuficiente ou tentativa de duplo gasto detectada.",
                )
        if tx.type == "ESCORT_PAYMENT":
            drone_id = tx.payload.get("drone_id")
            if drone_id not in DRONES:
                return False, "Drone inexistente."
            active = self.active_drone_missions(
                include_pending=include_mempool, extra=prior
            )
            if drone_id in active:
                return False, "Drone indisponível: já alocado em missão ativa."
            if tx.recipient != ESCROW_ADDRESS:
                return False, "Destinatário de pagamento inválido."
        if tx.type in {
            "DRONE_DISPATCH",
            "MISSION_COMPLETE",
            "MISSION_REPORT_PROOF",
        }:
            mission_id = tx.payload.get("mission_id")
            if not mission_id:
                return False, "mission_id é obrigatório."
            related = self._mission_transactions(
                mission_id, include_mempool, prior
            )
            payments = [item for item in related if item.type == "ESCORT_PAYMENT"]
            if not payments:
                return False, "A missão não possui pagamento de escolta confirmado ou pendente."
            if payments[0].sender != tx.sender:
                return False, "A operação não foi assinada pela companhia dona da missão."
            if tx.type == "DRONE_DISPATCH":
                if tx.payload.get("payment_tx_id") != payments[0].id:
                    return False, "Despacho não corresponde ao pagamento informado."
            if tx.type == "MISSION_REPORT_PROOF" and not any(
                item.type == "MISSION_COMPLETE" for item in related
            ):
                return False, "A prova exige uma conclusão de missão associada."
        return True, ""

    def add_transaction(self, tx: Transaction) -> tuple[bool, str]:
        with self.lock:
            valid, message = self.validate_transaction(tx)
            if not valid:
                return False, message
            self.mempool.append(tx)
            self._save()
            return True, "Transação aceita no mempool."

    def create_signed_transaction(
        self,
        company_id: str,
        tx_type: str,
        recipient: str,
        amount: int,
        payload: dict[str, Any],
    ) -> Transaction:
        wallet = self.wallets[company_id]
        tx = Transaction(
            id=str(uuid.uuid4()),
            type=tx_type,
            sender=wallet["wallet_address"],
            recipient=recipient,
            amount=amount,
            timestamp=now_iso(),
            payload=payload,
            public_key=wallet["public_key"],
        )
        tx.signature = sign(wallet["private_key"], transaction_signing_body(tx))
        return tx

    def _proof_of_work(self, candidate: Block) -> Block:
        prefix = "0" * self.difficulty
        while True:
            candidate.hash = block_hash(candidate)
            if candidate.hash.startswith(prefix):
                return candidate
            candidate.nonce += 1

    def mine(self) -> Block:
        with self.lock:
            if not self.mempool:
                raise ValueError("Não há transações pendentes.")
            valid_transactions: list[Transaction] = []
            for tx in list(self.mempool):
                valid, _ = self.validate_transaction(
                    tx, include_mempool=False, prior_in_block=valid_transactions
                )
                if valid:
                    valid_transactions.append(tx)
            if not valid_transactions:
                self.mempool.clear()
                self._save()
                raise ValueError("Nenhuma transação pendente continua válida.")
            candidate = Block(
                index=len(self.chain),
                timestamp=now_iso(),
                previous_hash=self.chain[-1].hash,
                hash="",
                nonce=0,
                transactions=valid_transactions,
                node_id=self.node_id,
            )
            block = self._proof_of_work(candidate)
            self.chain.append(block)
            accepted = {tx.id for tx in valid_transactions}
            self.mempool = [tx for tx in self.mempool if tx.id not in accepted]
            self._save()
            return block

    def validate_chain(
        self, chain: list[Block] | None = None
    ) -> tuple[bool, dict[str, Any] | None]:
        target = chain or self.chain
        if not target:
            return False, {"error": "Cadeia vazia.", "block_index": None}
        expected_genesis = self._genesis_block()
        if target[0].model_dump() != expected_genesis.model_dump():
            return False, {"error": "Bloco gênese divergente.", "block_index": 0}
        known_ids: set[str] = {tx.id for tx in target[0].transactions}
        balances = {
            wallet["wallet_address"]: 100 for wallet in self.wallets.values()
        }
        active: dict[str, str] = {}
        mission_owners: dict[str, str] = {}
        completed_missions: set[str] = set()
        for index, block in enumerate(target):
            expected_hash = block_hash(block)
            if block.hash != expected_hash:
                return False, {
                    "error": "Hash do bloco não corresponde ao conteúdo.",
                    "block_index": index,
                    "expected_hash": expected_hash,
                    "found_hash": block.hash,
                }
            if not block.hash.startswith("0" * self.difficulty):
                return False, {"error": "Proof of Work inválido.", "block_index": index}
            if index and block.previous_hash != target[index - 1].hash:
                return False, {
                    "error": "Encadeamento previous_hash inválido.",
                    "block_index": index,
                }
            if index == 0:
                continue
            for tx in block.transactions:
                if tx.id in known_ids:
                    return False, {
                        "error": "Transação duplicada na cadeia.",
                        "block_index": index,
                    }
                known_ids.add(tx.id)
                valid, error = self._validate_signature(tx)
                if not valid:
                    return False, {"error": error, "block_index": index}
                if tx.type in {"TRANSFER_CREDIT", "ESCORT_PAYMENT"}:
                    if balances.get(tx.sender, 0) < tx.amount:
                        return False, {
                            "error": "Duplo gasto ou saldo negativo na cadeia.",
                            "block_index": index,
                        }
                    balances[tx.sender] = balances.get(tx.sender, 0) - tx.amount
                    balances[tx.recipient] = balances.get(tx.recipient, 0) + tx.amount
                if tx.type == "ESCORT_PAYMENT":
                    drone_id = tx.payload["drone_id"]
                    mission_id = tx.payload["mission_id"]
                    if drone_id in active:
                        return False, {
                            "error": "Drone alocado duas vezes.",
                            "block_index": index,
                        }
                    if mission_id in mission_owners:
                        return False, {
                            "error": "Identificador de missão duplicado.",
                            "block_index": index,
                        }
                    active[drone_id] = mission_id
                    mission_owners[mission_id] = tx.sender
                if tx.type in {
                    "DRONE_DISPATCH",
                    "MISSION_COMPLETE",
                    "MISSION_REPORT_PROOF",
                }:
                    mission_id = tx.payload.get("mission_id")
                    if mission_id not in mission_owners:
                        return False, {
                            "error": "Operação sem pagamento de missão associado.",
                            "block_index": index,
                        }
                    if mission_owners[mission_id] != tx.sender:
                        return False, {
                            "error": "Operação assinada por carteira que não é dona da missão.",
                            "block_index": index,
                        }
                    if tx.type == "DRONE_DISPATCH":
                        payment_id = tx.payload.get("payment_tx_id")
                        if payment_id not in known_ids:
                            return False, {
                                "error": "Despacho referencia pagamento inexistente.",
                                "block_index": index,
                            }
                if tx.type == "MISSION_COMPLETE":
                    completed_missions.add(tx.payload["mission_id"])
                    for drone_id, mission_id in list(active.items()):
                        if mission_id == tx.payload["mission_id"]:
                            active.pop(drone_id)
                if (
                    tx.type == "MISSION_REPORT_PROOF"
                    and tx.payload["mission_id"] not in completed_missions
                ):
                    return False, {
                        "error": "Prova registrada antes da conclusão da missão.",
                        "block_index": index,
                    }
        return True, None

    def add_block(self, block: Block) -> tuple[bool, str]:
        with self.lock:
            if block.index != len(self.chain):
                return False, "Altura de bloco inesperada; sincronização necessária."
            candidate = self.chain + [block]
            valid, error = self.validate_chain(candidate)
            if not valid:
                return False, error["error"] if error else "Bloco inválido."
            self.chain.append(block)
            confirmed_ids = {tx.id for tx in block.transactions}
            self.mempool = [tx for tx in self.mempool if tx.id not in confirmed_ids]
            self._save()
            return True, "Bloco aceito."

    def replace_chain(self, chain: list[Block]) -> bool:
        with self.lock:
            valid, _ = self.validate_chain(chain)
            local_valid, _ = self.validate_chain(self.chain)
            candidate_score = (len(chain), -int(chain[-1].hash, 16))
            local_score = (len(self.chain), -int(self.chain[-1].hash, 16))
            if not valid or (local_valid and candidate_score <= local_score):
                return False
            self.chain = copy.deepcopy(chain)
            confirmed = self.transaction_ids(include_pending=False)
            self.mempool = [tx for tx in self.mempool if tx.id not in confirmed]
            self._save()
            return True
