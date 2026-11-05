"""
app/modules/work_completion/order_status_rules.py

Peta transisi status order klien (work_completion.order_status). Satu sumber untuk semua penulis status:
PM/OM override (PATCH /status dan PUT), keputusan ACC klien, dan tanda tangan PM (COMPLETED).

Disetujui pemilik, tanggal 2026-11-05 (riset 01 F-13; docs/adr/0001-peta-transisi-status-order.md).
Peta diturunkan dari kode yang sudah ada:
- UI: URGENT <-> ONGOING (tandai/hapus mendesak).
- Override PM/OM: PENDING, CANCELLED, ONGOING, URGENT, COMPLETED.
- Keputusan ACC: WAITING_ACC (MENUNGGU_ACC), ACCEPTED (DITERIMA), REWORK (DITOLAK_REWORK).
- BAST PM: COMPLETED.
DRAFT, PLANNED, IN_PROGRESS ada di CHECK skema tetapi tidak ditulis kode mana pun, jadi tidak masuk peta.
Tidak ada status baru di sini.
"""

from __future__ import annotations

from app.core.errors import AppError

LABEL_STATUS: dict[str, str] = {
    "ONGOING": "Sedang dikerjakan",
    "URGENT": "Mendesak",
    "PENDING": "Menunggu klien",
    "WAITING_ACC": "Menunggu ACC klien",
    "REWORK": "Perlu perbaikan",
    "ACCEPTED": "Diterima klien",
    "COMPLETED": "Selesai",
    "CANCELLED": "Dibatalkan",
}

# Dari status -> status tujuan yang sah. Status tujuan yang sama (tidak ada perubahan) selalu diterima.
TRANSISI: dict[str, frozenset[str]] = {
    "ONGOING": frozenset({"URGENT", "PENDING", "WAITING_ACC", "COMPLETED", "CANCELLED"}),
    "URGENT": frozenset({"ONGOING", "PENDING", "WAITING_ACC", "COMPLETED", "CANCELLED"}),
    "PENDING": frozenset({"ONGOING", "URGENT", "WAITING_ACC", "COMPLETED", "CANCELLED"}),
    "WAITING_ACC": frozenset({"ACCEPTED", "REWORK", "ONGOING", "CANCELLED"}),
    "REWORK": frozenset({"WAITING_ACC", "ONGOING", "CANCELLED"}),
    "ACCEPTED": frozenset({"COMPLETED", "ONGOING", "CANCELLED"}),
    "COMPLETED": frozenset({"ONGOING"}),
    "CANCELLED": frozenset({"ONGOING"}),
}

# Transisi "memundurkan" (kembali ke tahap sebelumnya atau membuka lagi order selesai/dibatalkan).
# Setiap perpindahan ini dicatat di app_activity_logs (action ORDER_STATUS_MUNDUR).
MUNDUR: frozenset[tuple[str, str]] = frozenset({
    ("WAITING_ACC", "ONGOING"),
    ("REWORK", "ONGOING"),
    ("ACCEPTED", "ONGOING"),
    ("COMPLETED", "ONGOING"),
    ("CANCELLED", "ONGOING"),
})

# Keputusan ACC klien -> status order yang dihasilkan.
ACC_KE_STATUS: dict[str, str] = {
    "MENUNGGU_ACC": "WAITING_ACC",
    "DITERIMA": "ACCEPTED",
    "DITOLAK_REWORK": "REWORK",
}


def cek_transisi(dari: str, ke: str) -> None:
    """Tolak (409 INVALID_STATE) bila perpindahan `dari` -> `ke` tidak ada di peta. Tanpa perubahan selalu boleh."""
    if dari == ke:
        return
    if ke not in TRANSISI.get(dari, frozenset()):
        raise AppError(
            "INVALID_STATE",
            f"Status order tidak bisa diubah dari {LABEL_STATUS.get(dari, dari)} "
            f"ke {LABEL_STATUS.get(ke, ke)}.",
            status=409,
        )


def is_mundur(dari: str, ke: str) -> bool:
    """True bila perpindahan termasuk yang memundurkan status (wajib masuk audit)."""
    return (dari, ke) in MUNDUR
