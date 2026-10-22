"""
app/shared/documents/office_convert.py
.docx → PDF dengan LibreOffice headless (pratinjau laporan, docs/37). Tidak tersedia → None (pemanggil
mengirim .docx apa adanya). Setiap konversi memakai profil LibreOffice sementara sendiri agar aman paralel.
"""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


def soffice_path() -> str | None:
    if settings.SOFFICE_PATH:
        return settings.SOFFICE_PATH if Path(settings.SOFFICE_PATH).exists() else None
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    default = Path("C:/Program Files/LibreOffice/program/soffice.exe")
    return str(default) if default.exists() else None

# Tanpa kompresi/penurunan resolusi gambar: foto & peta layout tetap tajam di PDF.
_PDF_FILTER = ('pdf:writer_pdf_Export:{"ReduceImageResolution":{"type":"boolean","value":"false"},'
               '"UseLosslessCompression":{"type":"boolean","value":"true"}}')


def _convert(docx: bytes, binary: str) -> bytes | None:
    with tempfile.TemporaryDirectory(prefix="vms-docx2pdf-") as tmp:
        src = Path(tmp) / "laporan.docx"
        src.write_bytes(docx)
        profile = Path(tmp, "profile").as_uri()
        try:
            subprocess.run(
                [binary, f"-env:UserInstallation={profile}", "--headless", "--norestore", "--convert-to", _PDF_FILTER,
                 "--outdir", tmp, str(src)],
                check=True, capture_output=True, timeout=settings.DOCX_TO_PDF_TIMEOUT_S,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            logger.warning("Konversi docx→pdf gagal: %s", type(exc).__name__)
            return None
        out = Path(tmp) / "laporan.pdf"
        return out.read_bytes() if out.exists() else None


_WORD_PS = (
    "$ErrorActionPreference='Stop'; $w = New-Object -ComObject Word.Application; $w.Visible = $false; "
    "try {{ $d = $w.Documents.Open('{src}', $false, $true); "
    "$d.ExportAsFixedFormat('{out}', 17, $false, 0); $d.Close([ref]0) }} "
    "finally {{ $w.Quit() }}"
)


def _convert_word(docx: bytes) -> bytes | None:
    """Cadangan pengembangan di Windows: Microsoft Word (COM) lewat PowerShell bila LibreOffice tidak ada."""
    with tempfile.TemporaryDirectory(prefix="vms-docx2pdf-") as tmp:
        src, out = Path(tmp) / "laporan.docx", Path(tmp) / "laporan.pdf"
        src.write_bytes(docx)
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", _WORD_PS.format(src=src, out=out)],
                check=True, capture_output=True, timeout=settings.DOCX_TO_PDF_TIMEOUT_S,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            logger.info("Word tidak tersedia untuk konversi pratinjau: %s", type(exc).__name__)
            return None
        return out.read_bytes() if out.exists() else None


async def docx_to_pdf(docx: bytes) -> bytes | None:
    binary = soffice_path()
    if binary is not None:
        return await asyncio.to_thread(_convert, docx, binary)
    if os.name == "nt":
        return await asyncio.to_thread(_convert_word, docx)
    return None
