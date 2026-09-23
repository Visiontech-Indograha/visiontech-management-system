# 11 · Standar Frontend (Web dan Mobile)

Aturan yang mengikat untuk `web/` (React) dan `mobile/` (Flutter). Tujuannya satu: antarmuka
yang **konsisten, bisa dipakai ulang, dan tidak ditulis dua kali**.

---

## 1. Tumpukan teknologi

### Web (`web/`)

| Kebutuhan | Pustaka | Catatan |
|---|---|---|
| Kerangka | React 19 + TypeScript (strict) | |
| Build | Vite | |
| Komponen UI | **shadcn/ui** | Radix UI + Tailwind; disalin ke repo, bukan dependensi |
| Gaya | Tailwind CSS **v4** | **Satu-satunya** sistem styling (via `@theme` di CSS, tanpa `tailwind.config.js`) |
| State server | TanStack Query | |
| State klien | **Zustand** | + middleware `persist` untuk draf dan preferensi |
| Form | react-hook-form + **zod** | zod, bukan yup — tipe TypeScript-nya lebih baik |
| Rute | React Router | |
| Tabel | TanStack Table (lewat `data-table` shadcn) | |
| Ikon | lucide-react | bawaan shadcn |
| Tanggal | date-fns + `date-fns-tz` | lokal `id`, zona `Asia/Jakarta` |
| Notifikasi | `sonner` (shadcn) | pengganti `alert()` yang dilarang |
| Grafik | Recharts (lewat `chart` shadcn) | hanya bila memang perlu |
| Tipe API | openapi-typescript | dibangkitkan, tidak ditulis tangan |
| Uji | Vitest + Testing Library + Playwright | |

### Mobile (`mobile/`)

| Kebutuhan | Paket | Catatan |
|---|---|---|
| Kerangka | Flutter (stable) | Android dulu |
| Komponen UI | **shadcn_ui** | diverifikasi di P0-7; lihat A-07 |
| State | Riverpod | padanan Zustand di Flutter |
| Rute | go_router | |
| HTTP | dio + interceptor refresh | |
| Basis data lokal | drift | antrean luring |
| Penyimpanan aman | flutter_secure_storage | token |
| Kamera | camera + image_picker | swafoto berwatermark |
| Lokasi | geolocator | + `permission_handler` |
| Gambar | flutter_image_compress | kompresi sebelum unggah |
| Konektivitas | connectivity_plus | indikator luring |
| Model | freezed + json_serializable | |
| Uji | flutter_test + integration_test | |

---

## 2. Mobile-first: aturan yang tidak bisa ditawar

**Tulis gaya untuk ponsel dulu, tambahkan ke atas.** Tidak pernah sebaliknya.

```tsx
// BENAR — dasar = ponsel, lalu ditambah
<div className="flex flex-col gap-4 p-4 md:flex-row md:gap-6 lg:p-8">

// SALAH — dasar = desktop, lalu dikurangi
<div className="flex flex-row gap-6 p-8 max-md:flex-col max-md:p-4">
```

### Titik henti

| Nama | Lebar | Perangkat | Kelas Tailwind |
|---|---|---|---|
| Dasar | < 640 px | Ponsel | *(tanpa awalan)* |
| `sm` | ≥ 640 px | Ponsel besar / ponsel mendatar | `sm:` |
| `md` | ≥ 768 px | Tablet | `md:` |
| `lg` | ≥ 1024 px | Laptop | `lg:` |
| `xl` | ≥ 1280 px | Monitor kantor | `xl:` |

### Pola tata letak per ukuran

| Elemen | Ponsel | Tablet | Desktop |
|---|---|---|---|
| Navigasi | Bilah bawah (≤ 5 item) atau drawer | Drawer | Sidebar tetap |
| Daftar data | Kartu bertumpuk | Kartu 2 kolom | Tabel penuh |
| Form | Satu kolom | Satu kolom lebar | Dua kolom |
| Aksi utama | Tombol lebar penuh, menempel di bawah | Inline | Inline kanan atas |
| Dialog | `Sheet` dari bawah | `Dialog` tengah | `Dialog` tengah |
| Filter | `Sheet` yang bisa dibuka | Inline sebagian | Bilah filter penuh |

**Tabel di ponsel.** Jangan pernah menggeser tabel lebar ke samping — itu tidak terbaca.
Ubah setiap baris menjadi kartu yang menampilkan 3–4 kolom terpenting, sisanya di halaman
detail. Satu komponen bersama (`ResponsiveDataView`) menangani peralihan ini, jadi tidak
ditulis ulang di setiap halaman.

### Aturan sentuh dan keterbacaan

- Sasaran sentuh minimal **44 × 44 px**. Ini bukan anjuran — pengguna memakai sarung tangan
  kerja.
- Ukuran teks dasar minimal **16 px** (di bawah itu, iOS/Android memperbesar sendiri dan
  merusak tata letak).
- Kontras minimal **4,5:1**. Layar dibaca di bawah matahari.
- Tidak ada informasi yang **hanya** disampaikan lewat warna; selalu ada teks atau ikon.
- Tidak pernah memakai `alert()`, `confirm()`, `prompt()` bawaan browser.

---

## 3. Struktur folder — atomic design + fitur

Atomic design murni (semua komponen dalam lima folder besar) menjadi kacau setelah ratusan
komponen: `organisms/` berubah jadi keranjang serba ada. Karena itu kita memakai **atomic
design untuk komponen bersama** dan **folder per fitur untuk yang khusus**.

```
web/src/
├── components/                 ← PUSTAKA BERSAMA (atomic design)
│   ├── ui/                     atoms — hasil salinan shadcn/ui, jangan diedit sembarangan
│   │   ├── button.tsx
│   │   ├── dialog.tsx
│   │   └── ...
│   ├── molecules/              gabungan kecil, masih netral domain
│   │   ├── search-field.tsx
│   │   ├── empty-state.tsx
│   │   ├── status-badge.tsx
│   │   └── confirm-dialog.tsx
│   ├── organisms/              blok besar yang dipakai lintas fitur
│   │   ├── data-table.tsx
│   │   ├── responsive-data-view.tsx
│   │   ├── form-layout.tsx
│   │   └── file-upload.tsx
│   └── templates/              kerangka halaman
│       ├── app-shell.tsx       sidebar/bottom-nav + header
│       ├── list-page.tsx
│       └── detail-page.tsx
│
├── features/                   ← PER DOMAIN, isinya boleh tahu soal bisnis
│   ├── work-plans/
│   │   ├── components/         komponen khusus fitur ini
│   │   ├── hooks/              useWorkPlans, useCreatePlan (TanStack Query)
│   │   ├── stores/             Zustand khusus fitur ini
│   │   ├── schemas/            skema zod
│   │   ├── pages/              halaman yang dipasang ke router
│   │   └── types.ts
│   ├── attendance/
│   ├── employees/
│   ├── assets/
│   ├── incidents/
│   ├── overtime/
│   ├── documents/
│   └── auth/
│
├── lib/
│   ├── api/                    klien HTTP + tipe hasil openapi-typescript
│   ├── auth/                   token, refresh, penjaga rute
│   ├── format/                 tanggal, angka, nama — satu sumber
│   ├── permissions/            pemetaan izin → menu & tombol
│   └── utils.ts                cn(), helper kecil
│
├── stores/                     Zustand global (sesi, tema, status luring)
├── routes/                     definisi rute
└── styles/
    └── tokens.css              variabel warna, radius, spasi
```

**Aturan arah ketergantungan** (ditegakkan oleh ESLint):

```
features/  →  boleh memakai  →  components/, lib/, stores/
components/→  TIDAK BOLEH memakai  →  features/
lib/       →  TIDAK BOLEH memakai  →  features/, components/
```

Komponen bersama yang mengimpor sesuatu dari `features/` berarti ia bukan komponen bersama.

### Struktur Flutter yang setara

```
mobile/lib/
├── core/           tema, token, router, http, penyimpanan, galat
├── shared/
│   ├── widgets/    atoms & molecules (shadcn_ui + buatan sendiri)
│   └── layouts/    templates
├── features/
│   ├── attendance/ {data, domain, presentation}
│   ├── fieldwork/
│   └── ...
└── main.dart
```

Nama komponen sengaja disamakan dengan web (`StatusBadge`, `EmptyState`, `ConfirmDialog`)
supaya pembicaraan tentang antarmuka tidak perlu diterjemahkan antara dua tim.

---

## 4. Aturan komponen

### Kapan boleh membuat komponen baru

```
Sudah ada di shadcn/ui?                        → pakai, jangan bikin
Bisa disusun dari 2–3 komponen shadcn?         → susun jadi molecule
Dipakai di ≥ 2 tempat?                         → naikkan ke components/
Dipakai di 1 tempat dan khusus domain?         → biarkan di features/<nama>/components/
Belum ada sama sekali di pustaka mana pun?     → buat, pakai token yang sama, dokumentasikan
```

**Jangan menaikkan komponen ke pustaka bersama sebelum dipakai dua kali.** Abstraksi yang
dibuat terlalu dini biasanya salah bentuk, dan memperbaikinya lebih mahal daripada menulis
komponen kedua.

### Bentuk komponen

- **Satu komponen, satu tanggung jawab.** Bila namanya mengandung "dan", pecah.
- **Props eksplisit dan bertipe.** Tidak ada `any`, tidak ada `props: object`.
- **Komponen tampilan tidak mengambil data sendiri.** Data masuk lewat props; pengambilan
  data terjadi di halaman atau di hook fitur. Ini yang membuat komponen bisa diuji dan
  dipakai ulang.
- **Varian memakai `cva`** (class-variance-authority), bukan rangkaian `if` di dalam JSX.
- Setiap komponen bersama punya contoh pemakaian di komentar kepala berkasnya.

---

## 5. DRY — dan batasnya

**Yang wajib DRY (satu sumber kebenaran, tanpa kecuali):**

| Hal | Di mana | Kenapa |
|---|---|---|
| Label status (`PUBLISHED` → "Sudah terbit") | `lib/format/labels.ts` | Kalau tersebar, satu layar akan menyebutnya berbeda |
| Format tanggal & waktu | `lib/format/date.ts` | |
| Aturan izin → menu & tombol | `lib/permissions/` | Menggandakannya = celah otorisasi |
| Tipe API | dibangkitkan dari OpenAPI | Tidak pernah ditulis tangan |
| Token warna, radius, spasi | `styles/tokens.css` | |
| Pesan galat standar | `lib/format/errors.ts` | |
| Skema validasi form | `features/*/schemas/` | Dipakai form dan uji |

**Yang tidak perlu dipaksakan DRY.** Dua komponen yang *kebetulan terlihat mirip* hari ini
belum tentu berubah bersama besok. Menggabungkan keduanya menghasilkan komponen dengan tujuh
props boolean yang tidak ada yang berani sentuh.

> Aturan praktisnya: **DRY berlaku untuk pengetahuan, bukan untuk kemiripan bentuk.**
> Bila dua tempat harus berubah bersama karena aturan bisnisnya sama → satukan.
> Bila dua tempat kebetulan mirip → biarkan.

---

## 6. State dengan Zustand

### Pembagian store

```
stores/
├── session.store.ts      pengguna aktif, peran, izin
├── ui.store.ts           sidebar, tema, dialog global
└── offline.store.ts      status koneksi, antrean (dipakai web juga untuk indikator)

features/work-plans/stores/
└── plan-filter.store.ts  filter & urutan daftar pekerjaan
```

### Aturan

1. **Data API tidak pernah masuk Zustand.** Simpan identitasnya, ambil datanya dengan
   TanStack Query. (Lihat A-22 — ini kesalahan paling umum dan paling mahal.)
2. **Satu store satu domain.** Tidak ada satu store raksasa berisi segalanya.
3. **Selector, bukan seluruh store.** `useStore(s => s.filter)` — bukan `useStore()` —
   supaya komponen tidak ikut me-render setiap kali apa pun berubah.
4. **Aksi ada di dalam store**, bukan `setState` yang dipanggil dari komponen.
5. **`persist` hanya untuk yang aman hilang**: preferensi, draf, filter. **Tidak pernah**
   untuk token atau data pribadi.

```ts
// bentuk yang dipakai
interface PlanFilterState {
  unit: string | null
  status: PlanStatus | null
  setUnit: (unit: string | null) => void
  reset: () => void
}
```

---

## 7. Form

Satu pola untuk seluruh aplikasi: **react-hook-form + zod + komponen `Form` shadcn**.

- Skema zod menjadi **satu-satunya** sumber aturan validasi di klien, dan dipakai juga oleh
  uji.
- Pesan validasi Bahasa Indonesia, ditulis di skema, bukan di komponen.
- **Validasi klien tidak menggantikan validasi server.** Server tetap memeriksa ulang;
  klien hanya mempercepat umpan balik.
- Galat dari server (422) dipetakan ke field yang bersangkutan, bukan ditampilkan sebagai
  toast umum.
- Form panjang (mis. penyusun SK) memakai draf otomatis di Zustand `persist` — kehilangan
  isi form yang sudah diketik 10 menit adalah cara tercepat membuat orang benci aplikasi.

---

## 8. Penanganan keadaan layar

Setiap layar yang mengambil data **wajib** menangani empat keadaan. Komponen bersama
(`QueryBoundary`) memaksanya, jadi tidak ada yang terlewat:

| Keadaan | Tampilan |
|---|---|
| Memuat | Skeleton yang bentuknya menyerupai isi, bukan spinner di tengah layar |
| Kosong | `EmptyState`: penjelasan + tindakan yang bisa dilakukan |
| Galat | Pesan Bahasa Indonesia + tombol "Coba lagi" |
| Berhasil | Isinya |

"Kosong" dan "galat" adalah keadaan yang paling sering dilupakan dan paling sering dilihat
pengguna baru.

---

## 9. Kinerja

- Pemecahan kode per rute (`lazy` + `Suspense`).
- Daftar panjang (> 100 baris) memakai virtualisasi.
- Gambar memakai `loading="lazy"` dan ukuran yang tepat (lihat dokumen 13 — server sudah
  menyediakan beberapa ukuran).
- Anggaran bundel awal: **< 250 KB** (gzip). Diperiksa di CI; melebihi = CI gagal.
- Tidak ada pustaka besar untuk keperluan kecil (mis. jangan menarik seluruh `lodash` hanya
  untuk `debounce`).

---

## 10. Daftar periksa sebelum satu layar dianggap selesai

1. [ ] Terbaca dan bisa dipakai pada lebar **360 px** tanpa gulir mendatar.
2. [ ] Tablet dan desktop diperiksa, bukan hanya diasumsikan.
3. [ ] Empat keadaan (memuat, kosong, galat, berhasil) ada semua.
4. [ ] Semua komponen berasal dari pustaka; yang buatan sendiri sudah masuk `components/`.
5. [ ] Tidak ada teks Inggris mentah dan tidak ada label status yang ditulis langsung.
6. [ ] Bisa dioperasikan dengan keyboard; fokus terlihat.
7. [ ] Kontras diperiksa.
8. [ ] Tidak ada data API yang disimpan di Zustand.
9. [ ] Tidak ada `any` dan tidak ada `@ts-ignore`.
10. [ ] Uji komponen untuk logika bersyarat; uji Playwright untuk alur utamanya.
