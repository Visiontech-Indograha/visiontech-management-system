# Pengujian web

## Status saat ini (bukti)

- 57 berkas tes di `web/src/test/` (`*.test.ts` dan `*.test.tsx`), datar. Tidak sejajar dengan komponen.
- Konfigurasi: `web/vitest.config.ts`: `environment: 'jsdom'`, `globals: true`, `setupFiles: ./src/test/setup.ts`, `testTimeout: 30000`. Alias `@` ke `src`.
- Tidak ada `@playwright/test` di `package.json`. Tidak ada E2E (bukti: riset `03` W8).
- Tidak ada gerbang cakupan di CI web (bukti: riset `01` F-22 untuk API; web sama).

## Piramida untuk web

| Lapisan | Porsi ideal (PDF bagian 11) | Alat | Contoh di VMS |
|---|---|---|---|
| Static analysis | 100% kode | `tsc -b`, ESLint | `npm run lint` |
| Unit | ~50-60% | Vitest | fungsi murni di `lib/` (`hseCarousel`, `zoomPan`) |
| Komponen | ~30-40% | Vitest + Testing Library (+ MSW bila perlu) | `test/*.test.tsx` |
| E2E | ~5-10% | Playwright | belum ada |

Sumber proporsi: panduan PDF `vms-next/docs/panduan/panduan-fullstack.txt` baris 1487-1521. Itu panduan umum, bukan standar tim.

## Prinsip Testing Library

Uji perilaku yang dilihat pengguna dan pembaca layar, bukan detail internal.

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

it('tombol simpan nonaktif dan sibuk saat menyimpan', async () => {
  const user = userEvent.setup();
  render(<Form onSubmit={slowSave} />);
  await user.click(screen.getByRole('button', { name: 'Simpan' }));
  expect(screen.getByRole('button', { name: /menyimpan/i })).toHaveAttribute('aria-busy', 'true');
});
```

Pakai `getByRole`, `getByLabelText`, `getByText` dengan nama yang sama dengan UI. Hindari `getByTestId` kecuali tidak ada cara lain.

## Lima kondisi layar per query

Setiap halaman yang punya query perlu tes untuk: memuat (skeleton), galat (pesan + tombol coba lagi memanggil `refetch`), kosong (teks dan aksi), berhasil. Gunakan MSW atau mock service untuk memaksa keadaan. Ini juga bagian dari checklist. Usulan dari riset `03` W-B: tes yang memeriksa keberadaan `QueryState` per halaman (belum dibuat).

## Uji per peran

Akses berbeda per peran (admin, PM, pekerja). Uji layar izin ditolak dan tombol yang disembunyikan per peran. Ada `lib/permissions.ts` sebagai sumber aturan di web.

## Uji konkurensi dan aksi ganda

Untuk tombol yang bisa diklik dua kali (ajukan cuti, simpan jadwal), uji bahwa mutasi hanya terkirim sekali atau tombol nonaktif saat pending. Di API, ada usulan tes konkurensi (riset `01` F-14).

## E2E untuk alur kunci (usulan, belum ada)

Tiga skenario dari riset `03` W-F: login dan ganti sandi, absen, ajukan cuti. Syarat:
- Pakai akun uji lokal di `scripts/akun-uji-lokal.txt`. Jangan menebak sandi berulang (ada lockout).
- Butuh API dan DB yang berjalan. Ikuti aturan DB uji di memori proyek.
- Playwright dijalankan atas perintah pengguna dan tidak masuk CI tanpa keputusan.

Catatan: aturan "Uji UI" di `CLAUDE.md` meminta tab Chrome sendiri, dan ditutup setelah selesai.

## Perintah

Dari `web/`:

```
npx vitest run                 # semua tes
npx vitest run src/test/hseCarousel.test.tsx
npx vitest                     # mode watch (lokal)
```

Dari root: `bash scripts/verify.sh web`.

Cara menjalankan Playwright lewat MCP dan uji per peran ada di skill `vms-qa` (bagian 6). Skill ini hanya menentukan alur mana yang perlu E2E.

Aturan memori proyek: tes dan skrip uji (pytest, uji DB) hanya dijalankan atas perintah pengguna. Tulis tes dulu, jalankan saat diminta.

## Checklist tes baru

- [ ] Nama tes menjelaskan perilaku dalam Bahasa Indonesia atau Inggris, konsisten dengan file sekitar.
- [ ] Query lewat peran dan label.
- [ ] Tidak ada `setTimeout` nyata. Pakai `vi.useFakeTimers()` untuk timer baca.
- [ ] Mock hanya dependensi eksternal (API lewat MSW atau mock service).
- [ ] `matchMedia` di-mock bila komponen memakai reduced motion (di jsdom tidak ada).
- [ ] `getBoundingClientRect` di-mock bila memakai virtualisasi.
