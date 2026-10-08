# 06 · Rencana Fase

Antrean kerja. Dikerjakan **berurutan**, satu task per iterasi. Task dianggap selesai hanya
bila *Definition of Done* (DoD) fasenya terpenuhi — bukan ketika kodenya "sudah jalan di
komputer saya".

Estimasi untuk **1 developer penuh waktu yang dibantu AI**. Angka ini sensitif terhadap dua
hal di luar kendali developer: kecepatan Anda mengambil keputusan, dan ketersediaan perangkat
Android untuk uji lapangan.

---

## Ringkasan

| Fase | Fokus | Minggu | Yang bisa didemokan |
|---|---|---|---|
| **0** | Fondasi repo, infra, kerangka 4 komponen | 1–2 | `docker compose up` jalan; web & app Flutter tampil |
| **1** | Identitas, sesi, peran, audit | 3–4 | Login, ganti kata sandi, cabut sesi, log audit |
| **2** | Berkas, karyawan, dokumen pribadi | 5 | HR memverifikasi dokumen; peringatan kedaluwarsa |
| **3** | SK & siklus pekerjaan | 6–8 | PM menerbitkan SK, ketua menerima/banding, adendum personel |
| **4** | Absensi lapangan + fondasi Flutter | 9–11 | Absen dari Android di lokasi; Finance memeriksa |
| **5** | Laporan harian, mingguan, akhir | 12–14 | Ketua melapor (termasuk luring), PM menilai |
| **6** | Tanda tangan QR + PDF | 15–16 | SK ber-QR; pindai QR → tanda tangan terverifikasi |
| **7** | Aset, insiden, lembur, lini masa OPS | 17–18 | Seluruh modul prototipe tersedia |
| **8** | Pengenalan wajah | 19–20 | Absensi dengan verifikasi wajah |
| **9** | Pengerasan, kinerja, aksesibilitas | 21 | Uji beban, uji keamanan, perbaikan |
| **10** | UAT dan rilis | 22–24 | Dipakai satu tim nyata, lalu seluruh perusahaan |

**Titik henti yang aman:** akhir fase 5 (minggu 14). Pada titik itu sistem sudah berguna
sehari-hari; fase 6–8 menambah nilai tetapi bukan syarat untuk mulai dipakai.

---

## Fase 0 — Fondasi *(minggu 1–2)*

| Task | Isi |
|---|---|
| P0-1 | Inisialisasi Git + monorepo (`api/`, `web/`, `mobile/`, `face-service/`, `db/`, `docs/`, `prototype/`). Prototipe V2 masuk sebagai `prototype/`, **dibekukan** |
| P0-2 | **Jalankan `db/01`–`db/04` di PostgreSQL 18**, perbaiki galat, jadikan baseline Alembic `0001`. Ganti `new_id()` → `uuidv7()` |
| P0-3 | Pasang pgvector; jalankan `db/05`. Bila gagal di Windows, pakai citra Docker PostGIS+pgvector dan catat keputusannya |
| P0-4 | API: app factory FastAPI, `pydantic-settings`, logging JSON + `request_id`, handler galat seragam, `/health` + `/ready`, sesi SQLAlchemy + middleware `SET LOCAL` |
| P0-5 | Docker: `Dockerfile` api (termasuk dependensi WeasyPrint), web multi-stage → Caddy, `docker-compose.yml` + `.dev.yml`, `.env.example` |
| P0-6 | Web: Vite + TS strict, Tailwind + **shadcn/ui** (`components.json`, komponen inti disalin), token desain dari prototipe, router, TanStack Query, **Zustand** (session/ui/offline store), klien API dengan interceptor refresh, kerangka menu dari `permissions[]` |
| P0-7 | Mobile: proyek Flutter (ambil dari `visiontech/mobile`), **verifikasi kelengkapan `shadcn_ui`** (form, dialog, sheet, select, date picker, tabel, toast), tema dari token yang sama, go_router, dio, secure storage, drift, flavor dev/prod. Application ID `id.co.visiontech.vms` |
| P0-8 | **Struktur folder ditegakkan otomatis**: `eslint-plugin-boundaries` untuk arah ketergantungan web (dokumen 11 §3); pemeriksa lapisan backend (router tidak boleh mengimpor repository) |
| P0-9 | **Kerangka lapisan backend**: contoh lengkap satu modul kecil menembus router → controller → service → repository, sebagai acuan modul berikutnya |
| P0-10 | face-service: kerangka FastAPI + `/health` (model belum dipasang) |
| P0-11 | CI GitHub Actions: lint + tipe + uji keempat komponen; `gen:api` + pemeriksaan kontrak; `gitleaks`; audit dependensi |
| P0-12 | **Webhook Discord `#vms-ci`**: notifikasi kegagalan build + `sanitize_for_discord()` beserta ujinya |
| P0-13 | **Garis dasar peringatan**: simpan peringatan dari `main`, laporkan hanya yang baru (dokumen 17 §3) |
| P0-14 | Server: firewall (hanya 80/443 + `tailscale0`), **port 22 tertutup dari internet**, ACL Tailscale + tag `server`/`admin`/`dev`/`ci`, akses konsol darurat diaktifkan dan dicatat di runbook |

**DoD:** `docker compose up` menjalankan db, api, web; `/health` hijau; CI hijau dan
kegagalan build benar-benar muncul di Discord; skema `db/` terpasang di basis data nyata;
shell web tampil dan **terbaca pada lebar 360 px**; aplikasi Flutter tampil; pemeriksa
struktur folder menolak impor yang melanggar arah ketergantungan.

> **Catatan:** P0-2 adalah pekerjaan pertama yang benar-benar bernilai. Sampai skema berjalan
> di basis data sungguhan, semua yang ada di `db/` masih berstatus dugaan.

---

## Fase 1 — Identitas, sesi, peran, audit *(minggu 3–4)*

| Task | Isi |
|---|---|
| P1-1 | argon2id, JWT EdDSA, penerbitan & rotasi sesi memakai `issue_session` / `rotate_session`, deteksi pemakaian ulang, lockout `login_is_locked` |
| P1-2 | Endpoint auth lengkap + `/auth/me` yang mengembalikan daftar izin |
| P1-3 | Peta izin (`core/permissions.py`) + `require_permission`; kerangka **uji RBAC parametrik endpoint × peran** |
| P1-4 | Fungsi kewenangan per pekerjaan: `is_plan_leader` / `is_plan_member` dipakai servis, bukan hanya RLS |
| P1-5 | CLI: `create-admin`, `seed`, `cleanup-orphans` |
| P1-6 | Audit: middleware `app.actor_label`, endpoint `/audit-events` |
| P1-7 | Web: halaman login, ganti kata sandi, penjaga rute, daftar sesi aktif + "keluarkan semua perangkat", halaman audit — **dirancang mobile-first** |
| P1-8 | **Peringatan keamanan → Discord `#vms-alerts`**: refresh token dipakai ulang, konteks RLS gagal disetel, lonjakan kegagalan login |

**DoD:** alur "buat admin → buat pengguna → login → ganti kata sandi → cabut sesi" berjalan
ujung ke ujung; memakai ulang refresh token lama benar-benar mencabut seluruh rantai (ada
ujinya); matriks RBAC hijau; menonaktifkan akun mengakhiri sesi pada permintaan berikutnya.

---

## Fase 2 — Berkas, karyawan, dokumen pribadi *(minggu 5)*

| Task | Isi |
|---|---|
| P2-1 | Abstraksi penyimpanan + MinIO; validasi magic bytes, batas ukuran; URL bertanda tangan ≤ 5 menit |
| P2-1b | **Kompresi gambar** (dokumen 13): WebP 3 ukuran (`thumb`/`view`/`full`) + buang EXIF, di `run_in_threadpool`; gambar gagal kompres tetap disimpan apa adanya; dokumen (PDF/Office) disimpan utuh tanpa diproses; deduplikasi SHA-256 |
| P2-2 | Endpoint karyawan, riwayat jabatan, promosi, offboarding, pemulihan |
| P2-3 | Dokumen pribadi: unggah, verifikasi HR, masa berlaku, nomor tersamar + hash |
| P2-4 | Servis kedaluwarsa + `v_document_expiry`; pengajuan perpanjangan dari profil |
| P2-5 | Web: direktori karyawan, profil, daftar dokumen + tombol perpanjangan, antrean verifikasi HR |

**DoD:** berkas bukan gambar ditolak; pengguna lain tidak bisa melihat dokumen pribadi orang
lain (404, bukan 403); peringatan ≤ 30 hari muncul; tombol perpanjangan ada di daftar dokumen
profil — bukan hanya di halaman detail (temuan prototipe yang wajib dibawa); **foto HP 5 MB
tersimpan ≤ 700 KB dengan EXIF benar-benar hilang**; PDF dan berkas Office tersimpan utuh,
byte-nya sama persis dengan yang diunggah.

---

## Fase 3 — SK dan siklus pekerjaan *(minggu 6–8)*

Fase inti. Di sinilah produk ini berbeda dari aplikasi lain.

| Task | Isi |
|---|---|
| P3-1 | Model + endpoint pekerjaan: draft, hari, tugas, anggota berjangka waktu |
| P3-2 | Penerbitan dokumen: snapshot JSONB, penomoran, immutability, `document_is_locked` |
| P3-3 | Transisi: `PUBLISH`, `ACCEPT`, `APPEAL`, `REVISE`, `START`, `CANCEL`, `RESTORE` |
| P3-4 | Adendum perpanjangan: usulan → persetujuan → berlaku |
| P3-5 | **Adendum personel**: usulan PM → penerimaan ketua masuk → penarikan PM → berlaku; penutupan baris anggota lama dan pembukaan baris baru |
| P3-6 | Penandaan bentrok jadwal personel (`personnel_conflict`) sebelum pengajuan |
| P3-7 | Penguncian optimistis `row_version` + pemetaan galat 409 berbahasa manusia |
| P3-8 | Web: daftar & detail pekerjaan, penyusun SK, dialog adendum, riwayat versi dokumen |

**DoD:** seluruh transisi prototipe menghasilkan hasil yang sama dengan `domain.js` pada uji
yang dipindahkan; ketua yang diganti kehilangan hak ketua tetapi tetap punya hak anggota bila
masih terdaftar; dokumen versi lama benar-benar terkunci; dua sesi yang menyimpan bersamaan
menghasilkan pesan "muat ulang", bukan saling menimpa.

---

## Fase 4 — Absensi lapangan *(minggu 9–11)*

Ditaruh lebih awal karena paling berisiko dan paling menentukan penerimaan pengguna.

| Task | Isi |
|---|---|
| P4-1 | Lokasi proyek (`site`) + radius; endpoint master |
| P4-2 | `check-in` / `check-out`: waktu dari jam server, jarak dari `ST_Distance`, penanda terlambat/pulang cepat |
| P4-3 | Swafoto berwatermark, unggahan, penyimpanan |
| P4-4 | Penjelasan karyawan + pemeriksaan Finance + pengajuan ulang di hari yang sama (riwayat lama tetap ada) |
| P4-5 | Ekspor CSV untuk Finance |
| P4-6 | **Flutter**: layar absensi, izin lokasi/kamera, penolakan akurasi GPS > 100 m, penanganan mode pesawat |
| P4-7 | Antrean luring untuk aksi lapangan **selain absensi** + indikator status |
| P4-8 | Web: daftar absensi + filter, panel pemeriksaan Finance |
| P4-9 | **Peringatan bisnis → Discord**: tidak ada absensi masuk sampai 09.00 WIB, lonjakan `NEEDS_REVIEW`, antrean luring tertahan > 24 jam |

**DoD:** absen berhasil dari perangkat Android **nyata** di lokasi nyata (bukan emulator);
di luar radius tercatat dan ditandai, tidak ditolak; jam perangkat diubah tidak mengubah
waktu tercatat; mode pesawat tidak membuat aplikasi mogok atau kehilangan data.

> **Butuh dari Anda:** minimal satu perangkat Android untuk uji, dan satu lokasi proyek nyata
> beserta koordinatnya. Tanpa keduanya fase ini tidak bisa dinyatakan selesai.

---

## Fase 5 — Laporan *(minggu 12–14)*

| Task | Isi |
|---|---|
| P5-1 | Laporan harian: tugas, teks pekerjaan, kendala, bukti; simpan & ajukan |
| P5-2 | Penilaian PM: setujui / minta perbaikan, beserta catatan |
| P5-3 | Laporan mingguan |
| P5-4 | Permintaan & persetujuan penyelesaian; laporan akhir |
| P5-5 | Larangan laporan untuk tanggal yang belum tiba |
| P5-6 | Flutter: laporan lapangan **luring** + unggahan foto yang bisa dilanjutkan |
| P5-7 | Web: layar laporan, penilaian, mode presentasi |

**DoD:** laporan yang diketik saat tanpa sinyal tidak pernah hilang; laporan yang ditolak
server muncul di daftar "perlu perhatian" dengan alasannya; teks laporan tidak pernah hilang
saat berpindah layar (regresi lama yang wajib diuji).

---

## Fase 6 — Tanda tangan QR dan PDF *(minggu 15–16)*

| Task | Isi |
|---|---|
| P6-1 | Kanonikalisasi JSON (RFC 8785) + perhitungan SHA-256 dokumen |
| P6-2 | Integrasi KMS/HSM; `signing_key`; rotasi kunci |
| P6-3 | `register_document_signature` + penomoran seri |
| P6-4 | Render PDF (Jinja2 + WeasyPrint): SK, adendum, laporan akhir, berita acara |
| P6-5 | Halaman verifikasi publik `/verify/{token}` + pembatasan laju |
| P6-6 | Pencabutan tanda tangan beserta alasan |

**DoD:** PDF dicetak ulang dengan versi WeasyPrint berbeda tetap `VALID` saat dipindai;
mengubah satu huruf pada snapshot menghasilkan `DOCUMENT_CHANGED`; halaman verifikasi terbaca
di layar ponsel dan tidak membocorkan data pribadi tambahan.

---

## Fase 7 — Aset, insiden, lembur, lini masa *(minggu 17–18)*

| Task | Isi |
|---|---|
| P7-1 | Aset: pesan → lepas → kembali → verifikasi; exclusion constraint jadwal |
| P7-2 | Kendaraan: pengemudi + pemeriksaan masa berlaku SIM |
| P7-3 | Insiden K3 (5 kategori) + penyelesaian, **tersaring unit** |
| P7-4 | Lembur + pemeriksaan Finance + rekap, **tersaring unit** |
| P7-5 | Lini masa OPS **dikelompokkan per pekerjaan**, rekap lintas pekerjaan |
| P7-6 | Web: seluruh layar modul ini |

**DoD:** satu aset tidak bisa dipesan dua pekerjaan pada rentang beririsan (ditolak basis
data, bukan UI); PM unit CCTV tidak melihat insiden/lembur unit lain (ada ujinya); lini masa
terbaca tanpa perlu dijelaskan.

---

## Fase 8 — Pengenalan wajah *(minggu 19–20)*

| Task | Isi |
|---|---|
| P8-1 | face-service: model ArcFace/InsightFace 512-d, `/embed`, `/liveness` |
| P8-2 | Persetujuan biometrik: pencatatan, penarikan, penonaktifan embedding |
| P8-3 | Pendaftaran wajah (3–5 foto) oleh HR |
| P8-4 | Integrasi ke `check-in`; `NO_MATCH`/`LOW_QUALITY` → `NEEDS_REVIEW` |
| P8-5 | **Kalibrasi ambang batas** dengan ≥ 30 karyawan nyata; ukur FAR & FRR; tetapkan nilai |
| P8-6 | `purge_face_probes()` terjadwal + halaman pengaturan retensi |

**DoD:** kalibrasi terdokumentasi dengan angka, bukan tebakan; menarik persetujuan benar-benar
menonaktifkan embedding pada saat itu juga; face-service mati → absensi tetap bisa dilakukan;
tidak ada satu pun foto wajah tersimpan di luar ketentuan.

> **Status (2026-10-06):** P8-1…P8-4, P8-6 selesai di kode dan sudah di `prod` (migrasi 0023). Keputusan pemilik yang
> berlaku: pendaftaran oleh **karyawan sendiri** lewat kamera (HP, atau webcam di web) dengan 2 tantangan acak yang
> diperiksa **server** (kiri/kanan/atas/bawah/buka mulut; kedip dihapus); foto bukti hanya di luar radius; gambar wajah
> absen = `face_probe` sementara; pekerja lapangan (HP, boleh luring) **dan** kantor (web, hanya online); karyawan
> terdaftar yang absen tanpa data wajah → Perlu review. `FACE_ENROLLMENT_REQUIRED` mewajibkan pendaftaran setelah login
> (bawaan mati). **Belum:** pencocokan wajah di HP saat luring (model ONNX + template), kalibrasi P8-5, pemasangan
> face-service di server. Laporan spike dan daftar kerja operasional: `docs/30-LAPORAN-SPIKE-WAJAH.md`.

> **Butuh dari Anda:** persetujuan tertulis dari karyawan yang ikut kalibrasi, dan kesepakatan
> bahwa wajah tidak akan dipakai untuk hal lain selain absensi.

---

## Fase 9 — Pengerasan *(minggu 21)*

| Task | Isi |
|---|---|
| P9-1 | Uji beban: 60 pengguna bersamaan, 400 absensi/hari |
| P9-2 | Uji keamanan mandiri: matriks RBAC penuh, percobaan lintas tenant, uji RLS bila servis lupa memfilter |
| P9-3 | Aksesibilitas: kontras, sasaran sentuh, navigasi keyboard, tanpa dialog native |
| P9-4 | Tinjauan pesan galat — semuanya harus bisa dipahami orang lapangan |
| P9-5 | Cadangan + pemulihan **diuji sungguhan**, bukan sekadar dikonfigurasi |
| P9-6 | Ringkasan harian Discord `#vms-digest`; penyetelan ambang peringatan; uji anti-banjir (dedup, jeda bertambah, batas 20/jam) |
| P9-7 | Audit struktur: tidak ada aturan bisnis di router, tidak ada model SQLModel yang jadi respons, tidak ada data API di Zustand |

**DoD:** pemulihan dari cadangan berhasil pada basis data kosong; tidak ada endpoint tanpa
baris di matriks RBAC; tidak ada teks Inggris mentah di layar pengguna.

> **Status (2026-10-08):**
> - **P9-7 selesai untuk router:** kedelapan router lama (R-25b: audit, kedaluwarsa dokumen, berkas, absensi,
>   karyawan, aset, HSE, SK) tidak lagi menyentuh basis data. SQL pindah ke `crud/`, aturan ke `services/`.
>   Sinkronisasi luring kini memanggil `HseService`, bukan fungsi router. `LEGACY` di
>   `test_router_layering.py` sudah kosong.
> - **P9-2 — RLS kini benar-benar berlaku (temuan 2026-10-08):** di produksi API tersambung sebagai `vms_app` yang
>   superuser **dan** pemilik tabel, jadi seluruh kebijakan RLS terlewati. Migrasi `0024_runtime_role` membuat peran
>   runtime `vms_api` (bukan superuser/pemilik, tanpa BYPASSRLS); alembic & CLI tetap memakai pemilik
>   (`MIGRATION_DATABASE_URL`). Seluruh suite (±930 uji) lulus dengan API sebagai `vms_api`. Penyesuaian yang
>   ditemukan: fungsi DB → SECURITY DEFINER (aturan bentrok personel/SIM/QR publik sempat diam-diam lolos, rekursi
>   kebijakan SK), batas RLS SK/absensi/lembur/insiden/token QR = tenant (docs/10 Bagian C), konteks pengguna
>   disetel saat login. Pengalihan prod: `deploy/pakai-peran-runtime.sh` (dijalankan pemilik; rollback `kembalikan`).
> - **Temuan P9-2 yang masih terbuka:**
>   - 7 tabel tenant belum ber-RLS: `site`, `file_object`, `notification`, `attendance_device_key`,
>     `attendance_offline_event`, `signature_serial_counter`, `app_user`.
>   - Menunggu keputusan pemilik (butuh migrasi + kebijakan per tabel).

---

## Fase 10 — UAT dan rilis *(minggu 22–24)*

| Task | Isi |
|---|---|
| P10-1 | Staging dengan data contoh realistis |
| P10-2 | **Uji terima bersama satu tim nyata** selama 1 minggu penuh pekerjaan |
| P10-3 | Perbaikan hasil UAT |
| P10-4 | Panduan singkat per peran (1 halaman, bergambar) + video pendek |
| P10-5 | Pelatihan: PM, HR, Finance, Aset, OPS, dan ketua tim |
| P10-6 | Rilis produksi bertahap: satu unit bisnis dulu, lalu seluruhnya |
| P10-7 | Distribusi APK + pemeriksaan versi minimum di server — **selesai 2026-10-08** (pembaruan otomatis tanpa Play, docs/32; diuji di Realme) |
| P10-8 | **CD produksi**: GitHub Environment dengan persetujuan manual, cadangan sebelum deploy, migrasi terpisah, uji asap, rollback otomatis, laporan ke `#vms-deploy`; jendela deploy di luar 07.00–19.00 WIB |
| P10-9 | **Kunci tanda tangan dipindah ke KMS** (K-05) sebelum produksi menyimpan dokumen sungguhan |

**DoD:** satu tim nyata menyelesaikan satu siklus pekerjaan penuh (SK → absensi → laporan →
penyelesaian) tanpa bantuan developer; tidak ada bug tingkat "menghalangi pekerjaan" yang
tersisa.

---

## Aturan kerja selama proyek

1. **Uji ditulis untuk aturan bisnis sebelum kodenya**, khususnya transisi dan otorisasi.
2. **Setiap fase membawa uji regresi prototipe** yang relevan. Bug yang pernah diperbaiki di
   prototipe tidak boleh muncul lagi.
3. **Tidak ada `alert()` / `confirm()` / `prompt()` bawaan browser.** Ini bukan selera: dialog
   itu memblokir halaman dan membekukan otomasi pengujian.
4. **Ambiguitas dicatat, tidak dikarang.** Setiap keputusan yang diambil karena spesifikasi
   tidak jelas ditulis di dokumen 10 bagian "keputusan implementasi", lengkap dengan
   "perlu konfirmasi?".
5. **Demo di akhir setiap fase.** Rencana yang tidak pernah ditunjukkan ke pemilik produk
   adalah rencana yang menyimpang diam-diam.
