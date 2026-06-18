from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .crypto import decrypt_for_wallet, encrypt_for_wallet, sha256_hex


class MissionStorage:
    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, mission_id: str) -> Path:
        safe_id = "".join(ch for ch in mission_id if ch.isalnum() or ch in "-_")
        if not safe_id or safe_id != mission_id:
            raise ValueError("Identificador de missão inválido.")
        return self.directory / f"{safe_id}.enc.json"

    def save(
        self, mission_id: str, report: dict[str, Any], encryption_public_key: str
    ) -> dict[str, str]:
        encrypted = encrypt_for_wallet(report, encryption_public_key)
        content = encrypted["encrypted_file"]
        path = self._path(mission_id)
        path.write_text(content, encoding="utf-8")
        return {
            "storage_pointer": mission_id,
            "report_hash": encrypted["report_hash"],
            "encrypted_file_hash": sha256_hex(content.encode()),
            "encrypted_access_key": encrypted["encrypted_access_key"],
            "encrypted_file": content,
        }

    def save_replica(self, mission_id: str, encrypted_file: str) -> None:
        json.loads(encrypted_file)
        self._path(mission_id).write_text(encrypted_file, encoding="utf-8")

    def read_encrypted(self, mission_id: str) -> str:
        path = self._path(mission_id)
        if not path.exists():
            raise FileNotFoundError("Arquivo off-chain não encontrado neste nó.")
        return path.read_text(encoding="utf-8")

    def decrypt(self, mission_id: str, encryption_private_key: str) -> dict[str, Any]:
        return decrypt_for_wallet(
            self.read_encrypted(mission_id), encryption_private_key
        )

    def verify(self, mission_id: str, registered_hash: str) -> dict[str, Any]:
        # Verification is public: comparing ciphertext hashes does not require
        # decrypting or exposing the confidential report.
        try:
            content = self.read_encrypted(mission_id)
        except FileNotFoundError as exc:
            return {
                "valid": False,
                "current_hash": None,
                "registered_hash": registered_hash,
                "message": str(exc),
            }
        current = sha256_hex(content.encode())
        valid = current == registered_hash
        return {
            "valid": valid,
            "current_hash": current,
            "registered_hash": registered_hash,
            "message": (
                "Arquivo off-chain íntegro."
                if valid
                else "Arquivo off-chain adulterado: o hash não corresponde."
            ),
        }

    def tamper(self, mission_id: str) -> None:
        path = self._path(mission_id)
        if not path.exists():
            raise FileNotFoundError("Arquivo off-chain não encontrado.")
        path.write_text(path.read_text(encoding="utf-8") + "\nTAMPERED", encoding="utf-8")
