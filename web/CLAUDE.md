# Web VMS (React 19 + Vite + TypeScript)

Aturan ringkas untuk folder `web/`. Teks UI wajib Bahasa Indonesia sehari-hari.

## Aturan inti
- Atomic design ditegakkan ESLint: Page > Template > Organism > Molecule > Atom. Page hanya impor template; halaman tidak impor halaman.
- Elemen HTML (`div` untuk isi, `button`, `p`, `img`, teks langsung) hanya di atom. Template, organisme, molekul: tag tata letak saja.
- HTTP hanya di `src/services/`. Data server lewat TanStack Query, bukan `useEffect` + `fetch`.
- Tipe respons dari `src/lib/apiTypes.ts` (`npm run gen:api`). Jangan tulis tangan.
- Lima kondisi layar lewat `QueryState`. Galat 422 lewat `applyFieldErrors`.
- Warna dari token semantik. Jangan hex atau kelas palet bawaan Tailwind (palet dimatikan di `src/styles/index.css`).
- Batas input sama dengan skema API. Pencarian pakai awalan.

## Skill terkait
- `vms-web`: pola data, form, performa, aksesibilitas, carousel, pengujian, anti-pola.
- `vms-ux-design-system`: token, glosarium istilah, popup K3, uji awam.
- Untuk HTML, CSS, atau JS klien baru: panggil `modern-web-guidance:modern-web-guidance` dulu.

## Perintah (dari `web/`)
- Cek tipe seperti CI: `npx tsc -b --noEmit` (jangan `tsc -p .`).
- Lint: `npm run lint`.
- Tes: `npx vitest run` (atas perintah pengguna).
- Build: `npm run build`.
- Dari root, semua langkah web: `bash scripts/verify.sh web`.
- Setelah API berubah: `npm run gen:api:export && npm run gen:api`.

## Hindari
- `any` (pakai `unknown` lalu parse dengan Zod).
- `console.log` tertinggal.
- Elemen HTML atau teks di luar atom (ESLint akan menolak).
- `eslint-disable` untuk melewati aturan atomic tanpa catatan.
- Virtualisasi atau memo manual tanpa ukuran.

## Uji UI
- Pakai tab Chrome sendiri dan tutup setelah selesai (`CLAUDE.md` root).
