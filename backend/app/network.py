from __future__ import annotations

import asyncio
from typing import Any

import httpx

from .ledger import Ledger
from .models import Block, Transaction


class PeerNetwork:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger

    async def _post(self, peer: str, path: str, payload: dict[str, Any]) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.post(f"{peer.rstrip('/')}{path}", json=payload)
                return response.is_success
        except httpx.HTTPError:
            return False

    async def propagate_transaction(self, tx: Transaction) -> dict[str, bool]:
        # Each peer validates the transaction independently on receipt.
        peers = sorted(self.ledger.peers)
        results = await asyncio.gather(
            *(self._post(peer, "/receive-transaction", tx.model_dump()) for peer in peers)
        )
        return dict(zip(peers, results))

    async def propagate_block(self, block: Block) -> dict[str, bool]:
        peers = sorted(self.ledger.peers)
        results = await asyncio.gather(
            *(self._post(peer, "/receive-block", block.model_dump()) for peer in peers)
        )
        return dict(zip(peers, results))

    async def replicate_file(self, mission_id: str, encrypted_file: str) -> dict[str, bool]:
        peers = sorted(self.ledger.peers)
        payload = {"mission_id": mission_id, "encrypted_file": encrypted_file}
        results = await asyncio.gather(
            *(self._post(peer, "/storage/replica", payload) for peer in peers)
        )
        return dict(zip(peers, results))

    async def peer_statuses(self) -> list[dict[str, Any]]:
        async def fetch(peer: str) -> dict[str, Any]:
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    response = await client.get(f"{peer.rstrip('/')}/node/status")
                    response.raise_for_status()
                    return {"url": peer, "online": True, **response.json()}
            except httpx.HTTPError:
                return {"url": peer, "online": False}

        return await asyncio.gather(*(fetch(peer) for peer in sorted(self.ledger.peers)))

    async def resolve_conflicts(self) -> dict[str, Any]:
        # No master node decides the winner: the local node fetches candidate
        # chains and applies the ledger's deterministic best-valid-chain rule.
        candidates: list[tuple[str, list[Block]]] = []
        for peer in sorted(self.ledger.peers):
            try:
                async with httpx.AsyncClient(timeout=4.0) as client:
                    response = await client.get(f"{peer.rstrip('/')}/ledger")
                    response.raise_for_status()
                    chain = [
                        Block.model_validate(block) for block in response.json()["chain"]
                    ]
                    candidates.append((peer, chain))
            except (httpx.HTTPError, ValueError):
                continue
        replaced = False
        source = None
        for peer, chain in sorted(
            candidates, key=lambda item: (len(item[1]), item[1][-1].hash), reverse=True
        ):
            if self.ledger.replace_chain(chain):
                replaced = True
                source = peer
                break
        return {
            "replaced": replaced,
            "source": source,
            "height": len(self.ledger.chain) - 1,
        }
