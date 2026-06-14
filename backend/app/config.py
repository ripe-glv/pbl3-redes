from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    node_id: str
    host: str
    port: int
    peers: tuple[str, ...]
    ledger_file: Path
    storage_dir: Path
    difficulty: int
    auto_mine: bool


def get_settings() -> Settings:
    node_id = os.getenv("NODE_ID", "node-a")
    return Settings(
        node_id=node_id,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8001")),
        peers=tuple(filter(None, os.getenv("PEERS", "").split(","))),
        ledger_file=Path(os.getenv("LEDGER_FILE", f"data/ledger-{node_id}.json")),
        storage_dir=Path(os.getenv("STORAGE_DIR", f"storage/{node_id}")),
        difficulty=int(os.getenv("POW_DIFFICULTY", "3")),
        auto_mine=os.getenv("AUTO_MINE", "true").lower() == "true",
    )

