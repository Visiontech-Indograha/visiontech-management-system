# 03. Sequence diagram

Dibuat dari kode per 2026-10-29. Pelaku: web (browser kantor), HP (aplikasi Flutter), API (FastAPI), DB (Postgres), MinIO (penyimpanan berkas). Setiap diagram diikuti tabel referensi berkas:baris.

Keterangan kode galat dalam diagram: 401 belum login, 403 izin atau relasi kurang, 404 tidak terlihat, 409 status tidak sesuai, 422 validasi.

## 3.1 Buat jenis pekerjaan (beserta template foto)

```mermaid
sequenceDiagram
    autonumber
    participant W as Web PM
    participant A as API
    participant D as DB
    participant S as MinIO
    W->>A: POST /work-types (CREATE_PLAN)
    alt tanpa izin CREATE_PLAN
        A-->>W: 403 FORBIDDEN
    else izin ada
        A->>A: PM hanya divisi sendiri (creator_div)
        A->>A: validasi nama dan label slot foto unik (422)
        A->>D: cek nama ganda di divisi (409 DUPLICATE)
        A->>D: cek foto contoh milik organisasi yang sama
        alt jenis titik SURVEY_POINT
            A->>D: pemasangan lanjutan harus jenis WORK di divisi sama (422)
        end
        A->>D: insert work_type dan replace photos
        A-->>W: 201 WorkTypeOut
    end
    W->>A: POST /work-types/:id/materials (template material)
    A->>D: insert default material (403 jika divisi lain)
    A-->>W: 201
```

Referensi: `api/app/modules/work_types/routes/work_type_route.py:61-76`, `api/app/modules/work_types/services/work_type_service.py:38-60` (validasi), `:62-79` (create), `:104-114` (`_check_kind`), `:133-147` (material).

## 3.2 Buat dan setujui jadwal harian

```mermaid
sequenceDiagram
    autonumber
    participant W as Web PM
    participant A as API
    participant D as DB
    participant N as Notifikasi
    W->>A: POST /work-plans/daily (CREATE_PLAN)
    A->>D: cek divisi, PM atau OM divisi (403 atau 422)
    A->>D: tim milik divisi aktif, tanggal tidak lampau (422)
    A->>D: tim belum punya jadwal di tanggal itu (409 TEAM_DAY_TAKEN)
    A->>D: proyek ONGOING dan sesuai divisi (422)
    A->>D: insert jadwal DRAFT
    A-->>W: 201 DailyPlanOut
    W->>A: POST /work-plans/daily/:id/items (MANAGE)
    A->>D: status DRAFT atau SUBMITTED (409), validasi jenis pekerjaan dan order
    A-->>W: 201 PlanItemOut
    W->>A: POST /work-plans/daily/:id/submit (MANAGE)
    A->>D: cek minimal 1 item (422 PLAN_EMPTY), DRAFT to SUBMITTED
    A->>N: daily_submitted
    A-->>W: 200 DailyPlanOut
    W->>A: POST /work-plans/daily/:id/approve (MANAGE, atau matriks POST /work-plans/daily/approve)
    A->>D: status DRAFT atau SUBMITTED (409), tanggal tidak lampau (422), minimal 1 item (422 PLAN_EMPTY)
    A->>D: SET APPROVED, approver diisi
    A->>N: daily_approved ke tim
    A-->>W: 200 (matriks: daftar approved dan skipped)
    opt PM menolak
        W->>A: POST /work-plans/daily/:id/reject (alasan)
        A->>D: SUBMITTED atau APPROVED to DRAFT
        A->>N: daily_rejected
    end
```

Referensi: `api/app/modules/work_plans/routes/daily_plan_route.py:82-93,131-149`; `api/app/modules/work_plans/services/daily_plan_service.py:113-150` (create), `:215-246` (submit, approve, reject), `:231-240` (matriks).

## 3.3 Absen masuk dan absen pulang (HP)

```mermaid
sequenceDiagram
    autonumber
    participant H as HP Anggota
    participant A as API
    participant D as DB
    participant S as MinIO
    participant F as Layanan wajah
    H->>A: POST /files/upload (swafoto)
    A->>S: simpan berkas selfie
    A-->>H: file_id
    H->>A: POST /attendance/check-in (site, lat, lng, accuracy, selfie_file_id, explanation)
    A->>D: kanal sesuai mode (FIELD ke MOBILE, OFFICE ke WEB) (403 WRONG_ATTENDANCE_CHANNEL)
    alt wajah belum terdaftar dan saklar wajib menyala
        A-->>H: 409 FACE_NOT_ENROLLED
    end
    alt selfie kosong
        A-->>H: 422 selfie wajib
    end
    alt akurasi GPS di atas 100 m (browser 300 m)
        A-->>H: 422 GPS_INACCURATE
    end
    A->>D: jam buka (ATTENDANCE_OPEN_TIME), cuti, sesi terbuka, batas percobaan
    alt melanggar aturan waktu, cuti, sesi, atau percobaan
        A-->>H: 409 atau 422 sesuai pelanggaran
    end
    A->>D: lokasi (404), unit lokasi, jarak ke radius
    alt di luar radius dan tanpa penjelasan
        A-->>H: 422 EXPLANATION_REQUIRED
    end
    opt jadwal kerja harian
        A->>D: pengabsen anggota atau ketua tim, jadwal APPROVED atau ONGOING, hari ini (403 atau 409)
    end
    A->>F: cocokkan swafoto dengan wajah terdaftar
    alt cocok ditolak online
        F-->>A: MISMATCH
        A-->>H: 422 FACE_MISMATCH
    else layanan mati
        F-->>A: tidak bisa dipastikan
        A->>D: PENDING_OM (NEEDS_REVIEW)
    end
    A->>D: insert absensi, AUTO_VALID bila dalam radius, selain itu PENDING_OM
    A-->>H: 200 AttendanceResponse
    H->>A: POST /attendance/check-out (kanal dan akurasi dicek)
    A->>D: sesi terbuka harus ada (409 NO_OPEN_SESSION)
    A->>D: isi check_out_at
    A-->>H: 200
```

Referensi: `api/app/modules/attendance/routes/attendance_route.py:92-115`; `api/app/modules/attendance/services/attendance_session_service.py:97-107` (kanal), `:205-217` (wajah), `:219-229` (jadwal harian), `:231-239` (verifikasi wajah), `:270-424` (check-in), `:426-541` (check-out); `api/app/modules/attendance/repositories/attendance_session_repository.py:365` (AUTO_VALID atau PENDING_OM).

Varian offline (`POST /attendance/offline`): data ditandatangani perangkat (ECDSA, kunci didaftarkan lewat `POST /attendance/device-key`). Server memverifikasi tanda tangan, jam jangkar, dan batas 7 hari (`api/app/modules/attendance/services/attendance_offline_service.py:78-190`).

## 3.4 Mulai hari kerja, isi progres item, dan unggah foto

```mermaid
sequenceDiagram
    autonumber
    participant K as HP Ketua
    participant A as API
    participant D as DB
    participant S as MinIO
    K->>A: POST /work-plans/daily/:id/start (LEADER)
    A->>D: status APPROVED (409), tanggal tidak lebih dari hari ini (422), absen masuk ketua pada tanggal jadwal atau hari ini WIB (409 CHECKIN_REQUIRED)
    A->>D: SET ONGOING
    A-->>K: 200 DailyPlanOut
    K->>A: POST /files/upload (foto hasil kerja)
    A->>S: simpan berkas
    A-->>K: file_id
    K->>A: PATCH /work-plans/items/:id/progress (completed_qty, photos, notes)
    A->>D: akses TEAM (anggota atau ketua tim), jadwal ONGOING (403 atau 409)
    A->>D: item tidak PENDING_ROLLOVER atau SHIFTED_DAY (409)
    A->>D: completed_qty tidak lebih dari target (422)
    alt item prasyarat belum selesai
        A-->>K: 409 PREREQUISITE_NOT_DONE
    end
    A->>D: file foto ada di tabel berkas (422)
    alt qty mencapai target
        A->>D: foto wajib per slot lengkap (422 PHOTOS_REQUIRED)
        A->>D: SET DONE
    else qty di bawah target
        A->>D: SET IN_PROGRESS atau TODO
    end
    A-->>K: 200 PlanItemOut
```

Referensi: `api/app/modules/work_plans/routes/daily_plan_route.py:152-157`; `api/app/modules/work_plans/services/daily_plan_service.py:249-255`; `api/app/modules/work_plans/services/plan_item_service.py:164-192`; `api/app/modules/work_plans/repositories/plan_item_repository.py:197-225`. Foto wajib dicek hanya saat qty mencapai target (`plan_item_service.py:186-190`) [VERIFIKASI praktik UI].

## 3.5 Rollover (minta pindah hari, keputusan PM)

```mermaid
sequenceDiagram
    autonumber
    participant K as HP Ketua
    participant A as API
    participant D as DB
    participant W as Web PM
    participant N as Notifikasi
    K->>A: POST /work-plans/items/:id/request-rollover (delay_reason, completed_qty)
    A->>D: LEADER, jadwal APPROVED atau ONGOING (403 atau 409)
    A->>D: item belum DONE, SHIFTED_DAY, atau PENDING_ROLLOVER (409)
    A->>D: completed_qty kurang dari target (422)
    A->>D: PENDING_ROLLOVER, WAITING_PM
    A-->>K: 200 PlanItemOut
    W->>A: POST /work-plans/items/:id/rollover-decision (approve, target_date atau target_daily_plan_id, target_team_id)
    A->>D: MANAGE dan lock item (403 atau 404)
    alt item DONE atau SHIFTED_DAY
        A-->>W: 409 INVALID_STATE
    else keputusan TOLAK
        A->>D: WAITING_PM wajib (409)
        A->>D: REJECTED_BY_PM, status IN_PROGRESS atau TODO
        A->>D: log keputusan REJECTED
        A-->>W: 200
    else keputusan SETUJUI
        A->>D: tim tujuan sama dengan tim asal (422)
        alt jadwal tujuan diberikan
            A->>D: divisi sama (422), tidak COMPLETED (409)
        else tanggal tujuan diberikan
            A->>D: cari jadwal tim di tanggal itu
            alt belum ada
                A->>D: clone_day, buat jadwal tujuan baru
            end
        end
        A->>D: tanggal tujuan setelah asal dan tidak lampau (422)
        A->>D: item asal SHIFTED_DAY, APPROVED_BY_PM
        A->>D: item baru TODO di jadwal tujuan dengan sisa volume
        A->>D: relink dependen
        A->>D: log APPROVED, proactive bila tanpa request
        A-->>W: 200 PlanItemOut item baru
    end
```

Referensi: `api/app/modules/work_plans/routes/plan_item_route.py:82-95`; `api/app/modules/work_plans/services/plan_item_service.py:194-275`; `api/app/modules/work_plans/repositories/plan_item_repository.py:233-268`.

## 3.6 Koreksi laporan harian

```mermaid
sequenceDiagram
    autonumber
    participant K as HP Ketua
    participant A as API
    participant D as DB
    participant W as Web PM
    participant N as Notifikasi
    K->>A: POST /work-plans/daily/:id/corrections (reason)
    A->>D: LEADER, jadwal COMPLETED (409), tidak ada koreksi terbuka (409 CORRECTION_OPEN)
    A->>D: insert REQUESTED
    A->>N: CORRECTION_REQUESTED ke PM divisi
    A-->>K: 201 CorrectionOut
    W->>A: POST /work-plans/corrections/:id/decision (APPROVE)
    A->>D: MANAGE, status REQUESTED (409)
    A->>D: REVISING, jadwal ONGOING
    A->>N: CORRECTION_DECIDED ke ketua
    K->>A: PATCH progres dan POST /work-plans/daily/:id/report
    A->>D: jadwal ONGOING, laporan diperbarui
    K->>A: POST /work-plans/corrections/:id/submit
    A->>D: LEADER, status REVISING (409), laporan ada (422 REPORT_REQUIRED)
    A->>D: IN_REVIEW, revisi naik
    W->>A: POST /work-plans/corrections/:id/decision (ACCEPT atau RETURN)
    A->>D: MANAGE, status IN_REVIEW (409)
    alt ACCEPT
        A->>D: ACCEPTED, jadwal COMPLETED
    else RETURN
        A->>D: REVISING, ketua revisi lagi
    end
    A->>N: CORRECTION_DECIDED ke ketua
```

Referensi: `api/app/modules/work_plans/routes/daily_correction_route.py:33-64`; `api/app/modules/work_plans/services/daily_correction_service.py:37-115`.

## 3.7 Lembur

```mermaid
sequenceDiagram
    autonumber
    participant K as HP Anggota atau Ketua
    participant A as API
    participant D as DB
    participant W as Web PM
    participant N as Notifikasi
    K->>A: POST /overtime (daily_plan_id, hours, reason)
    A->>D: TEAM, jadwal ONGOING (409)
    A->>D: jam lebih dari 0 dan paling banyak 12 (422), alasan wajib (422)
    A->>D: tidak ada pengajuan PENDING_PM untuk jadwal ini (409)
    A->>D: insert PENDING_PM
    A-->>K: 201 OvertimeResponse
    W->>A: POST /overtime/:id/review (decision, note)
    A->>D: status PENDING_PM (409)
    alt jadwal ada
        A->>D: MANAGE (PM, OM divisi, SUPER_ADMIN) (403)
    else tanpa jadwal
        A->>D: hanya admin (403)
    end
    A->>D: pengaju tidak memutuskan sendiri (403)
    A->>D: keputusan APPROVED atau REJECTED
    A->>N: OVERTIME_DECIDED ke pengaju
    A-->>W: 200 OvertimeResponse
```

Referensi: `api/app/modules/overtime/routes/overtime_route.py:26-34,59-68`; `api/app/modules/overtime/services/overtime_service.py:50-93`. Rekap: `GET /recaps/overtime` (`overtime_service.py:111-116`).

## 3.8 Survei (isi, kirim, tinjau, buat rencana)

```mermaid
sequenceDiagram
    autonumber
    participant K as HP Ketua
    participant A as API
    participant D as DB
    participant S as MinIO
    participant W as Web PM
    K->>A: GET /work-plans/surveys/:id (LOGIN, relasi)
    A-->>K: 200 SurveyOut (state, can_edit)
    K->>A: POST /work-plans/surveys/:id/points (titik, foto slot)
    A->>D: LEADER, jadwal APPROVED atau ONGOING, survei DRAFT (409)
    A->>D: jenis titik untuk divisi survei, slot foto sesuai (422)
    A->>D: foto ada di berkas (422)
    A-->>K: 201 SurveyOut
    K->>A: PUT /work-plans/surveys/:id/report
    K->>A: POST /work-plans/surveys/:id/lines (material)
    K->>A: POST /work-plans/surveys/:id/submit
    A->>D: minimal 1 titik (422), foto slot lengkap (422 PHOTOS_REQUIRED)
    A->>D: item DONE (state SUBMITTED), log SURVEY_SUBMITTED
    A-->>K: 200 SurveyOut
    W->>A: GET /exports/surveys/:id/preview (PDF pratinjau)
    A->>D: survei harus dikirim (409 SURVEY_NOT_SUBMITTED bila DRAFT)
    A-->>W: berkas pratinjau
    W->>A: POST /work-plans/surveys/:id/review (APPROVE atau RETURN)
    A->>D: MANAGE, status SUBMITTED (409)
    alt APPROVE
        A->>D: approved_by_pm_id diisi, dependen SURVEY ikut DONE
    else RETURN
        A->>D: IN_PROGRESS, approver kosong
    end
    A-->>W: 200 SurveyOut
    W->>A: POST /work-plans/surveys/:id/plan (tanggal atau jadwal tujuan, jenis pekerjaan, titik)
    A->>D: status APPROVED (409 Setujui survei terlebih dahulu)
    A->>D: jadwal tujuan DRAFT atau SUBMITTED (409), divisi sama (422), tanggal tidak sebelum survei (422)
    A->>D: buat item pemasangan
    A-->>W: 201 PlanFromSurveyOut
    W->>A: POST /exports/surveys/:id (laporan .docx baku)
    A-->>W: berkas .docx
```

Referensi: `api/app/modules/work_plans/routes/survey_route.py:36-132`; `api/app/modules/work_plans/services/survey_service.py:76-99` (editable), `:208-270` (titik dan kirim), `:325-333` (tinjau), `:335-404` (rencana); `api/app/modules/exports/routes/export_route.py:47-56,85-93`.

## 3.9 Selesai, BAST tanda tangan, dan verifikasi publik

```mermaid
sequenceDiagram
    autonumber
    participant K as HP Ketua
    participant A as API
    participant D as DB
    participant S as MinIO
    participant W as Web PM
    participant P as Pemindai QR publik
    K->>A: POST /work-plans/daily/:id/complete
    A->>D: ketua atau MANAGE, status ONGOING (409), tanpa koreksi terbuka (409 CORRECTION_OPEN), tanpa pindah hari menunggu (409 ROLLOVER_PENDING), laporan ada (422)
    A->>D: SET COMPLETED (hasil dikunci)
    A-->>K: 200
    K->>A: GET /work-completions/:id (LOGIN, relasi tim)
    A-->>K: 200 detail order dengan foto dan ringkasan
    K->>A: POST /files/upload (foto realisasi)
    A->>S: simpan
    K->>A: POST /work-completions/:id/sign (signature PNG, ringkasan, foto, kendala)
    A->>D: peran TEAM_LEADER dan on_team (403)
    A->>D: pm_signed_at kosong (409 ORDER_LOCKED), ringkasan wajib (422)
    A->>D: foto gambar dan ada (422), PNG valid dan maks 300 KB (422)
    A->>S: simpan signatures/work-completion/:id/leader.png (503 bila gagal)
    A->>D: leader_signed_at, notifikasi PM divisi
    A-->>K: 200 WorkCompletionOut
    W->>A: POST /work-completions/:id/sign (signature PNG)
    A->>D: MANAGE (403), leader_signed_at wajib (409 LEADER_SIGNATURE_REQUIRED)
    A->>D: pm_signed_at kosong (409)
    A->>S: simpan pm.png
    A->>D: pm_signed_at, order_status COMPLETED, signature_hash SHA-256 dihitung ulang
    A-->>W: 200 WorkCompletionOut (terkunci)
    P->>A: GET /verify/work-completions/:id?h=sha256 (tanpa login)
    alt h bukan 64 heks atau tidak cocok
        A-->>P: 404 atau 422
    else cocok
        A->>D: ambil signature_hash dan berkas tanda tangan
        A->>S: baca berkas tanda tangan
        A->>A: hitung ulang sidik
        A-->>P: 200 intact true atau false
    end
```

Referensi: `api/app/modules/work_completion/routes/work_completion_route.py:147-158` (sign), `:276-283` (verify); `api/app/modules/work_completion/services/work_completion_service.py:274-336` (sign), `:338-357` (verify); `api/app/modules/work_completion/repositories/work_completion_sign_repository.py:16-50`; `api/app/modules/work_plans/services/daily_plan_service.py:257-269`. Catatan: `sign_order` tidak memeriksa `acc_status` (T10).

## 3.10 Ekspor dokumen

```mermaid
sequenceDiagram
    autonumber
    participant W as Web atau HP
    participant A as API
    participant D as DB
    participant S as MinIO
    W->>A: POST /exports/work-completions/:id (template BAST, SURVEY_REPORT, BAST_PDF, BOQ, PROGRESS_SLIDES, ORDER_SHEET)
    A->>D: get_order_detail (visibilitas, 404 bila tak terlihat)
    alt BAST_PDF tanpa signature_hash
        A-->>W: 409 NOT_SIGNED
    else SURVEY_REPORT tanpa item survei
        A-->>W: 422 NO_SURVEY_ITEMS
    else lanjut
        A->>A: bangun dokumen (docx, pdf, xlsx, atau pptx)
        A->>S: simpan exports/work-completion/:id/...
        A->>D: insert catatan ekspor (source WORK_COMPLETION)
        A-->>W: berkas unduhan
    end
    W->>A: GET /exports/:export_id/file
    A->>D: pemilik, admin, atau OM (404 Dokumen bila tidak)
    A->>S: baca berkas (404 FILE_GONE bila hilang dari penyimpanan)
    A-->>W: berkas
    W->>A: POST /exports/daily-report (docx, satu jadwal)
    A->>D: ketua atau anggota tim, atau PM/OM divisi (jadwal dirilis)
    A-->>W: berkas docx
    W->>A: POST /exports/team-week (pptx, 7 hari, dari web)
    A-->>W: berkas pptx
    W->>A: POST /exports/periodic (xlsx atau pptx, rentang tanggal)
    A->>D: CREATE_PLAN (403), rentang maks 31 hari (422)
    A->>S: simpan rekap periodik
    A-->>W: berkas
```

Referensi: `api/app/modules/exports/routes/export_route.py:36-44,105-146`; `api/app/modules/exports/services/export_service.py:66-72` (templat), `:225-238` (ekspor order), `:246-263` (periodik), `:268-290` (unduh). Survei: `:115-135`.

## 3.11 Referensi cepat (sumber endpoint di web)

| Aksi web | Service web (berkas) | Endpoint |
|---|---|---|
| Submit, approve, start, complete jadwal | `web/src/services/dailyPlanService.ts:90-107` | `/work-plans/daily/:id/:action` |
| Item progres, rollover | `web/src/services/planItemService.ts:168-180` | `/work-plans/items/:id/...` |
| Koreksi | `web/src/services/dailyPlanService.ts:182-187` | `/work-plans/corrections/...` |
| Survei | `web/src/services/surveyService.ts:24-148` | `/work-plans/surveys/...` |
| Order klien dan BAST | `web/src/services/workCompletionService.ts:88-285` | `/work-completions/...` |
| Lembur | `web/src/services/overtimeService.ts:9-19` | `/overtime`, `/overtime/:id/review` |
| Verifikasi publik | `web/src/services/exportService.ts:79` | `/verify/work-completions/:id?h=` |
