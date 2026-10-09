# 33 · Standar Penulisan Kode, Penamaan, dan Atomic Design

Keputusan pemilik 2026-10-09. Diadaptasi dari *Panduan Konsep Arsitektur dan Penamaan Full-Stack*
dan disesuaikan dengan tumpukan yang terkunci di `CLAUDE.md`.

**Cakupan saat ini: web (`web/`).** Bagian mobile dan API menyusul. Untuk web, dokumen ini
**menggantikan** `docs/11` §3 (struktur folder) dan §4 (aturan komponen) bila bertentangan.

---

## 1. Prinsip

1. **Satu berkas, satu tanggung jawab utama.** Tampilan, alur halaman, komunikasi API, tipe data,
   dan validasi tidak ditumpuk di satu berkas.
2. **Aliran data harus bisa ditelusuri:**
   `Page → hook service (TanStack Query) → apiClient (axios) → endpoint FastAPI → JSON →
   hook service → Page → template/organism → molecule → atom`.
3. **Backend adalah sumber kebenaran kontrak API.** Tipe web mengikuti `lib/apiTypes.ts` hasil
   `npm run gen:api`; field tidak boleh dikarang.
4. **Ikuti pola yang sudah ada.** Mengubah standar = jelaskan alasan, cakupan, dampak, lalu catat di sini.
5. **Jangan menambah lapisan, pustaka, atau folder tanpa kebutuhan nyata.**

---

## 2. Atomic design (WAJIB)

Urutan dari terbesar ke terkecil (keputusan pemilik 2026-10-09):

```
tampilan UI (rute) > Page > Template > Organism > Molecule > Atom
```

Tiap tingkat hanya menyusun tingkat **di bawahnya**. **Atom atau molecule (termasuk elemen HTML mentah) di Page atau
Template = pelanggaran.**

| Tingkat | Isi | Contoh di repo | Tempat |
|---|---|---|---|
| **Atom** | Elemen UI terkecil, tanpa pengetahuan domain. Termasuk hasil salinan shadcn/ui. | `Button`, `Input`, `Label`, `Badge`, `Skeleton`, `Checkbox` | `components/atoms/` |
| **Molecule** | Gabungan beberapa atom dengan satu tujuan kecil, masih netral domain. | `TextField` (label + input + galat), `StatusBadge`, `QueryState`, `VmsDialog` | `components/molecules/` |
| **Organism** | Blok UI utuh yang punya tujuan bagi pengguna: tabel data, form, panel, kartu ringkasan, dialog bertujuan, kepala halaman. Boleh tahu domain bila milik fitur. | `PageHeader`, `NotificationBell` (bersama), `PlanDetailCard`, `PlanDayTable` (fitur) | `components/organisms/` (dipakai ≥ 2 fitur) atau `features/<fitur>/components/` |
| **Template** | Kerangka tata letak halaman tanpa data spesifik; hanya menyusun **organism** + elemen tata letak. | `PageTemplate`, `AppShell`, `TitleLayout` | `components/templates/` |
| **Page** | Satu rute. Mengambil data, memegang state halaman, memilih keadaan layar, menyusun template + organism. | `WorkPlansPage`, `SitesPage` | `features/<fitur>/pages/` |

**Elemen HTML mentah (`<button>`, `<input>`, `<select>`, `<textarea>`, `<table>`, `<label>`,
`<p>`, `<span>`, `<img>`, `<a>`, `<h1>`…`<h6>`, `<ul>`, …) setara atom/molecule.**

### 2.1 Aturan Page dan Template — dilarang keras

**Template** hanya boleh menyusun organism + elemen tata letak polos (daftar sama dengan Page di bawah); larangan
impor dan elemen HTML Page berlaku juga untuk Template.


Page **hanya** boleh berisi:

- hook data/service (TanStack Query) dan state halaman (`useState`, `useForm`, Zustand selector);
- **template** dan **organism** (bersama atau milik fitur);
- elemen tata letak polos: `div`, `section`, `main`, `header`, `footer`, `article`, `aside`
  (hanya untuk grid, jarak, dan pengelompokan; tanpa teks langsung).

Page **dilarang**:

- mengimpor dari `components/atoms/` atau `components/molecules/`;
- mengimpor ikon `lucide-react` (ikon adalah atom);
- menulis elemen HTML selain daftar tata letak di atas.

Ditegakkan ESLint (`web/eslint.config.js`, berkas `features/*/pages/*.tsx` dan `components/templates/*.tsx`).
Page/Template lama yang belum dimigrasi tercantum di daftar pengecualian sementara di berkas itu; daftar ini
**hanya boleh menyusut**.

### 2.2 Arah impor

```
pages/      → templates, organisms, features/<fitur>/components, service/hook, lib, stores
templates   → organisms, lib                   — TIDAK molecule/atom
organisms   → organisms lain, molecules, atoms, lib  (organism fitur boleh memakai service fiturnya)
molecules   → atoms, lib
atoms       → lib (cn, token)                  — tidak mengimpor tingkat di atasnya
components/ → TIDAK BOLEH mengimpor features/
lib/        → TIDAK BOLEH mengimpor features/ atau components/
```

### 2.3 Kapan memecah komponen

- Sudah ada atomnya (shadcn/ui)? Pakai, jangan buat ulang.
- Bagian Page memakai atom/molecule/elemen HTML → pindahkan ke **organism** bernama sesuai tujuannya.
- Organism dipakai di ≥ 2 fitur → naikkan ke `components/organisms/` (bukan sebelumnya).
- Jangan memecah setiap elemen menjadi berkas tanpa manfaat; organism mewakili satu tujuan pengguna.

---

## 3. Struktur folder web

```
web/src/
├── app/                    perakitan aplikasi: routes.tsx, lazyPages.ts, navigation.ts,
│                           SessionProvider.tsx, RouteGuards.tsx
├── components/             PUSTAKA BERSAMA, netral fitur
│   ├── atoms/              Button.tsx, Input.tsx, … (shadcn/ui)
│   ├── molecules/          Field.tsx (TextField…), StatusBadge.tsx, QueryState.tsx, …
│   ├── organisms/          PageHeader.tsx, NotificationBell.tsx, …
│   └── templates/          PageTemplate.tsx, AppShell.tsx, TitleLayout.tsx
├── features/<fitur>/       satu domain; nama folder kebab-case (work-plans)
│   ├── pages/              HANYA <Nama>Page.tsx
│   ├── components/         organism & molecule khusus fitur
│   ├── <fitur>Service.ts   tipe + hook TanStack Query untuk endpoint fitur
│   └── <helper>.ts         fungsi murni khusus fitur (camelCase)
├── lib/                    lintas fitur: apiClient.ts, apiTypes.ts, format.ts, labels.ts, …
├── styles/                 token Tailwind v4 (@theme)
└── test/                   setup & util uji
```

Uji ditaruh **di samping** berkasnya: `PlanDetailCard.test.tsx`.

---

## 4. Penamaan

| Jenis | Pola | Contoh |
|---|---|---|
| Komponen React (`.tsx`) | `[NamaFitur][OutputTampilan].tsx`, PascalCase | `PlanDetailCard.tsx`, `SiteTable.tsx`, `EmployeeForm.tsx` |
| Page | `[NamaFitur]Page.tsx` | `WorkPlansPage.tsx` |
| Atom shadcn/ui | PascalCase sesuai komponen utama | `Button.tsx`, `DropdownMenu.tsx` (setelah `npx shadcn add`, ganti nama berkas ke PascalCase) |
| Service fitur (`.ts`) | `[domain]Service.ts`, camelCase | `workPlanService.ts`, `siteService.ts` |
| API client bersama | `apiClient.ts` | `lib/apiClient.ts` (satu-satunya `axios.create`) |
| Hook | `use[Tujuan].ts` | `useDebouncedValue.ts` |
| Fungsi murni / konfigurasi | camelCase | `planChanges.ts`, `weekday.ts`, `labels.ts` |
| Folder fitur | kebab-case | `work-plans/`, `work-types/` |
| Folder lapisan | huruf kecil | `atoms/`, `pages/`, `components/` |
| Fungsi, variabel, props | camelCase | `selectedDay`, `onSubmit` |
| Komponen, `type`, `interface` | PascalCase | `WorkPlan`, `DayTableProps` |
| Konstanta tetap | UPPER_SNAKE_CASE | `MAX_UPLOAD_BYTES` |
| Callback props | `on[Peristiwa]` | `onSave`, `onCancel` |
| Boolean | `is/has/can/should…` | `isLocked`, `canEdit` |

**Aturan tambahan**

- Nama berkas = nama ekspor utama. Satu berkas boleh berisi beberapa komponen kecil yang
  hanya dipakai komponen utamanya.
- Hindari nama generik (`Box.tsx`, `Item.tsx`, `helpers.ts`, `data.ts`) dan istilah lama
  (`Sk…` → `Plan…`; SK = Rencana Kerja).
- `.tsx` hanya untuk berkas ber-JSX; selain itu `.ts`.

---

## 5. Service dan tipe

- **Satu klien HTTP:** `lib/apiClient.ts` (base URL dari env, token, refresh, galat bersama).
  Dilarang `axios.create` atau URL server di tempat lain.
- **Service per fitur** (`<domain>Service.ts`) berisi tipe kontrak + hook `useQuery`/`useMutation`.
  Nama hook menggambarkan maksud: `useWorkPlans`, `useCreateSite`, bukan `useGet`.
- Galat tidak disembunyikan menjadi "sukses kosong"; Page memilih tampilannya (`QueryState`).
- Tipe domain diambil/diturunkan dari `apiTypes.ts`; jangan menggandakan bentuk yang sama di banyak berkas.
- Bedakan tipe data server dengan tipe form (zod) bila bentuknya berbeda.
- Tidak ada `any`, `@ts-ignore`, `alert/confirm/prompt`.

---

## 6. Komentar

Komentar menjelaskan **tujuan, kontrak, alasan, dan batasan**, bukan mengulang kode. Bahasa Indonesia.

| Berkas | Isi komentar kepala |
|---|---|
| Page | tujuan halaman, data yang diambil, keadaan layar yang ditangani |
| Organism | tujuan blok, props penting, peristiwa yang diteruskan ke Page |
| Molecule/atom bersama | contoh pemakaian singkat |
| Service | endpoint yang dipakai, bentuk hasil, kebijakan galat |

Keputusan pemilik ditulis dengan tanggal: `// 2026-10-09 (pemilik): …`.

---

## 7. Tata cara migrasi Page lama (keputusan pemilik 2026-10-09)

Dikerjakan **per Page / per berkas besar**, bagian demi bagian agar minim galat:

1. Temukan bagian Page yang memakai atom, molecule, atau elemen HTML mentah.
2. **Pindahkan** bagian itu (tidak dihapus/ditulis ulang) ke organism baru di
   `features/<fitur>/components/` dengan nama sesuai §4; Page memanggil organism itu dengan props.
3. Jalankan `npm run typecheck`, `npm run lint`, dan uji terkait. Ada galat → perbaiki dulu.
4. Ulangi sampai Page hanya berisi template + organism + tata letak.
5. Hapus Page dari daftar pengecualian ESLint, jalankan `npm test`, commit (satu Page = satu commit).

Perilaku dan tampilan tidak boleh berubah selama migrasi.

---

## 8. Daftar periksa web

1. [ ] Page dan Template tanpa atom/molecule/ikon/elemen HTML mentah (ESLint hijau, tanpa pengecualian baru).
2. [ ] Nama berkas dan folder sesuai §3–§4.
3. [ ] Service memakai `apiClient`; tidak ada URL/axios tersebar.
4. [ ] Empat keadaan layar: memuat, kosong, galat, berhasil.
5. [ ] `components/` tidak mengimpor `features/`; `lib/` tidak mengimpor keduanya.
6. [ ] `npm run lint`, `npm run typecheck`, `npm test` hijau — dijalankan, bukan diasumsikan.
