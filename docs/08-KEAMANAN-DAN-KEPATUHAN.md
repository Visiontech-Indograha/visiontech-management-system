# 08 · Keamanan dan Kepatuhan

Sistem ini menyimpan tiga jenis data yang salah satunya tidak bisa diganti bila bocor:

1. **Data kepegawaian** — nomor KTP, SIM, sertifikat, kontrak.
2. **Data lokasi** — di mana seorang karyawan berada, setiap hari kerja.
3. **Data biometrik** — wajah. Kata sandi bisa diganti; wajah tidak.

Bagian ini menjelaskan cara ketiganya dijaga, dan apa yang menjadi tanggung jawab Anda
sebagai pemilik sistem.

---

## 1. Model ancaman — siapa yang mungkin menyerang dan bagaimana

| Penyerang | Yang diincar | Pertahanan |
|---|---|---|
| **Karyawan yang ingin absen palsu** | Absen dari rumah, titip absen | Geofence dihitung server, swafoto, waktu server, wajah (fase 8), semuanya tercatat |
| **Karyawan yang mengintip data rekan** | Gaji, dokumen pribadi, lokasi | RLS + otorisasi servis; dokumen pribadi hanya pemilik & HR |
| **Akun yang dibajak** | Apa saja sesuai peran korban | Token pendek, refresh berotasi, deteksi pemakaian ulang, pencabutan sesi |
| **Orang luar dengan dokumen palsu** | Memalsukan SK Visiontech | Tanda tangan QR; hash dokumen; dokumen palsu tidak punya nomor seri sah |
| **Penyerang internet umum** | Basis data, berkas | Hanya 443 terbuka; SSH, basis data, MinIO, dan staging hanya lewat **Tailscale** — tidak terlihat dari internet |
| **Mantan karyawan** | Akses setelah keluar | Offboarding mencabut seluruh sesi; akun nonaktif ditolak pada permintaan berikutnya |
| **Administrator sistem itu sendiri** | Semua | Audit yang tidak bisa di-UPDATE; kunci privat di KMS, bukan di server |

Baris terakhir sengaja ada. Sistem yang hanya aman dari orang luar bukan sistem yang aman.

---

## 2. Lapisan pertahanan

```
0. Tailscale     → SSH, psql, MinIO, staging hanya di tailnet; port 22 tertutup
1. Jaringan      → hanya Caddy terbuka; TLS wajib; HSTS
2. Sesi          → JWT pendek + refresh berotasi + deteksi pencurian + lockout
3. Otorisasi     → peran global + kewenangan per SK, diperiksa di servis
4. RLS           → jaring pengaman bila servis lupa memfilter
5. Batasan DB    → CHECK, exclusion, trigger immutability
6. Audit         → setiap perubahan penting tercatat, tidak bisa diubah
7. Berkas        → tidak di basis data; URL bertanda tangan ≤ 5 menit
8. Kunci         → di KMS, tidak pernah menyentuh disk server
```

Tidak ada satu pun lapisan yang dianggap cukup sendirian.

---

## 3. Autentikasi dan sesi

- Kata sandi: **argon2id** (parameter mengikuti rekomendasi OWASP saat implementasi).
- Access token EdDSA, 5–15 menit. **Tidak** memuat daftar izin — peran bisa dicabut kapan
  saja, dan izin diperiksa dari basis data pada setiap permintaan.
- Refresh token acak 32 byte, hanya disimpan sebagai SHA-256, dirotasi setiap dipakai.
  Pemakaian ulang token lama → seluruh rantai perangkat dicabut dan pengguna diberi tahu.
- Web menyimpan refresh di cookie `HttpOnly; Secure; SameSite=Strict`; Android di
  `flutter_secure_storage`.
- Lockout: 5 kegagalan dalam 15 menit per (login + IP), dihitung dari tabel `login_attempt`.
- **MFA**: kolomnya sudah ada (`mfa_secret_enc`). **Dikunci:** diaktifkan untuk peran PM, HR,
  dan Finance pada fase lanjutan (K-21) — merekalah yang bisa menerbitkan dokumen dan
  menyetujui pengeluaran.

---

## 4. Otorisasi

Dua sumber kewenangan, keduanya diperiksa:

1. **Peran global per unit** (`user_role`) — menentukan menu dan akses modul.
2. **Penugasan pada SK yang berlaku** (`is_plan_leader`, `is_plan_member`) — menentukan apa
   yang boleh dilakukan pada satu pekerjaan tertentu.

**Yang harus dijaga:** frontend hanya menyembunyikan tombol. Server tetap wajib menolak.
Setiap endpoint punya baris di matriks RBAC, dan endpoint tanpa baris membuat CI gagal.

---

## 5. Data pribadi (UU PDP No. 27/2022)

VMS memproses data pribadi karyawan, jadi UU PDP berlaku. Yang sudah dirancang:

| Kewajiban | Cara memenuhinya |
|---|---|
| **Dasar pemrosesan** | Hubungan kerja + persetujuan terpisah untuk biometrik |
| **Minimalisasi** | Nomor dokumen tidak disimpan utuh — hanya tersamar + hash; EXIF dibuang saat re-encode |
| **Pembatasan tujuan** | Wajah hanya untuk absensi; lokasi hanya untuk verifikasi kehadiran |
| **Hak akses** | Karyawan bisa melihat data dirinya sendiri di profil |
| **Hak menarik persetujuan** | Persetujuan biometrik bisa ditarik kapan saja, langsung berlaku |
| **Retensi** | Sudah dikunci di K-07 dan dokumen 13 §9 |
| **Keamanan** | Bagian §2 di atas |
| **Pencatatan** | `audit_event` yang tidak bisa diubah |

**Yang belum ada dan menjadi tanggung jawab Anda sebagai perusahaan:**

1. **Kebijakan privasi tertulis** yang diberikan ke karyawan.
2. **Formulir persetujuan biometrik** yang jelas: untuk apa, disimpan berapa lama, bagaimana
   menariknya, dan **apa akibatnya bila menolak** — jawabannya harus "tidak ada akibat
   merugikan; absensi tetap bisa dilakukan tanpa wajah". Bila menolak berarti tidak bisa
   absen, persetujuan itu bukan persetujuan yang sah.
3. **Penanggung jawab perlindungan data** — satu orang yang ditunjuk.
4. **Prosedur bila terjadi kebocoran** — UU PDP mewajibkan pemberitahuan dalam 3×24 jam.

---

## 6. Data biometrik — aturan yang lebih ketat

| Aturan | Penerapan |
|---|---|
| Yang disimpan embedding, bukan foto | `face_enrollment.embedding`; foto acuan hanya bila disetujui terpisah |
| Persetujuan wajib | Trigger menolak pendaftaran tanpa `biometric_consent = GRANTED` |
| Menarik persetujuan = menonaktifkan | Trigger `tg_consent_withdrawn()` |
| Akses paling sempit | Hanya HR dan pemilik data; `vms_readonly` dicabut haknya |
| Tidak bisa diubah | Perubahan = pendaftaran ulang; riwayat utuh |
| Retensi percobaan | `purge_face_probes()`, bawaan 30 hari |
| Bukan penentu tunggal | Tidak cocok → `NEEDS_REVIEW`, bukan penolakan |
| Tidak untuk pencarian 1:N bebas | Tidak ada endpoint "wajah siapa ini?" |

**Model kepercayaan liveness (2026-10-06):** absen/pendaftaran **online** hanya menerima bukti tantangan bertanda tangan
server (`/face/challenge-check` → JWT EdDSA, audience `vms-face-challenge`, terikat pengguna, 5 menit, sekali pakai,
2 tantangan berbeda); klaim `passed` dari HP hanya dipercaya untuk absen **luring** yang kemudian dihitung ulang server.
Langkah "depan" (meluruskan wajah) hanya panduan dan tidak menerbitkan bukti. Lisensi: model pralatih InsightFace
**non-komersial** — pemilik wajib memutuskan lisensi komersial sebelum produksi penuh.

**Dua hal yang paling sering salah pada sistem seperti ini, dan cara kita menghindarinya:**

- **Ambang batas ditebak.** Nilai 0,65 di skema hanyalah titik awal. Sebelum dipakai, ukur
  FAR (orang lain lolos) dan FRR (orang benar ditolak) pada karyawan nyata. Ambang yang
  keliru berarti orang tidak bisa bekerja, atau siapa pun bisa menitip absen.
- **Tidak ada deteksi keaslian (liveness).** Tanpa itu, foto layar bisa menembus pencocokan
  dan seluruh fitur menjadi teater keamanan. Liveness wajib ada sebelum fitur diaktifkan.

---

## 7. Kunci dan tanda tangan

- **Kunci privat tidak pernah ada di basis data atau di disk server.** `signing_key` hanya
  menyimpan kunci publik dan rujukan ke KMS/HSM.
- Dua jenis kunci: penandatangan dokumen (`DOCUMENT_SIGNATURE`) dan penandatangan JWT
  (`JWT_ACCESS`). Jangan dipakai bergantian.
- **Rotasi**: kunci baru diterbitkan berkala; tanda tangan lama tetap sah karena diverifikasi
  dengan `kid`-nya sendiri. Kunci lama tidak dihapus, hanya dihentikan pemakaiannya.
- **Bila kunci bocor**: tandai kunci `compromised`, terbitkan kunci baru, dan putuskan
  bersama apakah tanda tangan yang dibuat dengan kunci itu perlu dicabut massal. Prosedurnya
  ditulis di runbook (dokumen 09).

**Catatan kejujuran tentang kekuatan hukum.** Tanda tangan ini secara teknis kuat dan sangat
cukup untuk keperluan internal serta pembuktian keaslian. Tetapi untuk kekuatan hukum penuh
sebagai tanda tangan elektronik **tersertifikasi** menurut PP 71/2019, penerbitnya harus
Penyelenggara Sertifikasi Elektronik (PSrE) yang diakui Kominfo. Rancangan ini sudah siap
disambungkan ke PSrE bila nanti diperlukan — yang berubah hanya sumber kuncinya. Saya tidak
ingin Anda menganggap ini setara dengan PSrE padahal bukan.

---

## 8. Berkas dan unggahan

- Validasi *magic bytes*, bukan ekstensi nama berkas.
- Batas ukuran sesuai dokumen 13 §6.
- **Gambar di-re-encode dengan Pillow** — membuang EXIF (termasuk koordinat GPS yang tidak
  diminta) dan menetralkan berkas gambar yang disusupi muatan. Dokumen tidak di-re-encode,
  jadi validasi magic bytes dan batas ukurannya yang menjadi penjaga.
- Disimpan dengan nama acak, bukan nama asli dari perangkat.
- Diakses lewat URL bertanda tangan ≤ 5 menit, dibuat hanya setelah otorisasi diperiksa.
- Berkas yang tidak boleh dilihat → **404**, bukan 403, agar keberadaannya tidak terungkap.

---

## 9. Pencatatan dan pemantauan

**Yang dicatat:** login berhasil & gagal, perubahan peran, penerbitan & pencabutan dokumen,
penandatanganan, akses ke dokumen pribadi orang lain, pemeriksaan absensi, seluruh perubahan
pada tabel penting (`audit_event`).

**Yang tidak boleh masuk log:** kata sandi, token, isi embedding wajah, nomor dokumen utuh.

**Yang dipantau dan memicu peringatan:**
- Lonjakan kegagalan login.
- Pemakaian ulang refresh token (indikasi pencurian).
- Absensi `NEEDS_REVIEW` yang melonjak (bisa berarti ambang wajah salah atau lokasi salah).
- Verifikasi QR yang gagal berulang dari satu IP.

---

## 10. Tanggung jawab yang perlu Anda tetapkan

| Hal | Siapa | Kapan |
|---|---|---|
| Penanggung jawab perlindungan data | — | Sebelum fase 8 |
| Pemegang akses KMS | — | Sebelum fase 6 |
| Yang berhak mencabut tanda tangan | — | Sebelum fase 6 |
| Yang berhak melihat data biometrik | **HR** (dikunci, K-08) | Sebelum fase 8 |
| Kebijakan retensi data mantan karyawan | — | Sebelum rilis |
| Prosedur bila terjadi kebocoran | — | Sebelum rilis |

Kolom "siapa" sengaja saya kosongkan. Ini keputusan organisasi, bukan keputusan teknis, dan
sistem tidak bisa aman bila tidak ada orang yang bertanggung jawab atasnya.
