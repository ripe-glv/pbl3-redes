from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


TransactionType = Literal[
    "GENESIS_CREDIT",
    "TRANSFER_CREDIT",
    "ESCORT_PAYMENT",
    "DRONE_DISPATCH",
    "MISSION_REPORT_PROOF",
    "MISSION_COMPLETE",
]


class Transaction(BaseModel):
    id: str
    type: TransactionType
    sender: str
    recipient: str
    amount: int = Field(ge=0)
    timestamp: str
    payload: dict[str, Any] = Field(default_factory=dict)
    signature: str = ""
    public_key: str = ""


class Block(BaseModel):
    index: int
    timestamp: str
    previous_hash: str
    hash: str
    nonce: int
    transactions: list[Transaction]
    node_id: str


class PeerRequest(BaseModel):
    url: str


class CreditTransferRequest(BaseModel):
    sender_company_id: str
    recipient_company_id: str
    amount: int = Field(gt=0)


class EscortRequest(BaseModel):
    company_id: str
    drone_id: str
    route_id: str
    cost: int = Field(default=25, gt=0)


class MissionCompleteRequest(BaseModel):
    company_id: str
    result: str
    description: str
    evidence: list[str] = Field(default_factory=list)
    strategic_notes: str = ""
    risk_classification: str


class LoginRequest(BaseModel):
    company_id: str
    password: str


class SignRequest(BaseModel):
    message: dict[str, Any]


class TamperRequest(BaseModel):
    target: Literal["chain", "storage"] = "chain"
    mission_id: str | None = None
