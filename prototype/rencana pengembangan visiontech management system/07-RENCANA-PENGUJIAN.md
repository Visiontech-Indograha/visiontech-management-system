# 07 · Rencana Pengujian

Prinsip: **yang tidak diuji dianggap rusak.** Prototipe ini sudah membuktikannya — beberapa
kali sebuah bagian dinyatakan "sudah selesai" padahal uji membuktikan sebaliknya.

---

## 1. Lapisan pengujian

| Lapisan | Alat | Cakupan target | Kapan dijalankan |
|---|---|---|---|
| Unit aturan bisnis | pytest | **100% cabang** pada servis transisi | Setiap commit |
| Integrasi basis data | pytest + PostgreSQL nyata | Trigger, RLS, constraint | Setiap commit |
| Kontrak API | pytest + skema OpenAPI | Semua endpoint | Setiap commit |
| RBAC | pytest parametrik | endpoint × 7 peran | Setiap commit |
| Web komponen | Vitest | Komponen bersama + form | Setiap commit |
| Web ujung-ke-ujung | Playwright | Alur utama tiap peran | Setiap PR |
| Mobile unit/widget | flutter test | Logika luring, antrean | Setiap commit |
| Mobile perangkat nyata | manual, terskrip | Absensi, kamera, GPS | Setiap fase |
| Beban | k6 atau Locust | 60 pengguna bersamaan | Fase 9 |
| Keamanan | manual + ZAP | OWASP Top 10 | Fase 9 |
| Uji terima (UAT) | pengguna nyata | Satu siklus pekerjaan penuh | Fase 10 |

**Uji basis data memakai PostgreSQL sungguhan, bukan SQLite.** Setengah aturan sistem ini
hidup di trigger, RLS, dan exclusion constraint — SQLite tidak punya satu pun di antaranya,
jadi uji yang lulus di SQLite tidak membuktikan apa-apa.

---

## 2. Memindahkan uji prototipe

Prototipe punya tiga berkas uji yang **wajib** diterjemahkan, bukan ditinggalkan:

| Berkas prototipe | Menjadi |
|---|---|
| `tests/domain.test.cjs` (19 uji) | Uji pytest untuk servis transisi, nama uji dipertahankan |
| `tests/browser.mjs` (162 layar) | Playwright per peran; jumlah layar dipakai sebagai daftar periksa kelengkapan |
| `tests/offline_geo.mjs` | Uji Flutter untuk antrean luring + uji integrasi geofence di API |

Nama uji sengaja dipertahankan supaya perbandingan dengan prototipe bisa dilakukan sekilas.

---

## 3. Daftar regresi wajib

Setiap bug yang pernah ditemukan di prototipe menjadi satu uji. Bila salah satu dari ini
muncul lagi, fase yang bersangkutan **tidak boleh** dinyatakan selesai.

| # | Bug yang pernah terjadi | Uji yang menjaganya |
|---|---|---|
| R1 | Dialog native membekukan halaman dan otomasi | Tidak ada `alert/confirm/prompt` di seluruh kode web; Playwright gagal bila ada dialog |
| R2 | Kebocoran lintas unit pada insiden & lembur | PM unit A meminta data unit B → kosong/403 |
| R3 | Ketua diganti tetapi masih punya kewenangan ketua | Setelah adendum personel berlaku, ketua lama ditolak; hak anggota tetap ada |
| R4 | Dokumen versi lama masih bisa diubah | Semua kolom `plan_document` ditolak saat UPDATE |
| R5 | Teks laporan hilang saat berpindah layar | Uji Playwright: ketik → pindah → kembali → teks masih ada |
| R6 | Laporan bisa dibuat untuk tanggal yang belum tiba | Ditolak dengan pesan jelas |
| R7 | Penandaan bentrok personel tidak pernah jalan | Anggota yang bentrok benar-benar ditandai di dialog adendum |
| R8 | Tombol perpanjangan dokumen hilang dari profil | Ada di daftar dokumen, bukan hanya di halaman detail |
| R9 | Pengembalian aset buntu (deadlock persetujuan) | Siklus pesan → lepas → kembali → verifikasi selesai tanpa jalan buntu |
| R10 | Peringatan terlambat memakai jam perangkat | Ubah jam perangkat → waktu tercatat tidak berubah |
| R11 | Antrean luring hilang saat penyimpanan gagal | Simpan gagal → antrean tetap utuh, dicoba ulang |
| R12 | Service worker menyalahgunakan cache | Hanya cache `http(s)`; hanya `navigate` yang fallback ke index |

---

## 4. Uji khusus yang penting untuk sistem ini

### 4.1 Otorisasi
- **Matriks endpoint × peran** yang dibangkitkan otomatis. Endpoint baru tanpa baris di
  matriks → CI gagal.
- **Uji jaring pengaman RLS**: panggil servis dengan filter unit sengaja dihapus; RLS harus
  tetap menahan. Ini menguji pertahanan kedua, dan hanya berguna bila benar-benar dilakukan.
- **Uji lintas tenant**: pengguna organisasi A tidak pernah melihat satu baris pun milik B.

### 4.2 Tanda tangan dokumen
- PDF dibuat ulang dengan versi pustaka berbeda → QR tetap `VALID`.
- Satu karakter pada snapshot diubah → `DOCUMENT_CHANGED`.
- Tanda tangan dicabut → `REVOKED` beserta alasan.
- Kunci dirotasi → tanda tangan lama tetap terverifikasi oleh kunci lamanya.

### 4.3 Absensi
- Tepat di batas radius (100,0 m) → perilaku konsisten, tidak bergantung pembulatan.
- Akurasi GPS buruk (> 100 m) → ditolak dengan alasan, bukan diterima diam-diam.
- Jam perangkat dimajukan 3 jam → waktu tercatat tetap jam server.
- Absen dua kali di hari yang sama → ditolak; setelah absensi ditolak Finance → boleh ulang.

### 4.4 Luring
- Tulis 5 laporan dalam mode pesawat → nyalakan → semua terkirim sekali, tidak dobel.
- Kirim batch yang sama dua kali (`client_op_id` sama) → hasil sama, bukan duplikat.
- Server menolak satu item → item itu masuk "perlu perhatian", sisanya tetap terkirim.
- Aplikasi ditutup paksa saat antrean penuh → data tetap ada setelah dibuka lagi.

### 4.5 Wajah *(fase 8)*
- Karyawan belum terdaftar → absensi tetap berhasil (`NOT_ENROLLED`), tidak ditolak.
- face-service mati → absensi tetap berhasil (`SKIPPED`).
- Foto dari galeri (bukan kamera langsung) → ditolak oleh liveness.
- Persetujuan ditarik → embedding nonaktif, pencocokan berhenti pada saat itu juga.
- **Kalibrasi**: ≥ 30 orang, catat FAR dan FRR pada beberapa nilai ambang, pilih berdasarkan
  angka. Hasilnya ditulis di dokumen, bukan hanya di kepala developer.

---

## 5. Uji dengan perangkat nyata

Tidak bisa digantikan emulator. Yang wajib diuji di lapangan:

| Skenario | Kenapa |
|---|---|
| Absen di lokasi proyek sungguhan | Sinyal GPS di lapangan berbeda dari di kantor |
| Absen di bawah sinar matahari langsung | Layar terbaca? Swafoto terlalu terang? |
| Sinyal 2G/EDGE | Unggahan foto harus tetap selesai atau masuk antrean |
| Baterai rendah / mode hemat daya | Android membatasi GPS dan proses latar |
| Dua merek HP berbeda, minimal | Perilaku izin kamera/lokasi berbeda antar-produsen |

**Minta ke Anda:** dua perangkat Android untuk uji (satu kelas bawah, satu kelas menengah)
dan izin mengunjungi satu lokasi proyek.

---

## 6. Uji terima (UAT)

Bentuknya bukan daftar centang teknis, melainkan **satu siklus pekerjaan nyata** selama satu
minggu:

1. PM membuat dan menerbitkan SK untuk pekerjaan sungguhan.
2. Ketua tim menerima (atau mengajukan banding).
3. Tim absen setiap hari dari lokasi.
4. Ketua mengisi laporan harian, termasuk satu hari sengaja tanpa sinyal.
5. PM menilai, meminta perbaikan sekali.
6. Satu adendum personel dijalankan (ganti anggota).
7. Aset dipinjam dan dikembalikan.
8. Satu insiden dicatat dan diselesaikan.
9. Lembur diajukan dan diperiksa Finance.
10. Pekerjaan diselesaikan; PDF laporan akhir dicetak; QR-nya dipindai orang lain.

**Kriteria lulus:** seluruh langkah selesai **tanpa bantuan developer**, dan setiap peserta
bisa menjelaskan apa yang harus dia lakukan berikutnya tanpa bertanya. Kalau pengguna
bingung, itu bug antarmuka — bukan kesalahan pengguna.

---

## 7. Definisi "selesai" untuk satu task

1. Uji aturan bisnis ditulis dan hijau.
2. Lint dan pemeriksaan tipe bersih.
3. Uji regresi yang relevan dari daftar §3 masih hijau.
4. Pesan galat sudah berbahasa Indonesia dan bisa dipahami orang lapangan.
5. Bila menyentuh API: `openapi.json` diperbarui dan tipe frontend dibangkitkan ulang.
6. Bila ada ambiguitas yang diputuskan sendiri: dicatat di dokumen 10.
