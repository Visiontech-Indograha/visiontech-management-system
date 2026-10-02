"""Skema permintaan & respons: signature (dipindah dari api/v1/endpoints/signatures.py, R-28 M2b)."""
from datetime import datetime

from pydantic import BaseModel


class PlanDocumentOut(BaseModel):
    id: str
    kind: str
    version: int
    number: str
    status: str
    reason: str | None
    issued_at: datetime
    accepted_at: datetime | None
    sha256: str
    signature_count: int


class SignatureOut(BaseModel):
    id: str
    serial_number: str
    signer_name: str
    signer_position: str
    signer_unit: str | None
    signer_role: str
    signed_at: datetime
    signature_alg: str
    kid: str
    document_sha256_hex: str
    revoked_at: datetime | None
    revoked_reason: str | None


class RevokeRequest(BaseModel):
    reason: str


class VerifyOut(BaseModel):
    state: str
    serial_number: str | None
    signer_name: str | None
    signer_position: str | None
    signer_unit: str | None
    signer_role: str | None
    document_number: str | None
    document_title: str | None
    signed_at: datetime | None
    key_id: str | None
    algorithm: str | None
    document_sha256_hex: str | None
    note: str | None
