---
name: vms-laporan-ekspor
description: >-
  Pakai skill ini untuk ekspor dan cetak dokumen laporan VMS: laporan survei, harian, mingguan, bulanan, work completion (serah terima pekerjaan), rekap material, dalam format PDF, Word (docx), dan PowerPoint (pptx). Modul api/app/modules/exports, builder docx/pptx/pdf/xlsx, konversi LibreOffice, tombol unduh di web, izin per peran, judul dokumen berbahasa Indonesia awam, tes isi dokumen. Kata kunci: ekspor, cetak, laporan, PDF, docx, pptx, Word, PowerPoint, BAST, serah terima, survei, harian, mingguan, bulanan, work completion, rekap, python-docx, python-pptx, reportlab, WeasyPrint, LibreOffice.
---

# Laporan dan ekspor dokumen VMS

## Peta kode (baca dari origin/development)
- Route: `api/app/modules/exports/export_route.py`; service: `services/export_service.py`; builder: `services/builders/` (`docx_builders.py`, `office_builders.py` untuk pptx/xlsx, `pdf_builders.py`); konversi docx->pdf: `app/shared/documents/office_convert.py`.
- Pustaka: python-docx, python-pptx, reportlab, WeasyPrint, openpyxl; PDF dari Word lewat LibreOffice (soffice).
- Web: `WorkCompletionExportPanel`, `DailyPlanDetailDialog`, `DailyWeekToolbar`, `SurveyReviewBar`, `SurveyPreviewPanel`; layanan `exportService.ts`.

## Matriks target (satu sumber isi, tiga format)
Setiap jenis laporan (survei, harian, mingguan, bulanan, work completion) tersedia PDF, Word, dan PPTX dengan isi yang sama. Bangun Word/PPTX, lalu PDF dari Word lewat `office_convert`, supaya tata letak tidak ganda. Tanpa parameter format = perilaku lama (APK lama tetap jalan).

## Aturan
1. Rentang: harian = 1 tanggal; mingguan = 7 hari mulai Senin (validasi di skema API, 422 Bahasa Indonesia); bulanan = bulan kalender (tahun+bulan); rentang lain lewat `check_date_range`.
2. Builder sinkron WAJIB lewat `_build`/`build_limited` (threadpool), jangan dipanggil langsung di fungsi async.
3. POST ekspor idempoten (`idempotency_guard`): klik ganda tidak membuat banyak dokumen dan baris registri.
4. Izin: ikuti pola yang ada; objek yang tak boleh diketahui dijawab 404, peran kurang 403 (konsisten antar jenis).
5. Judul, kop, nama sheet, label tombol: Bahasa Indonesia awam sesuai skill `vms-ux-design-system` (mis. "Berita Acara Serah Terima", "Laporan Survei", "Rincian Volume dan Biaya", bukan BAST/BoQ/Survey Report). Nama enum internal API boleh tetap.
6. Foto: dikecilkan, ada batas per laporan; bila ada yang tidak disertakan, tulis di dokumen "N foto lain tidak disertakan".
7. Label tombol web mengikuti hasil (PDF/Word/PPTX), tombol nonaktif saat proses, galat ramah (lima kondisi layar).

## Tes (wajib)
- Matriks peran x jenis x format x lintas divisi (200/403/404).
- Periksa ISI dokumen: judul, rentang tanggal, jumlah baris/slide, bukan hanya status 200.
- Idempotensi (klik ganda), builder tidak memblokir event loop (pola `test_build_offload_unit`).
- Tes harus gagal di kode lama dan lulus di kode baru.
