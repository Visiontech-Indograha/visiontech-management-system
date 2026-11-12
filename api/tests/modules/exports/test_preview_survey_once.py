"""Pratinjau survei: dokumen survei (unduh + kecilkan foto) dibangun sekali dan PDF dibangun tepat sekali."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.modules.exports.services import export_service as es


@pytest.mark.asyncio
async def test_preview_survey_builds_doc_and_pdf_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"doc": 0, "docx": 0, "pdf": 0}

    class Surveys:
        async def detail(self, user: Any, task_id: Any) -> dict[str, Any]:
            return {"points": [{"name": "t1"}], "state": "SUBMITTED"}

    async def fake_doc(self: Any, s: Any, user: Any) -> object:
        calls["doc"] += 1
        return object()

    def fake_docx(data: Any) -> bytes:
        calls["docx"] += 1
        return b"docx"

    monkeypatch.setattr(es.ExportService, "_survey_doc", fake_doc)
    monkeypatch.setattr(es, "build_survey_docx", fake_docx)

    async def fake_convert(docx: bytes) -> bytes:
        calls["pdf"] += 1
        return b"%PDF"

    monkeypatch.setattr(es, "docx_to_pdf", fake_convert)
    svc = es.ExportService(SimpleNamespace(), SimpleNamespace(), Surveys())  # type: ignore[arg-type]
    kind, content = await svc.preview_survey(SimpleNamespace(), None)  # type: ignore[arg-type]
    assert (kind, content) == ("PDF", b"%PDF")
    assert calls == {"doc": 1, "docx": 1, "pdf": 1}
