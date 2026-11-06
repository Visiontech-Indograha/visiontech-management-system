"""reopen_items_for_rework hanya membuka item DONE/IN_PROGRESS; item lain tak disentuh; rowcount dikembalikan."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from app.modules.work_completion.repositories.work_completion_revision_repository import (
    WorkCompletionRevisionRepository,
)


class _Db:
    def __init__(self, rowcount: Any) -> None:
        self.rowcount = rowcount
        self.sql = ""
        self.params: dict[str, Any] = {}

    async def execute(self, query: Any, params: dict[str, Any]) -> Any:
        self.sql, self.params = str(query), params
        return SimpleNamespace(rowcount=self.rowcount)


@pytest.mark.parametrize("rowcount,expected", [(3, 3), (0, 0), (None, 0)])
def test_reopen_guards_status_and_returns_rowcount(rowcount, expected):
    db = _Db(rowcount)
    repo = WorkCompletionRevisionRepository(db)  # type: ignore[arg-type]
    result = asyncio.run(repo.reopen_items_for_rework("11111111-1111-4111-8111-111111111111"))
    assert result == expected
    assert "status IN ('DONE', 'IN_PROGRESS')" in db.sql
    assert "is_main_deliverable = TRUE" in db.sql and "delete_at IS NULL" in db.sql
    assert db.params == {"id": "11111111-1111-4111-8111-111111111111"}
