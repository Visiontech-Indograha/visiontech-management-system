---
name: vms-ux-design-system
description: "Desain sistem dan UI/UX VMS untuk web dan mobile: token warna dan ukuran tiga tingkat (primitive, semantic, component), tipografi, kontras, spasi, komponen inti, lima kondisi layar, formulir, dialog, sheet, popup wajib baca (K3, carousel berwaktu, zoom foto), responsif, aksesibilitas, bahasa sederhana untuk pengguna awam (glosarium pengganti istilah), pedoman uji awam, dan template review UX. Pakai saat merancang atau meninjau tampilan layar, memilih warna atau ukuran, menulis teks UI, membuat formulir atau popup, menyiapkan uji pengguna awam, atau mereview kesesuaian layar dengan aturan desain. Kata kunci: UI, UX, desain, design system, token, tema, warna, kontras, tipografi, font, spasi, komponen, layar, halaman, tampilan, bahasa, teks, istilah, glosarium, BAST, serah terima, work order, pekerjaan, rollover, pindah hari, prasyarat, realisasi, luring, daring, offline, uji awam, usability, pengguna awam, pekerja lapangan, popup, dialog, bottom sheet, carousel, zoom, responsif, aksesibilitas, WCAG, target sentuh, 48dp, template review, review desain."
---

# vms-ux-design-system

Skill desain untuk web dan mobile VMS. Pengguna utama: pekerja lapangan dan atasan proyek awam teknologi, sering pakai HP di luar ruang dengan sinyal lemah. Desain mengutamakan kejelasan, bukan kepadatan.

Pendamping:
- `references/token-komponen.md`: token tiga tingkat, warna, tipografi, spasi, komponen inti, responsif, popup.
- `references/glosarium-bahasa.md`: istilah yang dilarang di layar dan padanannya.
- `references/uji-awam.md`: cara menjalankan uji pengguna awam, dan template review UX.

## 1. Prinsip

1. Satu layar, satu tujuan utama. Tombol aksi utama jelas dan terlihat.
2. Bahasa sehari-hari. Tanpa singkatan dan istilah teknis di layar (memori proyek `vms-bahasa-sederhana`).
3. Lima kondisi layar wajib di setiap data asinkron: memuat, kosong, sebagian, berhasil, galat.
4. Target sentuh besar: minimal 48x48 dp (mobile) dan 44 px (web). Tombol aksi utama di zona jempol pada mobile.
5. Warna tidak dipakai sendiri untuk makna. Selalu ada ikon atau teks.
6. Luring (offline) dulu: tampilkan status sinkron, bukan layar kosong.
7. Desain satu bahasa di web dan mobile: nama token, istilah, dan urutan aksi sama.

## 2. Token tiga tingkat

Konsep (sumber: `vms-next/docs/04-DESAIN-UI.md`; panduan PDF bagian 9.3):

| Tingkat | Contoh | Aturan |
|---|---|---|
| Primitive | `brand.600`, `neutral.900` | Nilai mentah, tanpa makna |
| Semantic | `color.action.primary`, `color.status.danger.bg` | Makna dan peran; ganti tema di sini |
| Component | `button.primary.bg` | Pemakaian di komponen |

Komponen hanya memakai semantic atau component. Tidak ada hex, `px` acak, atau kelas palet bawaan di komponen.

Keadaan repo nyata (bukti):
- Web: `web/src/styles/index.css`. Palet bawaan dimatikan dengan `--color-*: initial` di `@theme inline`. Warna semantik ada sebagai variabel (`--primary: #232c6f`, `--danger: #a33a2c`, `--warning-bg: #fcf1dd`, `--muted-foreground: #5e6573`) dan dipetakan ke kelas (`--color-primary`, `--color-danger`, `--color-warning-bg`, dan lainnya).
- Mobile: `mobile/lib/core/theme/vms_colors.dart`, `vms_sizes.dart`, `vms_text_styles.dart`, `vms_theme.dart`, `vms_shad_theme.dart`.
- Tidak ada `design/tokens/*.json` dan tidak ada `tokens.css` atau `tokens.dart` yang dihasilkan (pipeline Style Dictionary di `docs/04` belum ada di repo ini). Token saat ini ditulis manual di dua tempat. Risiko ketidaksamaan web dan mobile. Usulan: sumber tunggal (lihat `token-komponen.md` bagian 2).
- Mode gelap: `index.css` mencatat varian `dark:` tidak aktif (di luar cakupan MVP). Jangan mendesain mode gelap tanpa keputusan.

## 3. Warna dan kontras

- Teks normal: kontras minimal 4.5:1 terhadap latar. Teks besar (18 pt atau 14 pt tebal ke atas): 3:1. (Sumber: WCAG 1.4.3, Level AA. Dari pengetahuan umum WCAG. Verifikasi di https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html sebelum dikutip.)
- Aturan 60-30-10 (sumber: panduan PDF bagian 9.1): 60% netral, 30% permukaan dan teks, 10% aksen aksi.
- Status: sukses, peringatan, bahaya, info. Selalu dengan ikon dan teks.
- Jangan mengandalkan warna saja untuk status absen, cuti, atau tolak.

## 4. Tipografi dan spasi

- Web font: Plus Jakarta Sans (`@fontsource-variable/plus-jakarta-sans`, `package.json`). Mobile: `google_fonts` (`pubspec.yaml`), cek jenis yang dipakai di `vms_text_styles.dart`.
- Usulan: ukuran teks isi minimal 14 px (web) dan 14 sp (mobile). Belum ada aturan tertulis di repo; cek ukuran terkecil yang dipakai di `index.css` dan `vms_text_styles.dart` sebelum menetapkannya.
- Dukung skala teks sistem 1.5 tanpa layout pecah (mobile). Web: zoom 200% tanpa kehilangan fungsi.
- Spasi kelipatan 8 (dengan 4 untuk elemen kecil). Sumber: panduan PDF bagian 9.1. Token spasi di `index.css` atau `vms_sizes.dart`.
- Batas baris teks panjang: dua baris dengan elipsis, dan detail di tampilan lain.

## 5. Komponen inti

| Komponen | Lapisan (web) | Catatan |
|---|---|---|
| Tombol | atom `Button`; molekul `ActionButton` | varian primary, outline, ghost, danger; ukuran minimal 44 px |
| Teks | atom `Text` | semua teks layar lewat atom |
| Ikon | atom `Icon` | `aria-label` untuk ikon tanpa teks |
| Isian | atom `Input`; molekul `FormField` | label di atas, pesan galat di bawah |
| Status | molekul `StatusPill` (bila ada) | ikon + teks + warna |
| Kosong, galat, memuat | molekul `QueryState` | lihat bagian 6 |
| Dialog | molekul `VmsDialog` | judul jelas, tombol batal dan simpan |
| Popup wajib baca | organisme `HseMandatoryPopupGate` | lihat bagian 8 |

Mobile: `shared/ui/vms_ui.dart`, `vms_text_field.dart`, `vms_select_field.dart`, `vms_list_filter.dart`, `floating_nav.dart`.

## 6. Lima kondisi layar (rincian)

| Kondisi | Tampilan yang benar | Yang dihindari |
|---|---|---|
| Memuat | skeleton berbentuk seperti konten | spinner di tengah layar kosong |
| Kosong | ilustrasi atau ikon, kalimat sebab, satu aksi | "Tidak ada data" tanpa aksi |
| Sebagian | data yang ada tampil, peringatan bila ada yang belum lengkap | menyembunyikan bagian yang kurang |
| Berhasil | data penuh, teks panjang dipotong dengan aman | teks yang melebar keluar kartu |
| Galat | kalimat manusiawi, apa yang terjadi, tombol "Coba lagi" | kode galat, "Error 500", pesan teknis |

Catatan jujur: `QueryState` (web) menangani memuat, galat, dan kosong. Keadaan "sebagian" belum punya komponen khusus. Keadaan izin ditolak ada di `ForbiddenPage`. Mobile: skeleton baru di satu berkas (lihat skill `vms-mobile`).

Offline: tambahkan keadaan "data terakhir dari HP" dan "menunggu sinkron" pada layar yang memakai cache.

## 7. Formulir, dialog, dan sheet

- Formulir panjang: pecah ke langkah bertahap (Hick's Law, panduan PDF 9.1). Simpan draf otomatis.
- Label selalu terlihat (bukan hanya placeholder). Pesan galat di dekat kolom dengan ikon.
- Aksi utama di kanan bawah (web) atau di bawah layar (mobile). Batal di kiri.
- Dialog web: lebar menyesuaikan konten, maksimal sekitar 80rem. Layar 640 px ke bawah jadi bottom sheet penuh (`docs/04`).
- Dialog mobile: maksimal sekitar 960 dp. Layar sempit jadi sheet penuh.
- Konfirmasi hanya untuk aksi yang tidak bisa dibatalkan (hapus, kirim ke tim, serah terima).
- Fokus dikunci di dialog dan kembali ke pemicu (web).

## 8. Popup wajib baca K3 (pola yang sudah ada)

Sudah dibangun dan diuji (bukti: `web/src/components/organisms/hse/HseMandatoryPopupGate.tsx`, `CampaignMediaCarousel.tsx`, `web/src/components/molecules/ZoomableImage.tsx`; mobile: `mobile/lib/features/hse/k3_campaign_view.dart`):

- Penuh layar. Muncul sebelum pekerja memakai aplikasi, sampai baca selesai dan konfirmasi.
- Carousel foto dengan keterangan per foto dan bilah waktu. Durasi baca 10 sampai 300 detik, minimal 3 detik per foto, maksimal 8 foto (`web/src/lib/hseCarousel.ts`).
- Timer baca tidak dipercepat navigasi manual. Pindah foto memulai ulang geseran otomatis.
- Zoom 1x sampai 4x dengan tombol Perkecil, Perbesar, Pas layar. Geser hanya saat zoom.
- Pengurangan gerakan: geseran otomatis mati bila sistem meminta (`prefers-reduced-motion`).
- Keyboard: panah kiri dan kanan pindah foto. Perilaku Escape pada popup wajib belum diverifikasi; cek `HseMandatoryPopupGate.tsx` sebelum menulis aturannya.
- Label "Foto N dari M" untuk pembaca layar.

Aturan desain untuk popup seperti ini:
- Teks instruksi di atas foto, bukan di dalam gambar.
- Tombol konfirmasi aktif hanya setelah waktu baca habis.
- Warna status tidak memakai kelas palet bawaan. Pakai token warning (lihat `anti-pola` di skill `vms-web`).

## 9. Responsif

Acuan (sumber: panduan PDF bagian 9.2, pengetahuan umum; sesuaikan dengan kebutuhan lapangan):
- Mobile di bawah 640 px: satu kolom, navigasi bawah.
- Tablet 640-1024 px: dua kolom, rel navigasi.
- Desktop di atas 1024 px: tiga atau empat kolom, sidebar penuh.

Di VMS, layar utama lapangan adalah mobile. Desktop dipakai atasan dan admin. Jangan membuat dasbor desktop-first yang menyulitkan HP.

## 10. Aksesibilitas (ringkas)

- Target sentuh: 48 dp (mobile), 44 px (web aksi lapangan). Minimum WCAG 2.2 AA untuk web 24 px.
- Fokus terlihat di web. Urutan fokus sesuai urutan visual.
- Label tombol ikon. Teks alternatif gambar bermakna.
- Pembaca layar: judul halaman, landmark, `aria-live` untuk status.
- Gerakan: hormati reduced motion. Hindari gerakan berulang yang tidak perlu.

Rincian dan pola kode ada di skill `vms-web` (`references/performa-a11y.md`) dan `vms-mobile`.

## 11. Teks dan bahasa

Ringkasan (rincian di `references/glosarium-bahasa.md`):
- Semua teks yang dilihat pengguna memakai Bahasa Indonesia sehari-hari.
- Hindari singkatan dan istilah teknis di layar: BAST, BoM, BoQ, rollover, prasyarat, realisasi, luring, daring. Nama teknis boleh tetap di kode dan API, bukan di layar.
- Kalimat pendek, kata kerja aktif, satu ide per kalimat.
- Tombol memakai kata kerja: "Simpan", "Kirim", "Ajukan", "Batal".
- Galat: sebab dan langkah berikutnya. Contoh: "Lokasi belum ditemukan. Pindah ke tempat terbuka lalu coba lagi."

## 12. Skill global yang boleh dipanggil atau dilebur

- `anthropic-skills:theme-factory`: untuk mengusulkan tema alternatif (presentasi, halaman informasi). Jangan mengganti token produksi tanpa keputusan. Hasilnya dilebur sebagai nilai semantic, bukan literal.
- `anthropic-skills:canvas-design`: untuk poster, ilustrasi, atau gambar statis (misalnya ilustrasi "kosong"). Hasil disimpan sebagai aset dengan nama token.
- `anthropic-skills:brand-guidelines`: bila ada aturan merek resmi. Cek dulu. Logo VMS dan palet navy-emas ada di `index.css` (komentar R-12).
- `dataviz`: untuk grafik dan dasbor angka. Aturan warna grafik mengikuti token semantic.
- `modern-web-guidance:modern-web-guidance`: untuk CSS dan HTML baru (dialog, container query, `:has`).

## 13. Template review UX

Gunakan `references/uji-awam.md` bagian 4. Ringkasnya: tujuan layar, pengguna, lima kondisi, bahasa, target sentuh, kontras, aksesibilitas, dan hasil uji awam. Pelaksanaan uji awam per peran, audit, dan Playwright ada di skill `vms-qa`.

## 14. Checklist layar baru

- [ ] Satu tujuan utama, satu aksi utama terlihat.
- [ ] Lima kondisi ada: memuat, kosong, sebagian, berhasil, galat.
- [ ] Teks Indonesia sehari-hari, tanpa istilah dari glosarium terlarang.
- [ ] Target sentuh 48 dp (mobile) atau 44 px (web).
- [ ] Kontras teks 4.5:1 atau lebih. Status tidak hanya warna.
- [ ] Warna dan spasi dari token, tidak hardcoded.
- [ ] Offline: status sinkron atau data terakhir tampil.
- [ ] Skala teks besar dan zoom tidak memecah layout.
- [ ] Uji awam dengan minimal 3 orang sebelum rilis layar kunci.

## 15. Sumber (diakses 2026-11-04)

- Desain UI VMS: `vms-next/docs/04-DESAIN-UI.md`, `vms-next/docs/02-ARSITEKTUR-DAN-STRUKTUR-FOLDER.md` (bagian 2.2.1 dan 2.3).
- Panduan PDF bagian 9 (UI/UX): `vms-next/docs/panduan/panduan-fullstack.txt` baris 1051-1361. Teks hasil ekstraksi PDF, sebagian rusak (lihat riset `01` bagian 1).
- Riset: `riset-best-practice/01-PDF-DAN-AUDIT-VMS.md` (T27, F-26, F-27), `03-WEB-MOBILE.md` (W5, W6, M8, M9).
- WCAG 2.2 Target Size: https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html
- Tailwind v4 theme: https://tailwindcss.com/docs/theme
- Memori proyek: `vms-bahasa-sederhana`, `vms-offline-first`.
- Belum dibuka langsung: Material Design dan Apple HIG untuk target sentuh (verifikasi bila dikutip).
