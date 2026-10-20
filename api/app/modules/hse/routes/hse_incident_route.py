"""
app/modules/hse/routes/hse_incident_route.py

Rute endpoint HTTP untuk insiden K3 (HSE) (/hse).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, incident_plan_access
from app.core.security import CurrentUser
from app.modules.hse.controllers.hse_controller import HseController
from app.modules.hse.schemas.hse_schema import (
    IncidentCreate,
    IncidentResolve,
    IncidentResponse,
)
from app.shared.access.access_service import PlanAccess, PlanNeed

router = APIRouter(prefix="/hse", tags=["HSE & Reports"])
_INCIDENT_VIEW_ACCESS = Depends(incident_plan_access(PlanNeed.VIEW))


@router.get("/incidents", response_model=list[IncidentResponse])
async def list_incidents(
    plan_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: HseController = Depends(),
) -> list[IncidentResponse]:
    """Mendapatkan daftar insiden untuk satu Surat Kerja (SK)."""
    return await controller.handle_list_incidents(current_user, plan_id)


@router.post("/incidents", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def report_incident(
    data: IncidentCreate,
    current_user: CurrentUser = Depends(get_current_user),
    controller: HseController = Depends(),
) -> IncidentResponse:
    """Melaporkan insiden baru untuk SK yang sedang berlangsung."""
    return await controller.handle_report_incident(current_user, data)


@router.post("/incidents/{inc_id}/resolve", response_model=IncidentResponse)
async def resolve_incident(
    inc_id: UUID,
    data: IncidentResolve,
    access: PlanAccess = _INCIDENT_VIEW_ACCESS,
    controller: HseController = Depends(),
) -> IncidentResponse:
    """Menyelesaikan masalah insiden K3."""
    return await controller.handle_resolve_incident(access, inc_id, data)
