# Rencana terukur: akurasi wajah miring dan kurang terang

Status: RENCANA + alat ukur (belum mengubah perilaku produksi). Turunan `docs/rencana/absen-web-kantor.md` (A3).
Prinsip pemilik: ambang TIDAK sekadar diturunkan; setiap perubahan ambang harus lewat ukuran FAR/FRR pada data nyata.

## 1. Keadaan nyata (kode)
- `face-service/main.py`: InsightFace `buffalo_s` (det_500m + `w600k_mbf`, 512-d), `det_size=(640,640)`, CPU. `/embed` memakai `FaceAnalysis.get`, yang sudah meluruskan wajah (`norm_crop` 112x112 dari 5 titik landmark) sebelum embedding. Jadi "alignment dari landmark" sudah ada untuk pose ringan; yang belum ada: penanganan yaw/pitch besar dan cahaya.
- `_quality` = skor deteksi x ukuran (>=160 px) x ketajaman Laplacian (>=80). Tidak mengukur cahaya, pose, atau oklusi.
- API (`face_service.py`): `MATCH_THRESHOLD=0.80`, `DUPLICATE_THRESHOLD=0.80`, `POSE_PAIR_MIN=0.30`, `MIN_ENROLL_QUALITY=0.30`. Pendaftaran 3-5 foto DIRATA-RATAKAN menjadi satu templat; pencocokan = satu swafoto vs satu templat.
- Web: satu bingkai JPEG 0,85 tanpa pemeriksaan cahaya/posisi (`SelfieCaptureDialog.tsx`).

## 2. Dugaan penyebab (HARUS diukur, bukan diasumsikan)
1. Kamera laptop redup: kontras rendah, derau tinggi, detektor/pengenal kurang andal.
2. Yaw/pitch besar: landmark 5 titik kurang akurat, crop bergeser.
3. Templat rata-rata satu vektor meratakan variasi pose/cahaya (mengaburkan, bukan mewakili).
4. Satu bingkai acak: bisa jatuh pada kedipan/gerak/blur.

## 3. Rencana bertahap (urutan = urutan pengerjaan)
| # | Langkah | Lokasi | Syarat lulus (sebelum aktif) |
|---|---|---|---|
| 0 | Alat ukur FAR/FRR + dataset skor | `face-service/akurasi.py` (SELESAI) | tes lulus; format JSON dipakai pemilik |
| 1 | Normalisasi pencahayaan (regang kontras + gamma, hanya bila redup/kontras rendah) | `face-service/lighting.py` (fungsi SELESAI, belum dipasang) | FRR kondisi "redup" turun, FAR@ambang sama tidak naik |
| 2 | Gerbang kualitas cahaya/pose di web (petunjuk "kurang terang", "hadap lurus") sebelum jepret | web `SelfieCaptureDialog` + `/challenge-check` | tidak menaikkan jumlah gagal ambil foto |
| 3 | Pilih bingkai terbaik: ambil N (3-5) bingkai 0,5 dtk, kirim yang `quality`/pose terbaik | web + `/embed` mengembalikan pose | FRR turun pada kondisi "miring" |
| 4 | Templat ganda: simpan beberapa embedding per orang (frontal, kiri, kanan, redup), skor = maks kosinus atau rata-rata top-2 | API + skema (migrasi expand, kolom baru, enkripsi sesuai vms-db) | FAR tidak naik (maks atas k templat menaikkan FAR; wajib diukur) |
| 5 | Alignment lebih kuat untuk pose besar (tolak yaw > ambang dengan petunjuk, bukan memaksa cocok) | face-service | FAR/FRR per pose |
| 6 | Tetapkan ambang dari kurva | `MATCH_THRESHOLD` | lihat bagian 5 |

Urutan 1 -> 3 -> 2 -> 4 dipilih karena murah, tanpa migrasi, dan bisa diukur terpisah. Langkah 4 menyentuh skema dan privasi: butuh keputusan pemilik.

## 4. Alat ukur (`face-service/akurasi.py`)
- FAR = impostor lolos / semua impostor; FRR = genuine ditolak / semua genuine; lolos bila kosinus >= ambang. Keluaran: FAR/FRR di ambang saat ini, EER, dan ambang terendah yang FAR-nya <= target (default 0,1%).
- Sintetis (`python face-service/akurasi.py --sintetis`): hanya menguji harness. Contoh keluaran (derau naik per kondisi, BUKAN akurasi model nyata):

| kondisi | FAR@0.80 | FRR@0.80 | EER (ambang) | ambang untuk FAR<=0,1% (FRR) |
|---|---|---|---|---|
| frontal | 0,00% | 3,00% | 0,17% (0,60) | 0,62 (0,2%) |
| miring | 0,00% | 84,50% | 1,92% (0,41) | 0,52 (7,0%) |
| redup | 0,00% | 99,83% | 11,33% (0,27) | 0,57 (72,2%) |

  Pelajaran bentuk kurva: ambang optimal berbeda per kondisi; satu ambang 0,80 bisa terlalu ketat untuk kondisi sulit tanpa menaikkan keamanan. Angka sintetis tidak boleh dipakai menetapkan ambang.
- Data nyata (`--skor skor.json`): `{"frontal": {"genuine": [..], "impostor": [..]}, "miring": {...}, "redup": {...}}`. Skor dihitung pemilik dari swafoto bersetujuan (embedding saja, bukan foto, tidak masuk repo).

## 5. Protokol pengukuran data nyata (perlu pemilik)
- Minimal 30 orang x (3 kondisi) x 5 foto; impostor = pasangan lintas orang (kondisi sama). Genuine = swafoto vs templat pendaftaran frontal.
- Target keamanan awal (usulan): FAR <= 0,1% pada seluruh kondisi. Ambang baru = ambang terendah yang memenuhi target pada kondisi terburuk yang diterima; jika FRR kondisi sulit tetap tinggi, jawabannya gerbang kualitas (langkah 2/3), bukan menurunkan ambang.
- Cadangan operasional yang sudah ada: `MISMATCH` ditolak 422; layanan mati = `PENDING_OM`. Pertimbangkan jalur "ragu" (skor antara ambang bawah dan 0,80 -> PENDING_OM, bukan tolak) sebagai pengaman FRR tanpa menurunkan FAR otomatis.

## 6. Yang diimplementasikan di cabang ini
- `face-service/akurasi.py`, `face-service/lighting.py`, `face-service/tests/test_akurasi.py` (murni Python, jalan di CI job face-service). Tidak ada perubahan ambang, endpoint, skema, atau kontrak OpenAPI.
- `lighting.build_lut(hist)` menghasilkan tabel 256 entri; pemasangan di `/embed` nanti: `cv2.LUT` pada kanal luma (YCrCb) bila `lighting_report` menyatakan redup/kontras rendah, di balik flag lingkungan, setelah langkah 0 membuktikan manfaatnya.

## 7. Keputusan pemilik
1. Setuju mengumpulkan dataset skor nyata (siapa, berapa orang, persetujuan PDP)?
2. Target FAR (usulan 0,1%) dan FRR yang bisa diterima per kondisi?
3. Templat ganda (langkah 4) menyimpan lebih dari satu embedding per orang: izinkan (dampak PDP, retensi 30 hari/reset)?
4. Jalur "ragu" -> PENDING_OM untuk skor di rentang bawah ambang?
