# 17 · CI/CD dan Notifikasi

**Status: dikunci.**

- **CI/CD:** GitHub Actions
- **Penampil hasil build dan peringatan:** **Discord** (webhook)
- **Jalur deploy ke server:** SSH **lewat Tailscale**, port 22 tertutup dari internet

Tujuannya dua: setiap perubahan diperiksa otomatis sebelum masuk, dan **setiap hal janggal
di server muncul di Discord tanpa ada yang perlu membuka terminal**.

---

## 1. Kanal Discord

Empat kanal, dipisah supaya yang penting tidak tenggelam:

| Kanal | Isi | Siapa yang harus membaca |
|---|---|---|
| `#vms-ci` | Hasil lint, tipe, uji, build | Developer |
| `#vms-deploy` | Deploy staging & produksi, migrasi, versi | Developer + IT |
| `#vms-alerts` | **Galat dan keanehan di server yang berjalan** | Developer + IT, **notifikasi menyala** |
| `#vms-digest` | Ringkasan harian pukul 08.00 WIB | Siapa saja |

**Aturan yang menentukan apakah ini berguna atau jadi kebisingan:**

- `#vms-alerts` hanya untuk hal yang **butuh tindakan manusia**. Kalau isinya hal yang tidak
  pernah ditindaklanjuti, kanalnya akan diabaikan — dan saat ada masalah sungguhan, tidak
  ada yang melihat.
- **Build sukses di cabang fitur tidak dikirim.** Hanya kegagalan, dan hanya sukses di
  `main`.
- Setiap pesan memuat **tautan langsung** ke log/commit, supaya tidak perlu mencari.

---

## 2. Aturan privasi — mengikat

Discord adalah layanan pihak ketiga di luar kendali perusahaan. Karena itu:

**Tidak boleh masuk pesan Discord:**
- Nama karyawan, NIK, email, nomor telepon
- Isi dokumen, isi laporan, nama berkas asli
- Koordinat lokasi
- Token, kata sandi, kunci, potongan `.env`
- Embedding wajah atau apa pun yang berkaitan dengan biometrik
- Jejak tumpukan yang memuat nilai variabel

**Yang boleh:**
- `request_id`, kode galat, nama endpoint, jumlah kejadian
- Nama tabel, nama migrasi, nama berkas kode, nomor baris
- Angka agregat ("42 absensi masuk antrean pemeriksaan")

Detail lengkapnya dilihat di log server lewat Tailscale. Discord hanya memberi tahu **bahwa
ada sesuatu**, bukan **apa isinya**.

Aturan ini ditegakkan kode: satu fungsi `sanitize_for_discord()` yang menyaring pola
sensitif, dan uji yang memastikan penyaringnya bekerja.

---

## 3. Alur CI (setiap push dan pull request)

```
push / PR
   ├── api      ruff check · ruff format --check · mypy · pytest (PostgreSQL nyata) · coverage
   ├── web      eslint · tsc --noEmit · vitest · build · cek ukuran bundel · cek kontrak OpenAPI
   ├── mobile   flutter analyze · flutter test
   ├── db       jalankan 01–05 di container kosong → wajib bersih
   └── security pip-audit · npm audit · gitleaks (cari rahasia yang lolos)
```

Semua berjalan paralel. Gagal satu → PR tidak bisa digabung.

**Yang menggagalkan build:**

| Pemeriksaan | Ambang |
|---|---|
| Lint / format | Ada pelanggaran |
| Tipe (mypy, tsc) | Ada galat |
| Uji | Ada yang gagal |
| Cakupan `services/` | Turun di bawah 100% cabang |
| Ukuran bundel web | > 250 KB gzip |
| Kontrak OpenAPI | Tipe frontend tidak lagi cocok |
| Matriks RBAC | Ada endpoint tanpa baris |
| Rahasia terdeteksi | Ada, satu pun |
| Kerentanan | Tingkat **tinggi** atau **kritis** |

**Yang tidak menggagalkan build tetapi dilaporkan ke Discord** — inilah bagian "janggal":

- **Peringatan baru** yang tidak ada di build sebelumnya (deprecation, peringatan Alembic,
  peringatan Flutter)
- **Uji yang goyah** (*flaky*): lulus setelah diulang
- Uji yang di-*skip* bertambah
- Cakupan turun meski masih di atas ambang
- Ukuran bundel naik > 10% dibanding `main`
- Waktu build naik > 50% dibanding rata-rata 7 hari
- Dependensi baru masuk lockfile
- Migrasi Alembic yang menghapus kolom atau tabel

Poin pertama yang paling berharga. **Peringatan yang selalu ada akan diabaikan; peringatan
yang baru muncul hampir selalu berarti sesuatu.** Karena itu CI menyimpan daftar peringatan
dari `main` sebagai garis dasar, dan hanya melaporkan selisihnya.

### Bentuk pesan di `#vms-ci`

```
❌ CI gagal — api
   PR #42 · feat: adendum personel · @dev
   pytest: 3 gagal dari 214
     test_personnel_addendum_transfers_leadership
     test_old_leader_loses_leader_rights
     test_old_leader_keeps_member_rights
   → github.com/.../actions/runs/123
```

```
⚠️ Peringatan baru — web
   PR #42 · 2 peringatan yang tidak ada di main
   react-hooks/exhaustive-deps · PlanForm.tsx:88
   Bundel: 231 KB → 248 KB (+7,4%)
   → github.com/.../actions/runs/124
```

---

## 4. Alur CD (deploy)

```
merge ke main          →  deploy STAGING otomatis
tag v*.*.*             →  deploy PRODUKSI (butuh persetujuan manual di GitHub Environment)
```

### Langkah deploy

```
1. Build image, beri tag dengan SHA commit
2. Kirim ke registry (GitHub Container Registry)
3. Sambung ke server lewat Tailscale (runner ber-tag:ci, auth key ephemeral)
4. Cadangkan basis data (produksi saja)
5. Jalankan migrasi Alembic — TERPISAH, sebelum aplikasi baru dinyalakan
6. Nyalakan versi baru, tunggu /health hijau
7. Uji asap: login, ambil satu daftar, /verify satu token contoh
8. Gagal di langkah mana pun → rollback ke image sebelumnya
9. Laporkan ke #vms-deploy
```

**Dikunci:**
- Migrasi dijalankan **terpisah** dari start aplikasi.
- **Deploy produksi butuh persetujuan manual** di GitHub Environment — bukan otomatis.
- **Jendela deploy produksi: di luar 07.00–19.00 WIB.** CI menolak deploy produksi di dalam
  jam itu kecuali diberi label `hotfix`. Deploy saat orang sedang absen adalah cara tercepat
  kehilangan kepercayaan.
- Runner yang menyentuh server memakai **auth key Tailscale ephemeral**, jadi tidak
  meninggalkan perangkat menggantung di tailnet.

### Bentuk pesan di `#vms-deploy`

```
🚀 Produksi — v1.4.0
   Migrasi: 0031_add_face_columns (12 detik)
   Cadangan sebelum deploy: ✅ 248 MB
   Uji asap: ✅ · Waktu henti: 6 detik
   → 14 commit sejak v1.3.2
```

```
🔴 ROLLBACK — produksi v1.4.1
   Gagal pada: uji asap (/health 503 setelah 60 detik)
   Kembali ke: v1.4.0 · Layanan pulih ✅
   Migrasi TIDAK di-rollback — periksa manual
```

Baris terakhir penting: migrasi maju-saja, jadi rollback aplikasi tidak mengembalikan skema.
Pesannya harus menyebutkan itu supaya tidak ada yang berasumsi keliru saat panik.

---

## 5. Peringatan dari server yang berjalan → `#vms-alerts`

Inilah bagian yang Anda minta: **hal janggal muncul sendiri di Discord**.

### 5.1 Galat aplikasi

| Pemicu | Tingkat |
|---|---|
| Pengecualian tak tertangani (500) | 🔴 selalu |
| Laju 5xx > 1% selama 5 menit | 🔴 |
| Endpoint tertentu gagal > 10× dalam 5 menit | 🔴 |
| Waktu respons p95 > 2 detik selama 5 menit | ⚠️ |
| Kueri basis data > 3 detik | ⚠️ |
| Galat 4xx melonjak tidak wajar | ⚠️ |

### 5.2 Keamanan — selalu 🔴

| Pemicu | Kenapa penting |
|---|---|
| **Refresh token dipakai ulang** (`reused = true`) | Tanda token dicuri |
| Lonjakan kegagalan login | Percobaan tebak kata sandi |
| **Konteks RLS gagal disetel** | Bug serius; bisa berarti kebocoran data |
| Akses ditolak berulang dari satu pengguna | Bisa berarti akun dibajak, bisa berarti bug izin |
| Verifikasi QR gagal berulang dari satu IP | Penyisiran token |
| Percobaan akses berkas oleh yang tidak berwenang | |

### 5.3 Keanehan bisnis — ini yang sering terlewat kalau tidak dipantau

| Pemicu | Artinya apa |
|---|---|
| Absensi `NEEDS_REVIEW` > 2× rata-rata harian | Ambang wajah salah, koordinat lokasi salah, atau GPS buruk |
| **Tidak ada absensi masuk sampai pukul 09.00 WIB** | Sesuatu rusak dan tidak ada yang melapor |
| Operasi luring `PENDING` > 24 jam | Sinkronisasi macet; laporan lapangan tertahan |
| Kegagalan kompresi gambar > 1% unggahan | Pillow/pillow-heif bermasalah |
| face-service tidak merespons | Wajah dilewati; absensi tetap jalan tetapi perlu diketahui |
| Penandatanganan dokumen gagal | Masalah kunci/KMS |
| `DOCUMENT_CHANGED` muncul pada dokumen sah | Bug hash — ini serius, lihat R-07 |
| Pertumbuhan MinIO > 2 GB/hari | Kompresi tidak jalan atau ada yang tidak wajar |

Baris kedua — **tidak ada absensi sampai pukul 09.00** — adalah jenis peringatan yang paling
berharga dan paling jarang dibuat orang. Sistem yang diam bukan berarti sistem yang sehat;
kadang itu berarti tidak ada yang bisa masuk dan semua orang sedang menelepon HR.

### 5.4 Infrastruktur

| Pemicu | Tingkat |
|---|---|
| `/health` gagal 2× berturut-turut | 🔴 |
| Disk tersisa < 20% | ⚠️ · < 10% 🔴 |
| Cadangan terakhir > 26 jam | 🔴 |
| Memori > 90% selama 10 menit | ⚠️ |
| Koneksi basis data > 80% pool | ⚠️ |
| Sertifikat kedaluwarsa < 14 hari | ⚠️ |

### Bentuk pesan di `#vms-alerts`

```
🔴 Galat server — VMS produksi
   POST /api/v1/attendance/check-in
   ValueError · attendance_service.py:142
   14 kejadian dalam 5 menit · 9 pengguna terpengaruh
   request_id contoh: 7f3a9c2e
   → log: ssh vms-prod (lewat Tailscale)
```

```
⚠️ Janggal — absensi
   Belum ada absensi masuk sampai 09.05 WIB
   Rata-rata hari kerja jam ini: 38
   Terakhir tercatat: kemarin 17.42
```

```
🔴 Keamanan — refresh token dipakai ulang
   1 rantai sesi dicabut otomatis
   user_id: 3f2a… (disamarkan) · IP berbeda dari sesi asal
   Tindakan: hubungi pengguna, periksa audit_event
```

### Aturan anti-banjir

Tanpa ini, kanal peringatan akan mati dalam seminggu:

1. **Dedup berdasarkan sidik jari** (jenis galat + lokasi kode). Kejadian sama dalam 15 menit
   digabung menjadi satu pesan dengan penghitung.
2. **Jeda diam bertambah**: galat yang sama berulang dilaporkan setelah 15 menit, lalu
   1 jam, lalu 4 jam.
3. **Batas 20 pesan/jam** per kanal. Bila terlampaui, kirim satu pesan ringkasan.
4. **Pemulihan juga dilaporkan** — "✅ /health kembali normal setelah 4 menit". Peringatan
   tanpa kabar pemulihan membuat orang tidak tahu apakah masalahnya masih ada.

---

## 6. Ringkasan harian → `#vms-digest`

Setiap pukul 08.00 WIB, satu pesan:

```
📊 VMS — 23 September
   Absensi: 87 masuk · 4 perlu diperiksa · 0 ditolak
   Laporan: 23 diajukan · 19 disetujui
   Dokumen terbit: 3 SK · 1 adendum personel
   Berkas: 214 unggah · 1,2 GB → 180 MB setelah kompresi (85%)
   Galat: 2 (keduanya sudah pulih)
   Antrean luring: 0 tertahan
   Versi: v1.4.0 · Cadangan terakhir: 02.00 ✅
```

Kegunaannya bukan pemantauan, melainkan **rasa normal**. Setelah membaca ini seminggu, angka
yang menyimpang langsung terasa aneh tanpa perlu ambang batas.

---

## 7. Rahasia yang dibutuhkan

Disimpan di **GitHub Secrets** dan `.env` server, tidak pernah di Git:

| Nama | Untuk |
|---|---|
| `DISCORD_WEBHOOK_CI` | Kanal `#vms-ci` |
| `DISCORD_WEBHOOK_DEPLOY` | Kanal `#vms-deploy` |
| `DISCORD_WEBHOOK_ALERTS` | Kanal `#vms-alerts` |
| `DISCORD_WEBHOOK_DIGEST` | Kanal `#vms-digest` |
| `TAILSCALE_OAUTH_CLIENT` | Runner bergabung ke tailnet |
| `REGISTRY_TOKEN` | Container registry |
| `DEPLOY_SSH_KEY` | Deploy lewat Tailscale |

**Webhook Discord adalah rahasia.** Siapa pun yang memegangnya bisa mengirim pesan ke kanal
Anda. Bila bocor, cabut dan buat baru — tidak ada cara lain.

---

## 8. Yang dikerjakan di fase mana

| Task | Fase | Isi |
|---|---|---|
| P0-9 | 0 | CI empat komponen + `gen:api` + pemeriksaan kontrak |
| P0-10 | 0 | Webhook Discord `#vms-ci`, notifikasi kegagalan build |
| P0-11 | 0 | Garis dasar peringatan + pelaporan peringatan baru |
| P1-8 | 1 | Peringatan keamanan → `#vms-alerts` (token dipakai ulang, RLS gagal, lonjakan login) |
| P4-9 | 4 | Peringatan bisnis absensi (tidak ada absensi sampai 09.00, lonjakan `NEEDS_REVIEW`) |
| P9-6 | 9 | Ringkasan harian, penyetelan ambang, uji anti-banjir |
| P10-8 | 10 | CD produksi + persetujuan manual + rollback otomatis |

Peringatan dibangun **bertahap bersama fiturnya**, bukan ditumpuk di akhir. Peringatan yang
dipasang setelah fiturnya jalan berbulan-bulan hampir selalu salah ambang, karena tidak ada
yang tahu bentuk normalnya.
