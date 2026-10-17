"""
app/modules/signatures/routes/plan_document_route.py

Rute endpoint HTTP untuk dokumen rencana kerja (/work-plans/{plan_id}/documents).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from fastapi import APIRouter, Depends

from app.api.deps import plan_access
from app.modules.signatures.controllers.signature_controller import SignatureController
from app.modules.signatures.schemas.signature_schema import PlanDocumentOut
from app.services.access_service import PlanAccess, PlanNeed

router = APIRouter(prefix="/work-plans/{plan_id}/documents", tags=["Documents & Signatures"])
_VIEW_ACCESS = Depends(plan_access(PlanNeed.VIEW))


@router.get("", response_model=list[PlanDocumentOut])
async def list_plan_documents(
    access: PlanAccess = _VIEW_ACCESS,
    controller: SignatureController = Depends(),
) -> list[PlanDocumentOut]:
    """Dokumen SK, revisi, dan adendum beserta jumlah tanda tangan yang berlaku."""
    return await controller.handle_list_plan_documents(access.plan.id)
