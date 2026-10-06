# 30 · Laporan spike wajah dan daftar kerja operasional

Tanggal: 2026-10-06 · Perangkat uji: Realme (Android) · Model: InsightFace `buffalo_s` (`det_500m` + `w600k_mbf`, 512-d).

## Hasil spike (Tahap 0 = GO)
| Ukuran | Hasil |
|---|---|
| Kemiripan embedding HP vs server (orang sama) | rata-rata **0,967** |
| Inferensi ONNX di HP | ±**71 ms**; ukuran model **13,6 MB** |
| Catatan build | plugin `onnxruntime` butuh override `compileSdk=36` di `android/build.gradle.kts` |

## Hasil uji nyata (2026-10-06)
- Arah yaw/pitch InsightFace pada bingkai kamera depan yang **tidak dicerminkan** terbalik dari dugaan awal → tanda
  dibalik di `face-service/main.py`; ambang kini dapat diatur lewat env (`FACE_YAW_MIN` 12, `FACE_PITCH_UP` 8,
  `FACE_MOUTH_MIN` 0,35, `FACE_FRONT_MAX` 12, `FACE_MIN_WIDTH` 0,25, `FACE_MAX_WIDTH` 0,80).
- Kedip tidak andal → dihapus. Ditambah tantangan **bawah**, panduan jarak/arah, dan langkah "Luruskan wajah".
- **Kalibrasi P8-5 (FAR/FRR dengan ≥ 30 karyawan) belum dilakukan.**

## Daftar kerja operasional (oleh pemilik/server)
1. Bangun citra `vms-face` dan tambah service `face` ke compose server (jaringan internal, `mem_limit`); isi `FACE_SERVICE_TOKEN`.
2. Isi `FACE_SERVICE_URL` dan `FACE_SERVICE_TOKEN` di `api.env`; cek `/health`, pendaftaran, probe, reverify.
3. Setelah face-service hidup: `FACE_ENROLLMENT_REQUIRED=true` untuk mewajibkan pendaftaran setelah login.
4. Periksa aturan Cloudflare untuk `/api/v1/auth/login`; bangun APK rilis dengan kunci rilis pemilik.
5. Putuskan lisensi komersial model InsightFace; lakukan kalibrasi P8-5.
6. Hapus data uji sintetis `UJI-003` di DB produksi (hanya dengan persetujuan pemilik).

## Belum dibangun
Pencocokan wajah **di HP** saat luring (embedder ONNX, penyelarasan 5 titik, penyimpanan template aman TTL 7 hari,
blok `face` bertanda tangan). Absen luring ber-wajah saat ini ditandai Perlu review di server.
