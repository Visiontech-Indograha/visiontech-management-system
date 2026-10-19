"""
app/modules/work_completion/crud/crud_work_completion.py

Shim re-export untuk kompatibilitas. Implementasi riil berada di
app.modules.work_completion.repositories.work_completion_repository.
"""

from app.modules.work_completion.repositories.work_completion_repository import (
    CRUDWorkCompletion,
    WorkCompletionRepository,
    _row_to_dict,
)

__all__ = ["CRUDWorkCompletion", "WorkCompletionRepository", "_row_to_dict"]
