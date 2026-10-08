# Rencana Kerja v3: panduan implementasi langkah demi langkah

> Ditulis 2026-10-08 untuk dikerjakan model hemat token. Target peluncuran **Sabtu 2026-10-10**.
> Branch: `feature/rencana-kerja-v3` di worktree `C:\Users\ageng\visiontect-vms\vms-update`.
> **Tidak boleh di-merge** ke `development` atau `prod` sebelum pemilik menyetujui hasil tinjauan lokalnya.

---

## 0. Untuk model pelaksana: baca bagian ini dulu

### 0.1 Aturan mutlak (melanggar salah satunya = berhenti, lapor ke pemilik)
1. **Subagent DILARANG.** Kerjakan sendiri dengan Read, Grep, Bash, dan Edit.
2. **Jangan menebak.** Kalau ragu, pakai `AskUserQuestion` dengan pilihan + rekomendasi. Pertanyaan yang sudah diketahui ada di §0.4.
3. **Prod tidak disentuh.** Jangan SSH dan jangan merge ke `prod` atau `development`. Push hanya ke branch `feature/rencana-kerja-v3`.
4. **Migrasi yang sudah ada (0001–0025) tidak diubah.** Perubahan skema = berkas migrasi baru plus `db/*.sql` yang disamakan di commit yang sama.
5. **Pagar RLS untuk setiap tabel baru:**
   - `GRANT SELECT, INSERT, UPDATE[, DELETE] ON vms.<t> TO vms_api;`
   - `ALTER TABLE vms.<t> ENABLE ROW LEVEL SECURITY;`
   - `CREATE POLICY <t>_isolation ON vms.<t> USING (organization_id = vms.current_org_id());`
   - Setiap fungsi baru memakai `SECURITY DEFINER SET search_path = vms, public` dan **memfilter `organization_id = vms.current_org_id()` sendiri**, karena definer melewati RLS.
   - **Satu perintah SQL per `op.execute(...)`**, karena asyncpg menolak multi-perintah.
   - Contoh pola: `api/alembic/versions/0025_rls_remaining_tables.py`. Penjaganya: `api/tests/test_rls_app_role.py`.
6. **Tiga aturan produk:**
   - kewenangan mengikuti versi dokumen rencana kerja yang berlaku;
   - dokumen terbit tidak pernah diubah (perubahan = versi baru);
   - jarak dan waktu absen dihitung server.
7. **Lapisan backend:** endpoint → service → crud. Endpoint tidak menyentuh DB, service tidak menulis SQL. Respons selalu lewat skema `<Entitas>In/Out`. Pesan galat `AppError(code, "Bahasa Indonesia")`.
8. **Rahasia tidak pernah dicetak.** Ini termasuk isi `api/.env` (hanya nama kuncinya yang boleh), sandi, dan token.
9. **Matikan server dan emulator yang Anda nyalakan** setelah selesai uji.
10. Suite uji **baru tidak ditulis** sekarang (keputusan pemilik). Yang wajib: lint, tipe, uji migrasi naik-turun, dan E2E lokal manual dengan bukti tangkapan layar.

### 0.2 Cara hemat token
- Rencana ini **sudah memuat nama berkas dan baris**. Jangan menjelajah ulang kode.
- Jangan membaca berkas >300 baris utuh. Pakai `grep -n "<kata>" <berkas>`, lalu `sed -n 'A,Bp' <berkas>`.
- Jangan menjalankan suite penuh tiap tugas. Cukup lint + tipe + uji yang namanya relevan (`pytest tests/test_<x>.py -q`). Suite penuh hanya di T11.
- Selesai satu tugas: centang di §1, commit, lanjut. Sesi baru cukup membaca §0, §1, dan tugas berikutnya.

### 0.3 Lingkungan lokal (sudah ada, jangan dibuat ulang)
| Komponen | Cara |
|---|---|
| Docker Desktop | Harus menyala. Bila mati, uji DB-nyata **diam-diam di-skip**. `docker.exe` ada di `C:\Users\ageng\AppData\Local\Programs\DockerDesktop\resources\bin` |
| DB uji | Kontainer `vms_db_test_local18`, port 55434, DB `vms_test`. Nyalakan: `docker start vms_db_test_local18` |
| MinIO lokal | Port 9100. Cari namanya dengan `docker ps -a --format '{{.Names}} {{.Ports}}'`, lalu `docker start <nama>` |
| Migrasi | `cd api && .venv/Scripts/python.exe -m alembic upgrade head` |
| Uji migrasi | `... alembic upgrade head` → `... alembic downgrade -1` → `... alembic upgrade head` (semua harus sukses) |
| API :8000 | Bash **latar** dari `vms-update/api`: `.venv/Scripts/python.exe -m uvicorn app.main:app --env-file .env --host 127.0.0.1 --port 8000 --reload --reload-dir app`. **Jangan** `preview_start api-lokal`, karena itu menjalankan repo lama |
| Web :5173 | `preview_start` dengan `name: "web-update"` (sudah ada di launch.json, menjalankan `vms-update/web`) |
| Emulator | Pengguna menjalankan `scripts\jalankan-emulator.bat`. Aplikasi debug memakai `http://10.0.2.2:8000` |
| Flutter / adb | `C:/Users/ageng/flutter/bin/flutter.bat`, `$LOCALAPPDATA/Android/Sdk/platform-tools/adb.exe` (tidak ada di PATH Bash) |
| Lint API | `cd api && .venv/Scripts/python.exe -m ruff check app && .venv/Scripts/python.exe -m mypy app` |
| Lint web | `cd web && npm run lint && npm run typecheck` (uji teks: `npm test`) |
| Lint HP | `cd mobile && C:/Users/ageng/flutter/bin/flutter.bat analyze` |
| Akun uji | Ada di DB lokal. Jangan mereset sandi akun yang ada. Bila perlu login dan sandinya tidak diketahui, tanyakan pemilik. Perintah seed ada di `api/app/cli.py` |

`api/.env` lokal sudah punya `FACE_ENROLLMENT_REQUIRED`. Ubah nilainya menjadi `true` hanya di lokal (T3).

### 0.4 Pertanyaan untuk pemilik: ajukan SEKALI di awal T0, dalam satu `AskUserQuestion`
1. **Nomor dokumen.** Nomor lama berawalan `SK-`. Pilihan:
   - (Rek.) nomor baru berawalan `RK-`, nomor lama tetap;
   - semua tetap `SK-`.
2. **Revisi PM sebelum ketua menerima** (status Terbit / Revisi diminta). Pilihan:
   - (Rek.) versi baru terbit dan **ketua tetap harus menerima** rencana kerja itu sekali;
   - langsung dianggap diterima.
   *Setelah ketua menerima, revisi PM berlaku langsung tanpa TTD ketua. Ini sudah keputusan pemilik.*
3. **Penolakan absen tanpa wajah di prod.** Pilihan:
   - (Rek.) dikunci ke `FACE_ENROLLMENT_REQUIRED`. Lokal/beta `true`; prod tetap `false` sampai face-service terpasang di server, karena kalau tidak, semua pekerja lapangan terkunci;
   - selalu ditolak.
4. **Absen pulang di luar radius.** Pilihan:
   - (Rek.) absen tetap tertutup tetapi ditandai **Perlu review** untuk PM, sama seperti absen masuk;
   - hanya diberi tanda tanpa review.

Catat jawabannya di `docs/10-KEPUTUSAN-TERKUNCI-DAN-RISIKO.md` Bagian C, lalu ikuti di tugas terkait.

---

## 1. Papan status (perbarui setiap tugas selesai)

| # | Tugas | Status |
|---|---|---|
| T0 | Persiapan & pertanyaan pemilik | ☑ |
| T1 | APK beta (lebih dulu, supaya pemilik bisa menguji HP sejak awal) | ☑ (build & paket terverifikasi; uji pasang+login di HP menunggu perangkat) |
| T2 | Bug: permintaan revisi dari ketua tidak terlihat oleh PM | ☐ |
| T3 | Bug: absen tanpa wajah terdaftar | ☐ |
| T4 | Istilah SK → Rencana Kerja, Adendum → Revisi (teks UI saja) | ☐ |
| T5 | Aturan rencana kerja: anggota opsional, 1 hari, luar kota (migrasi 0026) | ☐ |
| T6 | Revisi oleh PM kapan saja + riwayat/diff (migrasi 0027) | ☐ |
| T7 | Absen pulang di luar radius + kategori dalam/luar kota (migrasi 0028) | ☐ |
| T8 | Realtime SSE web + HP + notifikasi deskriptif | ☐ |
| T9 | Jenis pekerjaan + template foto + kamera/galeri (migrasi 0029) | ☐ |
| T10 | Album "Visiontech" di galeri HP + galeri dalam aplikasi | ☐ |
| T11 | Verifikasi akhir, CHANGELOG, laporan ke pemilik | ☐ |

Kalau waktu habis, T9 dan T10 yang digeser. Laporkan ke pemilik **lebih awal**, jangan diam-diam.

---

## T0. Persiapan
1. `git -C C:/Users/ageng/visiontect-vms/vms-update branch --show-current` harus `feature/rencana-kerja-v3`. Kalau tidak, berhenti dan tanyakan.
2. `git status --short` harus bersih (berkas ini boleh muncul).
3. Nyalakan Docker, DB uji, dan MinIO (§0.3). Jalankan `alembic upgrade head`. Kepala saat ini `0025_rls_remaining_tables`.
4. Ajukan pertanyaan §0.4 dan catat jawabannya di docs/10 Bagian C.
5. Commit: `docs: rencana implementasi Rencana Kerja v3 + keputusan pemilik`.

---

## T1. APK beta untuk uji lokal
**Tujuan:** APK "Visiontech Beta" terpasang **berdampingan** dengan aplikasi prod, mengarah ke API laptop, tanpa pembaruan otomatis.

**Berkas:**
- `mobile/android/app/build.gradle.kts`: `applicationId` di baris 28; `buildTypes` di baris 52–62, dengan `manifestPlaceholders["usesCleartextTraffic"]`.
- `mobile/android/app/src/main/AndroidManifest.xml:15`: `android:label="Visiontech"` (literal).
- `mobile/lib/core/constants.dart:10`: `API_BASE_URL` (dart-define).
- `mobile/lib/features/update/app_update_controller.dart:18`: `UPDATE_CHANNEL`. Selain `portal`, pemeriksaan pembaruan mati (contoh `play`). Tambahkan nilai `beta` dengan perilaku yang sama seperti `play`: tidak memeriksa.
- `mobile/lib/shared/app_frame.dart`: tempat pita.
- `scripts/rilis-apk.sh`: contoh cara build dan tanda tangan. Baca bagian signing, jangan diubah.

**Langkah:**
1. Di `build.gradle.kts`, tepat di dalam `defaultConfig`, tambahkan:
   ```kotlin
   val beta = System.getenv("VMS_BETA") == "1"
   if (beta) applicationIdSuffix = ".beta"
   manifestPlaceholders["appLabel"] = if (beta) "Visiontech Beta" else "Visiontech"
   ```
   Lalu di `release {}`: kalau `beta`, set `manifestPlaceholders["usesCleartextTraffic"] = "true"`. Beta mengakses `http://` laptop.
2. Di manifest, ganti `android:label="Visiontech"` menjadi `android:label="${appLabel}"`.
3. Di `app_frame.dart`, bungkus anak dengan `Banner(message: 'BETA · uji lokal', location: BannerLocation.topEnd)` bila `const bool.fromEnvironment('VMS_BETA')`.
4. Buat `scripts/bangun-beta.sh` (bash UCRT64):
   - `adb reverse tcp:8000 tcp:8000`, supaya HP USB memakai `http://127.0.0.1:8000` tanpa urusan firewall/LAN;
   - `VMS_BETA=1 flutter build apk --release --dart-define=API_BASE_URL=http://127.0.0.1:8000 --dart-define=VMS_BETA=true --dart-define=UPDATE_CHANNEL=beta`;
   - salin ke `mobile/build/beta/visiontech-beta-$(date +%Y%m%d-%H%M).apk`, lalu `adb install -r <apk>`;
   - cetak jalur APK di akhir. Folder `build/` sudah diabaikan git; pastikan dengan `git check-ignore`.
   - Catatan: `adb reverse` hilang bila kabel dicabut, jadi skrip mencetak pengingat untuk menjalankannya ulang.
5. Uji: build sukses, `aapt dump badging` atau `adb shell pm list packages | grep vms_mobile` menampilkan `com.visiontech.vms_mobile.beta`, dan ikon berlabel "Visiontech Beta". Login ke API lokal berhasil.

**Selesai bila:** APK beta dan prod terpasang bersamaan, beta login ke API laptop, ada pita BETA, dan tidak ada dialog pembaruan.
**Commit:** `feat(mobile): APK beta .beta untuk uji lokal + skrip bangun-beta`.

---

## T2. Bug: permintaan revisi dari ketua tidak terlihat oleh PM
**Fakta yang sudah dipastikan** (dugaan di rencana lama keliru; jangan diulang):
- `/appeal` **sudah** mengirim notifikasi ke PM: `api/app/services/plan_transition_service.py:166-175` → `NotificationService.amendment_requested`.
- `/amendments` (saat Berjalan) juga sudah mengirimnya (`plan_amendment_service.py:68-91`).

**Peta alur saat ini:**
| Status rencana kerja | Tombol di HP ketua | Endpoint | Yang terlihat di web PM |
|---|---|---|---|
| PUBLISHED | "Ajukan adendum" (`work_plans_screen.dart:663-675` → `_requestAmendment`) | `POST /work-plans/{id}/appeal` (`vms_api.dart:65-71`) | Status APPEALED + kotak alasan (`WorkPlanDetailPage.tsx:143, 203-205`) |
| ACCEPTED | **tidak ada tombol** | — | — |
| IN_PROGRESS | `_runningAmendment` (`work_plans_screen.dart:326`) | `POST /work-plans/{id}/amendments` (`vms_api.dart:150`) | `AmendmentPanel` (`AmendmentPanel.tsx:42-70`), tombol hanya bila `PENDING_PM && IN_PROGRESS` |

**Hipotesis (uji berurutan; berhenti di yang terbukti):**
- **H1, notifikasi ke orang yang salah.** Lihat `crud_notification.py` fungsi `plan_people`: kolom apa yang menjadi `pm`? Kalau itu pembuat rencana kerja (bisa OPS/admin), PM unit tidak menerima apa-apa. Perbaikan: kirim ke PM pembuat **dan** semua PM unit rencana kerja itu (lihat cara unit/PM ditentukan di `prod-roles-hierarchy`: PM per unit).
- **H2, tidak ada penanda di daftar/beranda.** `HomePage.tsx:18` memasukkan APPEALED ke "menunggu", tetapi rencana kerja IN_PROGRESS dengan usulan `PENDING_PM` tidak ditandai di mana pun. PM baru tahu kalau membuka detailnya.
- **H3, data basi.** `AmendmentPanel` memakai `useQuery` tanpa invalidasi saat notifikasi masuk. PM yang sedang membuka halaman tidak melihat apa-apa sampai muat ulang. Ini tertutup oleh T8, tetapi catat.
- **H4, status ACCEPTED** tidak punya jalur sama sekali (lihat tabel). Ini tertutup oleh T6: PM merevisi kapan saja, dan ketua bisa mengajukan permintaan di status apa pun.

**Langkah:**
1. Reproduksi E2E lokal:
   - ketua (APK beta/emulator) mengajukan dari PUBLISHED dan dari IN_PROGRESS;
   - PM login di web :5173, cek lonceng, beranda, daftar, dan detail;
   - cek DB: `SELECT recipient_user_id, kind, title FROM vms.notification ORDER BY created_at DESC LIMIT 5;` (lewat `docker exec ... psql`). Kolom penerima: lihat dengan `\d vms.notification`.
2. Perbaiki H1 bila terbukti.
3. Perbaiki H2 dengan field `pending_request` (bool) di `WorkPlanOut` daftar:
   - crud: `EXISTS (SELECT 1 FROM vms.plan_change WHERE work_plan_id = wp.id AND status = 'PENDING_PM')`, atau status `APPEALED`;
   - web: lencana "Perlu tindakan" di `WorkPlansPage.tsx` dan beranda PM.
4. Satukan ACCEPTED: tombol "Ajukan revisi" di HP muncul untuk ACCEPTED dan IN_PROGRESS, memakai `/amendments`.
   - `request_amendment` (`plan_amendment_service.py:79`) sekarang hanya IN_PROGRESS. Longgarkan menjadi `ACCEPTED, IN_PROGRESS`.
   - Cek `require_plan_status` menerima beberapa status; kalau tidak, cek manual.

**Selesai bila:** dari ketiga status, PM menerima notifikasi di lonceng, ada lencana di daftar/beranda, dan detail menampilkan permintaannya.
**Commit:** `fix: permintaan revisi ketua terlihat & ditandai untuk PM`.

---

## T3. Bug: absen tanpa wajah terdaftar
**Fakta:**
- `api/app/core/config.py:64`: `FACE_ENROLLMENT_REQUIRED: bool = False`.
- `api/app/services/face_service.py:154`: `enrollment_required = settings.FACE_ENROLLMENT_REQUIRED and not rows and not exempt_from_required`. **Pakai ulang** logika ini, jangan ditulis ulang. Baca baris 130–170 untuk nama fungsi publiknya.
- `attendance_session_service.py:157-176` (`apply_face`) meloloskan karyawan tanpa pendaftaran wajah. `check_in` ada di baris 83, `check_out` di baris 192.
- HP: `mobile/lib/features/face/face_enroll_gate.dart` hanya menutup akses bila server menyuruh.

**Langkah (ikuti jawaban pertanyaan #3):**
1. Di `check_in` dan `check_out`, sebelum menulis apa pun:
   - kalau channel `MOBILE` dan fungsi enrollment-required dari face_service bernilai benar untuk user ini, lempar `AppError("FACE_NOT_ENROLLED", "Daftarkan wajah Anda dulu di menu Profil sebelum absen.", status=409)`.
2. Jalur luring (`attendance_offline_service.py`):
   - event luring **tidak ditolak**, karena sudah terjadi;
   - tandai Perlu review dengan catatan "belum mendaftar wajah". Pakai `repo.flag_missing_face` seperti di `apply_face`.
3. HP: di `attendance_screen.dart`, tangani kode `FACE_NOT_ENROLLED` dengan dialog lalu buka layar pendaftaran wajah. Rutenya ada di `face_flow.dart` atau `shared/router.dart`; cari dengan `grep -n "enroll" mobile/lib/shared/router.dart`.
4. Set `FACE_ENROLLMENT_REQUIRED=true` di `api/.env` lokal (tanpa mencetak isi berkas). Restart API.

**Selesai bila:** akun lapangan tanpa wajah ditolak 409 dengan pesan di atas dan HP mengarahkan ke pendaftaran. Setelah mendaftar, akun itu bisa absen. Karyawan kantor dan yang dikecualikan tidak terpengaruh.
**Commit:** `fix(absen): tolak absen HP pekerja lapangan tanpa wajah terdaftar`.

---

## T4. Istilah: SK → Rencana Kerja, Adendum → Revisi (teks yang terlihat pengguna SAJA)
**Yang TIDAK diubah:**
- nama tabel, kolom, dan enum (`ADDENDUM`, `AMENDMENT`, `APPEALED`, …);
- rute API dan nama berkas/komponen/kelas/fungsi (mis. `SkPreviewDialog`, `sk_viewer_screen.dart`);
- `key`/`data-testid`;
- komentar dan docstring;
- nomor dokumen yang sudah terbit.

**Tabel ganti:**
| Lama | Baru |
|---|---|
| Surat Keputusan / SK | Rencana Kerja |
| SK (bila sempit, mis. tombol/lencana di HP) | RK |
| Adendum | Revisi |
| Ajukan adendum | Ajukan revisi |
| Adendum diminta (`labels.ts:10`, APPEALED) | Revisi diminta |
| Usulan adendum / Usulan perubahan SK | Permintaan revisi |
| Terima & ubah isi SK | Revisi rencana kerja |
| Tolak adendum | Tolak permintaan |
| dokumen adendum | dokumen revisi |

**Label versi dokumen:** `KIND_LABEL` di `api/app/services/pdf_service.py`:
- INITIAL_ORDER → "Rencana Kerja";
- REVISION, ADDENDUM, PERSONNEL_ADDENDUM → "Revisi ke-{N}", dengan N = nomor versi − 1.

**Langkah (per lapisan, commit per lapisan):**
1. **Web** (perkiraan 267 kemunculan "SK" + 47 "adendum"):
   - cari teks pengguna saja: `grep -rn '\bSK\b\|[Aa]dendum' web/src --include=*.tsx --include=*.ts | grep -v "^.*//"`;
   - `web/src/lib/labels.ts` dulu, lalu `features/work-plans/*`, `features/home/*`, dan `app/navigation.ts` (judul menu), `app/pageTitle.ts`;
   - perbarui uji teks di `web/src/test/*.test.tsx`, lalu `npm test`.
2. **HP** (62 + 24): string di `mobile/lib/**`. Cek panjang teks tombol di layar sempit; pakai "RK" bila meluap.
3. **API** (709 + 98, kebanyakan komentar, jadi abaikan komentar):
   - pesan `AppError`/`ValidationError`/`NotFoundError("SK")` → `NotFoundError("Rencana kerja")`;
   - judul/isi di `notification_service.py`;
   - template `api/app/templates/plan_document.html`, `report_document.html`, `final_report.html`, `bast.html`;
   - cari dengan: `grep -rn '"[^"]*\bSK\b[^"]*"\|"[^"]*[Aa]dendum[^"]*"' api/app --include=*.py`.
   - Uji API yang mencocokkan teks pesan **jangan diubah sekarang**. Catat namanya untuk T11.
4. Nomor dokumen baru: ikuti jawaban #1. Kalau `RK-`, cari fungsi pembuat nomor dengan `grep -n "'SK-\|SK-" db/02_functions.sql`, lalu ubah lewat migrasi **0026** (T5), bukan migrasi lama.

**Selesai bila:** tidak ada teks "SK"/"Adendum" yang terlihat di web, HP, PDF, dan notifikasi; `npm test` hijau; lint hijau.
**Commit:** `feat(istilah): SK → Rencana Kerja, Adendum → Revisi (web|mobile|api)` (tiga commit).

---

## T5. Aturan rencana kerja: anggota opsional, 1 hari, luar kota (migrasi 0026)
**Migrasi `api/alembic/versions/0026_rencana_kerja_rules.py`** (`down_revision = "0025_rls_remaining_tables"`):
- `ALTER TABLE vms.work_plan ADD COLUMN is_out_of_town boolean NOT NULL DEFAULT false`
- (bila jawaban #1 = RK-) ganti fungsi nomor. Salin definisi lengkap dari `db/02_functions.sql`, ubah prefiks, lalu `CREATE OR REPLACE`. Downgrade = definisi lama.
- Samakan `db/01_schema.sql` (kolom) dan `db/02_functions.sql`.

**Anggota opsional (ketua tetap wajib):**
- API: `plan_draft_service.py:180`, `plan_change_service.py:139`, dan `plan_transition_service.py:79-95` (`_check_members`, dipanggil saat publish). Hapus/longgarkan syarat "minimal 1 anggota", tetapi pertahankan syarat ketua.
- Web zod: `PlanEditorPage.tsx:45`, `PlanForms.tsx:84` dan `:288`, `PlanChanges.tsx:124`. Ubah `.min(1, ...)` pada members menjadi opsional.
- Cek trigger DB yang mungkin mewajibkan anggota: `grep -n "anggota\|member" db/02_functions.sql | grep -i "raise"`.

**Rencana kerja 1 hari:**
- Backend sudah mengizinkan (`plan_draft_service.py:154` menolak hanya bila `period_end < period_start`).
- Web editor: checkbox "Rencana kerja 1 hari". Kalau dicentang, `period_end = period_start` dan input tanggal selesai disembunyikan.
- Pastikan pembuatan hari/tugas dan laporan mingguan tidak galat untuk periode 1 hari. Uji lewat E2E.

**Luar kota:**
- Skema: tambah `is_out_of_town: bool = False` di skema masuk/keluar rencana kerja. Cari `class PlanDraftRequest` dan `class PlanDetailOut` di `api/app/schemas/`.
- crud draft/insert/update menulis kolom ini.
- Web editor: checkbox "Luar kota (uang absen luar kota)". Detail & daftar: lencana "Luar kota".
- HP: lencana "Luar kota" di kartu rencana kerja.

**Selesai bila:** migrasi naik-turun-naik sukses; rencana kerja 1 hari tanpa anggota bisa dibuat, diterbitkan, diterima, dan berjalan; centang luar kota tersimpan dan tampil.
**Commit:** `feat(rk): anggota opsional, rencana kerja 1 hari, tanda luar kota`.

---

## T6. Revisi oleh PM kapan saja + riwayat/diff (migrasi 0027), inti paket
**Keputusan pemilik:** PM merevisi kapan saja. Versi dokumen baru **langsung berlaku** dan ditandatangani PM otomatis. Ketua dan anggota mendapat notifikasi plus tampilan sebelum/sesudah. Ketua **tidak** menandatangani revisi. Untuk status sebelum diterima, ikuti jawaban #2.

**Kode yang dipakai ulang:**
- `plan_amendment_service.py:102-183` (`apply_amendment`) sudah melakukan hampir semuanya: ubah isi, buat dokumen versi baru, dan TTD PM lewat `signature_service.sign_latest_plan_document`. **Salin alurnya**, tetapi tanpa tahap `AWAITING_LEADER_ACCEPTANCE`. Versi baru langsung `EFFECTIVE` dan versi lama `SUPERSEDED`. Cari dengan `grep -n "EFFECTIVE\|SUPERSEDED\|AWAITING" api/app/services/plan_amendment_service.py api/app/crud/crud_plan_amendment.py`.
- Penjaga "hari yang sudah berlaporan tidak boleh diubah" ada di jalur apply. Pertahankan; cari dengan `grep -rn "berlaporan" api/app/services`.
- Editor web: rute `/work-plans/:id/amend/:changeId` → `PlanEditorPage` (`web/src/app/routes.tsx:70`). Tambahkan rute `/work-plans/:id/revise` dengan komponen yang sama dan mode "revise".

**Migrasi `0027_plan_revision.py`:**
- Tabel `vms.plan_revision`:
  - `id uuid PK default gen_random_uuid()`
  - `organization_id uuid NOT NULL`
  - `work_plan_id uuid NOT NULL REFERENCES vms.work_plan(id)`
  - `revision int NOT NULL`
  - `revised_by uuid` (employee)
  - `reason text NOT NULL`
  - `diff jsonb NOT NULL`
  - `resolved_change_id uuid NULL REFERENCES vms.plan_change(id)`
  - `created_at timestamptz NOT NULL DEFAULT now()`
  - `UNIQUE (work_plan_id, revision)`
- `GRANT SELECT, INSERT` ke vms_api, RLS tenant (pagar §0.1 #5).
- Samakan `db/01_schema.sql` dan `db/03_policies.sql`.

**Backend:**
- `api/app/crud/crud_plan_revision.py`: `insert_revision(...)`, `list_revisions(plan_id)`.
- `api/app/services/plan_revision_service.py`, kelas `PlanRevisionService`, method `revise_plan(access, data: PlanDraftRequest, reason: str, change_id: UUID | None)`:
  1. Status yang boleh: `PUBLISHED, APPEALED, ACCEPTED, IN_PROGRESS`. DRAFT memakai editor biasa. Status lain: `AppError("PLAN_NOT_REVISABLE", "Rencana kerja yang sudah selesai atau dibatalkan tidak bisa direvisi.", 409)`.
  2. `reason` wajib (422 "Alasan revisi wajib diisi.").
  3. Ambil **snapshot sebelum**: judul, deskripsi, periode, lokasi, ketua, anggota (nama), hari/tugas, `is_out_of_town`, jenis pekerjaan (T9).
  4. Terapkan perubahan memakai fungsi crud yang sama dengan `apply_amendment`.
  5. Ambil **snapshot sesudah**, lalu hitung `diff` = daftar `{field, label, before, after}` hanya untuk yang berbeda. Untuk anggota: `{added: [...], removed: [...]}`. Diff kosong → 422 "Tidak ada perubahan.".
  6. Buat dokumen versi baru → EFFECTIVE (atau menunggu terima bila PUBLISHED/APPEALED dan jawaban #2 = rekomendasi). TTD PM.
  7. Bila APPEALED → kembalikan ke PUBLISHED. Bila `change_id` diberikan (permintaan ketua `PENDING_PM`) → set status perubahan itu menjadi diterapkan. Pakai status yang sudah ada di enum `ChangeStatus`; jangan menambah enum. Isi `resolved_change_id`.
  8. Insert `plan_revision`.
  9. `NotificationService.plan_revised(plan_id, actor_name, diff, recipients)`. Penerima = ketua + anggota **lama dan baru** (gabungan, tanpa duplikat, tanpa PM itu sendiri).
- Kewenangan berpindah hari itu juga. Pastikan pemeriksaan "ketua menurut dokumen berlaku" (`crud_plan_access.py`) membaca versi terbaru. Cek dengan E2E: ketua lama kehilangan tombol ketua.
- Endpoint di `api/app/api/v1/endpoints/work_plan_revisions.py`, didaftarkan di `api/v1/router.py` (prefiks sama dengan `work_plan_amendments.py`):
  - `POST /work-plans/{id}/revisions` (PM unit/OPS; salin penjaga izin dari endpoint `PUT /amendments/{change_id}` di `work_plan_amendments.py:88`) → `PlanDetailOut`;
  - `GET /work-plans/{id}/revisions` (semua yang punya akses ke rencana kerja) → `list[PlanRevisionOut]`.
  - Jangan bentrok dengan `POST /revise` lama (`work_plan_transitions.py:203`); biarkan untuk APK lama.
- Skema `api/app/schemas/plan_revision.py`: `PlanRevisionIn` (draft + `reason` + `change_id?`) dan `PlanRevisionOut` (`revision, revised_by_name, reason, diff, created_at`).

**Web:**
- `WorkPlanDetailPage.tsx`: tombol "Revisi rencana kerja" untuk PM bila status ∈ {PUBLISHED, APPEALED, ACCEPTED, IN_PROGRESS} → `/work-plans/:id/revise`.
- `AmendmentPanel.tsx:62`: tombol "Terima & ubah isi SK" diarahkan ke `/work-plans/:id/revise?change=<id>`, dan syarat `plan.status === "IN_PROGRESS"` dilonggarkan ke ACCEPTED juga.
- `PlanEditorPage` mode revise: isi awal = data rencana kerja; field "Alasan revisi" wajib; kirim ke `POST /revisions`; sukses → kembali ke detail + toast.
- Komponen baru `features/work-plans/RevisionHistory.tsx` di detail: daftar revisi, tiap baris berisi `label: sebelum → sesudah`, anggota +/−.

**HP:**
- `vms_api.dart`: `planRevisions(planId)`.
- Layar baru `mobile/lib/features/plans/revision_history_screen.dart` (rute di `shared/router.dart`), tampilannya sama dengan versi web.
- Dari detail rencana kerja: tombol "Riwayat revisi". Notifikasi `PLAN_REVISED` membuka layar ini.

**Selesai bila (E2E):**
1. PM merevisi rencana kerja Berjalan dengan mengganti satu anggota dan memundurkan tanggal selesai. Hasilnya:
   - dokumen versi baru dengan TTD PM;
   - versi lama Tidak berlaku;
   - notifikasi ke anggota lama, anggota baru, dan ketua;
   - diff tampil di web dan HP.
2. PM mengganti ketua → ketua lama kehilangan tombol ketua di HP hari itu.
3. Mengubah hari yang sudah berlaporan → ditolak dengan pesan yang jelas.
4. Permintaan ketua `PENDING_PM` selesai otomatis setelah PM merevisi lewat tombolnya.

**Commit:** `feat(rk): revisi PM kapan saja + riwayat revisi (api|web|mobile)`.

---

## T7. Absen pulang di luar radius + kategori dalam/luar kota (migrasi 0028)
**Fakta:**
- `CheckOutRequest` (`api/app/schemas/attendance.py:69-76`) **sudah** menerima `location`, tetapi tidak disimpan. `check_out` (`attendance_session_service.py:192-213`) hanya memanggil `repo.close(session.id)`.
- Jarak absen masuk dihitung trigger DB. Cari dengan `grep -n "distance_m\|radius_m" db/02_functions.sql`; tiru polanya.

**Migrasi `0028_attendance_checkout_city.py`:**
- Kolom baru di `vms.attendance`:
  - `check_out_location geography(Point,4326) NULL`
  - `check_out_distance_m numeric NULL`
  - `check_out_selfie_file_id uuid NULL REFERENCES vms.file_object(id)`
  - `check_out_explanation text NULL`
  - `check_out_outside boolean NOT NULL DEFAULT false`
- Trigger `BEFORE UPDATE` (fungsi baru `vms.tg_attendance_checkout()`, `SECURITY DEFINER SET search_path = vms, public`). Saat `check_out_location` diisi:
  - hitung `ST_Distance` ke `site.location`;
  - bila lebih besar dari `radius_m`, set `check_out_outside = true`;
  - bila di luar radius tanpa `check_out_selfie_file_id` atau `check_out_explanation`, `RAISE` dengan pesan aturan yang sama gayanya dengan absen masuk, supaya `trigger_rule_message` (`attendance_session_service.py:150`) mengubahnya menjadi 422;
  - bila jawaban #4 = rekomendasi, set status Perlu review. Pakai nilai status yang sama dengan absen masuk di luar radius; cari di trigger absen masuk.
- Fungsi `vms.attendance_city_category(p_employee uuid, p_date date) RETURNS text`, `STABLE SECURITY DEFINER SET search_path = vms, public`:
  - mengembalikan `'LUAR_KOTA'` bila ada `work_plan` dengan `organization_id = vms.current_org_id()`, `is_out_of_town`, status ∈ (ACCEPTED, IN_PROGRESS, COMPLETION_REVIEW, COMPLETED), `p_date BETWEEN period_start AND period_end`, dan karyawan itu ketua atau anggotanya;
  - selain itu `'DALAM_KOTA'`;
  - join ketua/anggota: tiru `plan_people` di `crud_notification.py`.
  - Dihitung **saat dibaca**, jadi penugasan setelah absen otomatis mengubah kategori hari itu.
- Samakan `db/01_schema.sql` dan `db/02_functions.sql`.

**Backend:**
- `CheckOutRequest`: tambah `selfie_file_id: UUID | None = None`, `explanation: str | None = None`, `accuracy_m: float | None = None`. Untuk accuracy, tiru `CheckInRequest`.
- `check_out(...)` meneruskan lokasi, swafoto, dan penjelasan ke crud. `repo.close` diperluas (crud: `crud_attendance_session.py`) supaya mengisi kolom baru. Swafoto divalidasi milik org lewat pola `ensure_check_in_refs` (baris 65).
- Jalur luring `attendance_offline_service.py`: simpan lokasi pulang yang sama.
- Daftar absensi, rekap, dan CSV: tambahkan `city_category` (pilih `vms.attendance_city_category(a.employee_id, a.work_date)`) dan field pulang (`check_out_distance_m`, `check_out_outside`, `check_out_selfie_file_id`). CSV: kolom "Kategori" + "Jarak pulang (m)". Lihat `export_csv` di baris 69.

**HP (`mobile/lib/features/attendance/attendance_screen.dart`):**
- Alur pulang memakai ulang alur geofence + kamera absen masuk (`core/geofence_confirm.dart`, `core/photo_capture.dart`):
  - di luar radius → konfirmasi → swafoto → penjelasan → kirim;
  - **swafoto tidak masuk galeri HP**.
- Tampilkan lencana "Dalam kota"/"Luar kota" di kartu absen hari ini.

**Web:**
- `features/attendance/AttendancePage.tsx`: kolom Kategori, jarak pulang, tanda "Pulang di luar radius" + swafoto pulang di panel review.
- `features/monitoring/AttendanceRecapPage.tsx`: kolom Kategori.

**Selesai bila (E2E):**
1. Pulang di luar radius tanpa swafoto → ditolak dengan pesan jelas. Dengan swafoto dan penjelasan → tercatat dan tertanda (Perlu review sesuai #4).
2. Karyawan absen di kantor (kategori Dalam kota) → PM menugaskannya ke rencana kerja luar kota yang aktif hari itu → daftar absensi menampilkan Luar kota **tanpa** mengubah data absen.
3. CSV memuat kolom Kategori.

**Commit:** `feat(absen): pulang di luar radius wajib swafoto + kategori dalam/luar kota`.

---

## T8. Realtime SSE (web + HP) + notifikasi deskriptif
**Arsitektur:** satu endpoint SSE dengan broker di dalam proses. Prod menjalankan satu proses uvicorn; tulis batasan ini di docstring broker. Kalau nanti multi-worker, ganti ke Postgres LISTEN/NOTIFY.

**Backend:**
1. `api/app/core/events.py`:
   - kelas `EventBroker` berisi `dict[str, set[asyncio.Queue]]` per `user_id`, dengan method `subscribe(user_id)`, `unsubscribe(...)`, `publish(user_ids, event: dict)`;
   - antrean `maxsize=100`; kalau penuh, buang event lama;
   - fungsi `queue_event(db: AsyncSession, user_ids, topic: str, data: dict)` yang menambah ke `db.info.setdefault("pending_events", [])`.
2. **Publikasi hanya setelah commit.** Di `api/app/api/deps.py:85` (`get_db`), setelah `await db.commit()` sukses, kirim semua `db.info["pending_events"]` ke broker. Kalau rollback, buang. Cek juga `api/app/db/session.py:49-83` (jalur commit `persist=True`).
3. Sumber event:
   - `CRUDNotification.insert_many` (dipakai **semua** notifikasi): panggil `queue_event(db, recipients, "notification", {id?, kind, title, body, plan_id})`. Ini sudah mencakup sebagian besar perubahan.
   - Mutasi rencana kerja tanpa notifikasi (simpan draf, ubah hari, laporan disimpan): `queue_event(db, orang_terkait, "plan", {plan_id})`. Cukup di service yang mengubah status/isi.
   - Absensi: saat absen menjadi Perlu review, kirim `queue_event(..., "attendance", {})` ke PM unit; saat diputuskan, ke karyawannya.
4. Endpoint `api/app/api/v1/endpoints/events.py`, `GET /api/v1/events`, didaftarkan di router:
   - **Jangan memakai dependensi yang membuka sesi DB** (`get_db_with_user`), karena koneksi SSE berumur panjang dan akan menahan transaksi. Validasi token JWT saja, sekali saat terhubung. Cari fungsi decode token di `api/app/core/security.py` atau `deps.py`.
   - `StreamingResponse(media_type="text/event-stream")`, header `Cache-Control: no-cache`, `X-Accel-Buffering: no`.
   - Kirim `: ping\n\n` setiap 25 detik. Format event: `event: <topic>\ndata: <json>\n\n`.
   - Tutup aliran saat token kedaluwarsa (`exp`); klien menyambung ulang dengan token baru.
   - Periksa `api/tests/test_route_smoke.py`: uji asap tidak boleh menggantung di aliran. Daftarkan pengecualian atau pastikan tanpa token langsung 401.
5. Caddy prod butuh `flush_interval -1` untuk `/api/v1/events`. Caddyfile ada di server, jadi **pemilik** yang mengubahnya saat rilis; tulis di CHANGELOG bagian "Langkah rilis".

**Notifikasi deskriptif (`api/app/services/notification_service.py`):**
- Setiap method menerima `actor: str | None` (nama karyawan pelaku; service pemanggil mengirim nama user yang sedang login).
- Format judul: `<Pelaku> <kata kerja> <nomor RK>`. Isi: judul rencana kerja + rincian.
- Contoh:
  | Method | Judul | Isi |
  |---|---|---|
  | `plan_published` | "Ramadani menerbitkan RK-2026-014" | "Pemasangan CCTV Gudang A, 12–14 Okt. Anda ketua tim: tinjau lalu terima, atau ajukan revisi." |
  | `amendment_requested` | "Budi meminta revisi RK-2026-014" | "Alasan: tambah 1 hari untuk setting NVR." |
  | `plan_revised` (baru) | "Ramadani merevisi RK-2026-014" | Ringkasan diff, maksimal 3 butir. Contoh: "Tanggal selesai 12 → 14 Okt; anggota: +Andi, −Budi." |
  | `report_reviewed` | "Ramadani mengembalikan laporan 12 Okt" | "Catatan: foto panel kurang jelas." |
- Terapkan ke semua method yang ada (baris 48–173): `plan_published`, `amendment_requested`, `plan_accepted`, `plan_started`, `member_report_sent`, `report_submitted`, `report_reviewed`, `amendment_decided`, `amendment_accepted`, `completion_requested`, `completion_decided`.
- Tambah `plan_revised` dan `attendance_flagged` (ke PM: "Absen pulang Andi di luar radius (420 m)").

**Web:**
1. `web/src/lib/live-events.ts`, hook `useLiveEvents()`:
   - `fetch("/api/v1/events", {headers: {Authorization}})`. Token dan logika refresh diambil dari `web/src/lib/api.ts`; jangan menduplikasi.
   - Baca `response.body.getReader()`, parse per baris kosong.
   - Sambung ulang dengan jeda 1 → 2 → 5 → 15 → 30 detik. Pada 401, refresh token lalu sambung ulang.
2. Pasang hook sekali di layout yang memuat `NotificationBell.tsx` (`web/src/components/layout/`). Karena `components/` tidak boleh mengimpor `features/`, letakkan hook di `lib/` dan panggil dari layout.
3. Saat event:
   - `notification` → `invalidateQueries` kunci notifikasi (lihat `NotificationBell.tsx`) + toast berisi judul dan isi (pakai pustaka toast yang sudah dipakai; cari dengan `grep -rn "toast" web/src/lib web/src/components | head -3`);
   - `plan` → invalidasi kunci daftar dan detail rencana kerja (`features/work-plans/api.ts`);
   - `attendance` → kunci absensi.
4. Polling 60 detik di `NotificationBell.tsx:27` tetap ada sebagai cadangan.

**HP:**
1. Pustaka baru `flutter_local_notifications`. Catat di `docs/14-DAFTAR-PUSTAKA-TEKNOLOGI.md` dengan alasan "notifikasi sistem saat event SSE masuk; tanpa FCM". Izin `POST_NOTIFICATIONS` di manifest + permintaan saat runtime (Android 13+).
2. `mobile/lib/core/live_events.dart`:
   - `dio.get('/api/v1/events', options: Options(responseType: ResponseType.stream))` dengan token dari `core/token_storage.dart` / `api_client.dart`;
   - parse aliran, sambung ulang dengan jeda bertingkat;
   - putus saat `AppLifecycleState.paused`, sambung lagi saat `resumed`;
   - provider Riverpod di `core/providers.dart`.
3. Saat event:
   - `ref.invalidate(...)` provider notifikasi, daftar/detail rencana kerja, dan absensi (cari nama provider dengan `grep -rn "Provider" mobile/lib/features/<x>`);
   - untuk `notification`, tampilkan notifikasi sistem dengan judul/isi. Ketukan membuka rute rencana kerja (`plan_id`) atau riwayat revisi untuk `PLAN_REVISED`.
4. Batasan yang ditulis di CHANGELOG: notifikasi saat aplikasi **tertutup penuh** butuh FCM, di luar target Sabtu.

**Selesai bila (E2E, web dan HP terbuka bersamaan):** PM merevisi rencana kerja → dalam ≤ 3 detik, tanpa refresh:
- HP ketua menampilkan notifikasi Android berisi apa yang berubah;
- daftar dan detail di HP ikut segar;
- di web, PM lain melihat lonceng bertambah.

Tes juga putus koneksi: matikan dan nyalakan API, maka klien menyambung lagi sendiri.

**Commit:** `feat: realtime SSE + notifikasi deskriptif (api|web|mobile)`.

---

## T9. Jenis pekerjaan + template foto + foto laporan dari kamera/galeri (migrasi 0029)
**Keputusan pemilik:**
- PM mengelola jenis pekerjaan (mis. Replacement, Survei) dan menyusun template foto per jenis (label, petunjuk, wajib/tidak).
- Foto laporan boleh dari kamera bertanda air atau dari galeri.

**Migrasi `0029_work_type_photo.py`:**
- `vms.work_type`:
  - `id uuid PK`, `organization_id uuid NOT NULL`, `name text NOT NULL`, `is_active boolean NOT NULL DEFAULT true`, `created_at timestamptz DEFAULT now()`;
  - unik `(organization_id, lower(name))`.
- `vms.work_type_photo`:
  - `id uuid PK`, `organization_id uuid NOT NULL`;
  - `work_type_id uuid NOT NULL REFERENCES vms.work_type(id) ON DELETE CASCADE`;
  - `sort_order int NOT NULL`, `label text NOT NULL`, `hint text NULL`, `required boolean NOT NULL DEFAULT false`.
- `ALTER TABLE vms.work_plan ADD COLUMN work_type_id uuid NULL REFERENCES vms.work_type(id)`. Kolom `category` lama tetap.
- `ALTER TABLE vms.report_evidence` dan `vms.member_report_evidence` (`db/01_schema.sql:290, 310`): tambah `slot_label text NULL` dan `source text NOT NULL DEFAULT 'CAMERA' CHECK (source IN ('CAMERA','GALLERY'))`.
- GRANT `SELECT, INSERT, UPDATE, DELETE` (dua tabel baru) + RLS tenant.
- Samakan `db/01_schema.sql` dan `db/03_policies.sql`.

**Backend:**
- `crud/crud_work_type.py`, `services/work_type_service.py`, `schemas/work_type.py` (`WorkTypeIn`, `WorkTypeOut`, `WorkTypePhotoIn/Out`), `endpoints/work_types.py`:
  - `GET /work-types` (semua yang login, hanya yang aktif kecuali `?all=true` untuk PM);
  - `POST /work-types`, `PUT /work-types/{id}` (ganti seluruh daftar foto), `DELETE /work-types/{id}` (nonaktifkan, bukan hapus) untuk PM/OPS. Penjaga izin: tiru `endpoints/sites.py`.
- Rencana kerja: `work_type_id` di skema masuk/keluar. Detail menyertakan `photo_template: list[WorkTypePhotoOut]`.
- Bukti laporan: endpoint yang melampirkan foto laporan harian (ketua: `work_plan_days.py`/`crud_plan_day.py`; anggota: `member_report_service.py`; cari dengan `grep -n "evidence" ...`) menerima `slot_label` dan `source`.
- Saat laporan **dikirim**, server memeriksa setiap slot `required` dari template punya ≥ 1 foto dengan `slot_label` itu. Kalau tidak: 422 "Foto wajib belum lengkap: <label>.".

**Web:**
- Halaman baru `features/work-types/WorkTypesPage.tsx`, rute `/work-types`, menu untuk PM/OPS di `app/navigation.ts`:
  - daftar jenis; dialog tambah/ubah berisi nama + daftar slot (label, petunjuk, wajib) dengan urutan naik/turun;
  - form react-hook-form + zod; 4 keadaan layar.
- Editor rencana kerja: select "Jenis pekerjaan" (opsional).
- `DailyReports.tsx`: kelompokkan foto per `slot_label`, beri lencana "Dari galeri" untuk `source = GALLERY`.

**HP (`mobile/lib/features/plans/plan_day_screen.dart`; kamera saat ini di baris 106, 199, 579):**
- Pustaka baru `image_picker` (Flutter resmi). Catat di `docs/14` dengan alasan "memilih foto laporan dari galeri".
- Bagian foto laporan:
  - satu kartu per slot template (label, petunjuk, tanda wajib) + bagian "Foto lain";
  - tiap kartu punya tombol **Kamera** (`captureWatermarkedPhoto` dari `core/photo_capture.dart`, tidak diubah) dan **Galeri** (`ImagePicker().pickImage(source: ImageSource.gallery)`);
  - foto galeri diunggah apa adanya (server yang mengompresi) dengan `source: 'GALLERY'`.
- Tombol kirim dinonaktifkan sampai slot wajib terisi. Server tetap memeriksa.

**Selesai bila (E2E):**
1. PM membuat jenis "Replacement" dengan 3 slot (2 wajib) → membuat rencana kerja dengan jenis itu.
2. Anggota di HP beta melihat 3 slot, mengisi satu dari kamera (bertanda air) dan satu dari galeri.
3. Kirim ditolak bila slot wajib kosong; setelah lengkap, laporan terkirim.
4. Web menampilkan foto per slot dengan lencana "Dari galeri".

**Commit:** `feat: jenis pekerjaan + template foto + foto laporan dari galeri (api|web|mobile)`.

---

## T10. Album "Visiontech" di galeri HP + galeri dalam aplikasi
**Keputusan pemilik:** foto laporan dari kamera aplikasi juga muncul di galeri HP (album "Visiontech"). Swafoto absen **tetap privat**.

**Langkah:**
1. Kotlin `mobile/android/app/src/main/kotlin/com/visiontech/vms_mobile/GallerySave.kt`:
   - MethodChannel `vms/gallery`, method `saveImage(path)`;
   - pakai `MediaStore.Images.Media` dengan `RELATIVE_PATH = "Pictures/Visiontech"` dan `IS_PENDING` (API 29+);
   - untuk API < 29, tulis ke `Environment.DIRECTORY_PICTURES/Visiontech` lalu `MediaScannerConnection.scanFile`. Cek `minSdk` (`flutter.minSdkVersion`); kalau < 29, perlu izin `WRITE_EXTERNAL_STORAGE` dengan `maxSdkVersion="28"`.
   - Daftarkan di `MainActivity.kt` seperti `AppUpdate.kt`.
2. Dart `mobile/lib/core/gallery_save.dart`: `Future<void> saveToPhoneGallery(String path)`. Galat **tidak** menggagalkan laporan; cukup dicatat.
3. Panggil hanya setelah foto **laporan harian** dari kamera tersimpan (`plan_day_screen.dart`). Jangan dipanggil untuk swafoto absen.
4. Layar `mobile/lib/features/gallery/photo_gallery_screen.dart`:
   - grid foto dari folder lokal `LocalFileKind.dailyReport` (`core/local_storage.dart`), urut terbaru;
   - ketuk untuk pratinjau;
   - mode pilih (dibuka dari slot laporan) mengembalikan jalur berkas untuk dilampirkan (`source: 'CAMERA'`, karena aslinya dari kamera aplikasi);
   - akses dari Profil ("Galeri foto saya") dan dari tombol ketiga di tiap slot laporan.

**Selesai bila:** foto laporan dari kamera muncul di aplikasi Galeri/Foto HP di album "Visiontech", swafoto tidak muncul, dan galeri dalam aplikasi bisa memilih foto lama untuk dilampirkan.
**Commit:** `feat(mobile): album Visiontech di galeri HP + galeri foto dalam aplikasi`.

---

## T11. Verifikasi akhir & serah ke pemilik
1. Lint/tipe semua lapisan (§0.3). Migrasi naik-turun-naik dari 0025 ke 0029.
2. Suite lama:
   - `cd api && .venv/Scripts/python.exe -m pytest -q`, dengan Docker menyala supaya uji DB tidak di-skip;
   - `cd web && npm test`.
   Kegagalan karena **perubahan aturan yang disengaja** (teks SK/Adendum, anggota opsional, wajah wajib) dicatat dalam daftar dan **tidak diperbaiki diam-diam**: ujinya diperbarui setelah pemilik setuju. Kegagalan lain = bug, jadi diperbaiki.
3. E2E lengkap sekali lagi (8 alur), dengan tangkapan layar web dan HP:
   1. ketua minta revisi → PM mendapat notifikasi realtime;
   2. PM merevisi saat berjalan dengan mengganti anggota → dokumen baru dengan TTD PM, diff, kewenangan pindah;
   3. absen tanpa wajah ditolak;
   4. pulang di luar radius minta swafoto;
   5. absen kantor lalu ditugaskan ke rencana kerja luar kota → kategori Luar kota;
   6. laporan dengan slot template, kamera dan galeri → album "Visiontech";
   7. rencana kerja 1 hari tanpa anggota;
   8. web dan HP bersamaan: perubahan muncul tanpa refresh + notifikasi Android.
4. `CHANGELOG.md`: ringkasan v3 + bagian **"Langkah rilis (oleh pemilik)"**:
   - migrasi 0026–0029;
   - Caddy `flush_interval -1` untuk `/api/v1/events`;
   - `FACE_ENROLLMENT_REQUIRED` tetap `false` di prod sampai face-service terpasang (bila jawaban #3 = rekomendasi);
   - APK baru via `rilis-apk`.
5. Catat keputusan baru di `docs/10` Bagian C.
6. Periksa rahasia di commit yang belum di-push (`git diff origin/feature/rencana-kerja-v3..HEAD | grep -iE "password|secret|key_hex|token"`), lalu push branch ini saja.
7. Matikan API, web, dan emulator yang Anda nyalakan.
8. Laporkan ke pemilik:
   - apa yang selesai, apa yang tergeser, dan daftar uji lama yang perlu diperbarui;
   - cara memasang APK beta (`bash scripts/bangun-beta.sh`).
   - **Jangan merge.**
