from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass

from fastapi import Header, HTTPException


DEMO_PASSWORDS = {
    "gulf": "Gulf@2026",
    "atlas": "Atlas@2026",
    "orion": "Orion@2026",
}


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


@dataclass(frozen=True)
class AuthSession:
    company_id: str
    expires_at: int


class AuthManager:
    def __init__(self) -> None:
        self.secret = os.getenv(
            "AUTH_SECRET", "tec502-sentinel-ledger-demo-secret"
        ).encode()
        self.duration_seconds = int(os.getenv("AUTH_SESSION_SECONDS", "28800"))

    def authenticate(self, company_id: str, password: str) -> bool:
        expected = DEMO_PASSWORDS.get(company_id)
        return expected is not None and hmac.compare_digest(expected, password)

    def issue(self, company_id: str) -> tuple[str, int]:
        expires_at = int(time.time()) + self.duration_seconds
        payload = _b64url_encode(
            json.dumps(
                {"company_id": company_id, "exp": expires_at},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        )
        signature = _b64url_encode(
            hmac.new(self.secret, payload.encode(), hashlib.sha256).digest()
        )
        return f"{payload}.{signature}", expires_at

    def verify(self, token: str) -> AuthSession:
        try:
            payload, signature = token.split(".", 1)
            expected = _b64url_encode(
                hmac.new(self.secret, payload.encode(), hashlib.sha256).digest()
            )
            if not hmac.compare_digest(expected, signature):
                raise ValueError("invalid signature")
            data = json.loads(_b64url_decode(payload))
            company_id = str(data["company_id"])
            expires_at = int(data["exp"])
            if expires_at <= int(time.time()):
                raise ValueError("expired")
            if company_id not in DEMO_PASSWORDS:
                raise ValueError("unknown company")
            return AuthSession(company_id=company_id, expires_at=expires_at)
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=401, detail="Sessão inválida ou expirada."
            ) from exc


auth = AuthManager()


def require_session(authorization: str | None = Header(default=None)) -> AuthSession:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Login obrigatório.")
    return auth.verify(authorization.removeprefix("Bearer ").strip())

