"""Hook .githooks/commit-msg menolak atribusi AI di pesan commit, tanpa salah tolak pesan wajar."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[3] / ".githooks" / "commit-msg"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="bash tidak tersedia")


def jalankan(tmp_path, pesan: str):
    f = tmp_path / "MSG"
    f.write_bytes(pesan.encode("utf-8"))
    script = HOOK.read_bytes().replace(b"\r\n", b"\n")
    return subprocess.run(["bash", "-s", "--", str(f)], input=script, capture_output=True, check=False)


@pytest.mark.parametrize(
    "pesan",
    [
        "fix: perbaikan\n\nCo-Authored-By: Claude Sonnet <noreply@anthropic.com>\n",
        "fix: x\n\nco-authored-by: GitHub Copilot <c@x.com>\n",
        "fix: x\n\nCo-authored-by: Gemini <g@x.com>\n",
        "fix: x\n\nCo-Authored-By: Anthropic Bot <a@b.com>\n",
        "fix: x\n\nnoreply@anthropic.com\n",
        "fix: x\n\nGenerated with Claude Code\n",
        "fix: x\n\nClaude-Session: https://claude.ai/code/session_1\n",
    ],
)
def test_pesan_buruk_ditolak(tmp_path, pesan):
    r = jalankan(tmp_path, pesan)
    assert r.returncode == 1
    assert "COMMIT DITOLAK" in r.stderr.decode("utf-8", "replace")


@pytest.mark.parametrize(
    "pesan",
    [
        "fix(api): perbaiki validasi\n\nCo-Authored-By: Budi <budi@perusahaan.id>\n",
        "Merge pull request #1 from x/beta\n",
        'Revert "fix: x"\n\nThis reverts commit abc.\n',
        "fix: x\n# Co-Authored-By: Claude <noreply@anthropic.com>\n# Generated with\n",
    ],
)
def test_pesan_baik_lolos(tmp_path, pesan):
    assert jalankan(tmp_path, pesan).returncode == 0
