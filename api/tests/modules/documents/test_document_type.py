"""Jenis dokumen disimpan sebagai kode baku (seed V2: SIM_A, SERTIFIKAT_K3, …) apa pun ketikannya."""

import pytest
from pydantic import ValidationError

from app.modules.documents.schemas.document_schema import EmployeeDocumentCreate

FILE_ID = "01a0dd8d-b442-7c07-91b8-5d8ac8f059fb"


@pytest.mark.parametrize(
    ("typed", "stored"),
    [
        ("sim a", "SIM_A"),
        ("SIMA", "SIM_A"),
        ("  Sim   A ", "SIM_A"),
        ("sim-c", "SIM_C"),
        ("SIM B1", "SIM_B1"),
        ("sim b ii", "SIM_B2"),
        ("ktp", "KTP"),
        ("Sertifikat  K3", "SERTIFIKAT_K3"),
        ("kontrak pkwt", "KONTRAK_PKWT"),
    ],
)
def test_doc_type_is_normalised(typed: str, stored: str) -> None:
    assert EmployeeDocumentCreate(doc_type=typed, file_id=FILE_ID).doc_type == stored


@pytest.mark.parametrize("typed", ["   ", "x", "KTP/SIM"])
def test_invalid_doc_type_is_rejected(typed: str) -> None:
    with pytest.raises(ValidationError):
        EmployeeDocumentCreate(doc_type=typed, file_id=FILE_ID)


def test_expiry_cannot_precede_start() -> None:
    with pytest.raises(ValidationError):
        EmployeeDocumentCreate(doc_type="SIM A", file_id=FILE_ID, active_at="2026-05-01", expired_at="2026-04-30")
