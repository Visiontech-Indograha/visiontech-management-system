"""Jenis dokumen dirapikan agar aturan SIM di trigger (`doc_type = 'SIM A'`) tidak gagal karena
ketikan bebas ("sim a", "SIMA", "Sim  A")."""

import pytest
from pydantic import ValidationError

from app.modules.documents.schemas.document_schema import EmployeeDocumentCreate

FILE_ID = "01a0dd8d-b442-7c07-91b8-5d8ac8f059fb"


@pytest.mark.parametrize(
    ("typed", "stored"),
    [
        ("sim a", "SIM A"),
        ("SIMA", "SIM A"),
        ("  Sim   A ", "SIM A"),
        ("sim c", "SIM C"),
        ("SIM B1", "SIM B I"),
        ("sim bii", "SIM B II"),
        ("ktp", "KTP"),
        ("mcu", "MCU"),
        ("Sertifikat  K3 Umum", "Sertifikat K3 Umum"),
    ],
)
def test_doc_type_is_normalised(typed: str, stored: str) -> None:
    doc = EmployeeDocumentCreate(doc_type=typed, number="123", file_id=FILE_ID)
    assert doc.doc_type == stored


def test_blank_doc_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EmployeeDocumentCreate(doc_type="   ", number="123", file_id=FILE_ID)
