"""
Paket skema untuk modul work_types.
"""
from app.modules.work_types.schemas.work_type_schema import (
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

