# Token, komponen, dan responsif

## 1. Keadaan token saat ini (bukti)

| Platform | Berkas | Isi |
|---|---|---|
| Web | `web/src/styles/index.css` | `@theme inline`, `--color-*: initial`, variabel warna (`--primary: #232c6f`, `--danger: #a33a2c`, `--warning-bg: #fcf1dd`, `--muted-foreground: #5e6573`, `--border`), dipetakan ke kelas (`--color-primary`, `--color-mist`, `--color-line`, `--color-danger-soft`, `--color-success`, `--color-warning`) |
| Web | `web/src/styles/` | hanya `index.css` dan turunan (cek `ls web/src/styles`) |
| Mobile | `mobile/lib/core/theme/vms_colors.dart` | 43 `Color(0x...)` (sumber token) |
| Mobile | `vms_sizes.dart`, `vms_text_styles.dart`, `vms_theme.dart`, `vms_shad_theme.dart` | ukuran, teks, tema |
| Dokumen | `vms-next/docs/04-DESAIN-UI.md` | rencana: `design/tokens/{primitive,semantic,component}.json` (DTCG) dan Style Dictionary |

Temuan:
- Folder `design/` dan `tokens.dart` yang disebut `docs/04` tidak ada di repo ini. Token ditulis manual dua kali (web dan mobile).
- Warna semantik web dan mobile mungkin tidak sama. Verifikasi dengan membandingkan nilai `--primary` dan `vms_colors.dart`.
- Literal warna di luar token: web (riset `03` W5: hex di `SignaturePad.tsx`, `SelfieCaptureDialog.tsx`, `SurveyLayoutMap.tsx`), mobile (riset `03` M9: `watermark_camera_screen.dart` 2, `survey_screen.dart` 1, `vms_ui.dart` 11, `vms_theme.dart` 7).
- Kelas palet bawaan Tailwind di web (`text-amber-600` dsb.) tidak menghasilkan warna karena palet dimatikan. Lihat skill `vms-web` `references/anti-pola.md` A1.

## 2. Usulan sumber tunggal

Tujuan: satu berkas sumber yang menghasilkan dua keluaran (CSS dan Dart), sesuai `docs/04`. Langkah (usulan, belum disetujui):
1. Tulis `design/tokens/primitive.json`, `semantic.json`, `component.json` (format DTCG: `$value`, `$type`).
2. Konfigurasi Style Dictionary untuk keluaran CSS (`tokens.css`) dan Dart (`tokens.dart`, format kustom).
3. Tambah langkah di `scripts/verify.sh` yang memeriksa tidak ada selisih (`git diff --exit-code`), seperti usulan `docs/04`.
4. Hapus nilai manual dari `index.css` dan `vms_colors.dart` setelah keluaran menggantikannya.

Risiko: Style Dictionary bukan format bawaan untuk Dart. Format kustom perlu ditulis. Ini pertanyaan terbuka di ADR 0002 (`docs/04`). Perlu keputusan pemilik sebelum dikerjakan.

## 3. Contoh tiga tingkat (pola)

```
primitive:  brand.600      = #232c6f
semantic:   color.action.primary = {brand.600}      (terang)
            color.action.primary = {brand.300}      (gelap, bila nanti dibutuhkan)
component:  button.primary.bg = {color.action.primary}
```

Di web (Tailwind v4): semantic dipetakan lewat `@theme inline` ke kelas (`bg-primary`). Komponen memakai kelas itu, bukan hex.

Di mobile: semantic dipetakan lewat `ThemeExtension` (pola panduan PDF 9.4) atau konstanta di `vms_colors.dart`, dengan `lerp` bila ada mode gelap.

## 4. Warna

- Primer dan aksi: navy (`#232c6f` di `--primary`) dengan aksen emas (komentar R-12 di `index.css`).
- Permukaan: putih dan abu sangat muda.
- Status: sukses (`--success`, `--success-bg`), peringatan (`--warning`, `--warning-bg`), bahaya (`--danger`, `--danger-bg`), info (cek token).
- Teks sekunder: `--muted-foreground` (`#5e6573`). Periksa kontras pada latar `--card` atau `--background`.
- Pastikan kontras minimal 4.5:1. Bila tidak, gunakan token gelap untuk teks.

Cara cek kontras (manual): alat kontras browser, atau rumus rasio luminansi WCAG. Catat hasil di review.

## 5. Tipografi

- Web: Plus Jakarta Sans (variabel), dari `@fontsource-variable/plus-jakarta-sans`.
- Mobile: `google_fonts` (`pubspec.yaml`). Cek `vms_text_styles.dart` untuk family yang dipakai.
- Skala: definisikan 4-6 langkah (isi, isi tebal, judul kecil, judul, judul halaman). Hindari ukuran acak.
- Isi minimal 14 px / 14 sp. Judul halaman lapangan lebih besar bila memungkinkan.
- Baris panjang: dua baris lalu elipsis. Detail di layar lain.
- Angka uang dan tanggal: format Indonesia (titik ribuan, koma desimal untuk uang di layar; tanggal "4 Nov 2026"). Konfirmasi konvensi sebelum menulis fungsi format.

## 6. Spasi dan radius

- Skala: 4, 8, 12, 16, 24, 32, 40, 48, 64 px (kelipatan 8 dan 4 untuk elemen mikro; panduan PDF 9.1).
- Radius: satu atau dua nilai (kartu dan tombol). Token `--radius` atau `rounded-panel` (ada di `QueryState`).
- Bayangan: `shadow-card` (sudah dipakai). Jangan menambah bayangan besar (dimatikan di `index.css`).

## 7. Komponen dan pola

Web: `components/atoms/` (Button, Text, Image, Icon, Skeleton, Input), `components/molecules/` (QueryState, ActionButton, VmsDialog, ZoomableImage, PlainAction), `components/organisms/`, `components/templates/`.

Mobile: `shared/ui/` (vms_ui, vms_text_field, vms_select_field, vms_list_filter, vms_network_image, floating_nav).

Aturan:
- Komponen baru hanya memakai token.
- Komponen baru diberi nama istilah sederhana (`KartuPekerjaan` bukan `WoCard`, bila tampil di layar; nama kode tetap boleh teknis).
- Komponen yang dipakai di dua tempat dipindah ke `shared/ui` (mobile) atau molekul (web).

## 8. Responsif (web)

Ambang (dari panduan PDF 9.2, sesuaikan):
- Di bawah 640 px: satu kolom, aksi di bawah.
- 640 sampai 1024 px: dua kolom, rel navigasi.
- Di atas 1024 px: tiga atau empat kolom, master-detail bila cocok.

Dialog (`docs/04`):
- Lebar ikut konten, maksimal sekitar 80rem.
- Di bawah 640 px: bottom sheet penuh.

Mobile:
- Dialog maksimal sekitar 960 dp. Sheet penuh di layar sempit.
- Navigasi bawah (`floating_nav.dart`) dengan ikon dan teks.

## 9. Gerakan

- Animasi transisi singkat (sekitar 150-250 ms). Hormati `prefers-reduced-motion` (web) dan `MediaQuery.disableAnimations` (mobile, perlu cek API).
- Hindari animasi berulang yang mengganggu (kecuali indikator memuat).
- Optimistic UI untuk aksi ringan (lihat skill `vms-web`).

## 10. Ikon dan gambar

- Ikon: satu set (lucide-react di web; cek mobile). Ikon tanpa teks wajib `aria-label` (web) atau `tooltip`/`Semantics` (mobile).
- Gambar bermakna: teks alternatif. Gambar dekoratif: `alt=""`.
- Foto lapangan: watermark jam, koordinat, alamat, logo. Teks watermark harus terbaca (kontras, ukuran).
- Ilustrasi kosong: sederhana, satu warna aksen, dibuat sebagai aset SVG.
