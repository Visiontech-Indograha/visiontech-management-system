# Diagram alur work (VMS)

Dibuat dari kode per 2026-10-29. Perbarui bila alur berubah.

Dokumen ini dibangun dari kode sumber (route, service, repository, skema, dan layar web serta mobile), bukan dari dokumen lama. Dokumen lama tidak dijadikan sumber kebenaran. Tujuan utamanya sebagai peta pengujian: setiap transisi punya endpoint, peran, prasyarat, dan efek samping, dengan rujukan berkas:baris.

## Indeks

| Berkas | Isi |
|---|---|
| [00-peran-dan-izin.md](00-peran-dan-izin.md) | Peran (web kantor dan lapangan), izin global, dan matriks aksi work x peran dengan syarat relasi dan status. |
| [01-flowchart-end-to-end.md](01-flowchart-end-to-end.md) | Flowchart besar: master data, order, survei, jadwal, lapangan, koreksi, ACC, BAST, ekspor, dan verifikasi. Setiap node memuat peran dan layar. |
| [02-state-machine.md](02-state-machine.md) | State machine: DailyStatus, ItemStatus, RolloverStatus, SurveyState, CorrectionStatus, ACC dan BAST, status absensi, sesi dan perangkat, sesi login, status proyek. Setiap transisi punya tabel endpoint, peran, prasyarat, dan efek. |
| [03-sequence.md](03-sequence.md) | Sequence diagram sepuluh alur: jenis pekerjaan, jadwal, absen, progres, rollover, koreksi, lembur, survei, BAST dan verifikasi, ekspor. |
| [04-activity.md](04-activity.md) | Activity per peran: PM web, ketua HP, anggota HP, reviewer absensi dan lembur. Mencakup keputusan dan jalur galat. |
| [05-matriks-uji.md](05-matriks-uji.md) | Matriks uji: jalur normal, negatif, batas input, perilaku manusia. Kolom Hasil kosong. |

## Cara membaca

1. Mulai dari `01` untuk melihat gambaran besar, lalu cocokkan dengan peran di `00`.
2. Untuk satu objek (jadwal, item, survei, koreksi, order, absensi), buka `02`. Tabel di bawah setiap diagram memuat endpoint dan syarat yang harus dicek.
3. Untuk urutan panggilan antara web, HP, API, DB, dan MinIO, buka `03`.
4. Untuk perilaku satu peran di layar, buka `04`.
5. Untuk membuat kasus uji, ambil ID di `05`. Kolom Tipe menunjukkan apakah uji dilakukan lewat UI web, HP, atau API.

Konvensi:

- Kode galat: 401 belum login, 403 izin atau relasi kurang, 404 tidak terlihat (sengaja tidak dibedakan dari tidak ada), 409 status tidak sesuai, 422 validasi atau foto wajib kurang.
- Berkas:baris merujuk ke posisi di repo. Nomor baris diambil saat pembuatan dokumen dan dapat bergeser setelah perubahan kode.
- Label "Relasi" di matriks peran berarti izin bergantung pada hubungan (ketua tim jadwal, anggota tim, PM atau OM divisi, PM order).
- Tanda [VERIFIKASI] berarti perilaku belum bisa dipastikan dari kode yang dibaca, atau kode dan komentar tidak sepakat.

## Bagian yang TIDAK pasti [VERIFIKASI]

| Lokasi | Yang belum pasti |
|---|---|
| 00, aksi nomor 26 (rekap lembur PM) | Cakupan data yang dikembalikan untuk PM (divisi atau diri sendiri). `overtime_service.py:111-115`. |
| 00, aksi nomor 29 (lihat semua absensi untuk PM) | Cakupan absensi untuk PM. PM tidak punya VIEW_ALL_ATTENDANCE. |
| 00, aksi nomor 28 (tinjau absensi FINANCE, OPS) | Dibatasi SQL `can_review` pada system_role (T3). |
| 02, 2.2 (PATCH progres pada item DONE) | Apakah penurunan qty pada item DONE diizinkan. Tidak ada guard di `plan_item_service.py:164-192`. |
| 02, 2.2 (CANCELLED) | Tidak ada penulis nilai CANCELLED (T5). |
| 02, 2.5 (urutan ACC dan BAST) | Tidak ada guard urutan pada sign dan acc-decision (T10). |
| 02, 2.8 (urutan status proyek) | Tidak ada validasi urutan transisi proyek. |
| 02, 2.7c (login, refresh) | Detail alur login di `auth_login_route.py` belum dibaca penuh. |
| 03, 3.4 (foto wajib) | Apakah UI selalu mengirim foto saat qty mencapai target. |
| 04, 4.4 (reviewer) | Cakupan peninjauan absensi untuk FINANCE dan OPS. |
| 05, AB-08 (jam buka absen) | Nilai produksi `ATTENDANCE_OPEN_TIME`, lihat T14. |
| 05, BT-10 (batas ukuran berkas) | Batas unggah per jenis berkas belum diverifikasi. |
| 05, HM-13 (konflik dua tab) | Apakah server punya kontrol konkurensi (versi baris) pada item. |

## Temuan dan celah alur (dari kode, belum diuji)

Nomor T dipakai di berkas lain sebagai rujukan.

| No | Temuan | Bukti | Dampak |
|---|---|---|---|
| T1 | Akun ber-peran ADMIN lolos `require_permission` tanpa cek izin, termasuk DELETE_ANY. Padahal `permissions.py` sengaja mengecualikan DELETE_ANY dari ADMIN. | `api/app/api/deps.py:180`; `api/app/core/permissions.py:42-43`, `:108` | Hapus absensi bisa dilakukan ADMIN. [VERIFIKASI] niat. |
| T2 | ADMIN lolos izin CREATE_PLAN, tetapi approve, submit, dan lainnya ditolak 403 karena hanya SUPER_ADMIN yang dihitung sebagai manage. | `access_service.py:67-68`, `:77` | Kebingungan UI bila ADMIN mencoba. [VERIFIKASI] apakah disengaja. |
| T3 | FINANCE dan OPS legacy punya REVIEW_ATTENDANCE, tetapi SQL `can_review` hanya mengenali system_role SUPER_ADMIN, OM, PM, ADMIN_HR_GA. | `permissions.py:111`, `:120`; `attendance_session_repository.py:599-611` | Peninjauan absensi tidak bisa dilakukan FINANCE atau OPS legacy, padahal komentar R-33 menyebut keduanya. |
| T4 | Status DONE dipakai bersama oleh item progres selesai, survei dikirim, dan survei disetujui. Persetujuan survei juga mengubah item SURVEY dependen menjadi DONE. | `survey_repository.py:250-262`; `survey_service.py:267`, `:330` | Status tidak bisa membedakan "selesai dikerjakan" dan "disetujui PM". |
| T5 | Nilai CANCELLED ada di skema item, tidak ada penulis. | `plan_item_schema.py:18`; pencarian di `api/app/modules/work_plans` | Status yang tidak pernah tercapai. [VERIFIKASI] |
| T6 | Progres pada item DONE tidak diblokir. Menurunkan qty menurunkan status ke IN_PROGRESS atau TODO. | `plan_item_service.py:164-192`; `plan_item_repository.py:205` | Item selesai bisa dibuka lagi tanpa jejak koreksi. [VERIFIKASI] |
| T7 | Selesaikan jadwal tidak memeriksa koreksi terbuka. Saat koreksi disetujui, jadwal kembali ONGOING sehingga ketua bisa menutup lagi di tengah revisi. | `daily_plan_service.py:257-269`; `daily_correction_service.py:75-77` | Urutan koreksi bisa terlewati. [VERIFIKASI] |
| T8 | Tolak jadwal APPROVED tidak memeriksa absensi atau peminjaman aset yang sudah terkait. Hapus jadwal memeriksanya. | `daily_plan_service.py:242-246` vs `:200-205` | Jadwal bisa ditarik dari DRAFT padahal absensi sudah tercatat. [VERIFIKASI] |
| T9 | Item PENDING_ROLLOVER tidak punya batas waktu. Progres diblokir sampai PM memutuskan. | `plan_item_service.py:167-168`, `:194-202` | Item bisa macet bila PM lalai. |
| T10 | Tanda tangan BAST (ketua dan PM) dan acc-decision tidak mensyaratkan urutan ACC. PATCH status bisa mengubah order_status ke COMPLETED tanpa BAST. | `work_completion_service.py:274-330`, `:256-272`, `:402-410` | BAST bisa ditandatangani sebelum klien ACC. |
| T11 | Kosakata order_status bercampur: PATCH menerima PENDING, CANCELLED, ONGOING, URGENT, COMPLETED. ACC menulis WAITING_ACC, ACCEPTED, REWORK. Constraint DB menerima semuanya. | `work_completion_service.py:262`; `work_completion_revision_repository.py:25-30`; `api/alembic/versions/0043_work_plan_flow_revamp.py:49` | PATCH bisa menimpa status ACC tanpa mengubah acc_status. |
| T12 | Ketua BAST dikenali dari peran TEAM_LEADER, sedangkan ketua jadwal dikenali dari relasi team.leader_employee_id. | `work_completion_service.py:288-293`; `access_service.py:44-87` | Akun EMPLOYEE yang jadi ketua tim tidak bisa tanda tangan BAST. |
| T13 | CurrentUser.role = roles[0]. Cek peran di service memakai satu nilai. | `api/app/api/deps.py:97`, `:163` | Akun multi-peran bergantung urutan peran di token. [VERIFIKASI] |
| T14 | Jam buka absen: default config 06:45, komentar service menyebut 07:00. Komentar config menyebut operasional 07:00 s.d. 19:00. | `api/app/core/config.py:147-148`; `attendance_session_service.py:321` | Perilaku produksi bergantung env. [VERIFIKASI] |
| T15 | Route review lembur tidak punya gate izin di route. Pemeriksaan ada di service (jadwal MANAGE, lembur tanpa jadwal hanya admin). | `overtime_route.py:59-68`; `overtime_service.py:72-84` | Berbeda dengan pola route lain. Aman bila service benar. [VERIFIKASI] |
| T16 | Ubah dan hapus proyek maupun klien tidak memeriksa divisi atau kepemilikan. Izin hanya CREATE_PLAN. | `project_route.py:16`, `client_route.py:16`; `project_service.py`, `client_service.py` | PM divisi lain bisa mengubah proyek divisi ini. [VERIFIKASI] |
| T17 | Absen offline dengan wajah tidak cocok tidak ditolak, hanya ditandai untuk OM. | `attendance_session_service.py:231-239` | Disengaja menurut komentar. Pastikan OM memeriksa tanda tersebut. |
| T18 | Survei: ketua mengisi lewat `_LOGIN` lalu dibatasi di service. Survei yang ditolak PM (RETURN) kembali DRAFT dan bisa diisi ulang, tanpa catatan alasan tersimpan di status. | `survey_route.py:51-128`; `survey_service.py:325-333` | Alasan pengembalian tersimpan di log, bukan di status. Cek UI menampilkannya. [VERIFIKASI] |
| T19 | Setujui matriks menelan semua AppError dan hanya mengembalikan daftar skipped tanpa alasan. | `daily_plan_service.py:231-240` | UI tidak bisa menjelaskan kenapa jadwal dilewati. [VERIFIKASI] |
| T20 | Rekap lembur untuk PM memanggil `repo.recap(month, user.employee_id)`. Cakupannya belum dipastikan dari kode yang dibaca. | `overtime_service.py:111-116` | Lihat aksi nomor 26 di `00` [VERIFIKASI]. |

## Ruang lingkup dan batas

- Cakupan: alur work (daily-first), survei, order klien, absensi, lembur, ekspor, dan verifikasi publik. Modul mess, aset, cuti, dan offboarding hanya disentuh di matriks izin.
- Web diperiksa dari route dan service API (`web/src/app/routes.tsx`, `web/src/services/*`). Komponen UI tidak dibaca baris per baris, jadi label tombol dan kondisi tampil ditulis sebagai pemetaan, bukan sebagai kebenaran final.
- Mobile diperiksa dari `mobile/lib/shared/router.dart`, `mobile/lib/data/vms_api.dart`, dan layar `features/plans` serta `features/attendance`.
- Tidak ada pengujian yang dijalankan. Matriks di `05` adalah rancangan, bukan hasil.
