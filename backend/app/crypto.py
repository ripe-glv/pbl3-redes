from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def b64(value: bytes) -> str:
    return base64.b64encode(value).decode()


def unb64(value: str) -> bytes:
    return base64.b64decode(value.encode())


def ed_private_from_seed(seed: str) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(hashlib.sha256(seed.encode()).digest())


def x_private_from_seed(seed: str) -> X25519PrivateKey:
    raw = bytearray(hashlib.sha256(f"x25519:{seed}".encode()).digest())
    raw[0] &= 248
    raw[31] &= 127
    raw[31] |= 64
    return X25519PrivateKey.from_private_bytes(bytes(raw))


def private_bytes(key: Ed25519PrivateKey | X25519PrivateKey) -> str:
    return b64(
        key.private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption(),
        )
    )


def public_bytes(key: Ed25519PublicKey | X25519PublicKey) -> str:
    return b64(
        key.public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
    )


def wallet_address(public_key_b64: str) -> str:
    return "oc_" + sha256_hex(unb64(public_key_b64))[:40]


def sign(private_key_b64: str, message: Any) -> str:
    key = Ed25519PrivateKey.from_private_bytes(unb64(private_key_b64))
    return b64(key.sign(canonical_json(message)))


def verify(public_key_b64: str, signature_b64: str, message: Any) -> bool:
    try:
        key = Ed25519PublicKey.from_public_bytes(unb64(public_key_b64))
        key.verify(unb64(signature_b64), canonical_json(message))
        return True
    except (ValueError, TypeError):
        return False


def _derive_wrap_key(shared_secret: bytes) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"tec502-mission-report",
    ).derive(shared_secret)


def encrypt_for_wallet(report: dict[str, Any], recipient_public_key: str) -> dict[str, str]:
    plaintext = canonical_json(report)
    data_key = AESGCM.generate_key(bit_length=256)
    data_nonce = __import__("os").urandom(12)
    ciphertext = AESGCM(data_key).encrypt(data_nonce, plaintext, None)

    ephemeral = X25519PrivateKey.generate()
    recipient = X25519PublicKey.from_public_bytes(unb64(recipient_public_key))
    wrap_key = _derive_wrap_key(ephemeral.exchange(recipient))
    key_nonce = __import__("os").urandom(12)
    wrapped_key = AESGCM(wrap_key).encrypt(key_nonce, data_key, None)
    envelope = {
        "algorithm": "X25519+AES-256-GCM",
        "ephemeral_public_key": public_bytes(ephemeral.public_key()),
        "key_nonce": b64(key_nonce),
        "encrypted_access_key": b64(wrapped_key),
        "data_nonce": b64(data_nonce),
        "ciphertext": b64(ciphertext),
    }
    return {
        "report_hash": sha256_hex(plaintext),
        "encrypted_file": json.dumps(
            envelope, sort_keys=True, separators=(",", ":")
        ),
        "encrypted_access_key": envelope["encrypted_access_key"],
    }


def decrypt_for_wallet(encrypted_file: str, recipient_private_key: str) -> dict[str, Any]:
    envelope = json.loads(encrypted_file)
    private = X25519PrivateKey.from_private_bytes(unb64(recipient_private_key))
    ephemeral = X25519PublicKey.from_public_bytes(
        unb64(envelope["ephemeral_public_key"])
    )
    wrap_key = _derive_wrap_key(private.exchange(ephemeral))
    data_key = AESGCM(wrap_key).decrypt(
        unb64(envelope["key_nonce"]),
        unb64(envelope["encrypted_access_key"]),
        None,
    )
    plaintext = AESGCM(data_key).decrypt(
        unb64(envelope["data_nonce"]), unb64(envelope["ciphertext"]), None
    )
    return json.loads(plaintext)

