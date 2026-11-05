# ADR 0001: Peta transisi status order klien
Status: Diterima
Tanggal: 2026-11-05
Konteks: Status order (`work_completion.order_status`) ditulis oleh override PM/OM, keputusan ACC klien, dan BAST PM. Tanpa peta, perpindahan sembarang (mis. Selesai -> Dibatalkan) lolos. Kode: `api/app/modules/work_completion/services/order_status_rules.py` (isu #312).
Pilihan yang dipertimbangkan:
  A. Tanpa batas transisi (kelebihan: fleksibel; kekurangan: data tidak konsisten).
  B. Peta transisi eksplisit satu sumber (dipilih).
Keputusan: pakai B. Perpindahan di luar peta ditolak 409 INVALID_STATE; tanpa perubahan selalu diterima.

Peta (dari -> ke):
- ONGOING -> URGENT, PENDING, WAITING_ACC, COMPLETED, CANCELLED
- URGENT -> ONGOING, PENDING, WAITING_ACC, COMPLETED, CANCELLED
- PENDING -> ONGOING, URGENT, WAITING_ACC, COMPLETED, CANCELLED
- WAITING_ACC -> ACCEPTED, REWORK, ONGOING, CANCELLED
- REWORK -> WAITING_ACC, ONGOING, CANCELLED
- ACCEPTED -> COMPLETED, ONGOING, CANCELLED
- COMPLETED -> ONGOING (buka lagi)
- CANCELLED -> ONGOING (buka lagi)

Perpindahan mundur (ke ONGOING dari WAITING_ACC, REWORK, ACCEPTED, COMPLETED, CANCELLED) dicatat di audit (ORDER_STATUS_MUNDUR). Selesai tidak bisa Dibatalkan.

Konsekuensi: DRAFT, PLANNED, IN_PROGRESS ada di CHECK skema tetapi tidak ada di peta (default kolom ONGOING, tidak ada kode yang menulisnya). Order berstatus itu (data lama/impor) tidak dapat dipindah (409). Usulan perbaikan minimal bila ada datanya: migrasi data ke ONGOING, atau tambah ketiganya ke peta dengan tujuan ONGOING/CANCELLED. Perlu keputusan pemilik; tidak diubah di sini.
Keputusan pemilik: 2026-11-05, peta (4 aturan, termasuk "Selesai tidak bisa Dibatalkan") disetujui.
Sumber: order_status_rules.py; riset 01 F-13.

Query cek data (dijalankan pemilik di produksi, hanya baca):
```sql
SELECT order_status, count(*) FROM work_completion GROUP BY order_status ORDER BY 2 DESC;
SELECT count(*) FROM work_completion WHERE order_status IN ('DRAFT','PLANNED','IN_PROGRESS');
```
