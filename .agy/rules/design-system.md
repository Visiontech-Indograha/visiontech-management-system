---
name: design-system
description: >
  Aturan mengikat sistem desain VMS untuk web (React + shadcn/ui + Tailwind v4)
  dan mobile (Flutter + shadcn_ui). Berlaku untuk semua AI yang mengerjakan
  kode tampilan di direktori web/ dan mobile/.
---

# Sistem Desain VMS — Aturan AI

> **Sumber kebenaran:** `docs/design/tokens.json` (token) · `docs/18-SISTEM-DESAIN-UI.md` (aturan lengkap)

## 1. Warna

### Web
- Gunakan **hanya** variabel CSS yang sudah didefinisikan di `web/src/styles/index.css` (atau `theme.css`).
- Contoh benar: `bg-primary`, `text-muted-foreground`, `border-border`, `bg-success-bg text-success`.
- **DILARANG**: `bg-blue-500`, `text-indigo-600`, `bg-purple-*`, `text-green-*`, atau warna Tailwind bawaan lain yang bukan bagian palet VMS.
- **DILARANG**: nilai warna hardcoded seperti `#fff`, `rgb(...)`, atau `style={{ color: '...' }}`.

### Mobile
- Gunakan **hanya** konstanta dari `VmsColors` (`lib/core/theme/vms_colors.dart`).
- Contoh benar: `VmsColors.brand700`, `VmsColors.neutral200`, `VmsColors.dangerFg`.
- **DILARANG**: `Colors.blue`, `Colors.green`, `Color(0xFF...)` di luar file `vms_colors.dart`.
- Untuk warna dari `Theme` / `ColorScheme`: ambil via `Theme.of(context).colorScheme.primary` jika memang perlu dinamis.

## 2. Tipografi

### Web
- Gunakan kelas utilitas semantik: `text-title`, `text-heading`, `text-body`, `text-body-sm`, `text-caption`, `overline`.
- **DILARANG**: `text-4xl`, `text-5xl`, atau ukuran di luar skala tipografi VMS.
- **DILARANG**: `font-bold` sendirian tanpa kelas `text-*` yang sesuai (gunakan varian yang sudah membawa weight).
- Overline **selalu** huruf besar: pakai kelas `overline` atau `uppercase` yang sudah ada, bukan CSS manual.

### Mobile
- Gunakan **hanya** konstanta dari `VmsTextStyles` (`lib/core/theme/vms_text_styles.dart`).
- Contoh benar: `style: VmsTextStyles.body`, `style: VmsTextStyles.heading`.
- **DILARANG**: `TextStyle(fontSize: 16, ...)` di luar file `vms_text_styles.dart`.
- **DILARANG**: `Theme.of(context).textTheme.bodyLarge` — gunakan `VmsTextStyles.body` langsung.

## 3. Spasi & Ukuran

### Web
- Gunakan kelipatan 4 px (skala Tailwind standar): `p-2` (8px), `p-3` (12px), `p-4` (16px), `gap-4`, dll.
- Gunakan `container-*` untuk lebar konten: `max-w-[var(--container-form)]`.
- **DILARANG**: nilai `px-*` atau margin/padding di luar skala 4px.

### Mobile
- Gunakan konstanta dari `VmsSizes` (`lib/core/theme/vms_sizes.dart`).
- Contoh benar: `padding: EdgeInsets.all(VmsSizes.s16)`, `SizedBox(height: VmsSizes.s8)`.
- **DILARANG**: `SizedBox(height: 15)`, `Padding(padding: EdgeInsets.all(10))` atau nilai acak.
- Semua touch target **minimum 44 dp** (`VmsSizes.control`). Bungkus dengan `SizedBox(height: VmsSizes.control)` bila perlu.

## 4. Radius

| Level | Nilai | Kapan dipakai |
|---|---|---|
| `sm` (4px) | Badge kecil, tag sempit |
| `md` (6px) | Input kecil, chip |
| `lg` (8px) | **Default** — tombol, input, kartu |
| `xl` (12px) | Bottom sheet, dialog, avatar besar |
| `full` | Toggle, avatar lingkaran penuh |

- **DILARANG**: `rounded-2xl`, `rounded-3xl`, atau `Radius.circular(20+)` — terlalu bulat, bukan gaya korporat.

## 5. Elevasi / Bayangan

- Kartu dan kontrol: **flat** (elevation 0, tanpa bayangan).
- Dropdown/tooltip: `shadow-md` / elevation 1.
- Modal/dialog: `shadow-lg` / elevation 3.
- **DILARANG**: `shadow-2xl`, `drop-shadow-xl`, atau `BoxShadow` dengan blur > 48px.
- **DILARANG**: efek glassmorphism (`backdrop-blur`, `bg-white/70`).

## 6. Komponen UI

### Web — shadcn/ui
- Gunakan komponen shadcn yang tersedia: `Button`, `Input`, `Card`, `Badge`, `Dialog`, `Sheet`, dll.
- **JANGAN** buat komponen kustom yang menduplikasi fungsi shadcn.
- Untuk status badge: gunakan `variant` dari `Badge` dengan warna semantik (`success`, `warning`, `danger`, `info`, `neutral`).
- Tabel: gunakan `<Table>` shadcn. Kepala kolom pakai `overline`. Tanpa garis vertikal. Angka rata kanan dengan `tabular-nums`.

### Mobile — shadcn_ui / Material 3
- Gunakan komponen dari `shadcn_ui` bila tersedia (`ShadButton`, `ShadInput`, `ShadCard`, dll).
- Bila tidak tersedia di shadcn_ui, gunakan Material 3 dengan `VmsTheme` yang sudah dikonfigurasi.
- **DILARANG**: `RaisedButton`, `FlatButton`, widget Material 2 lama.
- Semua bottom sheet menggunakan `showModalBottomSheet` dengan `isScrollControlled: true`.

## 7. Ikon

### Web
- Gunakan **hanya** ikon dari `lucide-react`.
- Ukuran default: `size={20}` (iconMd). Ukuran kecil: `size={16}`. Ukuran besar (judul/hero): `size={24}`.
- **DILARANG**: ikon dari heroicons, tabler, atau library lain.

### Mobile
- Gunakan `Icons.*` dari Material Icons (sudah disertakan) atau ikon dari paket `lucide_icons` bila dipasang.
- Ukuran: `VmsSizes.iconSm` (16), `VmsSizes.iconMd` (20), `VmsSizes.iconLg` (24).

## 8. Status Domain → Warna

| Status Domain | Nada Warna |
|---|---|
| DRAFT | `neutral` |
| PUBLISHED, AWAITING_ACCEPTANCE | `info` |
| ACCEPTED, IN_PROGRESS | `brand` / `success` |
| COMPLETION_REVIEW | `warning` |
| COMPLETED, APPROVED | `success` |
| REJECTED, CANCELLED | `danger` |
| NEEDS_REVIEW, PENDING | `warning` |
| AUTO_VALID | `success` |
| OVERDUE, EXPIRED | `danger` |

## 9. Animasi & Transisi

- Durasi default: **180ms** (`duration-[180ms]` / `VmsSizes` atau `motion.base`).
- Easing: `cubic-bezier(0.2, 0, 0, 1)` (decelerate).
- **DILARANG**: `animate-bounce`, `animate-ping` (dinonaktifkan di tema).
- Hormat `prefers-reduced-motion`: theme CSS sudah menangani ini, jangan override.

## 10. Larangan Umum

- ❌ **Mode gelap** — di luar cakupan MVP. Jangan tambahkan `dark:` class atau `darkTheme` berbeda.
- ❌ **Font bawaan** — Poppins, Inter, Roboto, Montserrat, Geist. Hanya Plus Jakarta Sans.
- ❌ **Huruf kapital di tombol / judul** — hanya overline yang boleh uppercase.
- ❌ **Rata tengah untuk konten** — hanya `EmptyState` dan layar login.
- ❌ **Warna inline / hardcoded** di luar token sistem desain.
- ❌ **Style responsif dengan breakpoint manual** di mobile Flutter (gunakan LayoutBuilder bila perlu).

## 11. Cara Update Token

Jika perlu mengubah nilai warna/ukuran:
1. Ubah di `docs/design/tokens.json` terlebih dahulu.
2. Perbarui `docs/design/web/theme.css` (CSS variables).
3. Perbarui `mobile/lib/core/theme/vms_colors.dart` / `vms_sizes.dart` / `vms_text_styles.dart`.
4. Commit ketiganya **dalam satu commit** dengan pesan `design(tokens): ...`.
