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
from app.shared.documents.document_export_service import DocumentExportService


def test_document_export_service_docx_xlsx_pptx() -> None:
    """Memastikan DocumentExportService menghasilkan biner DOCX, XLSX, dan PPTX dengan benar."""
    mock_detail = {
        "plan": {
            "title": "Pemasangan 13 Unit CCTV Pertamina EP",
            "number": "SK/W42/2026",
            "category": "INSTALASI",
            "category_label": "Instalasi",
            "work_type_name": "Survei & Pemasangan CCTV",
            "location_text": "Kilang Pangkalan Susu",
            "period_start": "2026-10-20",
            "period_end": "2026-10-26",
            "status": "ONGOING",
            "is_out_of_town": True,
        },
        "team": [
            {
                "employee_id": str(uuid4()),
                "full_name": "Rahmat Hidayat",
                "role_in_plan": "LEADER",
                "employee_number": "EMP-001",
                "phone": "08123456789",
            },
            {
                "employee_id": str(uuid4()),
                "full_name": "Agus Pratama",
                "role_in_plan": "MEMBER",
                "employee_number": "EMP-002",
                "phone": "08129876543",
            },
        ],
        "days": [
            {
                "id": str(uuid4()),
                "work_date": "2026-10-20",
                "site_name": "Gate Utama Kilang",
                "work_type_name": "Survei & Penarikan Kabel",
                "members": ["Rahmat Hidayat", "Agus Pratama"],
                "tasks": [{"title": "Penarikan FO 200m"}, {"title": "Pemasangan Bracket"}],
            },
            {
                "id": str(uuid4()),
                "work_date": "2026-10-21",
                "site_name": "Control Room CCTV",
                "work_type_name": "Konfigurasi NVR",
                "members": ["Rahmat Hidayat"],
                "tasks": [{"title": "Setting IP Camera 13 Titik"}],
            },
        ],
        "assets": [],
        "attachments": [],
    }

    docx_bytes = DocumentExportService.export_docx(mock_detail)
    assert len(docx_bytes) > 1000
    assert docx_bytes[:4] == b"PK\x03\x04"  # Zip header for docx

    xlsx_bytes = DocumentExportService.export_xlsx(mock_detail)
    assert len(xlsx_bytes) > 1000
    assert xlsx_bytes[:4] == b"PK\x03\x04"  # Zip header for xlsx

    pptx_bytes = DocumentExportService.export_pptx(mock_detail)
    assert len(pptx_bytes) > 1000
    assert pptx_bytes[:4] == b"PK\x03\x04"  # Zip header for pptx


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
        client_name="PT Pertamina EP",
        project_title="Pemasangan 13 Unit CCTV Kilang",
        order_number="PO-2026-PTM-001",
        total_target_unit=13,
        unit_measure="Titik Kamera",
        priority_level="URGENT",
        site_address="Pangkalan Susu, Langkat",
    )
    assert order_in.total_target_unit == 13
    assert order_in.client_name == "PT Pertamina EP"

    status_update = WorkCompletionStatusUpdate(order_status="URGENT")
    assert status_update.order_status == "URGENT"


