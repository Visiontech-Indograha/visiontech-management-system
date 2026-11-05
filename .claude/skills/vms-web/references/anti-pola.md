# Anti-pola web VMS (dengan bukti)

Format: temuan, bukti (berkas), dampak, dan langkah perbaikan. "Perlu cek" berarti belum diverifikasi di browser atau profil.

## A1. Kelas palet bawaan Tailwind dipakai, padahal palet dimatikan (tinggi, perlu cek)

- Bukti kode: `web/src/styles/index.css` memakai `@theme inline { --color-*: initial; ... }` (sekitar baris 97-99). Komentar di berkas itu: `bg-purple-500`, `text-indigo-*` tidak lagi menghasilkan CSS.
- Bukti pemakaian: grep `(text|bg|border)-(amber|red|green|blue|slate|gray|emerald)-[0-9]{3}` di `web/src` (tsx) menemukan 171 baris, termasuk berkas tes. Berkas terbanyak: `organisms/media/ImageLightboxModal.tsx` (33), `organisms/work-orders/WorkOrderSurveyReviewModal.tsx` (26), `organisms/work-completions/WorkCompletionDetailModal.tsx` (18), `organisms/media/UniversalMediaModal.tsx` (17), `organisms/media/PdfViewerModal.tsx` (14), `organisms/audit/BackupRegistryTable.tsx` (12), `organisms/hse/HseCampaignsPanel.tsx` (9).
- Contoh: `web/src/components/organisms/hse/HseMandatoryPopupGate.tsx:214` memakai `text-amber-600`.
- Dampak: kelas tidak menghasilkan CSS, jadi warna tidak tampil. Tidak ada error. Dampak ke pengguna: status dan peringatan kurang terlihat, dan kontras tidak terjamin.
- Perbaikan: ganti dengan token semantik (`text-warning`, `bg-danger-soft`, `text-success`, dll. dari `index.css`). Tambahkan token bila belum ada. Cek di browser sebelum dan sesudah.
- Cara cek: buka halaman, periksa `getComputedStyle` pada elemen itu, atau cari aturan di CSS hasil build.

## A2. Hex literal di komponen (sedang)

- Bukti: riset `03` W5: `SignaturePad.tsx` (`#0f172a`), `SelfieCaptureDialog.tsx` (`#ffffff`), `SurveyLayoutMap.tsx` (`STATUS_COLOR`: `#16A34A`, `#0284C7`), `WorkOrderSurveyReviewModal.tsx` (marker HTML berisi `#0284C7`, dengan `onmouseover` inline).
- Perbaikan: token semantik (`--color-status-existing`, `--color-status-proposed`). Marker peta: kelas Tailwind dan event handler React, bukan string HTML.

## A3. Daftar panjang tanpa virtualisasi (sedang)

- Bukti: 0 impor `@tanstack/react-virtual`. Sekitar 87 berkas memakai `.map(` untuk daftar (riset `03` W3).
- Kandidat: daftar pekerja, audit log, rekap absensi, daftar work order (riset `03` W-A).
- Perbaikan: setelah paginasi server, virtualisasi bila >200 baris tampil.

## A4. Organisme dan modal terlalu besar (sedang)

- Bukti: `WorkOrderSurveyReviewModal.tsx` 33 KB (peta, marker HTML, form). Sekitar 17 organisme di atas 12 KB, termasuk `DocumentsPanel.tsx`, `WorkCompletionFormDialog.tsx`, `ClientSitesModal.tsx`, `HseMandatoryPopupGate.tsx` (riset `03` W9).
- Perbaikan: pecah ke hook (`useSurveyMarkers`, `useSurveyReviewForm`) dan sub-komponen organisme.

## A5. Dependensi tidak dipakai (rendah)

- Bukti: `eslint-plugin-boundaries` ada di `devDependencies`, tetapi `eslint.config.js` tidak memakainya (`grep -n boundaries web/eslint.config.js` kosong).
- Perbaikan: hapus setelah konfirmasi, lalu `npm run lint` dan `npx tsc -b --noEmit`.

## A6. Tidak ada E2E (sedang)

- Bukti: `package.json` tanpa `@playwright/test`. Tidak ada `web/e2e/`.

## A7. Pengambilan data di `useEffect` (sedang)

- Bukti: riset `01` T15: 3 berkas memakai `useEffect` dengan `fetch`.
- Perbaikan: pindahkan ke `useQuery`. Aturan dari panduan PDF baris 630-632.

## A8. Struktur fitur vs lapisan (informasi)

- `docs/02` (VMS Next) mengusulkan `features/<fitur>/{api,model,ui,pages}`. Kode nyata: lapisan `pages/ components/ services/ schemas/ hooks/ lib/` (`eslint.config.js` komentar baris 4-5).
- Ikuti kode. Usulan `features/` perlu keputusan pemilik.

## A9. Paginasi: cursor atau page (informasi)

- `docs/02` menyebut cursor (`X-Next-Cursor`). `CLAUDE.md` proyek dan kode memakai `page`, `size`, `X-Total-Count` (`ListParams`).
- Ikuti `CLAUDE.md`.

## A10. Elemen HTML atau teks di template, organisme, molekul, atau halaman (dicegah ESLint)

- Pola ini ditangkap `npm run lint`. Jangan menambah `eslint-disable` untuk melewatinya.

## A11. Pesan 422 mentah (dicegah lewat `applyFieldErrors`)

- Pesan pydantic berbahasa Inggris tidak boleh tampil. Pakai `applyFieldErrors` dan `errorMessage`.

## A12. Kode API dari tangan (dicegah lewat `gen:api`)

- Tipe respons harus dari `apiTypes.ts`. Verifikasi sinkron dijalankan `scripts/verify.sh` (langkah "web apiTypes sinkron").

## Kekuatan yang sudah baik (agar tidak diubah tanpa alasan)

- Atomic design ditegakkan ESLint. Tidak ada barrel `index.ts`.
- `QueryState` menangani memuat, galat, kosong.
- Route lazy dan `errorElement`.
- Carousel K3 dengan label ARIA, keyboard, reduced motion, dan zoom dengan tombol.
- Token dengan `@theme inline` dan palet dimatikan (perlu diikuti, bukan dilanggar).
