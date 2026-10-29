# 04. Activity per peran

Dibuat dari kode per 2026-10-29. Satu diagram per peran pelaku. Setiap keputusan dan jalur galat merujuk ke kode galat di service. Layar web dari `web/src/app/routes.tsx`, layar HP dari `mobile/lib/shared/router.dart`.

Istilah: "PM" di diagram mencakup PM divisi dan OM divisi, karena keduanya memakai relasi `pm_id` atau `om_id` (`api/app/shared/access/access_service.py:94-100`).

## 4.1 PM (web kantor)

Layar utama: `/work-plans` (jadwal harian), `/surveys` dan `/surveys/:id`, `/work-completions`, `/projects`, `/clients`, `/work-types`, `/attendance`, `/overtime-recap`, `/teams`, `/sites`.

```mermaid
flowchart TD
    S(["Mulai: PM buka /work-plans"]) --> P1{"Ada tim yang perlu jadwal?"}
    P1 -->|"tidak"| P9(["Selesai"])
    P1 -->|"ya"| P2["Buat jadwal DRAFT per tim per tanggal<br/>POST /work-plans/daily<br/>Galat: 422 jika tim tidak di divisi, tanggal lampau, atau proyek tidak ONGOING<br/>Galat: 409 TEAM_DAY_TAKEN jika tim sudah punya jadwal"]
    P2 --> P3["Tambah item per titik<br/>POST /work-plans/daily/:id/items<br/>Galat: 409 jika jadwal bukan DRAFT atau SUBMITTED"]
    P3 --> P4["Submit ke SUBMITTED<br/>POST submit<br/>Galat: 422 PLAN_EMPTY jika belum ada item"]
    P4 --> P5{"Setujui atau tolak"}
    P5 -->|"tolak dengan alasan"| P6["POST reject, kembali DRAFT<br/>Galat: 409 jika status bukan SUBMITTED atau APPROVED"]
    P6 --> P2
    P5 -->|"setujui satu-satu"| P7["POST approve<br/>Galat: 422 jika tanggal lampau<br/>Galat: 403 jika bukan PM divisi"]
    P5 -->|"setujui matriks"| P8["POST /work-plans/daily/approve<br/>Jadwal gagal dilewati (termasuk tanpa item, PLAN_EMPTY), dilaporkan di skipped"]
    P7 --> P10["Jadwal APPROVED, tim dapat notifikasi"]
    P8 --> P10
    P10 --> P11{"Ada pekerjaan pindah hari?"}
    P11 -->|"ya"| P12["Buka panel item<br/>Setujui atau tolak pindah hari<br/>POST /work-plans/items/:id/rollover-decision<br/>Galat: 409 jika item sudah DONE atau SHIFTED_DAY"]
    P11 -->|"tidak"| P13{"Ada koreksi laporan terbuka?"}
    P12 --> P13
    P13 -->|"ya"| P14["Putuskan koreksi di CorrectionsPanel<br/>APPROVE, REJECT, ACCEPT, atau RETURN<br/>Galat: 409 jika status tidak sesuai"]
    P13 -->|"tidak"| P15{"Ada lembur menunggu?"}
    P14 --> P15
    P15 -->|"ya"| P16["Putuskan lembur di /overtime-recap<br/>Galat: 403 jika mengajukan sendiri"]
    P15 -->|"tidak"| P17{"Ada absensi NEEDS_REVIEW?"}
    P16 --> P17
    P17 -->|"ya"| P18["Tinjau absensi di /attendance<br/>Catatan wajib<br/>Galat: 403 jika absen sendiri atau di luar kewenangan"]
    P17 -->|"tidak"| P19{"Survei dari ketua sudah dikirim?"}
    P18 --> P19
    P19 -->|"ya"| P20["Tinjau survei di /surveys/:id<br/>APPROVE atau RETURN<br/>Galat: 409 jika bukan SUBMITTED"]
    P19 -->|"tidak"| P22
    P20 --> P21{"Survei APPROVED?"}
    P21 -->|"ya"| P21a["Buat rencana pemasangan<br/>POST /work-plans/surveys/:id/plan<br/>Galat: 409 jika jadwal tujuan sudah APPROVED"]
    P21 -->|"tidak, RETURN"| P20
    P21a --> P22
    P22{"Order klien selesai dikerjakan?"}
    P22 -->|"belum"| P9
    P22 -->|"ya"| P23["ACC klien di /work-completions<br/>POST acc-decision<br/>DITOLAK_REWORK membuka ulang item utama"]
    P23 --> P24{"ACC DITERIMA?"}
    P24 -->|"tidak, REWORK"| P2
    P24 -->|"ya"| P25{"Ketua sudah tanda tangan BAST?"}
    P25 -->|"belum"| P26["Tunggu ketua tanda tangan<br/>Galat: 409 LEADER_SIGNATURE_REQUIRED jika PM mendahului"]
    P26 --> P25
    P25 -->|"ya"| P27["Tanda tangan BAST sebagai PM<br/>POST /work-completions/:id/sign<br/>Order terkunci, signature_hash tersimpan"]
    P27 --> P28["Ekspor dokumen: BAST docx, BoQ xlsx, slide pptx<br/>BAST PDF ber-QR hanya setelah tanda tangan PM"]
    P28 --> P9
```

Catatan: akun PM hanya bisa membuat order atas nama dirinya sendiri (`pm_id` harus sama dengan karyawan login). Lihat `work_completion_service.py:183-189`.

## 4.2 Ketua tim (HP lapangan)

Layar utama: tab `/` (absen, `AttendanceScreen`), tab `/plans` (jadwal, `DailyPlansScreen` lalu `DailyPlanScreen`), `SurveyScreen`, `ItemProgressScreen`, `BastSignScreen`.

```mermaid
flowchart TD
    K0(["Mulai: buka tab absen"]) --> K1{"Wajah sudah terdaftar?"}
    K1 -->|"belum"| K2["Daftar wajah dulu<br/>POST /face/enroll<br/>Galat: 409 FACE_NOT_ENROLLED"]
    K2 --> K1
    K1 -->|"ya"| K3["Ambil swafoto dan GPS<br/>POST /files/upload, lalu POST /attendance/check-in<br/>Galat: 422 GPS_INACCURATE, 422 EXPLANATION_REQUIRED, 422 FACE_MISMATCH"]
    K3 --> K4{"Absen diterima?"}
    K4 -->|"tidak, tanpa sinyal"| K5["Simpan offline, kirim otomatis<br/>POST /attendance/offline"]
    K4 -->|"ditolak"| K3
    K4 -->|"ya"| K6["Buka tab /plans, pilih jadwal hari ini"]
    K5 --> K6
    K6 --> K7{"Status jadwal?"}
    K7 -->|"APPROVED"| K8["Mulai hari kerja<br/>POST /work-plans/daily/:id/start<br/>Galat: 409 jika bukan APPROVED; 409 CHECKIN_REQUIRED jika ketua belum absen masuk pada tanggal jadwal atau hari ini"]
    K7 -->|"ONGOING"| K9["Kerjakan item"]
    K7 -->|"belum dirilis"| K0
    K8 --> K9
    K9 --> K10{"Jenis item?"}
    K10 -->|"survei"| K11["Isi survei: titik, material, laporan, foto<br/>Galat: 409 jika survei sudah dikirim"]
    K11 --> K12["Kirim survei<br/>Galat: 422 jika titik kosong, 422 PHOTOS_REQUIRED jika foto kurang"]
    K12 --> K9
    K10 -->|"pemasangan"| K13["Isi progres dan foto wajib<br/>PATCH /work-plans/items/:id/progress<br/>Galat: 422 PHOTOS_REQUIRED, 409 PREREQUISITE_NOT_DONE"]
    K13 --> K14{"Qty mencapai target?"}
    K14 -->|"ya"| K9
    K14 -->|"tidak, tak selesai hari ini"| K15["Minta pindah hari dengan alasan<br/>POST /work-plans/items/:id/request-rollover<br/>Galat: 409 jika sudah diajukan atau DONE"]
    K15 --> K9
    K9 --> K16{"Semua item selesai?"}
    K16 -->|"belum"| K9
    K16 -->|"ya"| K17{"Lembur?"}
    K17 -->|"ya"| K18["Ajukan lembur, 0 sampai 12 jam, alasan wajib<br/>POST /overtime<br/>Galat: 409 jika ada pengajuan menunggu"]
    K17 -->|"tidak"| K19
    K18 --> K19["Isi laporan harian<br/>POST /work-plans/daily/:id/report"]
    K19 --> K20["Absen pulang<br/>POST /attendance/check-out"]
    K20 --> K21["Selesaikan hari kerja<br/>POST /work-plans/daily/:id/complete<br/>Galat: 409 CORRECTION_OPEN atau ROLLOVER_PENDING jika koreksi atau pindah hari masih terbuka; 422 REPORT_REQUIRED jika laporan belum ada"]
    K21 --> K22{"Ada koreksi dari PM?"}
    K22 -->|"ya, REVISING"| K23["Revisi laporan lalu kirim<br/>POST /work-plans/corrections/:id/submit"]
    K23 --> K21
    K22 -->|"tidak"| K24{"Order klien perlu BAST?"}
    K24 -->|"ya, ketua tim order"| K25["Tanda tangan serah terima di BastSignScreen<br/>POST /work-completions/:id/sign<br/>Galat: 403 jika bukan TEAM_LEADER di tim order"]
    K24 -->|"tidak"| K26(["Selesai"])
    K25 --> K26
```

Catatan: "ketua" dalam diagram ini berarti relasi `team.leader_employee_id` pada jadwal (`access_service.py:44-87`). Untuk BAST, kode juga mewajibkan peran `TEAM_LEADER` (`work_completion_service.py:288-293`). Lihat T12.

## 4.3 Anggota tim (HP lapangan)

Layar: sama dengan ketua, tanpa tombol mulai, selesai, koreksi, dan BAST.

```mermaid
flowchart TD
    A0(["Mulai: buka tab absen"]) --> A1{"Wajah sudah terdaftar?"}
    A1 -->|"belum"| A2["Daftar wajah<br/>POST /face/enroll"]
    A2 --> A1
    A1 -->|"ya"| A3["Absen masuk: swafoto dan GPS<br/>POST /attendance/check-in<br/>Galat: 403 SITE_NOT_ALLOWED jika bukan anggota tim jadwal"]
    A3 --> A4{"Absen diterima?"}
    A4 -->|"ditolak, GPS kabur"| A5["Pindah tempat terbuka, ulangi<br/>Galat: 422 GPS_INACCURATE"]
    A5 --> A3
    A4 -->|"ditolak, di luar radius"| A6["Isi penjelasan, kirim ulang<br/>Galat: 422 EXPLANATION_REQUIRED"]
    A6 --> A3
    A4 -->|"diterima"| A7{"Jadwal sudah ONGOING?"}
    A7 -->|"belum"| A8["Tunggu ketua mulai hari kerja"]
    A8 --> A7
    A7 -->|"ya"| A9["Kerjakan item yang ditugaskan"]
    A9 --> A10{"Foto wajib lengkap?"}
    A10 -->|"belum"| A11["Ambil foto sesuai slot, unggah<br/>Galat: 422 PHOTOS_REQUIRED saat simpan"]
    A11 --> A9
    A10 -->|"ya"| A12["Simpan progres<br/>PATCH /work-plans/items/:id/progress"]
    A12 --> A13{"Ajukan lembur?"}
    A13 -->|"ya"| A14["POST /overtime<br/>Galat: 409 jika jadwal tidak ONGOING"]
    A13 -->|"tidak"| A15
    A14 --> A15{"Absen pulang?"}
    A15 -->|"ya"| A16["Absen pulang<br/>POST /attendance/check-out<br/>Galat: 409 NO_OPEN_SESSION"]
    A15 -->|"belum"| A9
    A16 --> A17(["Selesai"])
```

Catatan: anggota tidak punya izin untuk tombol mulai dan selesai (`daily_plan_route.py:152-163` memakai relasi ketua di service). Jika anggota mengirim progres saat jadwal bukan ONGOING, server mengembalikan 409 (`plan_item_service.py:166`).

## 4.4 Reviewer absensi dan lembur (OPS, FINANCE, OM)

Layar web: `/attendance` (tinjau absensi, `AttendanceReviewDialog.tsx`), `/overtime-recap` (rekap dan keputusan lembur), `/attendance-recap` (rekap bulanan). Peran: OPS dan FINANCE memiliki REVIEW_ATTENDANCE dan REVIEW_OVERTIME (`api/app/core/permissions.py:109-122`), OM memiliki keduanya (`permissions.py:132-136`).

```mermaid
flowchart TD
    R0(["Mulai: buka /attendance"]) --> R1{"Ada absensi NEEDS_REVIEW?"}
    R1 -->|"tidak"| R2["Lihat rekap dan daftar absensi<br/>VIEW_ALL_ATTENDANCE"]
    R1 -->|"ya"| R3{"Peran dan kewenangan?"}
    R3 -->|"peran tidak punya REVIEW_ATTENDANCE, misal HR"| R4["Ditolak 403 di route<br/>attendance_route.py:134"]
    R3 -->|"punya izin, tapi system_role tidak di SQL can_review"| R5["Ditolak 403 Absensi di luar kewenangan<br/>[VERIFIKASI] lihat T3, FINANCE dan OPS legacy"]
    R3 -->|"OM atau PM"| R6{"Absensi milik sendiri?"}
    R6 -->|"ya"| R7["Ditolak 403, empat mata"]
    R6 -->|"tidak"| R8["Isi catatan wajib, setujui atau tolak<br/>POST /attendance/:id/review<br/>Galat: 409 jika bukan NEEDS_REVIEW, 422 jika catatan kosong"]
    R8 --> R9["Absensi APPROVED atau REJECTED, pekerja dapat notifikasi"]
    R2 --> R10
    R9 --> R10{"Ada lembur PENDING_PM?"}
    R10 -->|"ya"| R11{"Lembur ber-jadwal?"}
    R11 -->|"ya"| R12{"Peninjau PM atau OM divisi?"}
    R11 -->|"tidak"| R13{"Admin?"}
    R12 -->|"ya"| R14["POST /overtime/:id/review<br/>Galat: 403 jika pengaju sendiri, 409 jika sudah diputus"]
    R12 -->|"tidak"| R15["Ditolak 403 MANAGE"]
    R13 -->|"ya"| R14
    R13 -->|"tidak"| R15
    R10 -->|"tidak"| R16{"Perlu rekap?"}
    R14 --> R16
    R16 -->|"ya"| R17["Rekap bulanan<br/>GET /recaps/attendance, GET /recaps/overtime<br/>Cakupan: OM, FINANCE, OPS semua, PM sebagian [VERIFIKASI]"]
    R16 -->|"ekspor CSV"| R18["Ekspor absensi CSV, FINANCE<br/>GET /attendance/export"]
    R16 -->|"tidak"| R19(["Selesai"])
    R17 --> R19
    R18 --> R19
```

Catatan: pemeriksaan galat untuk tinjau absensi ada di `api/app/modules/attendance/services/attendance_session_service.py:675-700`. Rekap lembur untuk PM dibatasi oleh `overtime_service.py:111-116` [VERIFIKASI cakupan divisi].
