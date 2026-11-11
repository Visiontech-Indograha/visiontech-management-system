# Rencana v2: struktur kode, tampilan, dan kegunaan (web dan mobile)

Status: USULAN (rencana, belum dikerjakan). Dasar: `origin/development` adda1521, VERSION 1.8.4, 2026-11-11.
Menggantikan bagian 4 (fase) dan bagian 6 (metrik) dari `struktur-dan-kualitas-kode.md` (v1). Bagian 0-3, 5, 7 dan lampiran v1 tetap berlaku sebagai konvensi dan rujukan; v2 tidak mengulanginya.
Menggabungkan tiga sumber menjadi satu urutan: Fase 0-5 (struktur kode, v1), UX-1..7 (audit tampilan), dan 42 temuan kegunaan U-01..U-42 dari `audit-usability-web.md` (berkas bersebelahan).
Hanya dokumen. Tidak ada kode yang diubah. Semua angka ukuran dan batas adalah usulan.

## 1. Ringkasan temuan kegunaan (pindai ulang web, 10 heuristik Nielsen)
Skor 0-3 per heuristik, rata-rata 30 baris halaman (rinci: audit):
| Heuristik | Skor | Heuristik | Skor |
|---|---|---|---|
| H10 Bantuan dan dokumentasi | 1,80 | H8 Minimalis | 1,07 |
| H7 Fleksibilitas dan efisiensi | 1,53 | H5 Cegah galat | 1,00 |
| H9 Pulih dari galat | 1,33 | H1 Status sistem | 0,97 |
| H4 Konsistensi | 1,30 | H6 Kenali, bukan ingat | 0,93 |
| H3 Kendali dan kebebasan | 1,27 | H2 Bahasa dunia nyata | 1,20 |
Aspek: Learnability 1,31 (terburuk), Errors 1,20, Efficiency 1,19, Memorability 1,12, Satisfaction 1,11.
Temuan: P0 2, P1 8, P2 21, P3 11 (total 42). Pola terpenting: tidak ada undo, tidak ada bantuan, galat tetap yang menelan penyebab (18 `catch {`), hapus tanpa konfirmasi (2 tempat), tanpa progres unggah (11 input berkas), tanpa pintasan, urut, atau filter tersimpan.
Kekuatan yang dipertahankan: `ConfirmDialog` anti klik ganda, penjaga formulir kotor di dialog, `RouteErrorPage`, `errorMessage()`, filter di URL, format tanggal WIB terpusat.

Status pekerjaan yang sudah masuk: UX-1 (target sentuh 44 px, teks minimal 12 px) sudah merge (#461; sisa 13 pemakaian `h-8/h-9` perlu dicek, masuk Gelombang 1). Status J1 (form dan teks), J3 (mobile), dan paket G2 diambil dari brief gelombang, belum diverifikasi di riwayat git; bila belum merge, gelombang yang bergantung padanya menunggu (kolom "Titik aman").

## 2. Prinsip urutan (mengapa urutannya begini)
1. Penegak dulu, perbaikan kemudian. Aturan yang hanya ada di dokumen akan dilanggar; angka pelanggaran dibekukan dengan baseline lalu hanya boleh menyusut. Jadi Gelombang 0 mendahului semuanya, supaya perbaikan di gelombang lain tidak ditimpa kode baru yang melanggar.
2. Kerugian terbesar, biaya terkecil lebih dulu. Dua temuan P0 dan beberapa P1 hanya butuh perubahan kecil tanpa komponen baru (Gelombang 1).
3. Komponen bersama sebelum migrasi halaman. 20+ temuan hilang bila `QueryState`, `ConfirmDialog`, `Button`, `Field`, dan unggahan diperbaiki sekali (Gelombang 2); memperbaiki per halaman lebih dulu berarti kerja dua kali.
4. Teks setelah komponen stabil, tetapi sebelum tes glosarium. Mengganti istilah sambil memindahkan komponen menyebabkan konflik; v1 sudah mensyaratkan Fase 1 mulai setelah UX-2 (J1) merge.
5. Yang menyentuh API (undo, urut, massal, sesi) terakhir di jalur web: tambahan opsional (APK lama tetap jalan), dan perlu keputusan pemilik.
6. Uji manusia menyela di tiga titik (garis dasar, setelah Gelombang 3, setelah Gelombang 4) agar perbaikan diukur, bukan ditebak.

## 3. Peta gelombang
```
G0 Penegak ───────────────┬─> G1 Pengaman cepat ──> G2 Komponen bersama ──> G3 Bahasa dan bantuan ──> G4 Efisiensi ahli (API) ──> G5 Tata letak, pecah berkas ──> G6 Mekanis (tes, token)
(web + mobile, 4-5 hari)  │                            (Fase 1 = UX-4)         (UX-2, glosarium)         (butuh keputusan)           (UX-3, Fase 2 web)                    (Fase 4, Fase 5 = UX-7)
                          └─> Jalur mobile paralel: UX-5 -> Fase 2 mobile -> Fase 3 -> UX-6
Uji kegunaan: UT-0 (garis dasar, sebelum G1) | UT-1 (setelah G3) | UT-2 (setelah G4)
```
Paralel: G1 dan G2 bisa berjalan bersamaan oleh dua pemilik bila berkas berbeda (G1 menyentuh dialog tertentu, G2 menyentuh komponen bersama; G1 selesai lebih dulu per berkas). G3 mulai setelah G2 (komponen) dan keputusan istilah. Jalur mobile independen dari web setelah G0.

## 4. Gelombang

### G0 - Penegak (4-5 hari, 5 PR; = Fase 0 v1 + PR 0.5)
- Isi: PR 0.1 lint batas modul (`eslint-plugin-boundaries`, `no-cycle`, larang barrel, `max-lines`, baseline); PR 0.2 tes arsitektur penamaan; PR 0.3 tes arsitektur mobile; PR 0.4 `riverpod_lint` dan `very_good_analysis` bertahap; PR 0.5 BARU: aturan desain web sebagai penegak (bagian 5): `no-restricted-syntax` untuk `catch` tanpa variabel (baseline 18, U-02), `toLocale*String` di luar `lib/format.ts` (U-38), tes `design-rules.test.ts` (hapus harus lewat konfirmasi, unggah harus lewat komponen, Title Case literal), skrip metrik `scripts/metrik-kode.sh` diperluas.
- Mengapa: lihat prinsip 1. Tanpa ini, setiap temuan yang diperbaiki bisa muncul lagi di PR lain. Biayanya kecil karena hanya konfigurasi dan tes.
- Definisi selesai: `verify.sh web` dan `verify.sh mobile` hijau tanpa memindah berkas; baseline ter-commit; angka awal metrik tercatat (butir V1-V12, bagian 8).
- Tes: Vitest penuh, `flutter analyze`, `flutter test`; tes penegak sendiri punya kasus uji (berkas contoh pelanggar harus gagal).
- Titik aman: tidak menyentuh `api/`, `db/`, atau kode fitur: tidak bentrok dengan RLS (J6, G2-RLS) maupun E2E. Boleh paralel dengan semua paket.
- Rollback: revert PR (hanya konfigurasi dan tes).

### G1 - Pengaman data dan galat cepat (4-5 hari, 6-8 PR kecil; web saja)
- Isi: U-01 (konfirmasi hapus lokasi cabang), U-10 (konfirmasi hapus material default), U-02 (ganti 18 `catch {` dengan `errorMessage(err, "apa-mengapa-solusi")`, per folder), U-25 (toast K3 nyasar menjadi banner di popup gate), U-26 (teks panjang), U-35, U-36, U-37, U-42 (tombol lihat sandi), U-21 (judul halaman = label menu lewat `pageTitle.ts`), sisa UX-1 (13 `h-8/h-9`).
- Mengapa: dua temuan P0 dan P1 dengan dampak langsung pada data dan kemampuan pengguna memperbaiki masalah, tetapi ukurannya setengah hari tiap butir dan tidak butuh komponen baru. Baseline G0 mengunci agar tidak bertambah.
- Definisi selesai: nol `window.confirm`-setara (aksi hapus tanpa konfirmasi) pada daftar pindaian; baseline `catch` tanpa variabel turun ke 0 di berkas yang disentuh; tes komponen: hapus lokasi memunculkan dialog dengan nama dan akibat; galat server tampil di toast.
- Tes: tes Testing Library per dialog (klik Hapus membuka konfirmasi, Batal tidak memanggil API, galat server tampil); tangkapan 375/768/1280 untuk kartu panjang; `verify.sh web`.
- Titik aman: web saja, tanpa `api/` dan `db/`. Dialog lokasi (`ClientSitesModal`) dipakai juga oleh B-17 (G2-WEB-A): urutkan, kerjakan setelah PR B-17 merge. E2E: teks tombol tidak berubah kecuali konfirmasi baru; beri tahu QA bahwa klik Hapus kini membuka dialog.
- Rollback: revert PR per butir.

### G2 - Komponen bersama v2 (10-12 hari, 8-10 PR; = Fase 1 v1 = UX-4, diperluas)
- Isi (urut): (1) deprecate dan lint `Modal`/`atoms/Dialog`, migrasi 3 pemakai media ke `VmsDialog` (v1 Fase 1 butir 1-2); (2) `Button` mendapat prop `pending` (spinner, `aria-busy`, nonaktif, teks proses satu gaya "Menyimpan…") (U-39, U-33); (3) `QueryState` v2: galat membaca `ApiError` dan `useOnline` ("Tidak ada koneksi internet", "Anda tidak punya izin melihat ini", "Server sedang sibuk"), dua jenis kosong ("Belum ada" vs "Tidak ada hasil"), skeleton berlabel `role="status"` (U-05, U-19, U-20) dan menuntaskan B-30; (4) `ConfirmDialog` v2: `confirmLabel` wajib, satu keluarga hapus (biasa dan ketik "HAPUS"), pola inline `DocumentsPanel` dihapus (U-12); (5) `Field` dan `DateField` tanpa pesan bawaan peramban, galat di kolom dengan `aria-invalid` dan fokus, ringkasan galat (U-06, U-14, U-29), migrasi 6 tempat validasi-lewat-toast; (6) `UploadField` dengan progres dan batas tertulis (U-08); (7) `Notice` gabungan dan `Tabs` satu gaya per tingkat (U-22, v1 butir 3-4); (8) `Breadcrumb` (U-24), alasan tombol nonaktif (U-13), banner offline global (U-28), peringatan keluar saat kotor (U-15); (9) ganti nama `*Modal` ke `*Dialog` dan `schemas` tunggal (mekanis).
- Mengapa: prinsip 3. Tiap komponen menyelesaikan satu keluarga temuan sekaligus; migrasi halaman kemudian hanya mengganti impor. Urutan dari yang paling sering dipakai dan paling berisiko ke yang mekanis.
- Definisi selesai: pemakai `Modal`/`atoms/Dialog` langsung 0; `toast.error` sebagai validasi 0 di berkas yang disentuh; setiap `useQuery` pada organisme memakai `QueryState` v2 atau menangani `isError` (tes arsitektur G0 menyusut); tidak ada `<input type="file">` di luar `UploadField`.
- Tes: tes komponen (Button pending tidak bisa diklik ganda; ConfirmDialog fokus masuk, ESC, `busy`; QueryState empat kondisi; Field `aria-invalid`; UploadField menampilkan persen dengan mock progres), tes perilaku dialog, tangkapan 375/768/1280, Vitest penuh dengan jumlah tes tidak turun.
- Titik aman: web saja. Mulai setelah PR UX-2/J1 merge (syarat v1) atau, bila J1 belum merge, kerjakan butir yang tidak menyentuh teks lebih dulu (2, 3, 6). Jangan bersamaan dengan G2-WEB-A pada folder yang sama. Satu pemilik untuk G2 (UX-4 tidak dikerjakan dua kali). E2E: nama berkas berubah, teks hanya berubah di keadaan galat dan kosong; QA diberi tahu per PR.
- Rollback: satu komponen per PR; alias lama dipertahankan sampai PR hapus terakhir.

### UT-1 dan G3 - Bahasa dan bantuan (6-8 hari, 5 PR) setelah G2
- Isi: UX-2 dan glosarium: U-09 (istilah campur; menu dan layar), U-21 (sisa), U-34 (sentence case), U-38 (`formatRupiah`, `formatDateRange`); U-07 (halaman Bantuan per peran, ikon "?" kontekstual pada Alokasi, Tugas klien, K3, Jenis pekerjaan, keadaan kosong yang mengajak); U-32 (pintasan terdokumentasi); U-16 (filter diingat per halaman dan chip "Filter aktif").
- Mengapa: Learnability adalah aspek terburuk (1,31) dan H10 rata-rata tertinggi (1,80). Teks dan bantuan baru layak ditulis setelah komponen stabil agar tidak ditulis dua kali. Menjadi dasar UT-1.
- Definisi selesai: tes glosarium (Fase 5 v1 butir 3.2) menyusut ke baseline 0 di berkas yang disentuh; halaman Bantuan dapat dijangkau dari tautan tetap; isi disetujui pemilik.
- Tes: tes pemindai istilah; Testing Library untuk Bantuan dan chip filter; uji awam 3 orang (istilah baru) sebelum merge (aturan UX-2).
- Titik aman: web saja. Teks yang dicari E2E berubah: QA diberi daftar sebelum merge. Keputusan pemilik: padanan istilah dan isi Bantuan (bagian 7).
- Uji kegunaan UT-1 (peran HR, PM, OM, FIN, HSE, SA; skenario di audit bagian 7) dijalankan setelah gelombang ini; hasil menentukan prioritas G4.

### G4 - Efisiensi ahli dan kendali (10-14 hari, 8-10 PR; menyentuh API secara opsional)
- Isi: U-04 (undo untuk penghapusan lunak: hook `useUndoableDelete` + endpoint pulihkan), U-03 (peringatan sesi 5 menit, kembali ke halaman semula), U-17 dan U-18 (urut kolom lewat `ListParams` opsional; nama entitas di audit), U-27 (persetujuan massal terbatas), U-15 lanjutan (draf form panjang).
- Mengapa: dampak besar untuk HR/OM/FIN yang bekerja berulang (Efficiency 1,19), tetapi butuh keputusan bisnis dan perubahan API; karena itu setelah komponen dan bahasa selesai. Undo adalah satu-satunya jaring pengaman untuk kesalahan yang lolos konfirmasi (NN/g: konfirmasi yang diulang menjadi refleks).
- Definisi selesai: setiap hapus lunak memunculkan "Urungkan" 8 detik dan tervalidasi tes; tabel utama (audit, direktori, survei, rekap) bisa diurut; peringatan sesi tampil di tes dengan jam palsu; parameter API baru opsional (APK lama tetap jalan); snapshot OpenAPI dan tipe web diperbarui.
- Tes: tes API (matriks peran, endpoint pulihkan tidak bisa memulihkan lintas kantor, parameter urut daftar putih kolom, tanpa `LIKE` depan dan `OFFSET` baru) dijalankan sesuai aturan pemilik (xdist `-n 4`, DB uji `vms_test`); tes web; `UPDATE_OPENAPI_SNAPSHOT=1` lalu `npm run gen:api`.
- Titik aman terhadap RLS: endpoint tambahan memakai repositori yang sama dan sesi DB berperan; pulihkan memakai kolom `delete_at` yang sudah ada sehingga diharapkan tanpa migrasi (verifikasi V11). Jadwalkan setelah J6 dan G2-RLS (v2_0037-v2_0045) merge, atau pastikan tidak menambah migrasi; tidak boleh menambah `OFFSET`/`LIKE` baru (`KNOWN` hanya menyusut); urut memakai keyset atau indeks yang ada. E2E: aksi hapus kini punya "Urungkan"; QA menambah kasus pulih.
- Rollback: tiap fitur satu PR; flag UI bila perlu; endpoint tambahan tidak merusak klien lama.

### G5 - Tata letak dan pemecahan berkas web (11-13 hari, 10-12 PR; = UX-3 + Fase 2 web)
- Isi: UX-3 (rincian dua kolom 61,8:38,2, spasi kotak info dialog, lebar konten 1200 dan kolom baca 65ch), U-23 (sidebar dapat dilipat), U-30 (form panjang dikelompokkan, contoh isian), U-41 (satu aksi utama per tampilan), U-31 dan v1 Fase 2 web (pecah 13 `.tsx` lebih dari 300 baris, dimulai dari `WorkOrderSurveyReviewModal` 667, `HseCampaignsPanel` 642, `OfficeCheckInCard` 555).
- Mengapa: H8 (minimalis) dan beban kognitif form panjang; pemecahan berkas paling aman setelah komponen bersama stabil (G2) karena bagian yang dipecah sudah memakai komponen baru. Tidak mendesak, maka belakangan.
- Definisi selesai: tidak ada `.tsx` lebih dari 500 baris, maksimal 3 lebih dari 300 (metrik v1); halaman rincian dua kolom pada 1280; tangkapan 375/768/1280 tanpa meluap.
- Tes: Vitest penuh tanpa perubahan jumlah tes; tangkapan; tes teks panjang 120 huruf pada kartu dan tabel.
- Titik aman: web saja; hindari folder yang sedang dikerjakan jalur lain (G2-WEB-A, G2-SPK pada modul klien). E2E: tata letak berubah; QA mengulang regresi tampilan.

### G6 - Mekanis (5-7 hari, 7-8 PR; = Fase 4 + Fase 5 v1 = UX-7)
- Isi: pindahkan tes ke samping berkas (Fase 4); `design/tokens.json` dan generator, tes paritas web dan mobile, tes glosarium dari `design/glosarium.json` (Fase 5).
- Mengapa: pemindahan murni dan token tidak mengubah perilaku; lebih aman setelah lokasi komponen stabil (G2, G5) dan setelah UX-5.
- Definisi selesai, tes, rollback: sesuai v1 Fase 4 dan 5 (jumlah tes sama sebelum dan sesudah; golden mobile berubah hanya dengan alasan).
- UT-2 dijalankan setelah G4 dan sebelum rilis MINOR yang memuatnya.

### Jalur mobile paralel (tidak diaudit ulang di v2; urutan v1 dipertahankan)
UX-5 (token warna dan tombol 48 dp, 1-2 hari) -> Fase 2 mobile (pecah `vms_ui.dart`, `vms_api.dart`, lima layar besar; 8-9 hari) -> Fase 3 (repository per fitur; 8-10 hari) -> UX-6 (filter jadwal satu tombol, kartu hero, `EmptyState` seragam; 2 hari, uji HP nyata wajib). Titik aman v1 berlaku: jangan bersamaan dengan G2-FACE di `attendance_screen.dart`; `vms_api.dart` setelah J3, G2-FACE, G2-ASET, G2-INSP mobile selesai. Aturan uji HP: HP uji, bukan aplikasi produksi, tanpa restart adb.

## 5. Aturan desain web (turunan 10 heuristik) dan penegakannya
Aturan ini wajib untuk kode web baru dan yang disentuh. Kolom "Penegakan" memakai mekanisme yang sudah ada (ESLint, Vitest arsitektur, tes komponen); butir bertanda (baru) dibuat di G0 atau G2. Tahap awal: peringatan dengan baseline, lalu galat setelah bersih (prinsip v1).
| No | Heuristik | Aturan | Cara menegakkan |
|---|---|---|---|
| R1 | H1, H5 | Tombol kirim nonaktif dan berlabel proses ("Menyimpan…") selama `pending`; tombol nonaktif karena izin atau syarat wajib punya alasan terlihat. Isian tak valid: tampilkan pesan di kolom, jangan abu-abu tanpa sebab | Prop `pending` di `Button` (baru, G2); tes komponen klik ganda; tes arsitektur: `disabled={*.isPending}` manual menyusut |
| R2 | H3, H5 | Aksi merusak: `ConfirmDialog` yang menyebut nama objek dan akibat, tombol bernama aksi (bukan "Ya"), varian destruktif; aksi permanen: ketik "HAPUS"; penghapusan lunak: ditambah toast "Urungkan" (setelah G4). Tidak memakai `window.confirm` | Tes arsitektur: berkas yang memanggil `use(Delete|Remove|Deactivate)*` atau `delete*Service` wajib mengimpor `ConfirmDialog`, `DeleteConfirmButton`, atau `useUndoableDelete` (baseline); `confirmLabel` wajib di tipe |
| R3 | H9 | Pesan galat berformat apa-mengapa-solusi dalam Bahasa Indonesia sederhana, tanpa kode galat; pesan server menang atas teks cadangan; jangan hapus isian pengguna | Wajib `errorMessage(err, cadangan)`; lint `no-restricted-syntax` `CatchClause` tanpa parameter (baseline 18); tes `errors.test.ts` memeriksa pemetaan status |
| R4 | H9, H5 | Validasi di kolom (Zod + `Field`), bukan toast; toast hanya untuk hasil aksi; galat tidak muncul sebelum pengguna sempat mengisi; fokus ke kolom galat pertama | Tes Testing Library `aria-invalid` dan fokus; tes arsitektur menyusut: `toast.error("…")` berliteral di fungsi validasi |
| R5 | H1 | Lima kondisi layar lewat `QueryState` v2: memuat (berlabel), kosong dua jenis, galat berpenyebab, sebagian/offline, sukses. Aksi lebih dari 1 detik punya indikator, unggahan punya persen | Tes arsitektur: `useQuery` pada organisme/halaman harus dibungkus `QueryState`; tes komponen empat kondisi; `UploadField` satu-satunya pintu `type="file"` |
| R6 | H2 | Bahasa Indonesia sederhana sesuai glosarium; istilah teknis diganti kecuali OM/PM; satu kalimat penjelasan untuk istilah yang tidak bisa diganti | Tes glosarium (Fase 5 v1, `design/glosarium.json`) memindai literal di `components/` dan `pages/` |
| R7 | H4 | Sentence case untuk label, judul, tombol; judul halaman sama dengan label menu | Tes pemindai Title Case pada `label=`, `placeholder=`, `title=` (baseline 83); `pageTitle.ts` sumber tunggal |
| R8 | H4 | Tanggal, angka, uang, jarak hanya lewat `lib/format.ts` (`formatDate`, `formatDateRange` dengan tahun, `formatRupiah`); isian tanggal lewat `DateField` berformat Indonesia dengan contoh | ESLint `no-restricted-syntax` `toLocale*String` di luar `lib/format.ts`; larang `` `Rp ${` `` literal |
| R9 | H4, H8 | Tata letak tombol: Simpan kanan dan Batal kiri (desktop), satu aksi utama per tampilan, varian destruktif hanya untuk hapus, target minimal 44 px (kebijakan VMS; minimum WCAG 2.5.8 adalah 24 px), tombol ikon wajib `aria-label` dan tooltip | `DialogActions` satu-satunya footer form; tes `h-8/h-9` penjaga yang sudah ada (#461); `no-restricted-syntax` ikon-saja tanpa `aria-label` |
| R10 | H6 | Label di atas kolom, petunjuk dan contoh di bawah (bukan placeholder), "(opsional)" untuk yang tidak wajib, nilai bawaan yang aman, pilihan "Pilih ..." tanpa tanda "--" | `Field` hanya menerima `hint`; tes pemindai placeholder panjang dan "-- " |
| R11 | H6, H3 | Pengguna selalu tahu lokasinya: judul = menu, breadcrumb di halaman detail, maksimal satu baris tab per tingkat; keluar dari form kotor meminta konfirmasi | `Breadcrumb` di `PageHeader`; penjaga `dialogGuard` plus `useBlocker`; tes `navigation.test.tsx` diperluas |
| R12 | H7 | Daftar: cari awalan, urut, filter diingat dan terlihat (chip), total (`X-Total-Count`), aksi massal bila pekerjaan berulang; pintasan terdokumentasi dan bukan satu huruf tanpa pengaman (WCAG 2.1.4) | `useListControls` diperluas; `ListToolbar` wajib; tes perilaku |
| R13 | H10 | Bantuan dalam konteks: ikon "?" pada form rumit, tautan Bantuan di tempat tetap (WCAG 3.2.6), keadaan kosong yang mengajak bertindak | Daftar periksa PR; tes keberadaan tautan Bantuan di `AppShell` |
| R14 | H1, H3 | Sesi: peringatan 5 menit sebelum habis, kembali ke halaman semula setelah masuk, banner offline global | Tes dengan jam palsu; `useOnline` di `AppShell` |
| R15 | H1 | Status penting lewat `role="status"`/`role="alert"`/`aria-live` (WCAG 4.1.3); skeleton berlabel | Tes komponen; tes arsitektur memeriksa `aria-hidden` pada skeleton menyusut |
Prinsip kebijakan R1: G1 (GOV.UK Button) menyarankan menghindari tombol nonaktif karena kontras buruk dan membingungkan, dan N6 (NN/g) menyebut galat terlalu dini sebagai pola memusuhi. Karena itu aturan R1 berbeda dari usulan "nonaktif sampai valid"; keputusan pemilik di bagian 7.

### Checklist PR web (salin ke deskripsi PR; hanya butir relevan)
- [ ] Tombol kirim memakai `pending` dan tidak bisa diklik ganda (R1)
- [ ] Aksi hapus/merusak lewat `ConfirmDialog` bernama objek dan akibat; permanen minta ketik "HAPUS"; bisa urung bila lunak (R2)
- [ ] Setiap `catch` memakai `errorMessage(err, "apa-mengapa-solusi")` (R3)
- [ ] Validasi di kolom dengan `Field`; fokus ke galat pertama; toast hanya untuk hasil (R4)
- [ ] Halaman dan daftar lewat `QueryState` v2; kosong dua jenis; unggahan lewat `UploadField` dengan persen (R5)
- [ ] Teks sesuai glosarium dan sentence case; judul sama dengan menu (R6, R7)
- [ ] Tanggal, angka, uang lewat `lib/format.ts` dan `DateField` (R8)
- [ ] Simpan kanan, Batal kiri; satu aksi utama; target 44 px; ikon-saja ber-`aria-label` (R9)
- [ ] Petunjuk di bawah label, bukan placeholder; contoh format (R10)
- [ ] Breadcrumb di halaman detail; filter terlihat dan bisa diatur ulang (R11, R12)
- [ ] Istilah baru punya penjelasan dan tercatat di glosarium; Bantuan diperbarui bila alur baru (R13)
- [ ] Tangkapan 375/768/1280; teks 120 huruf tidak meluap; `bash scripts/verify.sh web` hijau

## 6. Estimasi dan metrik
| Gelombang | Hari engineer | PR | Prasyarat |
|---|---|---|---|
| G0 Penegak | 4-5 | 5 | tidak ada |
| G1 Pengaman cepat | 4-5 | 6-8 | G0 (PR 0.5) |
| G2 Komponen bersama | 10-12 | 8-10 | G0; UX-2/J1 merge untuk butir bertemu teks |
| G3 Bahasa dan bantuan | 6-8 | 5 | G2; keputusan istilah dan isi Bantuan |
| G4 Efisiensi ahli | 10-14 | 8-10 | G2, G3; keputusan pemilik; J6/G2-RLS bila menyentuh `db/` |
| G5 Tata letak dan pecah berkas | 11-13 | 10-12 | G2; folder tidak bersamaan jalur lain |
| G6 Mekanis | 5-7 | 7-8 | G2, G5, UX-5 |
| Jalur mobile (UX-5, Fase 2, 3, UX-6) | 19-23 | sekitar 25 | G0 (PR 0.3, 0.4) |
Total kasar 69-87 hari engineer (web dan bersama 50-64, mobile 19-23); dengan tiga jalur paralel dan peninjauan, sekitar 6-9 minggu kalender. Hanya G0 yang menjadi prasyarat; G1 sendiri sudah menutup dua temuan P0. Gelombang boleh dihentikan setelah mana pun tanpa merusak hasil sebelumnya. Kriteria rem v1 berlaku (dua fase berturut-turut menaikkan waktu review atau regresi produksi: berhenti dan tinjau dengan pemilik).
Metrik tambahan (dicatat di deskripsi PR gelombang): jumlah `catch` tanpa variabel (18 -> 0), `toast.error` berliteral (33 -> turun), berkas `type="file"` di luar `UploadField` (11 -> 0), aksi hapus tanpa konfirmasi (2 -> 0), label Title Case (83 -> 0), halaman tanpa `QueryState` (tes G0), skor rata-rata heuristik (audit ulang setelah G3 dan G4), serta TSR, ER, SEQ per peran dari uji kegunaan (target: TSR ketat naik minimal 15 poin, ER turun minimal 30% pada tugas U-01..U-10). Metrik v1 (berkas besar, impor Modal, dst.) tetap.

## 7. Keputusan untuk pemilik (bahasa awam)
1. Tombol Simpan: apakah (a) abu-abu hanya saat sedang diproses atau tak berizin, dan isian yang salah diberi pesan di kolomnya (saran, lebih jelas bagi pengguna), atau (b) abu-abu sampai semua kolom wajib terisi? Saran: (a).
2. Bahasa baru untuk istilah teknis (Tugas Klien (WO), K3 / HSE, Offboarding, Audit log, Geofence, BAST, BOM, Master Klien, "bawaan item"): setujui padanan di glosarium lalu uji ke 3 orang awam. OM dan PM tetap.
3. Halaman Bantuan: siapa yang menulis isinya dan apakah per peran atau satu untuk semua. Saran: per peran, 5-8 tugas tersering.
4. "Urungkan" setelah menghapus: berapa lama masih bisa dipulihkan (saran: 8 detik di layar, data tetap bisa dipulihkan admin sampai batas retensi 30 hari yang sudah ada)? Menyentuh keputusan PDP dan retensi.
5. Setujui banyak sekaligus (cuti, lembur): siapa boleh dan batas jumlah per kali? Ini aturan bisnis.
6. Sesi 24 jam: tetap 24 jam mutlak dengan peringatan 5 menit, atau diperpanjang selama pengguna aktif? Menyentuh keamanan.
7. Jadwal uji kegunaan: 5 orang per peran (HR, PM, OM, FIN, HSE) dan 3 orang untuk Super Admin; siapa yang direkrut dan kapan UT-0 (garis dasar sebelum perbaikan).

## 8. Butir verifikasi tambahan (menambah V1-V9 v1)
| Kode | Butir | Cara cek | Keluaran |
|---|---|---|---|
| V10 | Form manual (tanpa react-hook-form) memfokuskan galat pertama? | baca form `useState` di dialog; uji dengan pembaca layar | daftar form yang perlu `Field` v2 |
| V11 | Endpoint pulihkan cukup dengan kolom `delete_at` yang ada tanpa migrasi | baca repositori hapus lunak dan `brief-hapus-terjadwal-restore.md` | memutuskan apakah G4 menyentuh rantai migrasi |
| V12 | Pemasangan axe/aturan a11y di Vitest atau E2E | `npm view` dan percobaan | tes kontras dan label otomatis, atau tunda |
| V13 | 3 berkas bermutasi tanpa penanda pending (`NotificationBell`, `SurveyLayoutMap`, `WeeklyPresentationDialog`) | baca berkas | nol atau perbaikan G2 |
| V14 | 13 sisa `h-8/h-9` (UX-1) | grep dan tangkapan | selesai atau dibiarkan beralasan |
| V15 | Status J1, J3, G2-WEB-A, G2-B30 di riwayat git | `git log` dan daftar PR | memastikan syarat G2 dan G3 terpenuhi |
Batas audit: skor adalah perkiraan ahli dari kode dan tangkapan layar tanpa server hidup, tanpa uji pengguna dan tanpa pengukuran kontras; halaman yang tidak dipotret tidak dilihat secara visual.

## Lampiran A: Indeks temuan U-xx -> gelombang
| Gelombang | Temuan |
|---|---|
| G1 | U-01, U-02, U-10, U-21, U-25, U-26, U-35, U-36, U-37, U-42 |
| G2 | U-05, U-06, U-08, U-11, U-12, U-13, U-14, U-15, U-19, U-20, U-22, U-24, U-28, U-29, U-33, U-39, U-40 |
| G3 | U-07, U-09, U-16, U-32, U-34, U-38 |
| G4 | U-03, U-04, U-17, U-18, U-27 |
| G5 | U-23, U-30, U-31, U-41 |
Keparahan: P0 = U-01, U-02. P1 = U-03..U-10. P2 = U-11..U-31. P3 = U-32..U-42. Rincian (heuristik, halaman, bukti, usulan, ukuran, dependensi) ada di `audit-usability-web.md` bagian 5.

## Lampiran B: rujukan kegunaan (dibaca langsung dari sumber)
- NN/g, 10 Usability Heuristics: https://www.nngroup.com/articles/ten-usability-heuristics/
- NN/g, Usability 101 (5 aspek): https://www.nngroup.com/articles/usability-101-introduction-to-usability/
- NN/g, Success Rate: https://www.nngroup.com/articles/success-rate-the-simplest-usability-metric/
- NN/g, How Many Test Users: https://www.nngroup.com/articles/how-many-test-users/
- NN/g, SUS, NASA-TLX, SEQ: https://www.nngroup.com/articles/measuring-perceived-usability/
- NN/g, Error-Message Guidelines: https://www.nngroup.com/articles/error-message-guidelines/
- NN/g, Confirmation Dialogs: https://www.nngroup.com/articles/confirmation-dialog/
- NN/g, Progress Indicators: https://www.nngroup.com/articles/progress-indicators/
- NN/g, User Control and Freedom: https://www.nngroup.com/articles/user-control-and-freedom/
- GOV.UK Design System, Error message: https://design-system.service.gov.uk/components/error-message/ ; Button: https://design-system.service.gov.uk/components/button/
- WCAG 2.2 Understanding: 3.3.1 error-identification, 3.3.3 error-suggestion, 3.3.4 error-prevention-legal-financial-data, 4.1.3 status-messages, 2.2.1 timing-adjustable, 2.1.4 character-key-shortcuts, 2.5.8 target-size-minimum, 3.2.6 consistent-help, 3.3.7 redundant-entry (https://www.w3.org/WAI/WCAG22/Understanding/)
Semua rujukan eksternal di atas diambil dan dibaca pada 2026-11-11. Rujukan struktur kode (W1-W11, M1-M12) ada di lampiran v1.
