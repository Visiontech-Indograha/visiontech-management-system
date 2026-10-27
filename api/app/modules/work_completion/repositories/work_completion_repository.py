"""
app/modules/work_completion/repositories/work_completion_repository.py
Akses data database untuk entitas Work Completion (Order Klien) Master V3.
Menggabungkan modul-modul repository: Core, Revision/ACC, BoM, dan Signature.
"""
from __future__ import annotations

from app.modules.work_completion.repositories.work_completion_bom_repository import WorkCompletionBomRepository
from app.modules.work_completion.repositories.work_completion_core_repository import (
    FIELD_SCOPE,
    WorkCompletionCoreRepository,
    _row_to_dict,
)
from app.modules.work_completion.repositories.work_completion_revision_repository import (
    WorkCompletionRevisionRepository,
)
from app.modules.work_completion.repositories.work_completion_sign_repository import (
    WorkCompletionSignRepository,
)


class WorkCompletionRepository(
    WorkCompletionCoreRepository,
    WorkCompletionRevisionRepository,
    WorkCompletionBomRepository,
    WorkCompletionSignRepository,
):
    """Repository gabungan entitas Work Completion."""


# Alias backward compatibility
CRUDWorkCompletion = WorkCompletionRepository

__all__ = [
    "FIELD_SCOPE",
    "CRUDWorkCompletion",
    "WorkCompletionBomRepository",
    "WorkCompletionCoreRepository",
    "WorkCompletionRepository",
    "WorkCompletionRevisionRepository",
    "WorkCompletionSignRepository",
    "_row_to_dict",
]
