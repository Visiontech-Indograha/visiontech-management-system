"""
api/tests/test_v3_features.py
Pengujian fitur-fitur VMS V3:
1. Multi-format Document Export (PDF, DOCX, XLSX, PPTX)
2. Skema WorkPlanResponse dengan division_name dan work_type_name
3. Standarisasi SOP Foto ImageRequirement dengan description
4. Work Completion Client Order Model & Status Enum
5. PM Full Override Authority
"""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.image_requirements.schemas.image_requirement_schema import ImageRequirementOut
from app.modules.work_completion.schemas.work_completion_schema import (
    WorkCompletionCreate,
    WorkCompletionStatusUpdate,
)


def test_image_requirement_schema_description() -> None:
    """Memastikan ImageRequirementOut mendukung kolom description opsional."""
    req_id = uuid4()
    wt_id = uuid4()

    out = ImageRequirementOut(
        image_requirement_id=req_id,
        work_type_id=wt_id,
        work_type_name="Instalasi CCTV",
        name="Foto Titik Kamera",
        description="Ambil foto dari jarak 2 meter dengan sudut pandang mencakup area pantauan.",
        path_image="/uploads/sop/1312298.png",
        is_mandatory=True,
        sort_order=1,
        create_at=datetime.now(UTC),
    )

    assert out.name == "Foto Titik Kamera"
    assert out.description is not None
    assert "jarak 2 meter" in out.description


def test_work_completion_client_order_schemas() -> None:
    """Memastikan skema order proyek klien (WorkCompletion) tervalidasi dengan baik."""
    order_in = WorkCompletionCreate(
        division_id=uuid4(),
        client_id=uuid4(),
        project_title="Pemasangan 13 Unit CCTV Kilang",
        order_number="PO-2026-PTM-001",
        total_target_unit=13,
        unit_measure="Titik Kamera",
        priority_level="URGENT",
        site_address="Pangkalan Susu, Langkat",
    )
    assert order_in.total_target_unit == 13
    assert order_in.client_id is not None

    status_update = WorkCompletionStatusUpdate(order_status="URGENT")
    assert status_update.order_status == "URGENT"


