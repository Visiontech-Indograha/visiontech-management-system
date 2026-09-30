"""Lampiran draf SK (V-29) — `domain.js` SAVE_ATTACHMENTS. Dibekukan di snapshot dokumen saat terbit."""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PlanAccess, PlanNeed, ensure_same_org, get_db_with_user, plan_access
from app.services.plan_attachment_service import PlanAttachmentService

router = APIRouter(prefix="/work-plans/{plan_id}/attachments", tags=["Work Plans"])
_VIEW_ACCESS = Depends(plan_access(PlanNeed.VIEW))
_PM_UNIT_ACCESS = Depends(plan_access(PlanNeed.PM_UNIT))    # domain.js SAVE_ATTACHMENTS: PM (unitnya), OPS


class AttachmentsRequest(BaseModel):
    file_ids: list[UUID]


class AttachmentResponse(BaseModel):
    file_id: str
    file_name: str
    mime_type: str
    byte_size: int
    sort_order: int


def _out(rows: list[Any]) -> list[AttachmentResponse]:
    return [AttachmentResponse(**row._mapping) for row in rows]


@router.get("", response_model=list[AttachmentResponse])
async def list_attachments(access: PlanAccess = _VIEW_ACCESS,
                           db: AsyncSession = Depends(get_db_with_user)) -> list[AttachmentResponse]:
    return _out(await PlanAttachmentService(db).list_attachments(access))


@router.put("", response_model=list[AttachmentResponse])
async def save_attachments(data: AttachmentsRequest, access: PlanAccess = _PM_UNIT_ACCESS,
                           db: AsyncSession = Depends(get_db_with_user)) -> list[AttachmentResponse]:
    await ensure_same_org(db, access.user.organization_id, files=data.file_ids)
    return _out(await PlanAttachmentService(db).save_attachments(access, data.file_ids))
