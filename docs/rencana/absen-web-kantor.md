# Rencana: absen web untuk pekerja kantor (lokasi dan wajah)

Status: RANCANGAN (belum disetujui pemilik). Pembuat: arsitek. Dasar: `origin/development` @ aac400c4.
Putusan pemilik: web = jalur absen UTAMA pekerja kantor (laptop tanpa GPS, kamera redup); HP = pekerja lapangan.
Permintaan pemilik: akurasi wajah tetap tinggi walau wajah miring atau cahaya kurang.

## A. Keadaan nyata kode

### A1. Alur absen web
- `web/src/components/organisms/attendance/OfficeCheckInCard.tsx`: lokasi lewat `navigator.geolocation.getCurrentPosition` (`enableHighAccuracy: true, timeout 20000, maximumAge 0`, baris ~63-78), mengirim `lat, lng, accuracy_m`. Bila di luar radius: penjelasan wajib, lalu swafoto.
- `SelfieCaptureDialog.tsx`: `getUserMedia({video:{facingMode:"user"}})`, satu bingkai ke canvas, `toBlob(..., "image/jpeg", 0.85)`, unggah ke `POST /files/upload`. Tidak ada pengukuran cahaya, tidak ada pilihan bingkai, tidak ada petunjuk posisi wajah.
- API: `api/app/modules/attendance/services/attendance_session_service.py` (check-in sekitar baris 438, check-out sekitar 561). Swafoto selalu wajib (`ValidationError` bila kosong).

### A2. Validasi lokasi (di API)
- `MAX_WEB_ACCURACY_M = 300` (baris 90) dan `MAX_GPS_ACCURACY_M = 100` untuk HP. Web dengan akurasi > 300 m ditolak `GPS_INACCURATE` (422). Akurasi <= 300 m diterima tetapi jarak dihitung dari titik mentah, tanpa memperhitungkan akurasi.
- Zona: `attendance_session_repository.py` (Haversine, `distance_to_target <= radius_m`, baris ~457). Target = kantor sendiri, lokasi tugas harian, atau kantor terdekat dari tepi radius (keputusan pemilik 2026-10-09). Di luar radius: `om_approval_status = PENDING_OM`, foto bukti dan penjelasan disimpan (`out_of_radius_photo_path`, `out_of_radius_note`).
- Masalah nyata: laptop tanpa GPS memakai posisi dari WiFi/IP. Akurasi sering 50-3000 m dan titiknya bisa meleset jauh, sehingga hasilnya "di luar zona" padahal ada di kantor. Persetujuan bergantung pada OM (bukan HR kantor tugas).

### A3. Face-service dan pencocokan
- `face-service/main.py`: InsightFace `FaceAnalysis` paket `buffalo_s` (detektor det_500m, pengenal `w600k_mbf`, 512-d), `det_size=(640,640)`, CPU, `FACE_MAX_CONCURRENCY=2`. `/embed` mengembalikan `normed_embedding`, `quality` (skor deteksi x ukuran >=160 px x ketajaman Laplacian >=80), `detection_score`. Tepat 1 wajah, selain itu tanpa embedding. Modul landmark 2D/3D ada (dipakai tantangan liveness di `rules.py`: yaw/pitch/mulut).
- Cahaya: TIDAK ada normalisasi (tanpa CLAHE/gamma) dan tidak ada ukuran kecerahan. Kualitas hanya mengukur skor, ukuran, ketajaman.
- Ambang diterapkan di API, bukan face-service: `api/app/modules/face/services/face_service.py` `MATCH_THRESHOLD = 0.80` (kosinus), `verify_selfie` (baris ~232). `DUPLICATE_THRESHOLD=0.80`, `POSE_PAIR_MIN=0.30`, `MIN_ENROLL_QUALITY=0.30`, pendaftaran 3-5 foto lalu DIRATA-RATAKAN jadi SATU templat (`_normalised_mean`). Pencocokan: swafoto vs templat tunggal. MISMATCH online = ditolak 422 `FACE_MISMATCH`; layanan mati = ditandai PENDING_OM; skor disimpan `attendance.face_match_score` (x100).
- Catatan ilmiah (perlu diverifikasi dengan pengukuran, bagian C): 0,80 sangat ketat untuk model berukuran kecil seperti `w600k_mbf`; kosinus orang yang sama pada kondisi nyata sering lebih rendah dari itu. Ini kemungkinan penyebab utama "tidak cocok" saat miring atau redup. Jangan mengubah angka tanpa data FAR/FRR.
- `FACE_FAKE_MODE` (`api/app/core/config.py:149`, `face_service.py:50`): hanya sah bila `APP_ENV=development` (penjaga di config menolak start selain itu). Mode ini melewati face-service: embedding sintetis, similarity tetap 0,95. Tes ambang tidak boleh memakainya.
- TEMUAN PENTING: `FaceService.enroll` menolak peran selain `FIELD_ROLES = (TEAM_LEADER, EMPLOYEE)` ("hanya untuk pekerja lapangan"). Pekerja kantor tidak bisa mendaftar wajah, dan `_require_enrolled` hanya berlaku untuk `channel == "MOBILE"`. Hasil: absen web kantor kini dicocokkan hanya bila karyawan kebetulan terdaftar; yang belum terdaftar ditandai "belum mendaftar wajah". Perlu dipastikan dengan pemilik (pertanyaan P3).
- Pendaftaran web: `web/src/components/organisms/account/FaceBiometricSection.tsx` (menu Profil).

### A4. Kolom DB terkait
- `employee.face_embedding JSONB` (vektor + meta `model`, `enrolled_at`; `db/06_master_schema_v2.sql:109`). Satu templat per karyawan.
- `attendance`: `face_match_score NUMERIC(5,2) NOT NULL` (627), `face_photo_path`, `face_status` (hasil eksplisit), `is_within_attendance_radius`, `out_of_radius_photo_path`, `out_of_radius_note`, `om_approval_status VARCHAR(25)` dengan CHECK di migrasi `v2_0004` (nilai: AUTO_VALID, PENDING_OM, APPROVED_BY_OM, REJECTED_BY_OM), `distance_from_main_office_m`, `city_zone_status`. Tidak ada kolom untuk akurasi lokasi, sumber lokasi, atau kualitas wajah.
- `office.attendance_radius_m`, `latitude`, `longitude`. Belum ada daftar IP/CIDR kantor.
- Kepala Alembic terbaru di `origin/development`: `v2_0039_indeks_organisasi_tenant`. Migrasi berikut mulai `v2_0040`. Tiap migrasi baru wajib menambah baris `down_revision` di `api/tests/architecture/test_alembic_v2.py`.

## B. Rancangan

### B1. Lokasi untuk web
1. Toleransi berbasis akurasi: dalam zona bila `jarak - min(akurasi, K) <= radius` (K = batas toleransi, mis. 150 m; saran awal, dikalibrasi dari data). Simpan `location_accuracy_m` dan `location_source` (`GPS` | `WEB_ESTIMATE` | `IP_OFFICE`).
2. Opsi IP kantor: tabel `office_network` (office_id, cidr, aktif). Bila IP publik permintaan cocok CIDR kantor karyawan dan akurasi tidak memadai, anggap "di kantor" (`IP_OFFICE`). Dasar IP dibaca dari header proxy tepercaya saja (ada pola serupa di `test_hse_ack_ip`). IP saja tidak cukup membuktikan lokasi bila VPN; karena itu dicatat sebagai sumber dan tetap bisa ditinjau.
3. Status "menunggu verifikasi HR kantor tugas": nilai baru `PENDING_HR` untuk `om_approval_status` (CHECK diperluas, expand-only). Dipakai bila web, akurasi buruk/di luar zona, tetapi IP tidak cocok. Peninjau: HR kantor tugas karyawan (satu kantor). Notifikasi lewat `NotificationService.attendance_flagged` yang sudah ada (jalur `_flag_for_review`), ditambah tujuan HR kantor. Aksi: setuju/tolak lewat endpoint tinjau yang ada, dengan kondisi status pada UPDATE (cegah dua peninjau sekaligus) dan catatan alasan.
4. Teks galat awam: "Lokasi laptop kurang tepat. Absen tetap tercatat dan menunggu pemeriksaan HR kantor Anda."

### B2. Wajah (urutan dampak)
1. Gerbang kualitas di sisi klien (web): ukur kecerahan rata-rata (luma kanvas kecil, mis. 64x64) sebelum memotret. Di bawah ambang: petunjuk "Terlalu gelap. Menghadap ke sumber cahaya atau nyalakan lampu." Juga: wajah terlalu kecil/besar, buram. Bukan pengganti server.
2. Multi-bingkai: ambil 5-7 bingkai dalam sekitar 1,5 detik, skor kualitas ringan di klien, kirim 1-3 terbaik (batas ukuran sama dengan batas API). Server memilih bingkai dengan `quality` tertinggi lalu menghitung kecocokan; ambil skor tertinggi dari bingkai yang lolos gerbang (bukan rata-rata).
3. Alignment landmark: face-service memakai `norm_crop` InsightFace (sudah dikerjakan di dalam `app.get`) dan menambah pengecekan sudut: tolak bila |yaw| atau |pitch| terlalu besar untuk absen, dengan petunjuk awam ("Hadapkan wajah lurus ke layar"). Wajah miring ringan ditangani alignment; miring berat diminta ulang, bukan ditolak sebagai "tidak cocok".
4. Normalisasi cahaya di face-service: CLAHE pada kanal luma atau koreksi gamma ringan hanya bila kecerahan rendah; embedding dihitung dari gambar yang dinormalisasi DAN yang asli, ambil kemiripan tertinggi. Wajib diukur (bagian C) sebelum aktif.
5. Templat pendaftaran ganda: simpan beberapa templat per karyawan (mis. depan, sedikit miring, redup) bukan satu rata-rata; skor = maksimum kosinus terhadap semua templat. Kolom baru `employee_face_template` (employee_id, vektor, model, label, kualitas), migrasi data dari `face_embedding` secara expand (kolom lama tetap dibaca sampai tahap lanjutan). Pendaftaran web untuk pekerja kantor ikut P3.
6. Retry 2-3 kali dengan alasan awam: setiap gagal tampil alasan konkret (gelap, miring, wajah tidak terlihat, tidak cocok) dan tombol "Coba lagi". Setelah 3 gagal: kirim sebagai PENDING_HR dengan foto terlampir (bukan ditolak buntu), sehingga pekerja tidak terhalang absen. Batas percobaan dihitung di server (per hari per karyawan) agar tidak bisa dipakai menebak wajah orang lain.
7. Ambang: tentukan dari data (bagian C), kemungkinan dua tingkat: >= T_tinggi = otomatis sah; antara T_rendah dan T_tinggi = sah dengan tanda "perlu cek" untuk HR; < T_rendah = ulang. Angka belum diputuskan.

### B3. UX (sesuai `vms-ux-design-system`)
Lima kondisi layar (memuat kamera, kamera ditolak/tidak ada, kurang cahaya, berhasil, galat); target sentuh 44 px; status tidak hanya warna; teks Bahasa Indonesia sederhana (hindari "embedding", "akurasi GPS", "CIDR"). Layar kamera menampilkan bingkai oval dan indikator cahaya berikon+teks.

### B4. API/sistem (sesuai `vms-api`, `vms-system-design`)
- Tidak ada rute baru tanpa `require_permission`; peninjau PENDING_HR dibatasi satu kantor (404 lintas kantor).
- Perluasan endpoint check-in/out hanya menambah field opsional (APK lama tetap jalan).
- Panggilan ke face-service tetap lewat `FaceEmbedClient` dengan timeout; multi-bingkai dibatasi (maks 3 embed per permintaan, `FACE_MAX_CONCURRENCY=2` dan RAM 4 GB tetap). Hitung kosinus banyak templat O(jumlah templat), kecil (<=5).
- Tanpa `LIKE '%'`, tanpa OFFSET baru. Embedding tidak pernah masuk respons atau log.

## C. Mengukur FAR/FRR
- Tanpa foto karyawan asli kecuali izin tertulis pemilik dan persetujuan tiap orang.
- Dataset: (1) relawan internal bersuka rela dengan persetujuan, kondisi variatif (terang/redup, miring 0/15/30 derajat, kacamata); (2) dataset publik berlisensi cocok untuk riset (mis. LFW untuk pasangan dasar; cek lisensi sebelum dipakai) untuk FAR pada impostor; (3) variasi sintetis (turunkan kecerahan, rotasi) dari foto relawan.
- Skrip di `face-service/eval/` (baru): membaca folder per-orang, memanggil `/embed` lokal (bukan produksi), menghasilkan pasangan genuine/impostor, menghitung FRR dan FAR pada rentang ambang 0,3-0,9, tabel per kondisi, dan titik EER. Keluaran hanya angka agregat (tanpa gambar atau vektor) ke CSV. Dataset tidak masuk repo (`.gitignore`) dan tidak di server produksi.
- Target awal usulan: FAR <= 0,1% (1 per 1000) dan FRR <= 5% pada cahaya redup + miring ringan. Dikonfirmasi pemilik (P2).
- Jangan mengukur dengan `FACE_FAKE_MODE`. Jangan menjalankan pytest DB; skrip ini mandiri.

## D. Urutan PR kecil
1. docs: rencana ini (PR ini).
2. db `v2_0040`: kolom `attendance.location_accuracy_m`, `location_source`, `face_quality`, `face_attempts`; CHECK `om_approval_status` + `PENDING_HR`; tabel `office_network`. Expand-only, `downgrade()` ada, baris di `test_alembic_v2.py`.
3. db `v2_0041`: tabel `employee_face_template` + salinan data dari `face_embedding`.
4. api: toleransi akurasi + IP kantor + status PENDING_HR + tinjau HR + notifikasi (OpenAPI snapshot, `gen:api`).
5. face-service: skrip `eval/` + (setelah ada data) normalisasi cahaya, penilaian pose, endpoint multi-bingkai.
6. api: verifikasi multi-templat + gerbang kualitas + batas percobaan; ambang dari konfigurasi (bukan konstanta).
7. web: indikator cahaya, multi-bingkai, retry beralasan, teks lokasi baru, tampilan status menunggu HR; tes Vitest.
8. web+api: pendaftaran wajah untuk pekerja kantor (bila P3 disetujui) dengan persetujuan biometrik.
Rilis MINOR (fitur, kompatibel mundur).

## E. Risiko PDP (data pribadi/biometrik)
- Wajah adalah data biometrik. Perlu persetujuan eksplisit, tertulis, terpisah (dicatat: siapa, kapan, versi teks) sebelum pendaftaran wajah, dan jalur menarik persetujuan (hapus templat). Selaras keputusan pemilik: data pribadi 30 hari, retensi arsip (lihat memori keputusan PDP).
- Foto bukti dan hasil multi-bingkai: simpan hanya bingkai terpilih; bingkai lain dibuang di memori. Templat jamak = lebih banyak data biometrik per orang; batasi 5 dan hapus saat reset.
- IP dan akurasi lokasi juga data pribadi; simpan seperlunya, tampilkan hanya ke peninjau berwenang.
- Lisensi InsightFace: paket model `buffalo_*` non-komersial (butir keputusan klien yang masih terbuka). Perlu kepastian sebelum perluasan ke seluruh kantor.
- Bias: akurasi bisa berbeda antar kelompok dan kondisi cahaya; ukuran FRR dilaporkan per kondisi.

## F. Pertanyaan untuk pemilik (dengan saran)
- P1. Boleh absen web yang lokasinya meragukan tetap tercatat dan menunggu HR kantor tugas (bukan ditolak)? Saran: ya.
- P2. Target ketelitian wajah: 1 salah terima per 1000 dan 5 dari 100 salah tolak? Saran: ya, lalu ditinjau setelah ada data.
- P3. Pekerja kantor wajib mendaftar wajah di web (saat ini hanya pekerja lapangan boleh mendaftar)? Saran: ya, bertahap per kantor, dengan persetujuan tertulis.
- P4. Boleh mencatat alamat IP jaringan kantor sebagai bukti lokasi? Saran: ya, IP kantor saja.
- P5. Siapa peninjau: HR kantor tugas saja, atau HR + OM? Saran: HR kantor tugas; OM tetap untuk absen lapangan.
- P6. Siapa relawan dan apakah boleh mengambil foto uji dari mereka (dengan persetujuan)? Saran: 10-20 orang, foto dihapus setelah pengukuran.
- P7. Kepastian lisensi model wajah untuk pemakaian komersial/internal sebelum meluas. Saran: tanya pembuat model atau siapkan model alternatif berlisensi jelas.
