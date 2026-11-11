# Audit kegunaan (usability) web VMS - pindai ulang

Dasar: `origin/development` adda1521, VERSION 1.8.4, 2026-11-11. Hanya baca dan dokumen; tidak ada kode aplikasi diubah. Server mati: bukti dari kode `web/src` dan tangkapan layar di scratchpad (`bukti-e2e-v2\*.png`, `g2-*.png`).
Kerangka: (A) 10 heuristik Nielsen, (B) 5 aspek usability Nielsen, (C) metrik uji kegunaan. Berkas `riset-uiux.md` tidak ditemukan di mana pun (tidak dipakai); `audit-uiux.md` dan `backlog-temuan.md` dipakai sebagai bahan.

## 0. Dasar rujukan (diambil langsung dari sumber resmi, bukan dari ingatan)
| Kode | Sumber | Dipakai untuk |
|---|---|---|
| N1 | NN/g, 10 Usability Heuristics (nngroup.com/articles/ten-usability-heuristics) | definisi H1-H10. Kutipan inti: H5 "cegah dulu, atau cek dan minta konfirmasi sebelum aksi"; H9 "bahasa sederhana (tanpa kode galat), tunjuk masalah tepat, beri solusi"; H7 "pintasan disembunyikan dari pemula"; H3 "dukung Undo dan Redo, tombol keluar yang jelas" |
| N2 | NN/g, Usability 101 | 5 aspek: learnability, efficiency, memorability, errors, satisfaction |
| N3 | NN/g, Success Rate: The Simplest Usability Metric | tingkat selesai dengan nilai sebagian (selesai bersih, selesai dengan masalah kecil, masalah besar, gagal) |
| N4 | NN/g, How Many Test Users | 5 pengguna per kelompok untuk uji kualitatif; 3-4 bila peran mirip |
| N5 | NN/g, Beyond NPS: SUS, NASA-TLX, SEQ | SUS butuh sekitar 20-30 responden untuk angka yang bisa digeneralisasi; dengan 5 orang pakai sebagai indikator saja; SEQ per tugas |
| N6 | NN/g, Error-Message Guidelines | terlihat jelas, bahasa manusia, saran perbaikan, jangan tampilkan galat terlalu dini, pertahankan isian |
| N7 | NN/g, Confirmation Dialogs Can Prevent User Errors | konfirmasi harus menyebut objek dan akibat, jangan dipakai berlebihan agar tidak jadi refleks |
| N8 | NN/g, Progress Indicators | indikator untuk aksi di atas sekitar 1 detik; spinner untuk 2-10 detik; persen selesai untuk 10 detik atau lebih |
| N9 | NN/g, User Control and Freedom | tombol Batal, Undo, "pintu darurat" |
| G1 | GOV.UK Design System: Error message, Button | pesan galat = apa yang salah + cara memperbaiki; jangan hapus isian; tombol nonaktif "hindari bila mungkin" karena kontras buruk dan membingungkan |
| W1 | WCAG 2.2: 3.3.1 Error Identification, 3.3.3 Error Suggestion, 3.3.4 Error Prevention (Legal, Financial, Data) = terbalikkan / dicek / dikonfirmasi, 4.1.3 Status Messages, 2.2.1 Timing Adjustable, 2.1.4 Character Key Shortcuts, 2.5.8 Target Size (Minimum) 24x24 px, 3.2.6 Consistent Help, 3.3.7 Redundant Entry | dasar teknis aturan; kebijakan VMS 44 px lebih ketat dari minimum AA 24 px |
Catatan jujur: H1 sampai H10 dinilai oleh pengaudit dari kode, bukan oleh evaluator ganda; NN/g menyarankan beberapa evaluator. Skor adalah perkiraan ahli, bukan hasil ukur pengguna.

## 1. Metode dan batas
1. Komponen bersama dibaca penuh: `QueryState`, `ConfirmDialog`, `DeleteConfirmButton`, `DialogActions`, `VmsDialog`, `Field`, `errors.ts`, `format.ts`, `useListControls`, `PageHeader`, `navigation.ts`, `sessionStore.ts`, `apiClient.ts`, `LoginForm`.
2. Pola dipindai dengan pencarian di seluruh `web/src` (angka di bagian 3). Hasil nol dicatat sebagai bukti ketiadaan.
3. Tangkapan layar yang dibaca: `g2-klien-err`, `g2-l5-galatassets`, `g2-sites-hapus`, `g2-m375-dialog`, `g2-audit`, `g2-wt-form`, `A7-05-tolak-kosong`, `A4-01-alokasi`; sisanya dipakai lewat nama (inventaris backlog dan audit-uiux).
4. Skor per halaman = skor dasar komponen bersama + penyesuaian dari bukti halaman itu. Halaman tanpa bukti khusus mewarisi skor dasar; ditandai "warisan" di kolom bukti bila relevan. Batas: tidak ada uji pengguna, tidak ada pengukuran kontras, halaman yang tidak dipotret tidak dilihat secara visual.
5. Skala: 0 tidak ada masalah, 1 minor, 2 mayor, 3 kritis. Keparahan temuan: P0 berisiko kehilangan data atau menggagalkan tugas tanpa jalan keluar; P1 menghambat tugas atau sering menyebabkan salah; P2 memperlambat atau membingungkan; P3 kosmetik atau kebiasaan ahli.

## 2. Matriks halaman x heuristik (30 baris: 28 folder halaman + shell; auth dipecah 3 baris)
H1 Status sistem | H2 Cocok dengan dunia nyata (bahasa) | H3 Kendali dan kebebasan | H4 Konsistensi | H5 Cegah galat | H6 Kenali, bukan ingat | H7 Fleksibilitas dan efisiensi | H8 Minimalis | H9 Kenali dan pulih dari galat | H10 Bantuan dan dokumentasi.

| Halaman | H1 | H2 | H3 | H4 | H5 | H6 | H7 | H8 | H9 | H10 | Jumlah | Bukti utama |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Shell: layout, sidebar, header | 1 | 1 | 2 | 2 | 0 | 1 | 2 | 1 | 1 | 3 | 14 | `app/navigation.ts:39,44,49-50,57,62`; `g2-l5-galatassets.png` (sidebar terpotong); tanpa breadcrumb dan bantuan; `stores/sessionStore.ts:74-88` |
| Login | 1 | 0 | 1 | 1 | 1 | 0 | 2 | 0 | 1 | 1 | 8 | `LoginForm.tsx:82,87` (tanpa tombol lihat sandi); kunci sementara jelas; `DeviceLimitHelpDialog` |
| Ganti sandi | 1 | 0 | 1 | 1 | 1 | 0 | 2 | 0 | 1 | 1 | 8 | `ChangePasswordForm.tsx:41` (aturan sandi tertulis); tanpa lihat sandi |
| Penyiapan awal (setup) | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 1 | 7 | `SetupForm.tsx:37,56,64` (aria-live, petunjuk kode) |
| Akun dan keamanan (account) | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 11 | `AccountSummaryCard`, `AccountSessionsPanel` memakai ConfirmDialog (warisan) |
| Alokasi mingguan (alokasi) | 1 | 2 | 2 | 2 | 2 | 2 | 1 | 2 | 1 | 3 | 18 | `AllocToolbar.tsx:61,64` nonaktif tanpa alasan; `A4-01-alokasi.png` (SIAGA vs Siaga, rentang tanpa tahun, 4 kontrol sejajar) |
| Kendaraan dan alat (assets) | 1 | 1 | 2 | 2 | 1 | 1 | 2 | 1 | 2 | 2 | 15 | `g2-l5-galatassets.png`: "Daftar kendaraan tidak dapat dimuat" tanpa sebab, toast K3 nyasar |
| Absensi (attendance) | 1 | 1 | 2 | 1 | 1 | 1 | 2 | 2 | 2 | 2 | 15 | `OfficeCheckInCard.tsx:330-348` (lima banner status/alert); `AttendanceList.tsx:61` (Rp manual), `:118` DeleteConfirmButton |
| Riwayat aktivitas (audit) | 1 | 2 | 1 | 2 | 0 | 2 | 2 | 1 | 1 | 2 | 14 | `g2-audit.png`: tanggal mm/dd/yyyy, "Akun pengguna 1d14ca72", tanpa urut, judul beda dari menu "Audit log" |
| Klien (clients) | 1 | 2 | 2 | 2 | 3 | 1 | 2 | 1 | 2 | 2 | 18 | `ClientSitesModal.tsx:136-142,333` hapus tanpa konfirmasi; `:85-106` validasi lewat toast; `:131,140` galat tetap; `:208` "Geofence"; `g2-klien-err.png` (nama meluap, dua baris tab) |
| Direktori karyawan (directory) | 1 | 1 | 2 | 2 | 1 | 1 | 2 | 1 | 1 | 2 | 14 | `DocumentsPanel.tsx:76-77,206-211` konfirmasi dua-langkah (pola ketiga); `DeleteConfirmButton`; `EmployeeCreateDialog` (form panjang) |
| Divisi dan jabatan (divisions) | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 11 | `MasterRemoveDialog.tsx:20-36` konfirmasi + `errorMessage` dengan cadangan (pola baik); `DivisionList.tsx:55,87` |
| Wajah (face) | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 11 | `FaceCamera.tsx:132,142` (petunjuk aria-live, galat role=alert) |
| Beranda (home) | 1 | 1 | 0 | 1 | 0 | 1 | 1 | 1 | 1 | 2 | 9 | `HomeStatGrid`, `HomeQueueCard`; tidak ada aksi merusak |
| K3/HSE (hse) | 1 | 2 | 2 | 2 | 2 | 1 | 2 | 2 | 2 | 2 | 18 | `HseCampaignsPanel.tsx` (642 baris); `HseCampaignPhotosField.tsx:99-103` hapus foto tanpa konfirmasi (lokal, belum disimpan); `HseMandatoryPopupGate.tsx:76` toast global |
| Cuti dan izin (leaves) | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 1 | 11 | `LeaveReviewDialog.tsx:30,152,160` galat di kotak terpisah, kolom tidak ditandai; label Title Case; `A7-05-tolak-kosong.png` |
| Mess | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 1 | 1 | 2 | 12 | `MessList`, `MessPlaceList`, `MessRequestList` memakai ConfirmDialog; tanpa urut |
| Rekap (monitoring) | 1 | 1 | 1 | 1 | 0 | 1 | 2 | 1 | 1 | 2 | 11 | `AttendanceRecapSummary`, `OvertimeRecapList`; tanpa urut dan filter tersimpan |
| Offboarding | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 12 | `OffboardingAddButton.tsx:5` istilah; `OffboardingDetailDialog.tsx:35` validasi lewat toast |
| Lembur (overtime) | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 10 | `OvertimeApplyDialog.tsx:28` satu-satunya pemakai `useOnline` |
| Proyek (projects) | 1 | 2 | 1 | 2 | 1 | 1 | 2 | 1 | 2 | 1 | 14 | `ProjectFormDialog.tsx` (10 label Title Case); "Master Proyek (SPK)" (`g2-klien-err.png`) |
| Lokasi kerja (sites) | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 9 | `g2-sites-hapus.png` konfirmasi menyebut nama dan akibat (pola baik); `SiteMapPicker.tsx:69` |
| Survei (surveys) | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 1 | 2 | 2 | 13 | `SurveyBomPanel.tsx:139`, `SurveyReviewBar.tsx:95` validasi lewat toast |
| Halaman sistem (system) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | `RouteErrorPage.tsx:9-17` apa-mengapa-solusi (pola baik) |
| Tim lapangan (teams) | 1 | 1 | 2 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 12 | `TeamsTemplate.tsx` memakai ConfirmDialog; tanpa urut |
| Verifikasi (verify) | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 2 | 10 | `CompletionVerificationCard.tsx`; halaman baca saja |
| Penyelesaian kerja (work-completions) | 1 | 2 | 2 | 2 | 2 | 1 | 2 | 2 | 3 | 2 | 19 | `WorkCompletionBomTable.tsx:111,130,144,446` galat tetap; `WorkCompletionDetailModal.tsx:241,275,304`; `WorkCompletionFormDialog` (11 label Title Case) |
| Tugas klien (work-orders) | 1 | 2 | 1 | 2 | 1 | 1 | 2 | 2 | 2 | 3 | 17 | `WorkOrderCreateModal.tsx:188`; `WorkOrderSurveyReviewModal.tsx` (667 baris), `:498` BOM; `WorkOrderBastModal.tsx:32` |
| Jadwal harian (work-plans) | 1 | 2 | 1 | 1 | 2 | 1 | 2 | 2 | 1 | 2 | 15 | `DailyPlanDetailDialog.tsx:35-40,273-287` konfirmasi baik; `DailyItemsPanel.tsx:83` "Putuskan pindah hari" |
| Jenis pekerjaan (work-types) | 1 | 2 | 2 | 1 | 2 | 1 | 1 | 1 | 2 | 2 | 15 | `WorkTypeMaterialsDialog.tsx:130-138,318` hapus tanpa konfirmasi + galat tetap; `g2-wt-form.png` (form panjang, "bawaan item") |

Halaman terburuk (jumlah): Penyelesaian kerja 19; Alokasi mingguan, Klien, K3/HSE 18; Tugas klien 17; Kendaraan dan alat, Absensi, Jadwal harian, Jenis pekerjaan 15. Terbaik: Halaman sistem 1; Lokasi kerja dan Beranda 9.

## 3. Angka pemindaian (bukti ketiadaan dan keberadaan)
| Pola | Hasil | Arti |
|---|---|---|
| `toast` (sonner) | 88 berkas | umpan balik sukses/galat seragam (baik). `main.tsx:20` posisi kanan bawah |
| Undo/Urungkan | 0 | tidak ada mekanisme undo sama sekali (N1 H3, N9) |
| `window.confirm` | 0 | tidak ada dialog bawaan peramban (baik); `ConfirmDialog` di 22 berkas |
| Berkas bermutasi tanpa penanda pending/busy/disabled | 3 dari 89 (`NotificationBell`, `SurveyLayoutMap`, `WeeklyPresentationDialog`) | anti klik ganda sudah hampir menyeluruh (baik); perlu cek 3 berkas |
| `catch {` tanpa variabel galat di `components`/`pages` | 18 | sebab galat dibuang, diganti teks tetap |
| `toast.error("...")` teks tetap | 33 (vs 36 yang memakai `errorMessage`) | setengah galat tidak memuat penyebab |
| `setFocus`/`shouldFocusError`/ringkasan galat | 0 | tidak ada pengelolaan fokus ke galat sendiri (react-hook-form fokus otomatis pada form `register`; form manual belum diverifikasi) |
| `onUploadProgress` | 0 (11 `type="file"`) | tidak ada progres unggah |
| `onKeyDown`/pintasan | 1 berkas (`useTimedCarousel`) | tidak ada pintasan keyboard |
| `aria-sort` | 0 | tabel tanpa urut |
| `useSearchParams` | `useListControls` (14 pemakai `ListToolbar`) | filter tersimpan di URL, tidak lintas kunjungan; tanpa `localStorage` untuk preferensi |
| `Breadcrumb` | 0 | tanpa penunjuk lokasi |
| "Bantuan/FAQ/Tooltip" khusus | 0 halaman bantuan; `title=` 99 (hanya hover), `aria-label` 121 | bantuan hanya `Field hint` dan `DeviceLimitHelpDialog` |
| `useOnline` | 1 pemakai (`OvertimeApplyDialog.tsx:28`) | tanpa banner offline global |
| `aria-busy` | 1 (`PageLoadingFallback`) | skeleton `QueryState` `aria-hidden` (`QueryState.tsx:28-33`) |
| Title Case pada label/placeholder/title | 83 di 28 berkas | tata bahasa label tidak seragam |
| "Memproses…" vs "Menyimpan..." | 74 tiga titik vs 15 elipsis (`ConfirmDialog.tsx:36`, `DialogActions.tsx:33-45`) | dua gaya teks proses |
| `text-[10px]/[11px]`, `h-8/h-9` | 0 dan 13 | UX-1 sebagian besar sudah selesai (sisa 13 `h-8/h-9` perlu dicek) |
| Format tanggal/angka | `lib/format.ts` pusat; langsung `toLocale*` di `WorkCompletionDetailModal.tsx:241,275`, `SelfieCaptureDialog.tsx:94`; `Rp` manual `AttendanceList.tsx:61` | sebagian terpusat |

## 4. Ringkasan skor
Rata-rata 30 baris, urut dari masalah terbesar:
| Heuristik | Rata-rata | Baris skor 3 | Baris skor 2 |
|---|---|---|---|
| H10 Bantuan dan dokumentasi | 1,80 | 3 | 18 |
| H7 Fleksibilitas dan efisiensi | 1,53 | 0 | 17 |
| H9 Kenali dan pulih dari galat | 1,33 | 1 | 9 |
| H4 Konsistensi | 1,30 | 0 | 10 |
| H3 Kendali dan kebebasan | 1,27 | 0 | 10 |
| H2 Cocok dengan dunia nyata | 1,20 | 0 | 10 |
| H8 Minimalis | 1,07 | 0 | 6 |
| H5 Cegah galat | 1,00 | 1 | 5 |
| H1 Status sistem | 0,97 | 0 | 0 |
| H6 Kenali, bukan ingat | 0,93 | 0 | 2 |

Lima aspek (rata-rata heuristik pembentuk; pemetaan adalah pendekatan pengaudit, karena NN/g sendiri menyatakan tidak ada pemetaan satu-satu, N2):
| Aspek | Heuristik pembentuk | Skor | Bacaan |
|---|---|---|---|
| Learnability | H2, H6, H10 | 1,31 | terburuk: tidak ada bantuan, istilah campur, tanpa onboarding peran |
| Errors | H3, H5, H9 | 1,20 | konfirmasi bagus di sebagian besar, tetapi tanpa undo dan galat tetap |
| Efficiency | H1, H7, H8 | 1,19 | tanpa pintasan, urut, filter tersimpan, aksi massal |
| Memorability | H4, H6 | 1,12 | tata letak stabil, tetapi judul beda dari menu, dua baris tab, tiga pola konfirmasi |
| Satisfaction | H1, H4, H8 | 1,11 | terbaik; sistem visual rapi, status sistem baik |
Kekuatan yang harus dipertahankan: `ConfirmDialog` (busy anti klik ganda), `DialogCancelButton` dengan penjaga formulir kotor (`dialogGuard.ts`), `RouteErrorPage`, konfirmasi menyebut nama objek (`g2-sites-hapus.png`), `errorMessage()` dan `translateFieldMessage()` (`errors.ts`), sinkron filter ke URL (`useListControls.ts`), format tanggal WIB terpusat (`format.ts`), `FaceCamera` aria-live.

## 5. Temuan (U-xx)
Ukuran: S sampai 0,5 hari, M 1-2 hari, L 3-5 hari. Dep: Fase 0-5 = rencana struktur kode; UX-1..7 = rencana audit tampilan; API = butuh perubahan backend (opsional, tidak merusak APK lama).

### P0 (2)
| ID | Heuristik | Halaman | Bukti | Usulan | Ukuran | Dep |
|---|---|---|---|---|---|---|
| U-01 | H5, H3 | Klien | `ClientSitesModal.tsx:136-142,333`: tombol Hapus lokasi cabang langsung memanggil API; hanya toast sukses. Lokasi dipakai untuk geofence absensi | Pakai `ConfirmDialog danger` dengan teks "Hapus lokasi {nama}? Absensi di lokasi ini tidak bisa memakainya lagi." (pola `g2-sites-hapus.png`); setelah undo tersedia (U-04) beri tombol "Urungkan" | S | UX-4 (bersatu dengan komponen dialog) |
| U-02 | H9 | Penyelesaian kerja, Klien, Jenis pekerjaan, Alokasi | `catch {` lalu teks tetap: `WorkCompletionBomTable.tsx:111,130,144,446`, `WorkCompletionFormDialog.tsx:167`, `ClientSitesModal.tsx:131,140`, `ClientDeactivateDialog.tsx:25`, `WeekConfirmDialogs.tsx:66`, `WorkTypeMaterialsDialog.tsx:138` | Ganti dengan `catch (err)` dan `toast.error(errorMessage(err, "Gagal menambahkan material. Periksa jumlahnya lalu coba lagi."))`; pesan server (sudah Bahasa Indonesia) menang atas teks cadangan. Lint: larang `catch` tanpa parameter di `components/` dan `pages/` (baseline 18, hanya menyusut) | S-M | Fase 0 (lint) |

### P1 (8)
| ID | Heuristik | Halaman | Bukti | Usulan | Ukuran | Dep |
|---|---|---|---|---|---|---|
| U-03 | H1, H3, H9 | Seluruh aplikasi | `sessionStore.ts:74-88` memanggil `clear()` diam-diam saat batas 24 jam; `apiClient.ts:156` 401 | Banner "Sesi Anda berakhir dalam 5 menit. Simpan pekerjaan Anda." (WCAG 2.2.1); saat habis tampilkan satu pesan di halaman masuk "Sesi berakhir. Masuk lagi untuk melanjutkan" dan kembali ke halaman semula (`lib/safeRedirect.ts` sudah ada). Perlu keputusan: perpanjangan sesi aktif (bisnis/keamanan) | M | API (opsional), ADR keamanan |
| U-04 | H3, H5 | Semua aksi hapus/ubah status | 0 mekanisme Undo | Toast "Dihapus. Urungkan" 8 detik untuk penghapusan lunak (jadwal, dokumen, lokasi, material) lewat satu hook `useUndoableDelete`; memerlukan endpoint pulihkan (lihat `brief-hapus-terjadwal-restore.md` di scratchpad sebagai awal). Aksi permanen tetap ketik "HAPUS" | L | API (restore), Fase 1 |
| U-05 | H9, H1 | Semua daftar | `QueryState.tsx:35-43`: galat hanya `errorText` + "Coba lagi"; `g2-l5-galatassets.png` | `QueryState` membaca `ApiError`/`useOnline`: "Tidak ada koneksi internet", "Anda tidak punya izin melihat ini", "Server sedang sibuk. Coba lagi sebentar lagi"; format baku 'apa-mengapa-solusi' | M | Fase 1 (komponen bersama) |
| U-06 | H9, H5 | Klien, Direktori, Survei, Tugas klien, Offboarding | Validasi lewat toast: `ClientSitesModal.tsx:85-106`, `EmployeeAddressesPanel.tsx:50,54`, `SurveyBomPanel.tsx:139`, `SurveyReviewBar.tsx:95`, `WorkOrderBastModal.tsx:32`, `OffboardingDetailDialog.tsx:35` | Pindah ke skema Zod + `Field error` (galat muncul di kolom, tidak hilang dalam beberapa detik); toast hanya untuk hasil. Lihat N6/W1 3.3.1 | M | Fase 1 |
| U-07 | H10 | Semua; terutama Alokasi, Tugas klien, K3, Jenis pekerjaan | 0 halaman bantuan; hanya `Field hint`, `DeviceLimitHelpDialog` | Halaman "Bantuan" per peran (langkah-langkah tugas umum, glosarium istilah), tautan tetap di footer sidebar (WCAG 3.2.6), ikon "?" kontekstual pada form rumit, keadaan kosong yang mengajak ("Belum ada klien. Tambah klien pertama untuk membuat tugas klien.") | L | Isi bahasa dari pemilik; UX-2 |
| U-08 | H1 | Direktori, Penyelesaian kerja, K3, Offboarding, Survei | `onUploadProgress` 0; 11 `type="file"` (mis. `DocumentsPanel.tsx:318` "maks. 10 MB") | `apiClient` meneruskan `onUploadProgress`; molekul `ProgressBar` ("Mengunggah 45%"); tombol "Coba lagi" bila gagal; N8 | M | Fase 1 |
| U-09 | H2 | Menu dan lebih dari 10 layar | Menu: `navigation.ts:39 "Tugas Klien (WO)"`, `:44 "K3 / HSE"`, `:57 "Offboarding"`, `:62 "Audit log"`; layar: `WorkOrderCreateModal.tsx:188 "Lokasi Site"`, `ClientSitesModal.tsx:208 "Geofence"`, `OffboardingAddButton.tsx:5`, `WorkCompletionDetailModal.tsx:304 "BAST"`, `WorkOrderSurveyReviewModal.tsx:498 "BOM"`, "Master Klien/Master Proyek (SPK)" (`g2-klien-err.png`), "Satuan/Fase bawaan item" (`g2-wt-form.png`), "Putuskan pindah hari" (`DailyItemsPanel.tsx:83`) | Padanan dari glosarium (`vms-ux-design-system/references/glosarium-bahasa.md`); istilah baru diuji 3 orang awam; OM/PM tetap | M | Keputusan pemilik (istilah), UX-2, Fase 5 (tes glosarium) |
| U-10 | H5 | Jenis pekerjaan | `WorkTypeMaterialsDialog.tsx:130-138,318-319`: ikon sampah menghapus material default langsung | `ConfirmDialog` "Hapus material {nama} dari jenis pekerjaan ini?" + teks tombol; galat dari server | S | Fase 1 |

### P2 (21)
| ID | Heuristik | Halaman | Bukti | Usulan | Ukuran | Dep |
|---|---|---|---|---|---|---|
| U-11 | H5, H8 | Klien, Divisi, Penyelesaian kerja | `g2-klien-err.png` "Lokasi Site / Ubah / Hapus" sejajar tanpa jarak; `WorkCompletionBomTable.tsx:309` ikon sampah tanpa teks; `DivisionList.tsx:55,87` | Hapus ke menu "Lainnya" atau dipisah jarak dan berwarna destruktif; ikon saja wajib `aria-label` dan tooltip | S | UX-4 |
| U-12 | H4, H5 | Direktori, Absensi, dll. | Tiga pola konfirmasi: `ConfirmDialog`, `DeleteConfirmButton` (ketik HAPUS, `delete:any`), dua-langkah inline `DocumentsPanel.tsx:206-211` ("Yakin hapus? (salah unggah)"); `ConfirmDialog.tsx:12` default "Ya, lanjutkan" | Satu keluarga: ConfirmDialog (biasa), ConfirmDialog + ketik (permanen); hapus pola inline; `confirmLabel` wajib (N7: tombol menyebut aksi) | S-M | UX-4 |
| U-13 | H1, H6 | Alokasi | `AllocToolbar.tsx:61,64` tombol nonaktif tanpa alasan (`A4-01-alokasi.png` "Salin minggu ke minggu berikutnya" abu-abu) | Teks bantu di bawah/tooltip "Pilih tim dan minggu terlebih dulu" memakai `aria-disabled` dan `aria-describedby`; G1 menyarankan hindari tombol nonaktif bila bisa | S | Fase 1 |
| U-14 | H9, H4 | Audit, Cuti, Lembur, form tanggal | `g2-audit.png` tanggal `mm/dd/yyyy`; backlog: 109 atribut required/min/type=date, hanya 27 berkas `noValidate` | Komponen `DateField` (isian teks `dd/mm/yyyy` + pemilih, petunjuk contoh, validasi sendiri); semua `<form>` `noValidate` dengan pesan Zod; mengikuti W1 3.3.1 | M | Fase 1 |
| U-15 | H3, H5 | Form panjang (karyawan, penyelesaian kerja, proyek) | `dialogGuard.ts` hanya menjaga saat tutup dialog; `beforeunload`/`useBlocker` 0 | Peringatan keluar saat formulir kotor (muat ulang, pindah halaman); draf tersimpan untuk form panjang (W1 3.3.7 mengurangi isian ulang) | M | Fase 1 |
| U-16 | H7, H6 | Semua daftar | `useListControls.ts:22-39` hanya URL; berpindah lewat sidebar mereset | Ingat filter terakhir per halaman (`sessionStorage`, bukan data pribadi), chip "Filter aktif: Status Disetujui [x]" dan tombol "Atur ulang" | M | Fase 1 |
| U-17 | H7 | Audit, Direktori, Survei, Rekap, Mess, Tim | `aria-sort` 0 | Urut kolom (klik judul, `aria-sort`); parameter urut opsional di `ListParams` (daftar putih kolom) | M-L | API (opsional) |
| U-18 | H6, H2 | Audit | `g2-audit.png`: "Akun pengguna 1d14ca72" | Tampilkan nama (server memuat label), ID di rincian saja | M | API |
| U-19 | H1, H4 | Semua daftar | `QueryState.tsx:44-50` satu jenis kosong | Dua jenis: "Belum ada data" (dengan aksi tambah) vs "Tidak ada hasil untuk '...'" (dengan tombol Hapus pencarian); tambah kondisi basi/offline | S-M | Fase 1 |
| U-20 | H1 | Semua daftar | `QueryState.tsx:28-33` skeleton `aria-hidden`; `aria-busy` 1 pemakai | `role="status"` + teks `sr-only` "Memuat daftar"; N8: tampilkan di atas ~1 detik | S | Fase 1 |
| U-21 | H4, H6 | Audit, Klien, Cuti | Menu "Audit log" vs judul "Riwayat aktivitas dan cadangan"; "Klien" vs "Master Klien"; "Cuti dan Izin" vs "Cuti dan Izin Karyawan" | Satu sumber `app/pageTitle.ts` untuk menu, judul, tab browser | S | UX-2 |
| U-22 | H4, H8 | Klien, Alokasi, Absensi | `g2-klien-err.png`: dua baris tab (tab ruang kerja + tab seksi) | Maksimal satu baris tab per tingkat; tab seksi menjadi tab bergaris bawah, tab ruang kerja tetap pil | M | UX-4 |
| U-23 | H8, H6 | Shell | 22 item menu, bagian bawah terpotong (`g2-l5-galatassets.png`, `A1-04`) | Grup bisa dilipat dan diingat; item aktif digulirkan ke tampak; bayangan tepi gulir | M | UX-3 |
| U-24 | H6, H3 | Detail karyawan, Detail survei, Verifikasi | `Breadcrumb` 0 | Molekul `Breadcrumb` di `PageHeader` untuk halaman detail: "Direktori > Nama karyawan" | S-M | Fase 1 |
| U-25 | H9, H1 | Semua halaman | `HseMandatoryPopupGate.tsx:76` toast "Gagal memuat panduan keselamatan kerja" tampil di halaman Kendaraan dan alat (`g2-l5-galatassets.png`) | Beri `id` toast, bawa ke banner dalam popup gate yang punya tombol "Coba lagi"; jangan tampil di halaman tak terkait | S | - |
| U-26 | H8 | Klien, Lokasi | `g2-klien-err.png`: nama panjang meluap keluar kartu | `min-w-0 break-words`/`line-clamp` + `title` penuh; kartu dan sel tabel wajib uji teks 120 huruf | S | UX-3 |
| U-27 | H7 | Cuti, Lembur, Absensi (HR/OM) | Aksi massal hanya "Pilih beberapa sel" (Alokasi); persetujuan satu per satu (`LeaveList`, `OvertimeReviewList`, `AttendanceReviewDialog`) | Pilih beberapa lalu "Setujui terpilih" (hanya yang memenuhi syarat); keputusan bisnis (siapa boleh, batas) | L | Keputusan pemilik, API bulk |
| U-28 | H1 | Semua | `useOnline` 1 pemakai (`OvertimeApplyDialog.tsx:28`) | Banner global "Tidak ada koneksi. Perubahan belum tersimpan" memakai `useOnline`; tombol kirim ditahan | S | Fase 1 |
| U-29 | H9 | Cuti, form dialog | `LeaveReviewDialog.tsx:30,160`: galat di kotak terpisah, kolom tidak ditandai/difokus (`A7-05-tolak-kosong.png`) | `Field error` + `aria-invalid`, fokus ke kolom; ringkasan galat bila lebih dari satu (G1 error summary) | S-M | Fase 1 |
| U-30 | H8, H6 | Jenis pekerjaan, Karyawan baru, Proyek, Penyelesaian kerja | `g2-wt-form.png`: 7+ kolom satu kolom panjang, istilah "bawaan item" | Kelompokkan bagian ("Data dasar", "Bawaan jadwal"), contoh isian di petunjuk, kolom jarang dipakai dalam "Lainnya" | M | UX-3 |
| U-31 | H8 | K3, Tugas klien, Absensi | `HseCampaignsPanel.tsx` 642, `WorkOrderSurveyReviewModal.tsx` 667, `OfficeCheckInCard.tsx` 555 baris (`:330-348` lima banner) | Pecah menjadi bagian bertahap; satu banner prioritas per waktu | L | Fase 2 web |

### P3 (11)
| ID | Heuristik | Halaman | Bukti | Usulan | Ukuran | Dep |
|---|---|---|---|---|---|---|
| U-32 | H7 | Semua | `onKeyDown` hanya `useTimedCarousel` | Pintasan terdokumentasi, tidak satu huruf (W1 2.1.4): "/" saat fokus di luar isian untuk Cari boleh karena bisa dimatikan; Alt+N tambah; daftar di Bantuan | M | U-07 |
| U-33 | H4 | Semua tombol proses | `ConfirmDialog.tsx:36` "Memproses…"; `DialogActions.tsx:33` "Menyimpan..." (74 vs 15) | Satu gaya: "Menyimpan…" lewat prop `pending` pada `Button` | S | U-39 |
| U-34 | H4 | 28 berkas | 83 label Title Case (`LeaveReviewDialog.tsx:152`, `ProjectFormDialog` 10, `WorkCompletionFormDialog` 11) | Sentence case; tes arsitektur memindai literal label | S | Fase 5 (glosarium) |
| U-35 | H4, H6 | Shell | `navigation.ts:49-50` ikon Hourglass dipakai dua menu | Ikon berbeda untuk Rekap lembur | S | - |
| U-36 | H6 | Cuti | `A7-05-tolak-kosong.png` placeholder "Wajib diisi jika menolak..." | Pindah ke petunjuk di bawah label (placeholder hilang saat mengetik) | S | - |
| U-37 | H4 | Tugas klien, Jenis pekerjaan | `WorkOrderCreateModal.tsx:188 "-- Pilih Lokasi Site (Opsional) --"`, `g2-wt-form.png "-- Pilih Divisi --"` | "Pilih divisi" tanpa tanda "--" | S | - |
| U-38 | H4 | Absensi, Alokasi, Penyelesaian kerja | `AttendanceList.tsx:61`, `WorkCompletionDetailModal.tsx:241,275`, `SelfieCaptureDialog.tsx:94`, `A4-01-alokasi.png` "9 November - 15 November" | `formatRupiah`, `formatDateRange` (dengan tahun) di `lib/format.ts`; lint larang `toLocale*String` langsung | S | Fase 0 |
| U-39 | H1, H5 | Semua tombol kirim | `Button` tanpa mode `pending` (label diganti manual); 3 berkas bermutasi tanpa penanda | Prop `pending` pada `Button` (spinner, `aria-busy`, nonaktif); cek 3 berkas | S-M | Fase 1 |
| U-40 | H4 | Dialog sempit | `g2-m375-dialog.png` Simpan di atas Batal; desktop Batal kiri/Simpan kanan (`DialogActions.tsx`) | Pastikan sengaja (pola sentuh); tulis di aturan desain | S | - |
| U-41 | H8 | Klien, Kendaraan dan alat | `g2-klien-err.png` tiga aksi kartu berbobot sama; `g2-l5-galatassets.png` dua tombol Tambah di header | Satu aksi utama per tampilan; aksi lain sekunder atau menu | S | UX-3 |
| U-42 | H7, H5 | Login, Ganti sandi, Setup | `LoginForm.tsx:87` `type="password"` tanpa tombol lihat | Tombol "Tampilkan sandi" (kurangi salah ketik, hindari lockout) | S | - |

Jumlah: P0 2, P1 8, P2 21, P3 11 = 42 temuan. Catatan yang ditandai "perlu verifikasi": U-29 (fokus galat form manual), U-39 (3 berkas), `h-8/h-9` 13 pemakaian (UX-1 sisa), halaman yang tidak dipotret.

## 6. Keputusan yang perlu pemilik
1. Aturan "tombol Simpan nonaktif sampai valid". Rekomendasi: nonaktifkan hanya saat sedang diproses atau tanpa izin; saat isian tidak valid tampilkan pesan di kolom dan fokuskan. Alasan: G1 menyatakan tombol nonaktif berkontras buruk dan membingungkan, N6 menyatakan galat terlalu dini bersifat memusuhi. Pilihan lain: nonaktifkan sampai semua kolom wajib terisi (tanpa validasi format) dengan petunjuk "Lengkapi kolom bertanda wajib".
2. Isi dan bahasa halaman Bantuan (U-07): siapa menulis, per peran atau umum.
3. Undo (U-04): masa pulih (mis. 8 detik di layar, 30 hari di server?), data apa saja yang boleh dipulihkan; menyentuh retensi PDP.
4. Persetujuan massal (U-27): siapa dan batas jumlah.
5. Perpanjangan sesi (U-03): tetap 24 jam absolut dengan peringatan, atau perpanjang saat aktif.

## 7. Rancangan tugas uji kegunaan web per peran
Mengikuti `vms-qa/references/uji-kegunaan.md`, diperluas dengan metrik (C). Akun uji lokal dari `scripts/akun-uji-lokal.txt`; data uji dihapus setelah sesi; tanpa HP produksi; E2E tanpa suntik API/SQL.

### 7.1 Metrik (C)
| Metrik | Definisi dan cara hitung | Satuan |
|---|---|---|
| Task Success Rate (TSR) | Per tugas, empat tingkat (N3): S1 selesai bersih; S2 selesai dengan masalah kecil (satu salah klik, lalu pulih sendiri); S3 selesai dengan masalah besar atau dibantu (macet 2 menit atau lebih); S4 gagal/menyerah. TSR ketat = S1 / semua percobaan; TSR longgar = (S1 + S2) / semua | % |
| Time on Task (ToT) | Detik dari membaca skenario sampai menyatakan selesai; hanya percobaan S1 dan S2 dihitung untuk median; batas = 2 x waktu pakar (QA mencatat dua kali lari sendiri, ambil median) | detik |
| Error Rate (ER) | (jumlah klik atau input yang bukan jalur benar + jumlah pesan galat yang tampil) / jumlah langkah minimum; juga hitung "galat fatal" (aksi merusak tak disengaja) | per tugas |
| SEQ | Pertanyaan 1-7 "Seberapa mudah tugas ini?" setelah tiap tugas | 1-7 |
| SUS | 10 pertanyaan di akhir; dengan 5 orang per peran hanya indikator, rata-rata semua peran digabung (N5) | 0-100 |
| Istilah | Kata yang ditanyakan atau ditafsir salah (masukan glosarium) | daftar |
Peserta: 5 orang per peran awam; HR, PM, OM, FIN, HSE dari pekerja sungguhan atau yang mendekati; SA (Super Admin) 3 orang (peran sempit; N4 membolehkan 3-4 per kelompok bila pengalaman mirip).

### 7.2 Kriteria lulus umum (per peran)
TSR ketat minimal 70% dan TSR longgar minimal 90% atas seluruh tugas; tidak ada tugas S4 pada 2 peserta atau lebih; ToT median setiap tugas di dalam batas; ER rata-rata maksimal 1,0 per tugas dan nol galat fatal; SEQ median minimal 5 dari 7; SUS indikator minimal 68; nol temuan P0/P1 baru yang belum ditangani. Gagal: rilis layar itu ditahan, temuan jadi brief, uji ulang peran itu.

### 7.3 Skenario per peran (tujuan, bukan langkah; jangan sebut nama menu)
| Peran | Tugas | Hasil jadi | Batas | Temuan yang diuji |
|---|---|---|---|---|
| HR (kantor Pekanbaru) | T1 Karyawan baru bernama X mulai Senin; daftarkan dia dan pastikan datanya lengkap. T2 Ada permohonan cuti dari bawahan; selesaikan (setujui satu, tolak satu dengan alasan). T3 Sediakan satu tempat mess untuk karyawan Y. T4 Seorang karyawan berhenti bulan ini; mulai proses keluarnya. T5 Satu dokumen karyawan salah unggah; buang dan ganti | karyawan tercatat; dua keputusan cuti; penempatan mess; proses keluar tercatat; dokumen terganti | 4 menit tiap tugas (T1 6 menit) | U-06, U-09, U-12, U-14, U-29, U-30 |
| PM | T1 Klien baru memesan pekerjaan; catat pekerjaannya. T2 Tugaskan survei ke satu tim pada Selasa depan. T3 Susun jadwal Rabu untuk dua tim lalu ajukan. T4 Pekerjaan klien selesai; minta tanda tangan serah terima. T5 Pindahkan satu pekerjaan ke hari lain | tugas klien dibuat; survei terjadwal; jadwal terbit; serah terima ditandatangani; jadwal bergeser | 4 menit (T4 5 menit) | U-02, U-06, U-09, U-13, U-30, U-31 |
| OM | T1 Lihat siapa belum absen hari ini di wilayah Anda. T2 Setujui tiga permohonan lembur sekaligus. T3 Susun alokasi mingguan: tim A di proyek P Senin-Rabu. T4 Salin alokasi minggu ini ke minggu depan. T5 Cari absensi bulan lalu milik satu karyawan | daftar belum absen; tiga lembur diputuskan; alokasi tersimpan; minggu depan terisi; rekap ditemukan | 3 menit (T3 5 menit) | U-13, U-16, U-17, U-19, U-27, U-07 |
| FIN | T1 Ekspor rekap absensi bulan lalu untuk satu kantor. T2 Cek total lembur satu karyawan bulan ini. T3 Cari lembur yang belum disetujui. T4 Lihat uang makan satu karyawan di tanggal tertentu | berkas rekap; angka lembur; daftar belum disetujui; nominal | 3 menit | U-14, U-16, U-17, U-38, U-18 |
| HSE | T1 Terbitkan panduan keselamatan baru untuk satu kantor dengan dua foto. T2 Ubah urutan foto dan simpan. T3 Arsipkan panduan lama. T4 Lihat siapa sudah membaca | panduan terbit; urutan baru; lama diarsipkan; daftar pembaca | 5 menit (T1 7 menit) | U-08, U-09, U-12, U-31, U-07 |
| SA | T1 Tambah satu kantor/lokasi kerja baru dengan titik peta. T2 Tambah klien lalu tambah lokasi cabangnya, lalu hapus lokasi yang salah. T3 Tambah divisi dan jabatan, ubah peran seorang karyawan. T4 Cari tindakan seseorang kemarin di riwayat aktivitas | lokasi tersimpan; klien dan cabang benar; peran berubah; ditemukan di audit | 5 menit | U-01, U-02, U-11, U-14, U-18, U-21 |

### 7.4 Prosedur dan pelaporan
1. Putaran 1 setelah Gelombang 1-2 rencana v2 (dasar sebelum perbaikan besar: jalankan putaran 0 pada versi sekarang bila ingin garis dasar). Putaran 2 setelah Gelombang 3. Putaran ulang hanya peran yang gagal.
2. Skrip fasilitator dan pencatatan mengikuti `uji-kegunaan.md` bagian 5; catat tiap klik salah dan tiap pesan galat dengan stempel waktu (rekam layar dengan izin).
3. Laporan satu berkas per putaran: tabel tugas x peserta (S1-S4, ToT, ER, SEQ), TSR per tugas dan per peran, SUS indikator, temuan P0-P3 baru dengan tangkapan layar, daftar istilah, putusan LULUS/TIDAK LULUS.
4. Target perbaikan terhadap garis dasar: TSR ketat naik minimal 15 poin, ER turun minimal 30% pada tugas yang menyentuh U-01 sampai U-10.
