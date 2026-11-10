# Golden layar utama

PNG di folder ini dibuat di **Linux** (runner CI `ubuntu-24.04`). Piksel teks dan anti-alias berbeda
antar OS, jadi tes bertag `golden` hanya dibandingkan di Linux dan dilewati (skip) di Windows/macOS.

Ukuran tetap 360x800, rasio piksel 1, skala teks 1,3; jam, data, dan provider ditiru.

## Memperbarui golden
1. Jalankan workflow GitHub Actions "Golden mobile" (workflow_dispatch, atau push ke cabang `golden-update/*`)
   (`.github/workflows/golden.yml`): menjalankan `flutter test --tags golden --update-goldens`
   di Linux dan mengunggah artefak `goldens`.
2. Unduh artefak, salin PNG ke `mobile/test/goldens/`, lalu commit.
3. Tinjau perubahan gambar di PR sebelum merge.

Di lokal (Windows/Mac) tes golden tampil "skipped". `VMS_GOLDEN=1` memaksa jalan hanya untuk melihat hasil;
jangan commit PNG hasil lokal.
