"""Skema permintaan & respons: sync (dipindah dari api/v1/endpoints/sync.py, R-28 M2b)."""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class OfflineOperation(BaseModel):
    client_op_id: UUID
    op_type: str
    payload: dict[str, Any]
    client_created_at: datetime


class SyncRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=200)
    operations: list[OfflineOperation] = Field(max_length=200)


class OperationResult(BaseModel):
    client_op_id: str
    status: str               # APPLIED | REJECTED | CONFLICT | PENDING
    error_message: str | None


class SyncResponse(BaseModel):
    results: list[OperationResult]


class OperationStatus(BaseModel):
    client_op_id: str
    op_type: str
    status: str
    error_message: str | None
    client_created_at: datetime
    received_at: datetime
    applied_at: datetime | None
