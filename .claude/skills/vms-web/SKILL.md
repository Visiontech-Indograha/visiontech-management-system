---
name: vms-web
description: "Panduan kerja frontend web VMS (React 19 + Vite + TypeScript + TanStack Query + Zod + Tailwind 4 + React Router 7 + Vitest). Pakai saat menambah atau mengubah halaman, template, organisme, molekul, atom, hook, service, form, daftar/tabel, carousel atau zoom foto, popup, tes web, atau mereview kode di folder web/. Kata kunci: web, react, vite, tsx, frontend, atomic design, page, template, organism, molecule, atom, useQuery, useMutation, queryKey, invalidasi cache, optimistic update, Zod, schema, form, react-hook-form, applyFieldErrors, 422, QueryState, lima kondisi layar, loading, kosong, galat, skeleton, aksesibilitas, WCAG, ARIA, focus, virtualisasi, TanStack Virtual, code splitting, bundle, performa, INP, Vitest, Testing Library, Playwright, E2E, halaman, carousel, zoom, popup K3, UI web, layar web, perbaiki web, review web."
---

# vms-web

Skill kerja untuk `web/` (SPA React untuk intranet). Teks UI wajib Bahasa Indonesia sehari-hari (lihat skill `vms-ux-design-system`).

Pendamping: `references/struktur-impor.md`, `references/data-form.md`, `references/performa-a11y.md`, `references/carousel-zoom.md`, `references/pengujian.md`, `references/anti-pola.md`.

## 1. Aturan inti (wajib)

1. Lapisan atomic design ditegakkan ESLint (`web/eslint.config.js`). Urutan: Page > Template > Organism > Molecule > Atom. Lihat `references/struktur-impor.md`.
2. Elemen HTML (`div` untuk isi, `button`, `p`, `img`, `table`, teks langsung) hanya di atom. Template, organisme, dan molekul hanya boleh tag tata letak (`div`, `section`, `main`, `header`, `footer`, `article`, `aside`, `nav`). Halaman tidak boleh memakai elemen HTML sama sekali (bukti: `eslint.config.js` aturan `no-restricted-syntax`).
3. Page hanya mengimpor template. Page tidak mengimpor page lain. Hanya `app/` (rute) yang mengimpor `pages/`.
4. Panggilan HTTP hanya di `services/`. Komponen memakai hook TanStack Query. Jangan `fetch` atau `api()` langsung di komponen (bukti: aturan `API_ONLY_IN_SERVICES` di `eslint.config.js`).
5. Data dari server hanya lewat TanStack Query. Jangan salin data server ke store global (Zustand) lewat `useEffect`.
6. Tipe respons API dari `src/lib/apiTypes.ts` hasil `npm run gen:api`. Jangan tulis tipe respons dengan tangan.
7. Validasi di batas: data dari API di-parse dengan Zod (`src/schemas/`), dan isian form juga Zod.
8. Setiap query punya lima kondisi layar: memuat, galat, kosong, sebagian, berhasil. Pakai `QueryState` (`src/components/molecules/QueryState.tsx`).
9. Galat 422 dari API dipetakan ke kolom form dengan `applyFieldErrors` (`src/lib/errors.ts`).
10. Warna lewat token semantik saja. Jangan pakai hex, `px` acak, atau kelas palet bawaan Tailwind (`text-amber-600`, `bg-red-500`). Palet bawaan sudah dimatikan di `src/styles/index.css` (`--color-*: initial`).
11. Jangan menambah tes atau menjalankan `vitest` tanpa perintah pengguna jika ada aturan itu di memori proyek. Untuk verifikasi rutin pakai perintah di bagian 9.

## 2. Struktur folder (ringkas)

```
web/src/
  app/          rute (routes.tsx), lazyPages.ts, navigasi, guard
  pages/        halaman per modul (tipis: pilih template, isi data)
  components/
    atoms/      Button, Text, Image, Icon, Skeleton, Input (elemen HTML di sini)
    molecules/  QueryState, ActionButton, ZoomableImage, VmsDialog
    organisms/  daftar, kartu, panel, modal per domain (hse/, assets/, mess/, ...)
    templates/  kerangka halaman (AppShell, HseCampaignsTemplate, ...)
  services/     fungsi HTTP per domain (hseService.ts, ...)
  hooks/        hook UI dan data (useListControls, usePagedList, useTimedCarousel)
  schemas/      skema Zod per domain
  lib/          apiClient.ts, errors.ts, apiTypes.ts (generated), util murni
  stores/       Zustand untuk state klien kecil (sessionStore)
  styles/       index.css (token @theme), tokens.css
  test/         tes Vitest, datar (flat), setup.ts
```

Catatan: `docs/02` (VMS Next) mengusulkan `features/<fitur>/`. Kode nyata memakai struktur berlapis di atas, dan `eslint.config.js` menyatakan "berbasis lapisan". Ikuti kode nyata. Jangan memindahkan struktur tanpa keputusan pemilik.

## 3. Pola data (ringkas, detail di `references/data-form.md`)

- Query key terpusat per domain, bentuk `[domain, 'list' | 'detail', ...param]`. Invalidasi memakai prefiks domain, bukan string lepas.
- Mutasi: `useMutation`, lalu di `onSuccess` invalidasi key yang terdampak. Untuk aksi ringan (centang, tandai baca) boleh optimistic dengan `onMutate` (snapshot), `onError` (rollback), `onSettled` (invalidate). Aksi persetujuan (approve, reject, serah terima) tidak boleh optimistic.
- Daftar memakai `ListParams` di API: `q`, `page`, `size`, total dari header `X-Total-Count`. Hook `usePagedList` dan `useListControls` sudah ada. (Catatan: `docs/02` menyebut cursor. `CLAUDE.md` proyek menetapkan page/size. Ikuti `CLAUDE.md`.)
- `staleTime` dipakai secukupnya. Jangan menyalin data ke state lokal kecuali untuk draf form (`useFormDraft`).

## 4. Lima kondisi layar

| Kondisi | Wajib tampil | Sumber VMS |
|---|---|---|
| Memuat | skeleton berbentuk seperti konten, bukan spinner di tengah | `QueryState` pakai `Skeleton` |
| Galat | kalimat manusiawi + tombol "Coba lagi" (`refetch`) | `QueryState` `errorText` |
| Kosong | penjelasan + aksi (`emptyAction`) | `QueryState` `empty`, `emptyText` |
| Sebagian | data sebagian tampil, peringatan jelas | belum ada komponen khusus (lihat skill `vms-ux-design-system`) |
| Berhasil | data penuh, teks panjang dipotong dengan aman | template |

Izin ditolak: `ForbiddenPage` (sumber: riset `03-WEB-MOBILE.md` W6). Bukti tes halaman belum diverifikasi otomatis (lihat `references/pengujian.md`).

## 5. Form dan galat 422

- Skema Zod di `src/schemas/`. Form memakai `react-hook-form` + `@hookform/resolvers` (versi ada di `package.json`).
- Saat mutasi gagal: `if (!applyFieldErrors(err, setError, KNOWN_FIELDS)) toast(errorMessage(err))`. Daftar `KNOWN_FIELDS` harus cocok dengan nama field API.
- Pesan 422 dari API berbahasa Inggris (pydantic). `applyFieldErrors` memakai pesan Indonesia seragam. Jangan menampilkan pesan mentah.
- Batas input (panjang, pola, rentang tanggal) harus sama dengan skema API (`max_length`, `ge`, `le`) (bukti: `CLAUDE.md` aturan "Batas input web/mobile harus sama dengan skema API").

## 6. Performa (Big O praktis)

- Filter dan urut di klien hanya untuk data yang sudah dibatasi server. Hindari O(n²) di render (dua loop bersarang atas daftar besar). Pakai `Map` atau `Set` untuk lookup (O(1)). Contoh pola benar: `work_plans` mengelompokkan dengan dict (bukti: `api/app/modules/work_plans/services/survey_service.py:112-114`, sumber: `riset-best-practice/01`, T1).
- Jangan N+1 di UI: satu query per baris tabel. Ambil data gabungan dari API atau pakai `useQueries` untuk jumlah tetap kecil.
- Virtualisasi (`@tanstack/react-virtual`) untuk daftar yang bisa lebih dari sekitar 200 baris setelah paginasi. Saat ini belum dipakai (0 impor). Lihat `references/performa-a11y.md`.
- Route lazy sudah ada (`app/lazyPages.ts`). Belum ada `manualChunks` di `vite.config.ts`.
- Ukur sebelum dan sesudah (INP, LCP). Angka bundle dari `dist` (entry 504 KB mentah) mungkin tidak sama dengan kode sekarang (sumber: riset `03` W7).

## 7. Aksesibilitas (WCAG 2.2 AA)

- Target sentuh minimal 24x24 CSS px (SC 2.5.8). Untuk lapangan gunakan 44-48 px. Tombol ikon wajib `aria-label`.
- Kontras teks 4.5:1 (teks besar 3:1). Jangan hanya warna: pakai ikon dan teks.
- Keyboard: semua aksi bisa lewat Tab, Enter, Space, Escape. Dialog memakai focus trap dan mengembalikan fokus ke pemicu.
- Keadaan: `aria-busy` saat simpan, `aria-invalid` dan pesan galat di kolom, `role="alert"` untuk galat (sudah di `QueryState`), `aria-live="polite"` untuk status yang berubah.
- Hormati `prefers-reduced-motion`: matikan geser otomatis dan animasi besar.
- Detail dan contoh: `references/performa-a11y.md`.

## 8. Carousel dan zoom foto (pola K3)

Sudah dibangun dan bisa ditiru: `components/organisms/hse/CampaignMediaCarousel.tsx`, `HseMandatoryPopupGate.tsx`, `components/molecules/ZoomableImage.tsx`, `hooks/useTimedCarousel.ts`, `lib/hseCarousel.ts`, `lib/zoomPan.ts`. Detail di `references/carousel-zoom.md`.

Ringkas: role region + `aria-roledescription="carousel"`, tombol "Foto sebelumnya/berikutnya", zoom 1x-4x dengan tombol Perkecil/Perbesar/Pas layar (bukan hanya cubit), timer baca wajib yang tidak dipercepat navigasi manual, dan geser otomatis mati bila reduced motion.

## 9. Perintah verifikasi (sama dengan CI)

Dari root repo:

```
bash scripts/verify.sh web        # tsc -b, lint, vitest, sinkron apiTypes
```

Atau manual di `web/`:

```
npx tsc -b --noEmit               # JANGAN "tsc -p ." (tidak memeriksa kode app)
npm run lint
npx vitest run
npm run build                     # tsc -b && vite build
npm run gen:api:export && npm run gen:api   # setelah API berubah
```

Peringatan dari memori proyek: `tsc --noEmit -p .` pernah lolos di laptop padahal CI gagal dengan 7 error. Selalu `tsc -b`.

Tes Vitest (`npx vitest run`) dan build adalah pekerjaan yang hanya dijalankan atas perintah pengguna jika memori "tes hanya atas perintah" berlaku di sesi itu. Tulis tes, jalankan belakangan.

## 10. Checklist selesai

- [ ] Lapisan benar (page hanya template, tidak ada elemen HTML di luar atom/tata letak).
- [ ] Tidak ada `fetch`/`api()` di komponen; panggilan ada di `services/`.
- [ ] Query key konsisten; invalidasi sesuai; aksi persetujuan tidak optimistic.
- [ ] Lima kondisi layar ada untuk setiap query.
- [ ] Form: Zod, `applyFieldErrors` untuk 422, pesan Indonesia sederhana.
- [ ] Warna dari token; tidak ada hex atau kelas palet bawaan.
- [ ] Aksesibilitas: label tombol ikon, fokus, target 44 px untuk aksi lapangan, `prefers-reduced-motion`.
- [ ] Batas input sama dengan API.
- [ ] `tsc -b`, lint, vitest, build hijau (sesuai perintah pengguna).
- [ ] Tidak ada `console.log`, tidak ada `any`, tipe dari `apiTypes`.

## 11. Anti-pola nyata (ringkas, detail di `references/anti-pola.md`)

1. Kelas palet bawaan Tailwind (`text-amber-600`, dll.) dipakai di banyak berkas padahal palet dihapus. Contoh: `web/src/components/organisms/hse/HseMandatoryPopupGate.tsx:214`. (bukti: `web/src/styles/index.css` baris 97-99; grep kelas palet menemukan 171 baris, sebagian di berkas tes). Perlu cek di browser.
2. Hex literal di komponen (`SignaturePad.tsx`, `SelfieCaptureDialog.tsx`, `SurveyLayoutMap.tsx`) (bukti: riset `03` W5).
3. Daftar panjang tanpa virtualisasi (bukti: 0 impor `@tanstack/react-virtual`).
4. Berkas organisme terlalu besar: `components/organisms/work-orders/WorkOrderSurveyReviewModal.tsx` 33 KB (bukti: riset `03` W9).
5. Dependensi tak dipakai: `eslint-plugin-boundaries` di `package.json` tetapi tidak ada di `eslint.config.js`.
6. Tidak ada Playwright (bukti: `package.json` tanpa `@playwright/test`).
7. Tes dan struktur: tes datar di `src/test/`, bukan sejajar fitur seperti `docs/02` (fakta, bukan masalah wajib).
8. Tiga berkas memakai `useEffect` + `fetch` manual (bukti: riset `01` T15). Pindahkan ke TanStack Query.

## 12. Skill global yang boleh dipanggil atau dilebur

- `modern-web-guidance:modern-web-guidance`: WAJIB dipanggil dulu untuk HTML, CSS, atau JS klien baru (dialog, popover, container query, View Transitions, performa). Jangan menebak API browser. Lebur hasilnya ke aturan di atas, bukan menyalin mentah.
- `simplify`: setelah perubahan selesai, untuk merapikan duplikasi dan pola berlebih. Tidak mencari bug.
- `code-review`: sebelum PR, untuk menemukan bug. Jalankan di diff, bukan di seluruh repo.
- Untuk grafik di web gunakan skill `dataviz` (bukan `vms-web`).

## 13. Sumber (diakses 2026-11-04)

- WCAG 2.2, SC 2.5.8 Target Size (Minimum): https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html
- TanStack Virtual, API Virtualizer: https://tanstack.com/virtual/latest/docs/api/virtualizer
- Tailwind CSS v4, Theme variables (`@theme`, `@theme inline`, `--color-*: initial`): https://tailwindcss.com/docs/theme
- Repo referensi (riset, diverifikasi 2026-11-04): `riset-best-practice/03-WEB-MOBILE.md` (bulletproof-react, TanStack Query/Virtual, yet-another-react-lightbox, react-zoom-pan-pinch).
- Belum dibuka langsung di sesi ini (tautan referensi, perlu verifikasi sebelum dikutip): React 19 (https://react.dev), TanStack Query (https://tanstack.com/query), Zod 4 (https://zod.dev), Vitest (https://vitest.dev), Testing Library (https://testing-library.com), Playwright (https://playwright.dev), Vite (https://vite.dev).
