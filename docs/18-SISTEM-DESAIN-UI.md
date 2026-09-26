# 18 · Sistem Desain UI

Aturan tampilan yang **mengikat** untuk `web/` (React + shadcn/ui) dan `mobile/` (Flutter +
shadcn_ui). Satu bahasa visual, satu set token, dua pustaka komponen.

Gaya yang dituju: **korporat modern** — tenang, rapat, mudah dibaca di bawah matahari,
terasa seperti alat kerja milik perusahaan, bukan halaman pemasaran dan bukan hasil
"generate UI" yang generik.

| Berkas | Isi | Siapa yang memakai |
|---|---|---|
| **dokumen ini** | Aturan, skala, pemetaan, larangan | Manusia & AI — dibaca sebelum menulis UI |
| `docs/design/tokens.json` | Satu-satunya sumber nilai token | Dasar kedua berkas di bawah |
| `docs/design/web/theme.css` | Tema shadcn/ui + Tailwind v4 siap salin | `web/src/styles/` |
| `docs/design/mobile/vms_theme.dart` | `ShadThemeData` siap salin | `mobile/lib/core/theme/` |
| `.agy/rules/ui-design-system.md` | Ringkasan aturan untuk agen AI | Dibaca otomatis oleh agen |

**Urutan kewenangan** (sama dengan CLAUDE.md): instruksi pemilik produk → dokumen 02/10 →
perilaku & label prototipe → dokumen ini → dokumen 11. Nilai token hanya boleh diubah di
`tokens.json` lalu diturunkan ke `theme.css` dan `vms_theme.dart` **dalam satu commit**.

---

> **Perubahan atas arahan pemilik (R-12, R-13 — 2026-09-26), mengalahkan aturan di bawah bila bertentangan:**
> palet brand kini **navy Visiontech `#232c6f` + aksen emas `#f0c000`** (dari logo), netral abu kebiruan;
> kartu boleh **bayangan halus** (`shadow-card`) dan radius 16 px (`rounded-panel`); cahaya lembut relatif
> kursor pada kartu dan animasi pegas/gulir diizinkan **asal hanya `transform`/`opacity`, tanpa pustaka,
> dan mati saat `prefers-reduced-motion`**. Nilai sumber: `web/src/styles/index.css`.

## 1. Prinsip

| # | Prinsip | Artinya |
|---|---|---|
| 1 | **Warna membawa makna** | Warna selain netral hanya dipakai untuk: aksi utama (brand) atau status (sukses/peringatan/bahaya/info). Tidak ada warna dekoratif |
| 2 | **Garis, bukan bayangan** | Kedalaman dibuat dengan border 1 px dan perbedaan latar. Bayangan hanya untuk lapisan melayang (popover, dialog, sheet, toast) |
| 3 | **Rapat tapi bernapas** | Data padat boleh; jarak tetap dari skala 4 px. Tidak ada ruang kosong raksasa ala landing page |
| 4 | **Satu aksi utama per area** | Tiap kartu/halaman/dialog punya paling banyak satu tombol `primary` |
| 5 | **Teks lebih dulu** | Ikon mendukung label, tidak menggantikannya. Status selalu punya teks, bukan hanya warna |
| 6 | **Sama di web dan mobile** | Nama komponen, warna, label status, dan istilah identik di kedua permukaan |
| 7 | **Pakai pustaka** | shadcn/ui (web) dan shadcn_ui (Flutter) dulu. Komponen sendiri hanya bila tidak ada — lihat dok 11 §4 |

---

## 2. Larangan "AI slop" (wajib dipatuhi)

Ciri-ciri di bawah ini membuat aplikasi terlihat seperti template generik buatan AI. **Satu
saja muncul → perubahan ditolak di tinjauan.**

**Visual**
- ❌ Gradien apa pun: latar, tombol, teks (`bg-gradient-*`, `bg-clip-text`), border, ikon.
- ❌ Ungu, indigo, violet, fuchsia, pink, neon, atau "warna AI" lain. Palet hanya dari §3.
- ❌ Glassmorphism: `backdrop-blur`, latar semi-transparan di atas konten, efek kaca/embun.
- ❌ Bayangan pada kartu biasa, bayangan berwarna, efek *glow*, `shadow-xl/2xl` di mana pun.
- ❌ Sudut terlalu bulat: `rounded-2xl`, `rounded-3xl`, tombol bentuk kapsul (`rounded-full`
  hanya untuk avatar, titik status, dan saklar).
- ❌ Ikon di dalam lingkaran/kotak berwarna sebagai hiasan kartu ("icon-in-colored-blob").
- ❌ Grid "kartu statistik" berisi angka + ikon + persentase naik-turun sebagai pengisi
  dasbor. Angka ringkasan hanya bila datanya nyata dan diminta di prototipe.
- ❌ Kartu di dalam kartu. Gunakan pemisah (`Separator`) atau daftar bergaris.
- ❌ Hero section, ilustrasi besar, blob/bentuk abstrak, pola latar, foto stok.
- ❌ Animasi dekoratif: angka berhitung, confetti, *shimmer* berpelangi, *parallax*,
  elemen melayang/berdenyut, transisi halaman yang memantul.
- ❌ Emoji di antarmuka, di teks tombol, di toast, di judul. Juga ikon "sparkles" (✨)
  untuk menandai apa pun.
- ❌ Semua elemen rata tengah. Teks dan konten rata kiri; rata tengah hanya untuk
  `EmptyState` dan layar login.
- ❌ Huruf kapital di tombol atau judul. Kapital hanya untuk label *overline* 12 px (§4.2).
- ❌ Font bawaan template (Inter, Roboto, Poppins, Montserrat, Geist). Hanya §4.1.
- ❌ Mode gelap / tombol tema — **di luar cakupan MVP** (K-23). Jangan buat varian `dark:`.

**Teks**
- ❌ Lorem ipsum, data palsu yang tampak nyata, nama "John Doe", angka karangan.
- ❌ Sapaan kosong: "Selamat datang kembali, Budi! 👋", "Mari mulai!", "Siap produktif?".
- ❌ Kata pemasaran: "Tingkatkan", "Maksimalkan", "Mulus", "Revolusioner", "Seamless",
  "Unlock", "Supercharge", "Powered by AI".
- ❌ Galat generik: "Oops!", "Ada yang salah", "Something went wrong". Lihat §9.
- ❌ Teks Inggris mentah di layar pengguna (termasuk `Loading...`, `Submit`, `Cancel`).
- ❌ Tanda seru di pesan biasa. Titik saja.

---

## 3. Warna

Dasar diambil dari prototipe yang sudah disetujui (hijau hutan `#164d40`, netral kehijauan),
lalu dirapikan menjadi skala dan **diuji kontrasnya** (target WCAG AA: teks ≥ 4,5:1, garis
kontrol ≥ 3:1). Semua nilai ada di `docs/design/tokens.json`.

### 3.1 Brand — hijau Visiontech

| Token | Hex | Pemakaian |
|---|---|---|
| `brand-50` | `#eef5f2` | Latar baris terpilih, hover item navigasi |
| `brand-100` | `#d5e8e0` | Latar badge `brand`, sorotan lembut |
| `brand-200` | `#aed3c3` | Garis aksen tipis (jarang) |
| `brand-300` | `#7fb7a0` | — (cadangan grafik) |
| `brand-400` | `#4f977d` | Bilah progres, grafik |
| `brand-500` | `#2d7a60` | **Cincin fokus** (5,2:1 di putih) |
| `brand-600` | `#1f634d` | Hover tombol primer |
| **`brand-700`** | **`#164d40`** | **Warna utama**: tombol primer, tautan, item navigasi aktif (9,7:1) |
| `brand-800` | `#113d33` | Tombol primer ditekan |
| `brand-900` | `#0c2d26` | — |

### 3.2 Netral — abu kehijauan

| Token | Hex | Pemakaian |
|---|---|---|
| `neutral-0` | `#ffffff` | Kartu, popover, dialog, input |
| `neutral-25` | `#f8faf8` | Kepala tabel, latar sidebar desktop |
| `neutral-50` | `#f3f6f3` | **Latar halaman** |
| `neutral-100` | `#e9eee9` | Latar `muted`, hover baris, tombol `secondary` |
| `neutral-200` | `#dde4de` | **Border** kartu, pemisah, garis tabel |
| `neutral-300` | `#c6cfc8` | Border saat hover |
| `neutral-400` | `#8a968e` | **Border input** (3,07:1 — syarat garis kontrol ≥ 3:1) |
| `neutral-500` | `#5f6b64` | **Teks sekunder** (5,6:1 di putih, 5,1:1 di latar halaman) |
| `neutral-600` | `#4a5650` | Ikon aktif, teks label form |
| `neutral-700` | `#36423c` | — |
| `neutral-800` | `#243b33` | **Teks utama** |
| `neutral-900` | `#16241f` | Judul halaman |

> Teks sekunder prototipe (`#758279`) hanya 4,0:1 (di putih) dan 3,7:1 (di latar halaman) — dinaikkan ke `neutral-500` agar lolos
> 4,5:1 sesuai dokumen 11 §2.

### 3.3 Status (semantik)

Setiap status punya empat nilai: `fg` (teks/ikon), `bg` (latar lembut), `border`, `solid`
(latar pekat dengan teks putih — hanya untuk tombol destruktif atau penanda kritis).

| Nada | `fg` | `bg` | `border` | `solid` | Makna |
|---|---|---|---|---|---|
| `success` | `#1e6b43` | `#e8f3ec` | `#b9dcc6` | `#23804f` | Selesai, disetujui, valid |
| `warning` | `#8a5a12` | `#fcf1dd` | `#efd29f` | `#c7892a`* | Perlu tindakan/perhatian, menunggu, di luar radius |
| `danger` | `#a33a2c` | `#fbecea` | `#f0c2ba` | `#b93c2d` | Ditolak, gagal, destruktif, K3 berat |
| `info` | `#2f5f8a` | `#e8f0f8` | `#bcd2e8` | `#3569a0` | Terbit, menunggu pihak lain, informasi netral |
| `neutral` | `#4a5650` | `#e9eee9` | `#dde4de` | `#5f6b64` | Draf, dibatalkan, tidak aktif |
| `brand` | `#164d40` | `#d5e8e0` | `#aed3c3` | `#164d40` | Sedang berjalan, aktif |

\* `warning.solid` memakai teks `neutral-900` (5,4:1), bukan putih. Rasio kontras seluruh pasangan di tabel ini sudah dihitung: teks `fg` di atas `bg` 5,3–7,6:1; teks putih di atas `solid` 4,9–5,7:1.

### 3.4 Pemetaan status domain → nada

Label **wajib** diambil dari prototipe (`prototype/js/ui.js`) dan disimpan di satu tempat:
web `lib/format/labels.ts`, mobile `core/labels.dart`. Tabel ini hanya menetapkan warnanya.

| Enum | Nilai → label prototipe → nada |
|---|---|
| `plan_status` | `DRAFT` Draft → neutral · `PUBLISHED` SK terbit → info · `ACCEPTED` Diterima → brand · `APPEALED` Banding → warning · `IN_PROGRESS` Berjalan → brand · `COMPLETION_REVIEW` Review penyelesaian → info · `COMPLETED` Selesai → success · `CANCELLED` Dibatalkan → neutral |
| `report_status` | `DRAFT` Laporan belum dikirim → neutral · `SUBMITTED` Menunggu review PM → warning · `CHANGES_REQUESTED` Perlu perbaikan → danger · `APPROVED` Laporan disetujui → success |
| `attendance_status` | `AUTO_VALID` Valid otomatis → success · `NEEDS_REVIEW` Perlu review → warning · `APPROVED` Disetujui → success · `REJECTED` Ditolak → danger |
| `document_status` | `AWAITING_ACCEPTANCE` → warning · `EFFECTIVE` → success · `SUPERSEDED` → neutral · `REJECTED` → danger · `WITHDRAWN` → neutral |
| `change_status` | `PENDING_PM` → warning · `AWAITING_LEADER_ACCEPTANCE` → warning · `EFFECTIVE` → success · `REJECTED` → danger · `WITHDRAWN` → neutral |
| `personal_document_status` | `PENDING` Menunggu verifikasi → warning · `VERIFIED` Terverifikasi → success · `REJECTED` Ditolak → danger |
| `personal_document_lifecycle` | `CURRENT` → success · `PENDING` → warning · `SUPERSEDED` → neutral · `EXPIRED` → danger. Kedaluwarsa ≤ 30 hari → warning |
| `asset_status` | `AVAILABLE` Tersedia → success · `RESERVED` Direservasi → info · `IN_USE` Dipakai → brand · `RETURN_PENDING` Menunggu pemeriksaan → warning · `MAINTENANCE` → warning · `RETIRED` → neutral |
| `incident_severity` | `RENDAH` → info · `SEDANG` → warning · `TINGGI` → danger · `KRITIS` → danger `solid` |
| `incident_status` | `OPEN` Terbuka → danger · `IN_REVIEW` → warning · `RESOLVED` Selesai → success |
| `approval_status` | `PENDING_PM` → warning · `APPROVED` → success · `REJECTED` → danger |
| `signature_state` | `VALID` → success · `DOCUMENT_CHANGED` → danger `solid` · `REVOKED` → danger · `KEY_EXPIRED` → warning · `UNKNOWN` → neutral |
| `face_check_result` | `MATCH` → success · `NO_MATCH` / `LOW_QUALITY` → warning (bukan danger — wajah hanya bukti pendukung) · `NOT_ENROLLED` / `SKIPPED` → neutral |
| `sync_status` | `PENDING` → info · `APPLIED` → success · `CONFLICT` → warning · `REJECTED` → danger |

Label enum yang belum ada di prototipe ditulis di `labels` lalu dicatat di dok 10 Bagian C.

### 3.5 Aturan pakai warna

- Latar halaman `neutral-50`; permukaan (kartu, tabel, form) `neutral-0` dengan border
  `neutral-200`. Tidak ada latar berwarna untuk halaman atau kartu.
- Warna brand muncul **sedikit**: tombol primer, tautan, navigasi aktif, cincin fokus.
  Bila satu layar terasa "hijau", itu terlalu banyak.
- Status tidak pernah hanya warna: badge selalu berteks; baris bermasalah juga diberi ikon.
- Grafik (hanya bila perlu): urutan seri `brand-700`, `info.solid`, `warning.solid`,
  `neutral-500`, `brand-400`. Maksimal 5 seri.
- Heksadesimal **dilarang** di komponen. Web memakai kelas token (`bg-primary`,
  `text-muted-foreground`, `bg-success-bg`); Flutter memakai `ShadTheme.of(context)` atau
  `VmsColors`.

---

## 4. Tipografi

### 4.1 Huruf

| Peran | Huruf | Alasan |
|---|---|---|
| Seluruh antarmuka | **Plus Jakarta Sans** (variable, 400–700) | Dirancang di Jakarta, humanis, terbaca di layar kecil, sudah dipakai web |
| Kode, nomor seri, koordinat | Tumpukan sistem: `ui-monospace, "Cascadia Mono", "Roboto Mono", monospace` | Tanpa dependensi tambahan |

- Web: `@fontsource-variable/plus-jakarta-sans` (swa-hosting, bukan Google Fonts CDN).
- Flutter: berkas TTF dibundel di `mobile/assets/fonts/` (lisensi OFL) — **bukan**
  `google_fonts`, karena aplikasi wajib jalan tanpa sinyal.
- Angka di tabel, jam, jarak, jumlah: `font-variant-numeric: tabular-nums`
  (Flutter: `FontFeature.tabularFigures()`).

### 4.2 Skala huruf

Satuan px; `lh` = tinggi baris. Nama sama di web (kelas `text-*`) dan Flutter
(`VmsText.*`).

| Token | Ukuran / lh | Berat | Letter-spacing | Pemakaian |
|---|---|---|---|---|
| `display` | 30 / 36 | 600 | -0.02em | Hanya angka utama halaman verifikasi QR. Bukan untuk judul biasa |
| `title-lg` | 24 / 32 | 600 | -0.015em | Judul halaman di `md+` |
| `title` | 20 / 28 | 600 | -0.01em | Judul halaman di ponsel, judul dialog |
| `heading` | 18 / 26 | 600 | -0.005em | Judul kartu/bagian |
| `subheading` | 16 / 24 | 600 | 0 | Subjudul, nama di baris daftar |
| **`body`** | **16 / 24** | 400 | 0 | **Teks dasar, isi input** (minimal 16 px — dok 11 §2) |
| `body-sm` | 14 / 20 | 400 / 500 | 0 | Teks sekunder, sel tabel di `lg+`, label form, tombol |
| `caption` | 12 / 16 | 500 | 0.01em | Badge, stempel waktu, keterangan kecil |
| `overline` | 12 / 16 | 600 | 0.06em, KAPITAL | Kepala tabel, label kelompok navigasi. Satu-satunya tempat huruf kapital |

- Berat yang diizinkan: **400, 500, 600**. 700 hanya untuk `display`. Tidak ada 300/800/900.
- Maksimal 3 ukuran berbeda dalam satu kartu.
- Panjang baris teks bebas maksimal ~72 karakter (`max-w-prose`).
- Tidak ada teks miring kecuali kutipan; tidak ada garis bawah kecuali tautan saat hover.
- **Catatan migrasi:** `web/src/styles/index.css` sekarang menyetel `html { font-size: 14px }`.
  Ini bertentangan dengan dasar 16 px dan harus diganti saat tema ini dipasang.

---

## 5. Spasi, tata letak, ukuran

### 5.1 Skala spasi (kelipatan 4 px)

`0 · 2 · 4 · 8 · 12 · 16 · 20 · 24 · 32 · 40 · 48 · 64` — nilai lain dilarang
(tidak ada `p-[13px]`, tidak ada `EdgeInsets.all(10)`).

| Pemakaian | Ponsel | `md` | `lg+` |
|---|---|---|---|
| Tepi halaman | 16 | 24 | 32 |
| Jarak antar-bagian | 24 | 24 | 32 |
| Padding kartu | 16 | 20 | 24 |
| Jarak antar-field form | 16 | 16 | 20 |
| Jarak label → input | 6 | 6 | 6 |
| Jarak antar-tombol | 8 | 8 | 12 |

### 5.2 Lebar konten

| Jenis halaman | Lebar maksimal |
|---|---|
| Daftar & tabel | 1280 px |
| Detail | 1024 px (kolom utama + kolom samping 320 px di `lg+`) |
| Form | 720 px |
| Dialog | 480 px (sedang 560, lebar 720) |
| Halaman login & verifikasi QR | 400 px |

### 5.3 Ukuran kontrol

| Kontrol | Tinggi | Catatan |
|---|---|---|
| Tombol, input, select (bawaan) | **44 px** | Sasaran sentuh minimal (sarung tangan kerja) |
| Tombol besar (aksi utama lapangan, mis. "Absen masuk") | 52 px | Lebar penuh, menempel di bawah pada ponsel |
| Tombol kecil | 36 px | **Hanya di `lg+`** dalam tabel padat; area sentuhnya tetap 44 px |
| Tombol ikon | 44 × 44 | Wajib `aria-label` / `semanticLabel` |
| Baris tabel | 52 px | 44 px untuk tabel padat di `lg+` |
| Bilah navigasi bawah (mobile) | 64 px + area aman | |
| Header aplikasi | 56 px ponsel · 64 px `lg+` | |

### 5.4 Radius

| Token | Nilai | Pemakaian |
|---|---|---|
| `radius-sm` | 4 px | Checkbox, badge kecil, tag |
| `radius-md` | 6 px | Badge, tooltip |
| `radius-lg` (`--radius`) | **8 px** | Tombol, input, select, item menu |
| `radius-xl` | 12 px | Kartu, dialog, sheet, popover, tabel |
| `radius-full` | 9999 px | Avatar, titik status, saklar — **hanya itu** |

### 5.5 Elevasi

| Token | Nilai | Pemakaian |
|---|---|---|
| `elevation-0` | tanpa bayangan + border `neutral-200` | Kartu, tabel, panel — **bawaan** |
| `elevation-1` | `0 1px 2px rgba(22,36,31,.06)` | Header lengket saat konten tergulir |
| `elevation-2` | `0 8px 24px rgba(22,36,31,.12)` | Popover, dropdown, toast |
| `elevation-3` | `0 16px 48px rgba(22,36,31,.16)` | Dialog, sheet |
| Scrim | `rgba(22,36,31,.48)` | Di belakang dialog/sheet. Tanpa blur |

### 5.6 Titik henti

Mengikuti dok 11 §2: dasar (< 640), `sm` 640, `md` 768, `lg` 1024, `xl` 1280.
Flutter memakai nilai yang sama lewat `ShadBreakpoints`.

---

## 6. Ikon, gambar, gerak

**Ikon** — **Lucide** saja (`lucide-react` di web, `LucideIcons` dari `lucide_icons_flutter`
yang dibawa shadcn_ui di Flutter). Ukuran 16 (di dalam badge/tabel padat), **20 (bawaan)**,
24 (navigasi bawah ponsel). Stroke bawaan 2; jangan diubah per ikon. Warna mengikuti teks
di sekitarnya. Satu makna = satu ikon di seluruh aplikasi (daftar di §7.4).

**Gambar** — hanya foto sungguhan dari pengguna (swafoto, bukti, dokumen). Rasio tetap,
`object-fit: cover`, radius `radius-lg`, latar `neutral-100` saat memuat. Tidak ada
ilustrasi dekoratif. Logo perusahaan hanya di header, login, dan PDF.

**Avatar** — inisial 2 huruf, latar `brand-100`, teks `brand-700`. Tidak ada warna acak
per orang.

**Gerak**

| Token | Nilai | Pemakaian |
|---|---|---|
| `duration-fast` | 120 ms | Hover, tekan, fokus |
| `duration-base` | 180 ms | Buka popover, dropdown, accordion |
| `duration-slow` | 240 ms | Dialog, sheet, drawer |
| `easing` | `cubic-bezier(0.2, 0, 0, 1)` | Semua transisi. Tidak ada efek pantul/pegas |

Hanya `opacity` dan `transform` yang dianimasikan. Hormati `prefers-reduced-motion`
(web) dan `MediaQuery.disableAnimations` (Flutter).

---

## 7. Komponen

### 7.1 Pemetaan komponen web ↔ mobile

Nama di kolom pertama dipakai di kode dan percakapan. Bila komponen belum ada, buat di
lokasi yang ditunjukkan dok 11 §3 dengan nama yang sama di kedua platform.

| Kebutuhan | Web (shadcn/ui) | Mobile (shadcn_ui) | Catatan |
|---|---|---|---|
| Tombol | `Button` | `ShadButton` | Varian: `default` (primer), `secondary`, `outline`, `ghost`, `destructive`, `link` |
| Input teks | `Input` + `Label` | `ShadInput` / `ShadInputFormField` | Label selalu di atas, bukan placeholder |
| Area teks | `Textarea` | `ShadInputFormField(maxLines:)` | |
| Pilihan | `Select` | `ShadSelect` | ≥ 8 opsi → `Combobox` / `ShadSelect.withSearch` |
| Tanggal | `Calendar` + `Popover` | `ShadDatePicker` | Format §8.3 |
| Centang, radio, saklar | `Checkbox`, `RadioGroup`, `Switch` | `ShadCheckbox`, `ShadRadioGroup`, `ShadSwitch` | |
| Form | `Form` (react-hook-form + zod) | `ShadForm` | Galat di bawah field |
| Kartu | `Card` | `ShadCard` | Tanpa bayangan |
| Badge status | `StatusBadge` (di atas `Badge`) | `StatusBadge` (di atas `ShadBadge`) | Menerima enum, bukan warna. §7.2 |
| Tabel | `DataTable` (TanStack Table) | — | Ponsel → `ResponsiveDataView` jadi kartu |
| Tab | `Tabs` | `ShadTabs` | Maksimal 5 tab |
| Dialog | `Dialog` / `AlertDialog` | `ShadDialog` / `ShadDialog.alert` | Ponsel web → `Sheet`/`Drawer` dari bawah |
| Lembar bawah | `Sheet` (`side="bottom"`) / `Drawer` | `showShadSheet` | Filter & aksi di ponsel |
| Toast | `Sonner` | `ShadToaster` / `ShadToast` | Pengganti `alert()` |
| Peringatan dalam halaman | `Alert` | `ShadAlert` | |
| Menu | `DropdownMenu` | `ShadContextMenu` / `ShadPopover` | |
| Tooltip | `Tooltip` | `ShadTooltip` | Hanya di perangkat bertetikus; jangan sembunyikan info penting di tooltip |
| Skeleton | `Skeleton` | `ShadSkeleton` | Bentuk menyerupai isi |
| Progres | `Progress` | `ShadProgress` | |
| Avatar | `Avatar` | `ShadAvatar` | Inisial |
| Pemisah | `Separator` | `ShadSeparator` | |
| Navigasi samping | `Sidebar` | — | `lg+` |
| Navigasi bawah | `BottomNav` (buatan, `components/organisms`) | `NavigationBar` bertema token | ≤ 5 item |
| Keadaan kosong | `EmptyState` | `EmptyState` | Ikon 24, judul, 1 kalimat, 1 aksi |
| Konfirmasi | `ConfirmDialog` | `ConfirmDialog` | §9.4 |

### 7.2 Aturan per komponen

**Tombol**
- Label = kata kerja + objek: "Terbitkan SK", "Absen masuk", "Kirim laporan". Bukan "OK",
  "Submit", "Ya".
- Maksimal satu `default` (primer) per area. Aksi kedua `outline`, aksi ketiga+ `ghost`
  atau masuk menu "Lainnya".
- `destructive` hanya untuk aksi yang menghapus/membatalkan/menolak, dan selalu lewat
  `ConfirmDialog`.
- Urutan di desktop: aksi batal di kiri, aksi utama di **kanan**. Di ponsel: aksi utama
  lebar penuh di **bawah**, aksi batal di atasnya sebagai `ghost`.
- Saat memproses: tombol tetap selebar semula, teks diganti "Menyimpan…", ikon
  `LoaderCircle` berputar, tombol nonaktif. Jangan buka dua permintaan.

**Input & form**
- Label di atas field (`body-sm`, 500, `neutral-600`). Placeholder hanya contoh format,
  bukan pengganti label.
- Wajib: tidak diberi tanda bintang; yang **opsional** diberi "(opsional)".
- Pesan bantuan di bawah field (`caption`, `neutral-500`); galat menggantikannya
  (`caption`, `danger.fg`, ikon `CircleAlert` 16).
- Input selalu 16 px agar ponsel tidak memperbesar layar.
- Satu kolom di ponsel dan tablet; dua kolom hanya di `lg+` untuk field pendek yang
  berkaitan (tanggal mulai / selesai).

**Kartu** — border `neutral-200`, radius `radius-xl`, padding §5.1, tanpa bayangan.
Kepala kartu: judul `heading` di kiri, satu aksi `ghost`/`outline` di kanan.

**StatusBadge** — tinggi 24, padding 8 horizontal, `caption` 500, latar `bg`, teks `fg`,
radius `radius-md`, tanpa border. Opsional titik 6 px di kiri. Menerima `(enum, nilai)` dan
mengambil label + nada dari `labels` — **tidak pernah** menerima warna dari pemanggil.

**Tabel (web)** — kepala `overline`, latar `neutral-25`; sel `body-sm`; garis antar-baris
`neutral-200`; tanpa garis vertikal, tanpa zebra. Angka rata kanan + `tabular-nums`.
Kolom aksi paling kanan, ikon `Ellipsis` membuka menu. Di bawah `md` → kartu
(`ResponsiveDataView`), tidak pernah gulir mendatar.

**Daftar (mobile)** — baris 64–72 px: avatar/ikon 40 → judul `subheading` + baris kedua
`body-sm` `neutral-500` → badge/chevron di kanan. Pemisah `neutral-200` inset 16.

**Dialog** — judul `title`, isi `body`, aksi di kaki. Menutup dengan Esc/tombol kembali
Android kecuali form kotor → tanya "Buang perubahan?".

**Toast** — maksimal 1 baris + 1 aksi opsional. Sukses 4 detik, galat tetap sampai
ditutup. Posisi: atas-tengah di ponsel, bawah-kanan di `lg+`. Jangan pakai toast untuk
galat validasi field.

**Navigasi**
- Web `lg+`: sidebar kiri 256 px, latar `neutral-0`, border kanan; item aktif latar
  `brand-50`, teks `brand-700`, 500; kelompok dengan label `overline`.
- Web ponsel & mobile: bilah bawah 5 item maksimal (ikon 24 + label `caption`), item
  lain di "Lainnya". Aktif: ikon & label `brand-700`; tidak aktif `neutral-500`.
- Header: judul halaman di kiri, satu aksi utama + lonceng notifikasi + avatar di kanan.

### 7.3 Pola khusus VMS

| Pola | Aturan |
|---|---|
| **Indikator luring** (mobile & web) | Bilah tipis di bawah header: `warning.bg` + ikon `CloudOff` + "Tidak ada sinyal · 3 aksi menunggu dikirim". Hilang saat daring dan antrean kosong |
| **Perlu perhatian** | Daftar aksi ditolak server: kartu dengan garis kiri 3 px `danger.solid`, alasan penolakan sebagai teks, tombol "Perbaiki" |
| **Absen masuk/pulang** | Satu tombol besar 52 px lebar penuh di bawah; jarak ke lokasi ditampilkan sebagai teks ("120 m dari lokasi · di luar radius") + badge warning, bukan hanya peta |
| **Hasil verifikasi QR** | Halaman publik 400 px: blok status besar (`display`, ikon 32) berlatar `bg` nada status, lalu daftar detail (penandatangan, jabatan, nomor seri mono, nomor dokumen, waktu). `DOCUMENT_CHANGED` pakai `danger.solid` |
| **Dokumen terkunci / versi lama** | Badge neutral "Versi lama · terkunci" + ikon `Lock`; seluruh aksi ubah disembunyikan, bukan dinonaktifkan |
| **Riwayat versi SK** | Lini masa vertikal: garis 2 px `neutral-200`, titik 8 px bernada status, nomor dokumen mono |
| **Kedaluwarsa dokumen** | ≤ 30 hari: badge warning "Berakhir 12 hari lagi"; lewat: danger "Kedaluwarsa". Tombol "Ajukan perpanjangan" ada di baris daftar, bukan hanya di detail |

### 7.4 Kamus ikon (satu makna = satu ikon)

| Makna | Lucide |
|---|---|
| Beranda | `House` |
| Pekerjaan / SK | `ClipboardList` / `FileText` |
| Absensi | `MapPinCheck` (masuk), `LogOut` (pulang) |
| Laporan | `NotebookPen` |
| Aset / kendaraan | `Package` / `Truck` |
| Insiden K3 | `TriangleAlert` |
| Lembur | `Clock` |
| Karyawan / tim | `Users` |
| Dokumen pribadi | `IdCard` |
| Tanda tangan / QR | `QrCode`, `ShieldCheck` (valid) |
| Luring / sinkron | `CloudOff` / `RefreshCw` |
| Notifikasi | `Bell` |
| Lainnya | `Ellipsis` |
| Terkunci | `Lock` |
| Galat / info / sukses / peringatan | `CircleAlert` / `Info` / `CircleCheck` / `TriangleAlert` |

---

## 8. Teks antarmuka (microcopy)

### 8.1 Gaya bahasa

- **Bahasa Indonesia baku yang ringkas**, sapaan "Anda" hanya bila perlu; lebih baik
  kalimat tanpa subjek ("Simpan perubahan?").
- **Sentence case** di semua tempat: "Terbitkan SK", "Daftar pekerjaan", bukan
  "Terbitkan Sk" atau "Daftar Pekerjaan".
- Singkatan resmi tetap kapital: SK, K3, PM, HR, QR, GPS, SIM, KTP, BPJS, MCU, PKWT.
- Istilah **wajib** mengikuti dokumen 16 (Glosarium) dan label prototipe: "Pekerjaan"
  (bukan "Proyek" / "Task"), "Ketua tim", "Anggota", "Adendum personel", "Banding",
  "Absen masuk" / "Absen pulang", "Swafoto", "Lembur", "Insiden K3", "Aset".
- Kalimat pendek: judul ≤ 5 kata, deskripsi ≤ 2 kalimat, tombol ≤ 3 kata.

### 8.2 Pola teks

| Tempat | Pola | Contoh |
|---|---|---|
| Judul halaman | Kata benda | "Pekerjaan", "Absensi tim" |
| Tombol | Kata kerja + objek | "Terbitkan SK", "Ajukan banding" |
| Toast sukses | Apa yang terjadi, lampau | "SK diterbitkan." |
| Galat | Apa yang terjadi + apa yang bisa dilakukan | "Laporan belum terkirim. Periksa sinyal lalu coba lagi." |
| Keadaan kosong | Kenapa kosong + aksi | "Belum ada laporan hari ini. Laporan bisa diisi setelah absen masuk." |
| Konfirmasi | Pertanyaan + akibat | "Batalkan pekerjaan ini? Tim akan kehilangan akses ke SK." |
| Memuat | Hanya skeleton; teks bila > 3 detik | "Memuat data absensi…" |

### 8.3 Format data (satu sumber: web `lib/format/`, mobile `core/format.dart`)

| Data | Format | Contoh |
|---|---|---|
| Tanggal | `d MMM yyyy`, lokal `id` | 23 Sep 2026 |
| Tanggal + hari | `EEEE, d MMMM yyyy` | Rabu, 23 September 2026 |
| Jam | `HH.mm` + zona bila lintas zona | 08.05 WIB |
| Tanggal-jam | | 23 Sep 2026, 08.05 |
| Relatif | Hanya < 7 hari | "2 jam lalu", "kemarin" |
| Rentang | | 23–30 Sep 2026 |
| Angka | pemisah ribuan titik, desimal koma | 1.250,5 |
| Uang | | Rp 1.250.000 |
| Jarak | < 1 km dalam m, selebihnya km 1 desimal | 120 m · 1,2 km |
| Durasi | | 2 j 30 m |
| Nomor seri / dokumen | Huruf mono | `VTI/2026/000123` |
| Nomor identitas | Hanya bentuk tersamar | `3201 •••• •••• 8901` |

Zona waktu tampilan: `Asia/Jakarta`. Server tetap sumber waktu (dok 03 §2.3).

---

## 9. Keadaan layar dan umpan balik

### 9.1 Empat keadaan (dok 11 §8)
Memuat → `Skeleton` sebentuk isi · Kosong → `EmptyState` · Galat → `Alert` danger +
"Coba lagi" · Berhasil → isi. Tidak ada spinner di tengah layar kosong.

### 9.2 Galat
- Pesan dari server (`error.message`) sudah Bahasa Indonesia — tampilkan apa adanya.
- `NETWORK_ERROR` → "Tidak ada koneksi ke server. Periksa sinyal lalu coba lagi."
- Galat validasi 422 → di bawah field terkait, bukan toast.
- 409 (row_version) → `Alert` warning: "Data ini baru saja diubah orang lain. Muat ulang
  untuk melihat versi terbaru." + tombol "Muat ulang".
- Kode galat, jejak tumpukan, dan ID teknis tidak pernah tampil ke pengguna.

### 9.3 Dinonaktifkan
Opasitas 0,5 + kursor `not-allowed`. Bila alasannya tidak jelas, tampilkan alasan di bawah
kontrol ("Laporan bisa diisi mulai 24 Sep 2026"), bukan tooltip.

### 9.4 Konfirmasi
Hanya untuk aksi yang tidak bisa dibatalkan atau berdampak ke orang lain. Judul
pertanyaan spesifik, isi menjelaskan akibat, tombol aksi mengulang kata kerjanya
("Batalkan pekerjaan"), tombol lain "Kembali". Aksi berbahaya tinggi (offboarding,
cabut tanda tangan) wajib mengisi alasan.

---

## 10. Aksesibilitas

- Kontras: teks ≥ 4,5:1, teks besar & garis kontrol ≥ 3:1 — nilai §3 sudah memenuhi di
  atas `neutral-0` dan `neutral-50`. Kombinasi baru wajib dicek dulu.
- Fokus: cincin 2 px `brand-500` + jarak 2 px, **selalu terlihat** saat navigasi keyboard.
- Sasaran sentuh ≥ 44 × 44 px, jarak antar-sasaran ≥ 8 px.
- Setiap ikon tanpa teks punya label aksesibel.
- Urutan fokus = urutan baca. Dialog mengurung fokus dan mengembalikannya saat ditutup.
- Teks bisa diperbesar 200 % tanpa terpotong (web) / mengikuti `textScaler` sampai 1,3
  (Flutter).

---

## 11. Pustaka dan versi

Versi stabil terbaru **per 23 September 2026**, diperiksa langsung dari registri npm dan
pub.dev. Aturan menambah pustaka tetap di dokumen 14 §6. Saat memasang, pakai versi ini
atau yang lebih baru di jalur mayor yang sama; periksa ulang registri bila dokumen ini
sudah > 3 bulan.

**Web**

| Paket | Versi | Status di `web/package.json` |
|---|---|---|
| `tailwindcss`, `@tailwindcss/vite` | 4.3.3 | ✅ sesuai |
| `shadcn` (CLI, dijalankan lewat `npx shadcn@latest`) | 4.21.0 | belum dipakai — `components.json` belum ada |
| `radix-ui` (paket tunggal, dipakai shadcn terbaru) | 1.6.7 | belum ada |
| `class-variance-authority` | 0.7.1 | belum ada |
| `tailwind-merge` | 3.7.0 | belum ada |
| `clsx` | 2.1.1 | ✅ |
| `tw-animate-css` | 1.4.0 | belum ada |
| `lucide-react` | 1.47.0 | `^1.43.0` — tercakup rentang |
| `sonner` | 2.0.8 | belum ada; **`react-hot-toast` harus diganti** (dok 11 §1) |
| `vaul` (Drawer shadcn) | 1.1.2 | belum ada |
| `@fontsource-variable/plus-jakarta-sans` | 5.3.0 | memakai `@fontsource/plus-jakarta-sans` statis — ganti ke varian variable |
| `@tanstack/react-table` | 9.2.4 | belum ada |

**Mobile**

| Paket | Versi | Status di `mobile/pubspec.yaml` |
|---|---|---|
| `shadcn_ui` | **0.57.0** | ⚠️ `^0.13.0` — sangat tertinggal (caret pada 0.x tidak naik ke 0.57). **Harus dinaikkan** sebelum UI dibangun. Butuh Flutter ≥ 3.41, Dart ≥ 3.11 |
| `lucide_icons_flutter` | 3.1.20 | dibawa `shadcn_ui`, tidak perlu ditambah langsung |
| Plus Jakarta Sans (TTF) | aset lokal | belum ada — tambahkan di `assets/fonts/` + `pubspec.yaml` |

API tema di `docs/design/mobile/vms_theme.dart` sudah dicocokkan dengan sumber
`shadcn_ui` 0.57.0 (`ShadColorScheme`, `ShadTextTheme`, `ShadButtonSizesTheme`).

---

## 12. Daftar periksa tinjauan UI

Tambahan untuk dok 11 §10. Satu kotak kosong → belum selesai.

1. [ ] Tidak ada satu pun butir larangan §2.
2. [ ] Tidak ada heksadesimal, `px` acak, atau ukuran huruf di luar skala di komponen.
3. [ ] Hanya satu tombol primer per area.
4. [ ] Status memakai `StatusBadge` + label dari `labels`, nada sesuai §3.4.
5. [ ] Teks mengikuti §8: sentence case, istilah glosarium, tanpa Inggris mentah.
6. [ ] Format tanggal/angka/jarak lewat helper format, bukan ditulis di komponen.
7. [ ] Kontrol ≥ 44 px, input 16 px, fokus terlihat.
8. [ ] Tampilan web dan mobile untuk fitur yang sama memakai nama komponen, label, dan
   warna yang sama.
