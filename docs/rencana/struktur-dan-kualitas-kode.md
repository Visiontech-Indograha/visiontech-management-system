# Rencana: struktur dan kualitas kode (web dan mobile)

Status: USULAN (rencana, belum dikerjakan). Dasar: `origin/development` 92fa113b, VERSION 1.8.4, tanggal 2026-11-11.
Sumber: riset 23 referensi (W1-W11 web, M1-M12 mobile; tautan ada di bagian Lampiran), audit UI/UX, backlog temuan, brief gelombang, `web/CLAUDE.md`, `mobile/CLAUDE.md`.
Hanya dokumen. Tidak ada kode yang diubah oleh rencana ini. Semua angka batas (300/500 baris dst.) adalah usulan, bukan kutipan sumber.

Format tiap rekomendasi: Apa / Mengapa (alasan + rujukan) / Bukti di VMS (file:baris) / Penegakan / Risiko regresi / Ukuran.

## 0. Prinsip

1. Satu sumber kebenaran. Satu komponen per konsep UI, satu klien API per platform, satu berkas token warna, satu glosarium istilah. Dua jalur untuk satu hal = pasti melenceng (M2, W6).
2. Colocation. Tes, gaya, dan pembantu diletakkan di samping kode yang dipakainya (W5, M3).
3. Batas modul eksplisit dan ditegakkan mesin. Aturan yang hanya ada di dokumen akan dilanggar; aturan di lint/tes/CI tidak (W11, W2, M6).
4. Perubahan kecil dan bisa dibalik. Satu PR = satu langkah mekanis atau satu pemecahan, tanpa campur perubahan perilaku. Penjagaan baru masuk sebagai peringatan + baseline dulu, baru jadi galat setelah dibersihkan.
5. Tidak ada pindah besar-besaran (big-bang). Atomic design di web dipertahankan (524 berkas, sudah dijaga lint); yang diperbaiki adalah celahnya.
6. Tidak bentrok dengan paket lain: lihat tabel titik aman di bagian 4.

## 1. Konvensi target WEB

### 1.1 Struktur folder (tetap atomic design)
- Apa: `components/{atoms,molecules,organisms,templates}`; organisme dan template dikelompokkan per domain (`organisms/<domain>/`); `pages/<domain>/`, `services/<domain>Service.ts`, `schemas/<domain>Schema.ts`, `hooks/use<Nama>.ts`, `lib/<nama>.ts`, `stores/` hanya `sessionStore`. Atom dan molekul generik (tanpa nama domain).
- Mengapa: struktur sudah dipakai luas dan dijaga lint; pindah ke fitur-first (W1) atau FSD (W2) mahal dan tidak menambah penegakan. Dipakai dari W1/W2 hanya aturan "satu arah" dan "domain tidak saling impor".
- Bukti: aturan lapisan sudah kuat di `web/eslint.config.js:12` (PAGES), `:14` (DATA), `:26` (HTTP hanya di services), `:106-115` (larangan arah impor). `find web/src -name index.ts*` = 0 (sesuai W8).
- Penegakan: sudah ada; ditambah 1.3.
- Risiko: nol (tidak ada pemindahan).
- Ukuran: 0 hari.

### 1.2 Penamaan
| Jenis | Aturan | Contoh |
|---|---|---|
| Komponen | `PascalCase.tsx`, satu komponen utama per berkas, named export | `LeaveApplyDialog.tsx` |
| Hook | `useXxx.ts` (`.tsx` bila memuat JSX) | `useListControls.ts` |
| Service | `<domain>Service.ts` + `<domain>Keys` (query key factory) | `leaveService.ts` |
| Schema | `<domain>Schema.ts` (tunggal) | `accountSchema.ts` |
| Tes | `Nama.test.tsx` di samping berkas; variasi `Nama.<topik>.test.tsx` | `teamService.logo.test.tsx` |
| Dialog | akhiran `Dialog` untuk SEMUA pop-up (konfirmasi dan form). `*Modal` baru dilarang | `AllocateDialog` |
| Lib/util | camelCase, satu topik per berkas | `errors.ts` |
- Mengapa: penamaan seragam membuat pencarian berkas dan aturan lint berbasis glob andal (W10). Satu akhiran untuk satu konsep.
- Bukti: schema campuran jamak/tunggal di `web/src/schemas/` (`accountSchemas.ts` vs `loginSchema.ts`, `setupSchema.ts`); dialog campur: `WorkOrderBastModal`, `ClientSitesModal`, `ImageLightboxModal` (`organisms/media/ImageLightboxModal.tsx`) vs `AllocateDialog`, `LeaveApplyDialog`; 37 service sudah konsisten `*Service.ts` (baik).
- Penegakan: tes arsitektur Vitest (glob nama berkas) dengan daftar baseline; berkas baru yang melanggar gagal. Ganti nama lama dilakukan oleh Fase 1, bukan sekaligus.
- Risiko: rendah (ganti nama + perbarui impor, tsc menangkap sisa). Git rename dijaga dengan PR terpisah dari perubahan isi.
- Ukuran: tes penjaga 0.5 hari; ganti nama bertahap dalam Fase 1.

### 1.3 Aturan impor (eslint-plugin-boundaries)
- Apa: pakai `eslint-plugin-boundaries` yang sudah terpasang. Elemen: `atoms|molecules|organisms|templates|pages|services|hooks|lib|stores|schemas|app`. Aturan baru: (a) `organisms/<domainA>` tidak impor `organisms/<domainB>` (kecuali daftar putih molekul/atom); (b) `lib/` dan `stores/` tidak impor `app/` selain berkas bertanda mock; (c) `import/no-cycle` sebagai peringatan; (d) larang berkas `index.ts` (barrel) lewat `no-restricted-imports`. Konfigurasi mulai `warn` + baseline, jadi `error` setelah bersih.
- Mengapa: W11 (alat), W1 (fitur tak saling impor), W2 (arah impor satu arah), W8 (tanpa barrel: modul lebih sedikit dimuat Vite). Dependensi sudah dibayar tetapi tak terpakai.
- Bukti: `web/package.json:56` memasang plugin; `grep boundaries web/eslint.config.js` = 0 hasil. `web/src/stores/sessionStore.ts:12` mengimpor `../app/mockSession` (lihat butir verifikasi V1).
- Penegakan: `npm run lint` (sudah di `verify.sh web` dan CI). Baseline = berkas daftar pelanggaran yang diterima; hanya boleh menyusut (pola sama dengan `KNOWN` di `api/tests/architecture/test_sql_rules.py`).
- Risiko: rendah-sedang. Salah konfigurasi menghasilkan banyak peringatan palsu; mulai `warn` agar build tidak patah. Pilihan cadangan bila plugin terlalu rewel: hapus dependensi tak terpakai (keputusan tetap tertulis).
- Ukuran: 1-1.5 hari.

### 1.4 Batas ukuran berkas dan fungsi
- Apa: ESLint `max-lines` (skipBlankLines, skipComments) `.tsx` komponen: peringatan 300, galat 500; `max-lines-per-function` peringatan 80; `complexity` peringatan 12. Berkas yang sudah melebihi masuk baseline `eslint-suppressions`/daftar tutup, hanya boleh menyusut. `apiTypes.ts` (dibangkitkan) dikecualikan.
- Mengapa: berkas kecil = review cepat dan konflik merge sedikit (W5 colocation memudahkan memecah; W6 state kecil dan terpusat). Angka adalah usulan.
- Bukti: 13 `.tsx` di `components/` > 300 baris. Terbesar: `organisms/work-orders/WorkOrderSurveyReviewModal.tsx` 667, `organisms/hse/HseCampaignsPanel.tsx` 642, `organisms/attendance/OfficeCheckInCard.tsx` 555. Tidak ada `max-lines`/`complexity` di `web/eslint.config.js`.
- Penegakan: lint (warn dulu); metrik dihitung skrip (bagian 6).
- Risiko: rendah untuk aturan; sedang untuk pemecahan (lihat Fase 2).
- Ukuran: aturan 0.5 hari; pemecahan 13 berkas ~4-5 hari (opsional, bertahap, bukan prasyarat).

### 1.5 Satu jalur dialog, satu jalur notifikasi
- Apa: `molecules/VmsDialog` = kanonik. `molecules/Modal.tsx` (alias ke `atoms/Dialog`) dan pemakaian langsung `atoms/Dialog` dideprecate: tandai `@deprecated`, lint `no-restricted-imports` untuk impor baru, migrasi pemakai lama bertahap, lalu hapus. `Notice` (alias `atoms/Alert`) dan `RetryNotice` digabung menjadi satu `Notice` dengan varian (`info|sukses|peringatan|galat`) + opsi aksi "Coba lagi".
- Mengapa: tiga jalur untuk satu konsep membuat perilaku fokus/ESC/ukuran berbeda dan menggandakan perbaikan (M2 satu sumber kebenaran; UX-4 audit).
- Bukti: `VmsDialog` diimpor 62 kali; `molecules/Modal.tsx:2-8` hanya alias `atoms/Dialog` (3 pemakai: `ImageLightboxModal`, `PdfViewerModal`, `UniversalMediaModal`); `molecules/Notice.tsx:2` alias `atoms/Alert` (2 pemakai); `RetryNotice` 9 pemakai; 60 berkas `*Dialog|*Modal`.
- Penegakan: `no-restricted-imports` (ESLint) dengan baseline; tes arsitektur "jumlah impor Modal/atoms/Dialog tidak boleh naik".
- Risiko: sedang. Dialog media (lightbox/PDF) butuh tata letak khusus dan tidak boleh kehilangan fokus-trap/ESC; uji tangkapan 375/768/1280 dan tes Testing Library perilaku (W9). Lakukan per komponen.
- Ukuran: 2-3 hari (sejalan UX-4).

### 1.6 Server state vs UI state
- Apa: data dari server hanya di TanStack Query; satu hook per query di `hooks/` atau berkas service domain; `<domain>Keys` factory (kunci dari umum ke spesifik, semua variabel masuk kunci); invalidasi per awalan. `useState` hanya untuk UI (buka/tutup, nilai input). Data server tidak disalin ke `useState`. Zustand tetap hanya `sessionStore`.
- Mengapa: W3 (hook pembungkus, jangan salin server state), W4 (key factory), W6 (hindari duplikasi state). Mencegah bug basi seperti B-04 (batal cuti tetap "Menunggu" karena invalidasi cache).
- Bukti: `useQuery(` di 34 berkas; `useState` di 128 berkas tsx; belum ada audit penyalinan (V3) dan keberadaan key factory (V4). Store global tunggal `stores/sessionStore.ts` (52 pemakai).
- Penegakan: kajian manual terarah Fase 0 (V3, V4) lalu `@tanstack/eslint-plugin-query` bila tersedia (V5). Tes: tes regresi invalidasi per mutasi.
- Risiko: rendah bila hanya menambah factory dan memindah kunci; hati-hati salah kunci = cache tak terinvalidasi (tes wajib per domain yang disentuh).
- Ukuran: audit 1 hari; adopsi factory bertahap saat menyentuh domain.

### 1.7 Tes colocated
- Apa: tes unit/komponen di samping berkas (`Nama.test.tsx`); `src/test/` hanya untuk tes lintas domain/halaman penuh dan pembantu (`render`, mock server).
- Mengapa: W5 (colocation), W9 (tes berbasis peran pengguna).
- Bukti: 10 tes colocated (mis. `components/molecules/FilePreview.test.tsx`) vs 71 berkas di `web/src/test/` (mis. `attendance-office.test.tsx`, `navigation.test.tsx`); gaya penamaan kebab di `test/` berbeda dengan PascalCase komponen.
- Penegakan: tes arsitektur: berkas tes baru di `src/test/` ditolak kecuali tertulis di daftar "lintas domain"; Vitest `include` tetap mencakup kedua lokasi selama migrasi.
- Risiko: rendah (pemindahan + perbaikan jalur impor relatif); pastikan hitungan tes tetap sama sebelum/sesudah.
- Ukuran: 3-4 hari (Fase 4), bertahap per domain.

### 1.8 Tambahan kecil web
- `ts-reset` (W7): opsional, 0.25 hari, risiko tipe baru memunculkan galat tsc; masuk Fase 0 hanya sebagai evaluasi.
- 3 `eslint-disable react-hooks/exhaustive-deps` (`organisms/sites/SiteMapPicker.tsx:69`, `hooks/useClientList.ts:26`, `hooks/useListControls.ts:49`): beri alasan tertulis atau perbaiki (sesuai `web/CLAUDE.md` bagian Hindari). 0.5 hari.

## 2. Konvensi target MOBILE

### 2.1 Struktur: feature-first dengan lapisan
- Apa: `lib/features/<fitur>/{presentation,domain,data}`. `presentation/` = layar + widget + controller (Notifier/AsyncNotifier); `domain/` = model dan aturan murni Dart (tanpa Flutter); `data/` = repository + sumber data (panggilan API lewat satu klien, Drift). Lapisan `domain/` dibuat hanya bila ada logika/model yang dipakai lebih dari satu tempat (hindari upacara kosong). `lib/shared/` kecil dan generik; `lib/core/` dipilah (2.5). `test/` mencerminkan `lib/`.
- Mengapa: M1 (UI vs Data, repository sebagai sumber kebenaran), M2 (aliran data satu arah, dependensi lewat antarmuka agar bisa diganti di tes), M3 (feature-first), M11 (pembanding pemisahan). Cocok dengan aturan offline-first VMS di `mobile/CLAUDE.md` (Drift sumber lokal, `SyncEngine`).
- Bukti: `mobile/lib/features/` 15 folder, 45 berkas, datar (tanpa lapisan); hanya 5 dari 45 berkas fitur yang mengimpor `data/vms_api.dart`; layar memanggil klien langsung (verifikasi per fitur di V7).
- Penegakan: `eslint`-setara untuk Dart: tes arsitektur Dart (`test/architecture/layer_test.dart`) yang membaca `import` dan gagal bila `presentation` mengimpor `data` langsung ke klien Dio, atau `domain` mengimpor `package:flutter`; baseline menyusut. Analyzer tidak punya aturan lapisan bawaan.
- Risiko: sedang. Pindah berkas mengubah jalur impor (relatif; lint `prefer_relative_imports` sudah ada di `mobile/analysis_options.yaml:32`) dan golden bisa bergeser jika widget berpindah paket. Satu fitur per PR, tanpa ubah perilaku.
- Ukuran: kerangka + 1 fitur contoh 1.5 hari; sisa 14 fitur 0.5-1 hari masing-masing (Fase 3).

### 2.2 Pecah berkas raksasa
- Apa: urutan prioritas (pecah dulu yang jadi hambatan semua fitur): `shared/ui/vms_ui.dart` (856) menjadi satu berkas per widget (`surface_card.dart`, `empty_state.dart`, `notice_banner.dart`, `hero_header.dart`, dst.); `data/vms_api.dart` (927) menjadi `data/api/<domain>_api.dart` + `data/api/api_client.dart` (Dio, interseptor, token) + `data/models/`; layar: `attendance_screen.dart` (1199), `daily_plan_screen.dart` (851), `survey_screen.dart` (807), `survey_point_screen.dart` (787), `item_progress_screen.dart` (778) dipecah menjadi widget per bagian + controller.
- Mengapa: M1 (pisah View dan data), M3, M9 (kerja di `build()` terkontrol; widget kecil = rebuild kecil). Mengurangi konflik merge antarjalur mobile.
- Bukti: jumlah baris di atas (`wc -l`); 12 berkas > 600 baris termasuk `data/app_database.g.dart` 2038 (dibangkitkan, dikecualikan).
- Penegakan: tes Dart `test/architecture/file_size_test.dart` (peringatan 400, galat 600 untuk non-generated, baseline menyusut). Barrel tipis sementara `vms_ui.dart` yang `export`-kan semua widget baru agar impor lama tetap jalan, dihapus di akhir.
- Risiko: pecah `vms_ui.dart`/`vms_api.dart` rendah-sedang (mekanis; tes + analyzer menangkap); pecah layar sedang-tinggi (state lokal, controller kamera/lokasi). Golden harus hijau tanpa `--update-goldens`; bila berubah, itu tanda pemecahan mengubah tampilan, bukan kemajuan.
- Ukuran: `vms_ui` 1 hari, `vms_api` 1.5 hari, layar masing-masing 1-1.5 hari (5 layar ~6 hari).

### 2.3 Semua fitur memakai repository lewat satu klien API
- Apa: setiap fitur punya `<fitur>_repository.dart` (kelas biasa + provider Riverpod) yang membungkus `SyncEngine.fetchList/fetchMap/submit` dan klien API; layar/controller tidak memanggil Dio. Satu `ApiClient` (Dio) sebagai satu-satunya titik HTTP.
- Mengapa: M1/M2 (repository = sumber kebenaran, bisa digantikan di tes), M4 (controller -> service -> repository). Sejalan dengan outbox `client_op_id` yang sudah ada: tulis tetap lewat `engine.submit`.
- Bukti: `data/vms_api.dart` satu kelas 927 baris dengan semua metode; hanya 5 dari 45 berkas fitur mengimpornya (sisanya lewat jalur lain/ad hoc, V7).
- Penegakan: tes arsitektur Dart (3 aturan di 2.1) + tes unit repository dengan fake klien.
- Risiko: sedang-tinggi pada jalur offline (antrean foto/absen). Wajib: tes sinkron/outbox tidak berubah, uji HP nyata lewat UI untuk fitur absen (aturan E2E tanpa injeksi), parameter API tetap opsional (APK lapangan lama jalan).
- Ukuran: lihat Fase 3 (~8-10 hari total, bertahap).

### 2.4 Lint: riverpod_lint dan very_good_analysis (disetujui pemilik, bertahap)
- Apa: tambahkan `riverpod_lint` (via `custom_lint`/plugin analyzer sesuai versi Riverpod 3 yang terpasang) dan `very_good_analysis` secara bertahap: (1) pasang sebagai `include` dengan aturan yang mengganggu dimatikan dulu (misal `public_member_api_docs`); (2) hasilkan baseline daftar pelanggaran; (3) aktifkan aturan satu per satu menjadi galat setelah bersih. Tidak boleh merusak `flutter analyze` di CI.
- Mengapa: M6 (riverpod_lint menangkap pola salah seperti `ref` di dispose, properti Notifier publik), M5 (aturan lebih ketat dari `flutter_lints`), M8 (urutan impor/penamaan). Disetujui pemilik lewat autopilot.
- Bukti: `mobile/pubspec.yaml` dev_dependencies (sekitar baris 72-87) tidak memuat `riverpod_lint`/`custom_lint`; `mobile/analysis_options.yaml:3` hanya `flutter_lints`; aturan manual di `:19` (`unawaited_futures`), `:26` (`avoid_print`), `:32` (`prefer_relative_imports`); 8 `// ignore:` di `lib/`.
- Penegakan: `flutter analyze` di `verify.sh mobile` dan CI. Header `analysis_options.yaml` meminta persetujuan pemilik untuk mengubah aturan; PR memuat tautan persetujuan.
- Risiko: sedang. Kompatibilitas versi analyzer/Dart SDK/riverpod_lint dengan Riverpod 3 dan `build_runner`/`drift_dev` (V6) harus dicoba di cabang dulu; bila bentrok, tunda `very_good_analysis` dan pilih aturan terpilih.
- Ukuran: spike 0.5 hari; pemasangan + baseline 1 hari; penurunan baseline bertahap.

### 2.5 Penamaan dan pemilahan core
- Apa: `snake_case.dart` (sudah). Akhiran peran tetap: `_screen`, `_controller`, `_repository`, `_api`, `_model`, `_widget`. `_view` dan `_state` diganti bertahap (`k3_campaign_view.dart` -> `k3_campaign_screen.dart`; `auth_state.dart` boleh tetap). `core/` dipilah: `core/theme/`, `core/platform/` (kamera, lokasi, biometrik, notifikasi), `core/sync/`, `core/network/` (klien, token), `core/error_message.dart` tetap.
- Mengapa: M8 (aturan nama Dart), M3 (kode bersama kecil, terpilah). `core/` 30 berkas berubah jadi keranjang campuran.
- Bukti: 0 berkas PascalCase (baik); akhiran campur `_view`, `_state`, `_gate` di `features/hse/k3_campaign_view.dart`, `features/auth/`; `lib/core/` 30 berkas datar.
- Penegakan: lint `file_names` (sudah di flutter_lints) + tes arsitektur akhiran untuk berkas baru.
- Risiko: rendah (ganti nama + impor relatif; analyzer menangkap).
- Ukuran: 1 hari.

### 2.6 Riverpod dan kinerja
- Apa: data async = `AsyncNotifier`; state sinkron = `Notifier`; `ref.watch` hanya di `build`, `ref.read` di handler; daftar panjang `ListView.builder`; kerja berat di isolate (`compute`) sesuai `mobile/CLAUDE.md`.
- Mengapa: M4, M6, M7, M9.
- Bukti: hanya 4 berkas memakai `Notifier`/`AsyncNotifier`, 33 berkas `ConsumerWidget`/`ConsumerStatefulWidget`; contoh `features/auth/auth_controller.dart:23`, `core/providers.dart:21`. Detail `const`/`RepaintBoundary`/isolate di luar halaman yang dibaca (V8).
- Penegakan: riverpod_lint (2.4) + tinjauan PR; profil DevTools bila ada keluhan.
- Risiko: sedang bila mengubah pola state di layar kamera/absen; lakukan saat layar itu dipecah (2.2), bukan terpisah.
- Ukuran: ikut Fase 2/3.

## 3. Lintas platform

### 3.1 Token tunggal (terkait UX-7)
- Apa: `design/tokens.json` -> generator `scripts/gen-tokens.*` -> `web/src/styles/tokens.css` dan `mobile/lib/core/theme/vms_tokens.dart`. Tes paritas di `verify.sh`: nilai hex web = mobile; tes gagal bila berkas hasil tak sesuai generator (drift). Termasuk `color.action.primary` (navy) vs `color.action.highlight` (emas hanya aksi absen), skala radius 6/10/14/20, spasi 4-pt.
- Mengapa: satu sumber kebenaran (prinsip 1, M2). Sekarang nilai sama tetapi ditulis tangan dua kali.
- Bukti: audit UI/UX bagian 1: web primary #232c6f di `web/src/styles/index.css`, mobile `vms_*.dart` brand/neutral sama; radius beda (web kartu 14-16, HP dialog 24); `design/` belum ada.
- Penegakan: tes paritas + CI; larangan `Colors.*` dan hex literal (lint kustom/tes Dart, UX-5).
- Risiko: rendah-sedang (golden mobile bisa berubah halus bila pembulatan beda). Dikerjakan setelah J1/J3 selesai.
- Ukuran: 1-1.5 hari (sudah diperkirakan UX-7).

### 3.2 Glosarium istilah
- Apa: satu berkas `design/glosarium.json` (istilah Inggris -> padanan Indonesia, dengan OM/PM dipertahankan) dibaca tes web dan mobile yang memindai teks UI untuk istilah terlarang.
- Mengapa: satu sumber kebenaran; istilah campur ditemukan di audit (P2 temuan 4). Keputusan pemilik sudah ada (istilah Inggris diganti kecuali OM/PM).
- Bukti: istilah campur "Tugas Klien (WO)", "K3 / HSE", "Offboarding", "Audit log" di layar (audit-uiux bagian 2 butir 4).
- Penegakan: tes arsitektur memindai literal string pada `components/`, `pages/`, `lib/features/`; baseline menyusut. Dikerjakan setelah UX-2 (J1) agar tidak bertabrakan.
- Risiko: rendah (tes saja); false positive pada nama kode, jadi hanya pindai literal tampilan.
- Ukuran: 1 hari.

### 3.3 Kontrak API bertipe otomatis
- Apa: pertahankan alur `UPDATE_OPENAPI_SNAPSHOT=1 pytest` -> `npm run gen:api:export && npm run gen:api` (web). Untuk mobile: evaluasi bangkitkan DTO Dart dari snapshot OpenAPI yang sama (spike), atau minimal tes kontrak yang mem-parse contoh respons ke model Dart.
- Mengapa: satu sumber kebenaran lintas lapisan; mencegah APK lama dan API melenceng (aturan parameter opsional).
- Bukti: web: `web/src/lib/apiTypes.ts` dibangkitkan (21.765 baris, dikecualikan dari metrik). Mobile: `data/vms_api.dart` menulis tangan DTO (927 baris).
- Penegakan: CI sudah memeriksa snapshot OpenAPI; tambah tes kontrak mobile.
- Risiko: sedang (generator Dart menambah dependensi/build_runner); hanya spike di rencana ini.
- Ukuran: spike 1 hari; keputusan generator setelah Fase 3.

## 4. Fase pelaksanaan

Estimasi hari = hari engineer, di luar menunggu CI/review. Semua PR ke `development`; tidak ada force-push; commit tanpa `--no-verify`.

Titik aman (tidak bentrok):
| Paket berjalan | Area sentuh | Aturan untuk rencana ini |
|---|---|---|
| RLS/migrasi DB (J6, G2-RLS; v2_0037-v2_0045) | `db/`, `api/` | Rencana ini tidak menyentuh `api/` atau `db/`: tidak ada bentrok. Satu-satunya titik: `UPDATE_OPENAPI_SNAPSHOT` tidak dipakai. |
| UX-2 (glosarium, J1) | teks di `components/`, `pages/` | Jangan ganti nama/pindah komponen yang sedang diedit J1; Fase 1 mulai setelah PR UX-2 merge. |
| UX-3..UX-6 | web layout, mobile hero/filter | Fase 2 mobile (layar) setelah J3 (UX-5) dan hindari `home`/jadwal sampai UX-6 merge; pemecahan `vms_ui.dart` sebelum UX-5 harus berkoordinasi (UX-5 mengganti `Colors.*`). Lebih aman: UX-5 dulu, lalu pecah. |
| UX-4 (satukan Tab/Dialog/Badge/Notice) | identik dengan Fase 1 | Fase 1 = UX-4; jangan dikerjakan dua kali, satu pemilik. |
| UX-7 (token) | tema | Fase 5 = UX-7; setelah pecah `vms_ui.dart`. |
| E2E (uji manusia/QA) | seluruh UI | Fase yang mengganti nama komponen/teks diberi tahu QA; PR pemindahan berkas tidak mengubah teks. |

### Fase 0 - Penjagaan tanpa memindah berkas (3-4 hari, 4 PR)
- PR 0.1 web lint: aktifkan `eslint-plugin-boundaries`, `import/no-cycle`, larang barrel, `max-lines`/`complexity` sebagai `warn`, baseline pelanggaran. (1.5 h)
- PR 0.2 web tes arsitektur: penamaan (Dialog/Schema), hitungan impor `Modal`/`atoms/Dialog` tidak naik, tes baru di `src/test/` ditolak, `index.ts` nol. (1 h)
- PR 0.3 mobile: tes arsitektur Dart (ukuran berkas 400/600 non-generated, akhiran peran, `domain` tanpa Flutter, `presentation` tanpa Dio) dengan baseline. (1 h)
- PR 0.4 mobile lint (spike lalu pasang): `riverpod_lint` + `very_good_analysis` bertahap dengan baseline; tolak bila `flutter analyze` merah. (1.5 h; bisa dipisah dua PR)
- Tugas verifikasi (hasil ditulis di deskripsi PR/lampiran dokumen ini): V1-V9 (bagian 7).
- Selesai bila: `verify.sh web` dan `verify.sh mobile` hijau tanpa pindah berkas; baseline ter-commit; jumlah peringatan tercatat sebagai metrik awal.
- Tes hijau: Vitest penuh, `flutter analyze`, `flutter test` (golden Linux di CI), E2E tidak terpengaruh.
- Rollback: revert PR (hanya konfigurasi/tes); tidak ada data atau perilaku.
- Titik aman: tidak menyentuh kode fitur; boleh paralel dengan semua paket.

### Fase 1 - Penyatuan komponen duplikat web (4-5 hari, 4-5 PR; = UX-4)
- Urutan: (1) deprecate + lint `Modal`/`atoms/Dialog` (0.5 h); (2) migrasi 3 pemakai `Modal` media ke `VmsDialog` atau varian lebar (1.5 h); (3) gabung `Notice`/`Alert`/`RetryNotice` (1 h); (4) satukan Tabs (pil vs garis bawah) dan Badge (`Pill`/`StatusBadge`/`Badge`) (1.5 h); (5) ganti nama `*Modal` ke `*Dialog` (mekanis, satu PR, 0.5 h) dan `schemas/` ke tunggal (0.5 h).
- Selesai bila: pemakai `Modal`/`atoms/Dialog` langsung = 0 (atau tinggal atom internal VmsDialog); hapus berkas alias; tes arsitektur Fase 0 menyusut.
- Tes hijau: Vitest penuh, tes perilaku dialog (fokus, ESC, aria), tangkapan 375/768/1280, E2E sentuh dialog (beri tahu QA nama berkas berubah, teks tidak).
- Rollback: tiap komponen satu PR, revert PR; alias lama dipertahankan sampai PR hapus terakhir.
- Titik aman: setelah UX-2 (J1) merge, dan saat tidak ada jalur web besar yang mengedit dialog yang sama (G2-WEB-A: koordinasi per folder).

### Fase 2 - Pemecahan berkas raksasa (mobile dulu; 10-12 hari, 8-10 PR)
- Mobile urutan: 2.1 `vms_ui.dart` -> per widget + barrel sementara (1 h); 2.2 `vms_api.dart` -> `ApiClient` + `<domain>_api.dart` (1.5 h); 2.3 `attendance_screen.dart` (1.5 h); 2.4 `daily_plan_screen.dart`, `survey_screen.dart`, `survey_point_screen.dart`, `item_progress_screen.dart` (masing-masing 1-1.5 h; boleh paralel bila fitur berbeda).
- Web (opsional, setelah mobile): 13 `.tsx` > 300 baris, dimulai dari 3 terbesar (667, 642, 555), 0.5-1 h per berkas.
- Selesai bila: tidak ada berkas non-generated mobile > 600 baris; web tidak ada > 500; baseline menyusut.
- Tes hijau: `flutter analyze` + `flutter test` tanpa `--update-goldens`; uji HP nyata lewat UI untuk absen (aturan: HP uji, bukan produksi, tanpa restart adb); Vitest penuh untuk web.
- Rollback: revert PR; barrel `vms_ui.dart` menjaga kompatibilitas impor selama transisi.
- Titik aman: `vms_api.dart` dipecah setelah paket mobile yang menyentuh API selesai (J3, G2-FACE, G2-ASET, G2-INSP mobile); `attendance_screen.dart` jangan bersamaan dengan G2-FACE (layar absen). Pecah `vms_ui.dart` setelah UX-5.

### Fase 3 - Migrasi fitur mobile ke repository (8-10 hari, 15 PR kecil)
- Satu fitur per PR dari yang paling sederhana: kerangka + fitur contoh (cuti), lalu fitur lain; absensi dan galeri terakhir (jalur offline paling sensitif).
- Selesai bila: tidak ada layar/controller yang memanggil Dio atau `VmsApi` langsung; tes arsitektur Fase 0 nol pelanggaran; tes repository dengan fake klien.
- Tes hijau: `flutter test` (termasuk sinkron/outbox), uji HP nyata lewat UI, parameter API tetap opsional.
- Rollback: per fitur revert PR; repository membungkus jalur lama sehingga perilaku identik.
- Titik aman: setelah Fase 2.2; per fitur, tidak bentrok dengan jalur mobile aktif pada fitur yang sama.

### Fase 4 - Pemindahan tes colocated (3-4 hari, 5-6 PR)
- Web: pindahkan `src/test/*.test.tsx` per domain ke samping komponen/halaman target; tersisa hanya tes lintas domain. Mobile: rapikan `test/` agar mencerminkan `lib/` setelah Fase 2-3.
- Selesai bila: `src/test/` berisi hanya pembantu + tes lintas domain; jumlah tes sebelum = sesudah.
- Tes hijau: Vitest (hitungan tes sama), `flutter test`.
- Rollback: revert PR (pemindahan murni).
- Titik aman: sesudah Fase 1 dan 2 (komponen sudah stabil lokasinya); hindari bersamaan dengan jalur yang sedang menulis tes di folder sama.

### Fase 5 - Token tunggal (2-3 hari, 2 PR; = UX-7 + glosarium 3.2)
- Generator + tes paritas, lalu pindahkan nilai ke `design/tokens.json`; tes glosarium.
- Selesai bila: tes paritas di `verify.sh`; tidak ada hex literal baru.
- Tes hijau: golden mobile (perubahan hanya bila nilai sengaja diubah, dengan alasan di PR), Vitest, tangkapan web.
- Rollback: revert PR; berkas hasil tetap di-commit sehingga build tidak bergantung generator saat rollback.
- Titik aman: setelah J1, J3 (UX-1/2/5) merge.

Total estimasi: Fase 0 (3-4) + 1 (4-5) + 2 (10-12) + 3 (8-10) + 4 (3-4) + 5 (2-3) = 30-38 hari engineer. Hanya Fase 0 yang menjadi prasyarat; Fase 1 dan 2 bisa paralel (web vs mobile). Fase 3-5 boleh ditunda tanpa merusak hasil sebelumnya.

## 5. Cara menambah fitur baru (checklist)

Urutan PR: API -> tipe -> web -> mobile. Satu fitur = beberapa PR kecil, masing-masing hijau di `verify.sh`.

### 5.1 Umum (semua fitur)
1. Tulis brief: tujuan, peran yang boleh (izin `require_permission`), cakupan kantor/divisi, kondisi layar, istilah. Bila aturan bisnis baru, tanya pemilik dulu.
2. PR-A API (bila perlu): route + skema; daftar pakai `ListParams`/`apply_list`; parameter baru opsional; tes matriks peran; snapshot OpenAPI. Audit/jejak perubahan dan izin tercatat.
3. PR-B tipe web: `npm run gen:api:export && npm run gen:api`; tidak menulis tipe tangan.
4. PR-C web, PR-D mobile (boleh paralel setelah A merge).
5. Teks UI lewat glosarium (3.2); Bahasa Indonesia sederhana; galat 422 lewat `applyFieldErrors` (web), `core/error_message.dart` (mobile).
6. Lima kondisi layar: memuat, kosong (belum ada data vs hasil pencarian kosong), galat + coba lagi, sebagian/offline, sukses.
7. `bash scripts/verify.sh <lapisan>` hijau; uji klik lewat UI (bukan API/SQL).

### 5.2 Web
1. Service: `services/<domain>Service.ts` (satu-satunya tempat HTTP) + `<domain>Keys`.
2. Schema Zod: `schemas/<domain>Schema.ts`, batas input sama dengan skema API.
3. Hook: `hooks/use<Domain>.ts` membungkus `useQuery`/`useMutation`; invalidasi per awalan kunci.
4. Komponen dari bawah: atom/molekul yang sudah ada -> organisme `organisms/<domain>/` -> template -> halaman `pages/<domain>/`. Dialog = `VmsDialog` bernama `*Dialog`. Tanpa barrel. Berkas < 300 baris.
5. Halaman memakai `QueryState` untuk lima kondisi; tombol sesuai peran (izin dari sesi).
6. Tes colocated `Nama.test.tsx` (Testing Library, query berbasis peran), plus tes izin/peran; aksesibilitas (label, fokus dialog).
7. Daftar rute/menu + hak akses; tangkapan 375/768/1280.

### 5.3 Mobile
1. `features/<fitur>/` dengan `presentation/`, `data/` (dan `domain/` bila perlu). Model dari kontrak API.
2. Repository: bungkus `SyncEngine.fetchList/fetchMap` (baca cache) dan `engine.submit` dengan `client_op_id` (tulis, offline-first); satu klien API.
3. Controller: `AsyncNotifier`/`Notifier`; `ref.watch` di `build`; tidak ada `e.toString()` ke pengguna.
4. Layar: widget kecil per bagian (< 400 baris), `ListView.builder` untuk daftar, tombol >= 48 dp, warna/teks dari token (tanpa `Colors.*`/`fontSize` literal).
5. Lima kondisi layar dengan `EmptyState`/`NoticeBanner`/`SyncStatusBanner`; galat + "Coba lagi".
6. Tes: unit repository (fake klien), widget test, golden bila tampilan baru (Linux di CI); tes offline/antrean bila menulis data.
7. Uji HP nyata lewat UI di HP uji (bukan aplikasi produksi); APK dev dibangun bila perlu.

## 6. Metrik keberhasilan dan jadwal evaluasi

Skrip `scripts/metrik-kode.sh` (dibuat di Fase 0) mencetak tabel; hasil dicatat di deskripsi PR fase.
| Metrik | Garis dasar (2026-11-11) | Target akhir |
|---|---|---|
| Berkas web `.tsx` komponen > 300 baris | 13 | <= 3 (tidak ada > 500) |
| Berkas mobile non-generated > 600 baris | >= 11 (12 total termasuk `app_database.g.dart`) | 0 |
| Pelanggaran batas modul (boundaries + no-cycle + barrel) | belum diukur (plugin belum aktif) | 0 galat; baseline kosong |
| Pemakai `Modal`/`atoms/Dialog` langsung | 3 (+ alias) | 0 |
| Berkas fitur mobile yang memanggil klien API langsung | belum diukur (V7) | 0 |
| Tes web di `src/test/` vs colocated | 71 vs 10 | `src/test/` hanya lintas domain |
| Ukuran bundle web (dist, gzip, per chunk) | belum diukur (V9) | tidak naik > 5% per fase |
| Waktu build web, `flutter analyze`, `verify.sh` | belum diukur | tidak naik > 10% per fase |
| Cakupan tes (web Vitest, mobile `flutter test --coverage`) | belum diukur | tidak turun per fase; naik di fitur yang disentuh |
| `eslint-disable`/`// ignore:` | web 3 (hooks), mobile 8 | tiap satu punya alasan tertulis; tidak naik |
Jadwal evaluasi: akhir Fase 0 (garis dasar nyata), akhir setiap fase (metrik naik/turun), lalu tiap 3 bulan. Kriteria rem: bila dua fase berturut-turut menaikkan waktu review atau regresi produksi, hentikan fase berikut dan tinjau ulang dengan pemilik.

## 7. Butir "perlu verifikasi" (tugas Fase 0)

| Kode | Butir | Cara cek | Keluaran |
|---|---|---|---|
| V1 | `web/src/stores/sessionStore.ts:12` mengimpor `mockMe` dari `app/mockSession`. Dipakai di `:57` hanya bila `import.meta.env.DEV && VITE_MOCK_ROLE` (terjaga DEV). Apakah modul mock masuk bundle produksi? | `npm run build` lalu cari penanda `mockMe`/string dari `mockSession.ts` di `dist/` | Bila ada: ubah ke impor dinamis `if (import.meta.env.DEV)` atau pindahkan; bila tidak ada: tutup dengan catatan |
| V2 | `ts-reset` (W7) cocok dengan tsconfig dan tidak memicu galat massal | coba di cabang | keputusan pasang/tidak |
| V3 | Penyalinan data server ke `useState` (128 `useState` vs 34 `useQuery`) | audit per halaman terarah pada `useEffect(() => setX(data))` | daftar halaman bermasalah |
| V4 | Keberadaan query key factory | grep `queryKey` di `services/` dan `hooks/` | rancangan `<domain>Keys` |
| V5 | Ketersediaan/versi `@tanstack/eslint-plugin-query` dan `eslint-plugin-testing-library` yang cocok ESLint saat ini | `npm view` + percobaan | pasang atau tunda |
| V6 | Kompatibilitas `riverpod_lint`/`very_good_analysis` dengan Riverpod 3, Dart SDK, `drift_dev`/`build_runner` | spike cabang | versi terkunci, atau tunda |
| V7 | Berapa layar/controller mobile memanggil Dio/`VmsApi` langsung, dan di mana | grep import `vms_api`/`dio` per fitur | peta migrasi Fase 3 |
| V8 | Praktik `const`, `RepaintBoundary`, isolate (M9 tak membahasnya) | baca sumber Flutter performance tambahan | aturan kinerja tambahan |
| V9 | Ukuran bundle `manualChunks` (`web/vite.config.ts:21`) belum diukur | `npm run build` + ringkas ukuran chunk | garis dasar metrik |
Verifikasi lain yang ikut: struktur `test/` mobile mencerminkan `lib/` (belum dicek); artikel Riverpod architecture (M4) hanya dari cuplikan; Airbnb style tidak dibaca (tidak dipakai).

## Lampiran: rujukan
Web: W1 https://github.com/alan2207/bulletproof-react; W2 https://feature-sliced.design/docs/get-started/overview; W3 https://tkdodo.eu/blog/practical-react-query; W4 https://tkdodo.eu/blog/effective-react-query-keys; W5 https://kentcdodds.com/blog/colocation; W6 https://react.dev/learn/choosing-the-state-structure; W7 https://www.totaltypescript.com/ts-reset; W8 https://vite.dev/guide/performance; W9 https://testing-library.com/docs/guiding-principles; W10 https://google.github.io/styleguide/tsguide.html; W11 https://github.com/javierbrea/eslint-plugin-boundaries.
Mobile: M1 https://docs.flutter.dev/app-architecture/guide; M2 https://docs.flutter.dev/app-architecture/concepts; M3 https://codewithandrea.com/articles/flutter-project-structure/; M4 https://codewithandrea.com/articles/data-mutations-riverpod; M5 https://pub.dev/packages/very_good_analysis; M6 https://pub.dev/packages/riverpod_lint; M7 https://riverpod.dev/; M8 https://dart.dev/effective-dart/style; M9 https://docs.flutter.dev/perf/best-practices; M10 https://drift.simonbinder.eu/; M11 https://bloclibrary.dev/architecture/; M12 https://github.com/VeryGoodOpenSource/very_good_cli.
Pemakaian: web W1,W2,W3,W4,W5,W6,W7,W8,W9,W10,W11 (11 dari 11); mobile M1-M11 (M12 hanya pembanding, tidak dipakai).
