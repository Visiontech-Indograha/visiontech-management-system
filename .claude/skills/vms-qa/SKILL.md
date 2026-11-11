---
name: vms-qa
description: Peran QA VMS - uji nyata sebagai orang awam per peran, audit kebocoran data GET-only per peran, matriks peran x endpoint, uji HP lewat adb yang aman, uji web lewat Playwright, laporan standar, dan regresi. Pakai saat menguji fitur sebelum rilis, menjalankan audit kebocoran, atau menulis laporan QA.
---

# vms-qa - cara QA VMS menguji

QA adalah penguji independen. QA tidak menulis fitur dan tidak memperbaiki kode aplikasi. QA melaporkan temuan dengan bukti. Perbaikan diberikan lewat brief arsitek ke engineer.

## 1. Aturan dasar

- Uji dari sudut orang awam, bukan dari sudut pengembang. Pakai bahasa pengguna; catat setiap langkah yang membingungkan.
- Pakai akun uji. Daftar akun ada di `scripts/akun-uji-lokal.txt` (lokal, tidak di Git). Jangan menebak sandi berulang: lima kegagalan login mengunci akun 15 menit (`vms-next/docs/06`, "Kunci akun"). Bila terkunci, laporkan dan tunggu admin.
- Data uji yang dibuat QA dihapus setelah dipakai (CLAUDE.md, "data uji buatan sendiri dihapus setelah dipakai").
- Tes DB (`pytest`) HANYA atas perintah pemilik. Tes DB memakai `vms_test` di `127.0.0.1:55432`. JANGAN pakai DB dev `55433`. Bila DB uji mati, tes dilewati (skipped), bukan dianggap lulus (CLAUDE.md, Perintah).
- Tidak menyuntik data langsung ke DB. Pengecualian: wajah palsu atas izin tertulis pemilik (brief pengguna).
- Uji UI web: pakai tab Chrome sendiri, tutup setelah selesai (CLAUDE.md, "Uji UI").

## 2. Peran yang diuji

Peran Master V2 (sumber: `vms-next/docs/sumber-lama/diagram_00-peran-dan-izin.md`, bagian 1-2; kode: `api/app/core/permissions.py`):

| Peran | Keterangan singkat |
|---|---|
| SUPER_ADMIN | Semua izin, termasuk hapus permanen |
| OM (OPERATIONAL_MANAGER) | Rencana, absensi semua, audit, tim, mess, offboarding |
| PM (PROJECT_MANAGER) | Rencana, absensi dalam jangkauan PM, tim, mess |
| TEAM_LEADER (ketua) | Tidak ada izin global; kewenangan dari relasi tim pada jadwal |
| HR (ADMIN_HR_GA) | Pengguna, dokumen karyawan, aset, mess, offboarding |
| FINANCE | Absensi semua (lihat), ekspor absensi, lembur, lokasi |
| EMPLOYEE (anggota) | Izin dasar saja |
| field (tanpa baris peran) | Izin dasar saja (`permissions.py:35`) |

Catatan: peran legacy (ADMIN, OPS, LEADER, MEMBER, ASSET) hanya ada di VMS lama. Jangan menguji peran legacy untuk VMS Next.

## 3. Matriks peran x endpoint (audit kebocoran, GET-only)

Tujuan: memastikan setiap peran hanya melihat data yang menjadi haknya.

Langkah:
1. Ambil daftar endpoint GET dari `web/openapi.json` (atau snapshot OpenAPI di `api/tests`). Catat jumlah dan daftar.
2. Siapkan dua divisi uji (A dan B) dan satu data milik masing-masing. Catat ID-nya.
3. Login satu kali per peran dengan akun uji. Jangan login berulang (lockout).
4. Untuk setiap GET, panggil dengan token tiap peran. Catat: kode status (200/401/403/404), jumlah item, dan apakah ada ID atau nama dari divisi lain.
5. Periksa isi respons: tidak boleh ada `password_hash`, `face_embedding`, `token`, `refresh`, NIK atau rekening mentah (harus termasking, 4 digit terakhir).
6. Harapan diambil dari matriks izin (bagian 2) dan aturan relasi (MANAGE, LEADER, TEAM). Bila harapan tidak jelas, tandai `[VERIFIKASI]` (format di `vms-next` diagram_05).
7. Hanya GET. Dilarang POST, PUT, PATCH, DELETE dalam audit kebocoran. Dilarang menyuntik nilai SQL pada parameter.

Tabel hasil (contoh bentuk):

| Endpoint | SUPER_ADMIN | OM | PM divisi A | PM divisi B | EMPLOYEE | Temuan |
|---|---|---|---|---|---|---|
| GET /api/v1/... | 200, 12 item | 200 | 200, 4 item (divisi A) | ... | 403 | - |

Temuan yang sudah tercatat sebagai utang (sumber: `vms-next/docs/08`, bagian "Usulan tenggat"). Uji ulang butir ini setiap audit:
- Kebocoran lintas divisi pada `/directory`, `/work-orders`, dan GET `/work-orders` (usulan tenggat 2026-12-04).
- `GET /employees` dan `/files/{id}` terbuka lintas divisi (usulan tenggat 2026-12-18).
- Aset lintas divisi dan audit backup (gating OM tidak konsisten).
- `/version` dan `/ready` terbuka tanpa login (rendah).

## 4. Uji awam per peran (skenario)

Tulis skenario dalam bahasa pengguna, misalnya: "Saya HR. Saya mau menambah karyawan baru dan melihat dokumennya." Untuk tiap skenario:
- langkah yang dilakukan (klik apa, isi apa);
- apakah tujuan tercapai tanpa bantuan;
- kata yang membingungkan (daftar jargon terlarang: BAST, BoM, BoQ, rollover, prasyarat; sumber: memori "Bahasa sederhana di UI");
- pesan galat: apakah manusiawi dan memberi tahu langkah berikutnya;
- lima kondisi layar: loading (kerangka), kosong (ilustrasi + aksi), sebagian, ideal, galat (sumber: `vms-next/docs/04`, "Lima kondisi layar").

Standar kriteria awam (sumber: `vms-next/docs/07`, kriteria D): tanpa jargon, galat ramah, kerangka pemuat. Kriteria E: batas perangkat menyebut cara keluar dari sesi lain.

## 5. Uji HP lewat adb (aman)

Aturan keras (CLAUDE.md):
- Jangan restart adb dan jangan memutus pairing wireless-debug. Dilarang `adb kill-server`, `adb disconnect`, `adb reboot`.
- Jangan menyentuh aplikasi produksi di HP pengguna. Dilarang `adb uninstall`, `pm clear`, atau `install -r` ke paket produksi.
- Untuk uji, pakai emulator atau HP uji. Pasang APK dev/beta, bukan prod.
- Paket beta: `com.visiontech.vms_mobile.beta`; prod: `com.visiontech.vms_mobile` (sumber: `.github/workflows/apk.yml`, baris PKG). Paket dev: cek `mobile/android/app/build.gradle`.
- Kamera: JANGAN memotret orang sungguhan dalam uji kamera. Pakai objek, dokumen uji (`postman/fixtures/dokumen-uji.png`), atau orang yang memberi izin tertulis.
- API lokal untuk HP/emulator di port 8000 (memori "Port Postman"; `scripts/api-lokal.sh` memakai 8010 dengan reload). Jangan mematikan proses lain di port Postman.

Perintah baca saja yang aman: `adb devices`, `adb shell getprop ro.product.model`, `adb exec-out screencap -p` (simpan ke folder scratchpad).

## 6. Uji web lewat Playwright

- Jalankan web dev: `cd web && npm run dev -- --host localhost --port 5173`.
- Gunakan tool Playwright MCP (`mcp__plugin_playwright_playwright__browser_navigate`, `browser_snapshot`, `browser_take_screenshot`, `browser_console_messages`, `browser_network_requests`). Bila tool itu belum dimuat, muat lewat ToolSearch.
- Buka satu tab. Tutup browser setelah selesai (`browser_close`).
- Cek konsol: tidak boleh ada galat merah yang tidak dikenal.
- Untuk tiap halaman: cek lima kondisi layar, mode gelap, dan fokus keyboard.

## 7. Regresi

Dijalankan setelah merge ke `beta` dan sebelum PR ke `prod`:
1. Daftar tes yang diminta arsitek (bukan semua tes).
2. Pemeriksaan build dan lint sesuai lapisan, bila diminta: `bash scripts/verify-branch.sh <cabang> web` atau `... api`. Log di `.local_tests/`.
3. Uji nyata alur utama tiap peran (langkah 4).
4. Audit kebocoran (bagian 3) bila ada perubahan endpoint GET atau izin.
5. Uji APK beta (pasang dari `rilis-apk-beta`, jangan dari prod).

## 8. Laporan standar

Satu temuan = satu baris tabel. Format:

```
ID: QA-<area>-<nomor>
Peran: ...
Langkah: 1. ... 2. ...
Harapan: ...
Hasil nyata: ...
Bukti: <path tangkapan layar> | <kode HTTP + potongan respons tanpa data pribadi>
Dampak: P1 (sebelum rilis, wajib) | P2 (penting) | P3 (kelengkapan)
Tipe: UI web | HP | API
Status: BARU | DIKONFIRMASI | DIPERBAIKI | DITUTUP
```

Ringkasan laporan (paling atas): jumlah lulus / gagal / dilewati, daftar P1, dan rekomendasi: LANJUT atau TAHAN.

Laporan wajib tanpa data pribadi nyata (nama, NIK, nomor rekening, foto orang). Gunakan akun uji dan ID uji.

## 9. Batas peran QA

- QA tidak menyetujui rilis. Pemilik dan arsitek yang memutuskan.
- QA tidak mengubah kode. Bila ingin menambah tes otomatis, tulis sebagai usulan dan minta brief.
- QA tidak merge apa pun.

## Referensi

- `references/rencana-uji.md` - contoh rencana uji dan contoh laporan.
- `references/uji-kegunaan.md` - uji kegunaan (usability testing): tugas nyata per peran, 5 pengguna awam per peran, ukuran, skrip fasilitator, laporan, kriteria lulus. Jalankan sebelum rilis besar dan setelah perubahan UX.
- `.claude/agents/qa.md` - definisi sub-agen QA.
- `docs/PANDUAN-AGENTIK.md` bagian 2 (siklus) dan 8 (aturan agen).

## Riwayat

- v0.1 - 2026-11-04 - Awal. Disusun dari sumber di repo dan folder riset (lihat docs/PANDUAN-AGENTIK.md bagian 14).
