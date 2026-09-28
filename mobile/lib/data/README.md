# data/

Database lokal (drift) & repository untuk pola offline-first:

- Skema tabel drift per entitas yang disinkronkan (absensi, cuti, laporan+BOM, peminjaman kendaraan/alat).
- Antrian sync: record yang dibuat/diubah offline menunggu di sini sampai online.
- Repository per entitas yang menjembatani UI (features/) <-> local db <-> API client (core/).
- Logika retry dengan exponential backoff & resolusi konflik (server-wins) sesuai
  `docs/requirements/MOBILE_SYNC_CONTRACT.md` di repo backend.
