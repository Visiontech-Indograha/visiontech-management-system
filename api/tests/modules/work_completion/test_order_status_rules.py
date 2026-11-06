"""Peta transisi status order klien (order_status_rules). Tanpa basis data: tabel sah dan tidak sah."""
from __future__ import annotations

import pytest

from app.core.errors import AppError
from app.modules.work_completion.services.order_status_rules import (
    ACC_KE_STATUS,
    LABEL_STATUS,
    MUNDUR,
    TRANSISI,
    cek_transisi,
    is_mundur,
)

SAH = [
    ("ONGOING", "URGENT"), ("ONGOING", "PENDING"), ("ONGOING", "WAITING_ACC"),
    ("ONGOING", "COMPLETED"), ("ONGOING", "CANCELLED"),
    ("URGENT", "ONGOING"), ("URGENT", "PENDING"), ("URGENT", "WAITING_ACC"),
    ("URGENT", "COMPLETED"), ("URGENT", "CANCELLED"),
    ("PENDING", "ONGOING"), ("PENDING", "URGENT"), ("PENDING", "WAITING_ACC"),
    ("PENDING", "COMPLETED"), ("PENDING", "CANCELLED"),
    ("WAITING_ACC", "ACCEPTED"), ("WAITING_ACC", "REWORK"), ("WAITING_ACC", "ONGOING"),
    ("WAITING_ACC", "CANCELLED"),
    ("REWORK", "WAITING_ACC"), ("REWORK", "ONGOING"), ("REWORK", "CANCELLED"),
    ("ACCEPTED", "COMPLETED"), ("ACCEPTED", "ONGOING"), ("ACCEPTED", "CANCELLED"),
    ("COMPLETED", "ONGOING"), ("CANCELLED", "ONGOING"),
    # Tanpa perubahan selalu sah (PUT dengan status yang sama, atau ulang override).
    ("ONGOING", "ONGOING"), ("COMPLETED", "COMPLETED"), ("CANCELLED", "CANCELLED"),
]

TIDAK_SAH = [
    ("ONGOING", "ACCEPTED"), ("ONGOING", "REWORK"), ("ONGOING", "DRAFT"),
    ("ONGOING", "PLANNED"), ("ONGOING", "IN_PROGRESS"),
    ("URGENT", "REWORK"), ("URGENT", "ACCEPTED"),
    ("PENDING", "ACCEPTED"), ("PENDING", "REWORK"),
    ("WAITING_ACC", "COMPLETED"), ("WAITING_ACC", "URGENT"), ("WAITING_ACC", "PENDING"),
    ("REWORK", "COMPLETED"), ("REWORK", "ACCEPTED"), ("REWORK", "URGENT"),
    ("ACCEPTED", "URGENT"), ("ACCEPTED", "PENDING"), ("ACCEPTED", "WAITING_ACC"), ("ACCEPTED", "REWORK"),
    ("COMPLETED", "CANCELLED"), ("COMPLETED", "URGENT"), ("COMPLETED", "PENDING"),
    ("COMPLETED", "WAITING_ACC"), ("COMPLETED", "ACCEPTED"), ("COMPLETED", "REWORK"),
    ("CANCELLED", "URGENT"), ("CANCELLED", "COMPLETED"), ("CANCELLED", "PENDING"),
    ("CANCELLED", "WAITING_ACC"),
]


@pytest.mark.parametrize(("dari", "ke"), SAH)
def test_transisi_sah_diterima(dari: str, ke: str) -> None:
    cek_transisi(dari, ke)


@pytest.mark.parametrize(("dari", "ke"), TIDAK_SAH)
def test_transisi_tidak_sah_ditolak_409(dari: str, ke: str) -> None:
    with pytest.raises(AppError) as galat:
        cek_transisi(dari, ke)
    assert galat.value.code == "INVALID_STATE"
    assert galat.value.status == 409
    assert "tidak bisa diubah" in galat.value.message


def test_pesan_galat_berbahasa_indonesia_dengan_label() -> None:
    with pytest.raises(AppError) as galat:
        cek_transisi("COMPLETED", "URGENT")
    assert galat.value.message == "Status order tidak bisa diubah dari Selesai ke Mendesak."


@pytest.mark.parametrize(("dari", "ke"), sorted(MUNDUR))
def test_perpindahan_memundurkan_masuk_audit(dari: str, ke: str) -> None:
    assert is_mundur(dari, ke)
    cek_transisi(dari, ke)  # setiap pasangan MUNDUR juga sah di peta


@pytest.mark.parametrize(("dari", "ke"), [("ONGOING", "URGENT"), ("WAITING_ACC", "ACCEPTED"), ("ONGOING", "ONGOING")])
def test_perpindahan_maju_tidak_masuk_audit(dari: str, ke: str) -> None:
    assert not is_mundur(dari, ke)


def test_keputusan_acc_memetakan_ke_status_yang_ada() -> None:
    assert ACC_KE_STATUS == {"MENUNGGU_ACC": "WAITING_ACC", "DITERIMA": "ACCEPTED", "DITOLAK_REWORK": "REWORK"}
    for ke in ACC_KE_STATUS.values():
        assert ke in LABEL_STATUS


def test_peta_hanya_memakai_status_yang_berlabel_dan_tidak_menambah_status() -> None:
    semua = set(TRANSISI) | {ke for tujuan in TRANSISI.values() for ke in tujuan}
    assert semua <= set(LABEL_STATUS)
    assert set(LABEL_STATUS) == {
        "ONGOING", "URGENT", "PENDING", "WAITING_ACC", "REWORK", "ACCEPTED", "COMPLETED", "CANCELLED",
    }
    assert {(d, k) for d, tujuan in TRANSISI.items() for k in tujuan} >= MUNDUR
