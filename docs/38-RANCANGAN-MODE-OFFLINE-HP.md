# 38 · Rancangan Mode Offline (Offline-First) Aplikasi HP

Status: **catatan rancangan untuk milestone berikutnya** (permintaan pemilik 21-10-2026: "semua fitur bisa
berfungsi di mode offline, saat terhubung kembali langsung sinkronisasi").
Tidak menambah tabel/kolom server tanpa persetujuan (aturan docs/36).

## 1. Kondisi sekarang

| Lapisan | Sudah ada | Belum |
|---|---|---|
| DB lokal (drift) | `PendingSyncOperations` (antrean tulis), `CachedSyncGroups` (cache baca kunci→JSON), `PendingAttachments` (foto tertunda) | — |
| Mesin sync | `SyncEngine.submit/_push/syncAll`, `client_op_id` idempoten, dead-letter + layar Antrian Sinkronisasi, `ConnectivitySync` (kirim ulang saat online) | — |
| Server | `POST /sync/operations`; `OFFLINE_ALLOWED = ("OVERTIME_REPORT",)` | handler op lain (fitur V2 ditulis ulang) |
| Absensi | absen offline bertanda tangan (`OfflineAttendance`) | — |
| Baca offline | `daily_today` (absensi), **21-10-2026:** daftar jadwal mingguan (`daily_<senin>`), detail jadwal (`daily_plan_<id>`), daftar survei (`surveys_mine`), detail survei (`survey_<id>`) lewat `fetchList`/`fetchMap` | galeri, profil, katalog material, detail item |
| Tulis offline | lembur | progres item/titik, survei (titik, foto, laporan, kirim), BAST, insiden |

## 2. Pola yang dipakai semua fitur (aturan pengembangan berikutnya)

1. **Baca:** setiap layar memuat lewat `engine.fetchList(key, …)` / `engine.fetchMap(key, …)`. Kunci cache stabil
   (`<fitur>_<id>`). Saat offline tampilkan isi cache + penanda "Data tersimpan · <waktu>"
   (`SyncEngine.neverCached` / `offlineNoDataMessage` bila belum pernah dimuat).
2. **Tulis:** jangan panggil `api.post/put` langsung dari layar. Panggil `engine.submit(opType, payload, files)`:
   - payload berisi **id buatan HP** (`Uuid().v4()`) untuk entitas baru (titik survei, item, laporan), supaya
     operasi lanjutan (foto, ubah, hapus) bisa merujuk id itu sebelum server pernah melihatnya;
   - foto disimpan sebagai path lokal (`_local_files`) dan diunggah tepat sebelum operasinya dikirim;
   - UI langsung memperbarui cache lokal (optimistic) dan memberi label "Menunggu sinyal".
3. **Server:** tiap op baru = satu handler di `modules/system/services/sync_service.py` yang memanggil **service
   modul pemiliknya** (bukan SQL baru), ditambahkan ke `OFFLINE_ALLOWED`. Idempoten per `client_op_id`; entitas
   baru memakai id dari klien (`INSERT … ON CONFLICT (id) DO NOTHING`).
4. **Konflik:** server-wins. Op yang ditolak (4xx: jadwal sudah ditutup, survei sudah disetujui, dll.) masuk
   dead-letter beserta alasan, terlihat di layar Antrian Sinkronisasi (coba lagi / hapus).
5. **Wajib online (tidak diantrekan):** login, verifikasi wajah enrol, persetujuan PM, penerbitan jadwal,
   unduh laporan resmi. Tombolnya dinonaktifkan saat offline dengan keterangan.

## 3. Urutan op yang direncanakan

| Op | Endpoint online yang ditiru | Catatan |
|---|---|---|
| `SURVEY_POINT_UPSERT` | `POST /work-plans/surveys/{task}/points`, `PUT …/points/{pid}` | `point_id` dari HP |
| `SURVEY_POINT_DELETE` | `DELETE …/points/{pid}` | |
| `SURVEY_POINT_MOVE` | `PUT …/points/{pid}/location` | |
| `SURVEY_REPORT_SAVE` | `PUT …/{task}/report` | |
| `SURVEY_SUBMIT` | `POST …/{task}/submit` | dikirim setelah semua op titik tugas itu sukses (urut per `task_id`) |
| `ITEM_PROGRESS` | progres titik/item jadwal | foto bukti via `_local_files` |
| `BAST_LEADER_SIGN` | tanda tangan ketua | |
| `INCIDENT_REPORT`, `DAILY_REPORT_*` | sudah ada di klien, perlu handler V2 di server | |

Pratinjau laporan survei offline: tidak dirender di HP (butuh LibreOffice); tampilkan ringkasan titik dari cache
dan tombol pratinjau aktif kembali saat online.

## 4. Cache berkas (foto)

`Image.network` tidak menyimpan ke disk. Tahap berikutnya: unduh varian `thumb`/`view` ke folder aplikasi
(kunci `file_id+variant`, batas ±200 MB, LRU) sehingga foto titik, foto panduan PM, dan galeri tampil offline.
URL berkas dari API relatif (`/api/v1/files/{id}?token=…`) — selalu di-resolve ke `baseUrl` (`VmsApi.fileUrl`).

## 5. Uji penerimaan

- Mode pesawat → buka jadwal/survei yang pernah dibuka → data tampil dengan penanda tersimpan.
- Mode pesawat → tambah titik + foto → keluar-masuk aplikasi → titik masih ada (antrean).
- Online kembali → antrean terkirim otomatis, tidak ada duplikat (kirim ulang `client_op_id` sama → idempoten).
- Survei disetujui PM saat HP offline → op ubah titik ditolak → muncul di "Perlu perhatian" dengan alasan.
