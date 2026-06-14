from __future__ import annotations

from .crypto import (
    ed_private_from_seed,
    private_bytes,
    public_bytes,
    wallet_address,
    x_private_from_seed,
)


COMPANY_SPECS = (
    ("gulf", "Gulf Shipping Co."),
    ("atlas", "Atlas Maritime"),
    ("orion", "Orion Logistics"),
)

DRONES = ("DRONE-01", "DRONE-02", "DRONE-03")
ROUTES = {
    "ROTA-ALFA": "Canal norte, corredor de navegação comercial",
    "ROTA-BRAVO": "Canal central, área de maior tráfego",
    "ROTA-CHARLIE": "Canal sul, rota alternativa de contingência",
}


def build_wallets() -> dict[str, dict[str, str]]:
    wallets = {}
    for company_id, name in COMPANY_SPECS:
        signing = ed_private_from_seed(f"tec502:{company_id}:sign")
        encryption = x_private_from_seed(f"tec502:{company_id}:encrypt")
        public_key = public_bytes(signing.public_key())
        wallets[company_id] = {
            "company_id": company_id,
            "name": name,
            "public_key": public_key,
            "private_key": private_bytes(signing),
            "encryption_public_key": public_bytes(encryption.public_key()),
            "encryption_private_key": private_bytes(encryption),
            "wallet_address": wallet_address(public_key),
        }
    return wallets

