# Carousel dan zoom foto (pola K3)

Sumber kode (sudah dibangun, dibaca sebagai acuan):
- `web/src/components/organisms/hse/CampaignMediaCarousel.tsx` (160 baris): carousel foto dengan tombol dan label.
- `web/src/components/organisms/hse/HseMandatoryPopupGate.tsx` (372 baris): popup wajib baca K3 (penuh layar, timer baca).
- `web/src/components/molecules/ZoomableImage.tsx`: zoom dan geser foto, tombol Perkecil, Perbesar, Pas layar.
- `web/src/hooks/useTimedCarousel.ts` (112 baris): timer baca dan auto-geser.
- `web/src/lib/hseCarousel.ts` (56 baris): logika murni (interval, sisa detik, indeks).
- `web/src/lib/zoomPan.ts` (67 baris): matematika zoom dan batas geser (fungsi murni).
- Tes: `web/src/test/hseCarousel.test.tsx`, `web/src/test/zoomCaption.test.tsx`.
- Mobile setara: `mobile/lib/features/hse/k3_campaign_view.dart` (532 baris), `k3_campaign_controller.dart`, `k3_campaign_gate.dart`, tes `mobile/test/k3_campaign_test.dart`.

## Aturan waktu (dari `lib/hseCarousel.ts`)

- Durasi baca 10 sampai 300 detik (`CAROUSEL_MIN_SECONDS`, `CAROUSEL_MAX_SECONDS`).
- Minimal 3 detik per foto (`CAROUSEL_SECONDS_PER_PHOTO`). Durasi harus >= jumlah foto x 3.
- Maksimal 8 foto per kampanye (`CAROUSEL_MAX_PHOTOS`).
- Interval geser = durasi total / jumlah foto, minimal 1 detik.
- Timer baca wajib berjalan sejak mount dan tidak dipercepat navigasi manual. Setiap pindah foto (otomatis atau manual) memulai ulang interval geser.
- Aturan ini selaras dengan API (`api/app/modules/hse/services/hse_service.py`). Jika aturan berubah, ubah keduanya dan tes.

## Pola ARIA carousel

```tsx
<section role="region" aria-roledescription="carousel" aria-label="Foto panduan K3">
  <div aria-live="polite" aria-atomic="true" className="sr-only">
    {`Foto ${index + 1} dari ${count}`}
  </div>
  <Button aria-label="Foto sebelumnya" onClick={prev}>...</Button>
  <Image src={current.src} alt={current.alt} />
  <Button aria-label="Foto berikutnya" onClick={next}>...</Button>
</section>
```

Setiap slide punya label "Foto N dari M". Tombol panah diberi `aria-label`. Keyboard: panah kiri dan kanan memindah foto (`useTimedCarousel` `keyboard`).

Jika ada jeda otomatis, sediakan tombol Jeda (WCAG 2.2 SC 2.2.2). Pada K3, timer baca wajib memang tidak boleh dijeda oleh pengguna. Itu keputusan produk, bukan kelalaian. Dokumentasikan alasannya di komponen dan tes.

## Zoom

- Skala 1x sampai 4x (`ZOOM_MIN`, `ZOOM_MAX`). Klik ganda memperbesar ke 2x (`ZOOM_DOUBLE_TAP`).
- Tombol Perkecil, Perbesar, Pas layar wajib ada (bukan hanya cubit). Tombol nonaktif saat batas tercapai.
- `aria-live="polite"` pada label persentase zoom.
- Geser (pan) hanya saat zoom, dibatasi tepi (`clampPan`). Saat belum zoom, geser satu jari diberikan ke carousel.
- Sediakan alternatif tombol untuk geser (WCAG 2.5.7).

## Popup wajib baca (`HseMandatoryPopupGate`)

- Penuh layar dan memblokir sampai waktu baca selesai dan konfirmasi.
- Fokus masuk ke dialog, dikunci di dalamnya, dan kembali ke pemicu.
- Timer ditampilkan dengan `role="timer"` dan sisa detik. Pada K3 `aria-live="off"` agar pembaca layar tidak diberondong.
- Bilah kemajuan memakai `readProgressPercent`.

Catatan jujur: popup ini memakai kelas palet bawaan (`text-amber-600`, baris 214). Kelas itu tidak menghasilkan CSS karena palet dimatikan (lihat `anti-pola.md`). Ganti dengan token warning.

## Checklist carousel atau zoom baru

- [ ] Logika waktu dan indeks di fungsi murni (`lib/`), dengan tes unit.
- [ ] Hook untuk timer, dengan `prefers-reduced-motion`.
- [ ] Tombol sebelumnya, berikutnya, zoom dengan `aria-label` dan ukuran 44 px.
- [ ] Label "Foto N dari M" dan region carousel.
- [ ] Keyboard: panah dan Escape.
- [ ] Gambar punya `alt`. Tidak ada teks alt kosong untuk foto bermakna.
- [ ] Tes di jsdom untuk aturan waktu dan batas zoom.
- [ ] Cek manual di HP lapangan (sentuh dan cahaya terang).
