"""Skema permintaan & respons: plan transition (dipindah dari api/v1/endpoints/work_plan_transitions.py, R-28 M2b)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class FinalReportOut(BaseModel):
    status: str  # SUBMITTED | CHANGES_REQUESTED | APPROVED
    body: str
    obstacle: str | None
    evidence_file_ids: list[str]
    submitted_at: datetime | None
    submitted_by_name: str | None
    review_note: str | None
    reviewed_at: datetime | None
    reviewed_by_name: str | None


class FinalReportSignatureOut(BaseModel):
    id: str
    serial_number: str
    signer_name: str
    signer_position: str | None
    signer_unit: str | None
    signer_role: str
    signed_at: datetime
    signature_alg: str
    kid: str
    document_sha256_hex: str
    revoked_at: datetime | None
    revoked_reason: str | None


class TransitionRequest(BaseModel):
    row_version: int
    reason: str = ""


class CompletionRequest(BaseModel):
    row_version: int
    body: str
    obstacle: str
    evidence_file_ids: list[UUID] = []
