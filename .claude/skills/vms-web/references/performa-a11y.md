# Performa dan aksesibilitas web

## 1. Big O praktis untuk UI

| Operasi | Biaya | Catatan VMS |
|---|---|---|
| Lookup kunci (`Map`, `Set`, objek) | O(1) | Pakai untuk "sudah dipilih?", "milik tim mana?" |
| Urut daftar di klien | O(n log n) | Hindari jika server bisa mengurutkan |
| Satu loop + lookup hash | O(n) | Pola benar |
| Loop bersarang atas daftar | O(n·m) | Hindari di render; kelompokkan dulu |
| Satu query per baris | O(n) request | N+1 di UI; gabungkan di API |

Pola yang benar (bukti: `api/app/modules/work_plans/services/survey_service.py:112-114`, `daily_plan_service.py:377-380`): ambil semua data sekali, kelompokkan dengan dict, lalu render dari lookup.

Riset PDF menyebut "Gunakan IN (...) atau JOIN, bukan N+1" (sumber: `vms-next/docs/panduan/panduan-fullstack.txt` baris 86-92 dan 1-97). Di web, artinya: satu endpoint daftar yang sudah menggabungkan data, bukan satu request per baris.

## 2. Virtualisasi

Kapan: daftar setelah paginasi yang bisa lebih dari sekitar 200 baris tampil bersamaan, atau tabel dengan baris tinggi tidak tetap. Sumber ambang: riset `01` F-25.

Dasar API `useVirtualizer` (sumber: https://tanstack.com/virtual/latest/docs/api/virtualizer, diakses 2026-11-04):
- `count`: jumlah item.
- `getScrollElement`: elemen yang bisa di-scroll (boleh `null` saat belum siap).
- `estimateSize`: perkiraan tinggi item.
- `overscan`: item tambahan di atas dan bawah (default 1).
- `measureElement`: opsional, untuk tinggi dinamis (pakai `ResizeObserver`).
- `getVirtualItems()`: item yang harus dirender.

Contoh pola:

```tsx
const parentRef = useRef<HTMLDivElement>(null);
const v = useVirtualizer({
  count: rows.length,
  getScrollElement: () => parentRef.current,
  estimateSize: () => 56,
  overscan: 8,
});
return (
  <div ref={parentRef} style={{ height: 480, overflow: 'auto' }}>
    <div style={{ height: v.getTotalSize(), position: 'relative' }}>
      {v.getVirtualItems().map((item) => (
        <div key={item.key} data-index={item.index} ref={v.measureElement}
             style={{ position: 'absolute', top: 0, transform: `translateY(${item.start}px)` }}>
          {/* baris dari atom/molekul, bukan elemen HTML langsung */}
        </div>
      ))}
    </div>
  </div>
);
```

Risiko (sumber: riset `03` W-A): tinggi berbeda butuh `measureElement`. Tes Vitest perlu mock `getBoundingClientRect`. Virtualisasi mengubah perilaku pemilihan teks dan navigasi keyboard; uji dengan keyboard.

Catatan aturan atomic: baris virtual harus dirender dari organisme/molekul. Elemen wrapper dengan `style` tetap `div` tata letak (boleh di organisme).

## 3. Memo, transisi, dan INP

- React Compiler belum dipakai di VMS. Jangan menambah `useMemo` dan `useCallback` di mana-mana. Tambahkan hanya bila profil menunjukkan masalah.
- `useTransition` untuk filter dan pencarian yang memicu render berat, agar ketikan tetap responsif. Target INP di bawah 200 ms (sumber: panduan PDF baris 711-714, bukan dari dokumentasi React yang dibuka sesi ini).
- Ukur dengan Lighthouse atau `web-vitals` sebelum dan sesudah. Riset belum mengukur INP VMS.

## 4. Bundle dan code splitting

- Route halaman sudah lazy (`app/lazyPages.ts`).
- Komponen berat (peta Leaflet, kamera, tanda tangan, PDF) di-lazy di tingkat fitur, dengan `Suspense` dan skeleton.
- `manualChunks` belum ada. Tambah setelah analisis (`npx vite-bundle-visualizer` atau `rollup-plugin-visualizer`). Pisahkan vendor (react, query, zod) agar cache browser awet.
- Ukuran di `dist` (riset, dibuat 4 Nov 09:05; mungkin tidak sama dengan kode sekarang): entry 504 KB, `PageTemplate` 247 KB (mentah). Chunk `PageTemplate` yang besar diduga menarik dependensi berat. Verifikasi dulu.

## 5. Aksesibilitas (WCAG 2.2 AA)

Kriteria yang sering dipakai di VMS:

| Kriteria | Ketentuan | Penerapan |
|---|---|---|
| 2.5.8 Target Size (Minimum) | minimal 24x24 CSS px; ada pengecualian spacing | Pakai 44-48 px untuk aksi lapangan |
| 2.5.7 Dragging Movements | sediakan alternatif tanpa geser | tombol Sebelumnya/Berikutnya di samping geser |
| 2.2.2 Pause, Stop, Hide | gerakan otomatis >5 dtk harus bisa dijeda | timer carousel perlu tombol jeda |
| 1.4.3 Contrast (Minimum) | 4.5:1 teks normal, 3:1 teks besar | pakai token semantik |
| 1.4.1 Use of Color | informasi tidak hanya warna | ikon + teks |
| 2.4.7 Focus Visible | fokus terlihat | jangan `outline: none` tanpa ganti |
| 4.1.2 Name, Role, Value | semua kontrol punya nama | `aria-label` untuk tombol ikon |

Sumber: https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html (diakses 2026-11-04). Kriteria lain di atas dari pengetahuan umum WCAG 2.2 dan belum dibuka langsung di sesi ini; verifikasi sebelum dikutip.

Pola ARIA:
- `aria-busy="true"` pada area yang sedang memuat atau tombol saat simpan.
- `aria-invalid="true"` dan `aria-describedby` ke pesan galat pada kolom.
- `role="alert"` untuk galat yang harus diumumkan (sudah di `QueryState`).
- `aria-live="polite"` untuk status (hitung mundur, jumlah hasil). Hindari `assertive` kecuali darurat.
- Dialog: `role="dialog"`, `aria-modal`, judul dengan `aria-labelledby`, fokus masuk ke dialog, fokus kembali ke pemicu saat tutup, Escape menutup.

Catatan: pemakaian `aria-busy` di VMS masih jarang (riset `01` T27: `aria-busy` 1 kali). Periksa tombol simpan.

## 6. Reduced motion

```ts
const reduce = typeof window !== 'undefined'
  && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
```

Dengan reduce aktif: matikan geser otomatis, kurangi animasi transisi. Contoh di `hooks/useTimedCarousel.ts`.

## 7. Galat dan pesan

- Tampilkan pesan Indonesia yang menjelaskan apa yang terjadi dan apa yang bisa dilakukan. Jangan tampilkan kode mentah (`Error 500`).
- `errorMessage(err)` mengambil pesan dari `ApiError` atau pesan umum.
- Error boundary route: `errorElement: <RouteErrorPage />` (bukti: `web/src/app/routes.tsx:67`).
