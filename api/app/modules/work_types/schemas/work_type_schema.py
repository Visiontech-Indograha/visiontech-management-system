"""
app/modules/work_types/schemas/work_type_schema.py

Skema data untuk jenis pekerjaan dan template foto bukti.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.5.
"""

from app.schemas.work_type import (
    EvidenceIn,
    EvidenceOut,
    EvidenceSource,
    WorkTypeIn,
    WorkTypeOut,
    WorkTypePhotoIn,
    WorkTypePhotoOut,
    merge_evidence,
)

__all__ = [
    "EvidenceIn",
    "EvidenceOut",
    "EvidenceSource",
    "WorkTypeIn",
    "WorkTypeOut",
    "WorkTypePhotoIn",
    "WorkTypePhotoOut",
    "merge_evidence",
]
