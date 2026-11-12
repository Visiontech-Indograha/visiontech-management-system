# Lint mobile (Fase 0)

`mobile/analysis_options.yaml` memakai `very_good_analysis` dan plugin `riverpod_lint`.
Perilaku aplikasi tidak berubah; aturan yang belum dibereskan dimatikan di bagian `BASELINE Fase 0`.

## Menyusutkan baseline
1. Pilih satu aturan di bagian BASELINE, hapus barisnya (aturan jadi aktif).
2. Jalankan `cd mobile && ~/flutter/bin/flutter.bat analyze`.
3. Perbaiki pelanggaran (`dart fix --apply` bila ada), atau kembalikan baris bila terlalu banyak.
4. Satu aturan per PR kecil. Baseline hanya boleh menyusut.
5. Mode ketat (`strict-casts`, `strict-inference`, `strict-raw-types`) dinyalakan terakhir.

Pengecualian satu berkas: `// ignore_for_file: nama_aturan` di atas berkas, disertai alasan.
