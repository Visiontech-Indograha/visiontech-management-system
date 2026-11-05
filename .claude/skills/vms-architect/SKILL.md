---
name: vms-architect
description: Cara arsitek VMS bekerja - memecah tugas per lapisan, menulis brief untuk engineer, meninjau PR, membuat ADR, menyiapkan urutan rilis, dan mendaftar keputusan yang harus diputuskan klien. Pakai saat merancang fitur, menulis brief, meninjau hasil engineer, atau menyiapkan rilis VMS.
---

# vms-architect - cara kerja arsitek VMS

Dipakai oleh sesi utama Claude (arsitek). Engineer dan QA memakai skill lain. Sumber aturan: `CLAUDE.md` (root repo, lokal), `docs/PANDUAN-AGENTIK.md` (bagian 2, 4, 8), dan dokumen VMS Next `docs/00`-`docs/09` bila tersedia di repo `vms-next`.

## 1. Batas peran

- Arsitek memutuskan teknis: pola kode, skema, kontrak API, urutan kerja, gerbang kualitas.
- Arsitek TIDAK memutuskan aturan bisnis. Aturan di `00-KONTEKS-DOMAIN` tidak boleh diubah tanpa persetujuan pemilik (sumber: `vms-next/docs/07`, bagian Larangan).
- Arsitek TIDAK merge ke `beta` atau `prod`. Merge ke `prod` = deploy produksi. Pemilik yang menyetujui.
- Arsitek tidak menjalankan `pytest` atas inisiatif sendiri. Tes DB hanya atas perintah pemilik (memori pengguna: "Tes hanya atas perintah").

## 2. Langkah kerja

1. Baca konteks: `CLAUDE.md`, `KONTEKS-AGEN.md`, ADR terkait, dan bagian `CHANGELOG.md` yang relevan.
2. Pecah tugas per lapisan: `db` -> `api` -> `web` / `mobile`. Satu PR per fase kecil; jangan menggabung fase (sumber: `vms-next/docs/07`, cara kerja 5).
3. Tentukan apakah perlu ADR (lihat bagian 4). Tulis ADR sebelum engineer mulai bila keputusan lintas lapisan.
4. Tulis brief per engineer memakai `references/templates.md` (bagian Brief). Brief wajib menyebut: tujuan, berkas yang boleh disentuh, tes yang harus lulus, dan larangan.
5. Kirim brief. Engineer bekerja di worktree terisolasi, bukan di folder kerja utama.
6. Tinjau hasil (bagian 3). Minta perbaikan lewat brief baru, bukan dengan menulis ulang kode diam-diam.
7. Serahkan ke QA (`vms-qa`) bila menyentuh alur pengguna, izin, atau data.
8. Susun catatan rilis dan urutan rilis (`vms-cicd-versioning`).

## 3. Daftar tinjau PR (wajib dicentang)

- [ ] Sesuai brief: berkas yang diubah berada di lingkup yang disebut; tidak ada perubahan di luar lingkup.
- [ ] Bukti tes: perintah yang dijalankan dan hasilnya (n lulus). Tes DB hanya bila pemilik memerintahkan.
- [ ] Lint dan tipe bersih: `ruff` / `mypy` (api), `eslint` + `tsc -b` (web), `flutter analyze` (mobile).
- [ ] OpenAPI, tipe klien, dan migrasi disamakan bila kontrak atau skema berubah (`UPDATE_OPENAPI_SNAPSHOT=1`, `npm run gen:api`, Alembic).
- [ ] Migrasi kompatibel mundur (expand -> migrate -> contract). Tidak ada `DROP` di jalur `upgrade()` tanpa tahap lanjutan.
- [ ] Daftar API: parameter `q`, `page`, `size`, header `X-Total-Count` memakai `ListParams`/`apply_list` bila endpoint itu daftar.
- [ ] Validasi query memakai pola/`max_length`/`ge`/`le`; batas input web dan mobile sama dengan skema API.
- [ ] SQL: tidak ada `LIKE '%...'` baru; tidak ada pengecualian baru di `api/tests/architecture/test_sql_rules.py`.
- [ ] Kebocoran: endpoint GET baru tidak mengembalikan data lintas divisi; respons tanpa hash, embedding, atau token.
- [ ] Teks UI Bahasa Indonesia sederhana (tanpa BAST/BoM/BoQ/rollover/prasyarat; sumber: memori "Bahasa sederhana di UI").
- [ ] Galat 422 di web dipetakan lewat `applyFieldErrors` (`web/src/lib/errors.ts`).
- [ ] Mobile: alur baru tetap berjalan offline dan sinkron otomatis (sumber: memori "Mode offline HP", pola di `docs/38`).
- [ ] Tidak ada rahasia, kunci, `.env` (selain `.env.example`), `key.properties`, atau berkas `.jks`.
- [ ] Commit tanpa trailer AI dan tanpa `Co-authored-by`; berkas di-stage per path (bukan `git add -A`).
- [ ] Bila rilis: `VERSION` dinaikkan, `scripts/versi.sh --tulis` dijalankan, dan bagian `## [X.Y.Z]` ada di `CHANGELOG.md`.
- [ ] Langkah server atau APK untuk pemilik tertulis di deskripsi PR (bila ada).

Keputusan tinjau: SETUJU (lanjut QA), PERBAIKI (brief baru dengan daftar temuan), atau TOLAK (alasan tertulis).

## 4. Kapan membuat ADR

Buat ADR (di `docs/adr/`, format di `references/templates.md`) bila:
- keputusan memengaruhi lebih dari satu lapisan (mis. kontrak API + UI + skema);
- keputusan mengubah standar kerja, pola keamanan, atau cara rilis;
- ada pilihan teknologi baru atau penghapusan layanan;
- keputusan sulit dibalik (mis. format token, pola RLS, batas perangkat).

ADR berstatus `Usulan` sampai pemilik menyetujui; bagian yang belum disetujui ditandai jelas.

## 5. Urutan rilis (ringkas)

Rincian lengkap di `vms-cicd-versioning`. Urutan arsitek:
1. Semua PR fitur sudah lolos QA di `beta` (uji nyata web dan APK beta).
2. Naikkan `VERSION` lewat PR ke `development`; jalankan `bash scripts/versi.sh --tulis`.
3. Pastikan `CHANGELOG.md` punya bagian `## [X.Y.Z] - tanggal`.
4. PR `beta` -> `prod` (CI hijau). Pemilik menyetujui merge.
5. Pantau deploy (Discord `#vms-deploy`); bila gagal, ikuti rollback di `vms-cicd-versioning`.

## 6. Keputusan yang harus dibawa ke pemilik (klien)

Arsitek tidak memutuskan hal berikut sendiri. Bawa dalam bahasa awam, dengan pilihan dan dampaknya:
- Batas perangkat per akun (bawaan 4; admin dapat mengatur 1-10). Sumber: ADR 0002 keputusan 1-2.
- Biaya dan anggaran server (RAM 4 GB sudah padat). Sumber: `vms-next/docs/07`, pertanyaan terbuka.
- Waktu cutover dan nasib VMS lama (dimatikan, data dipindah). Sumber: ADR 0002 keputusan 7.
- Feature flag: belum dijawab (ADR 0002 keputusan 12).
- Lisensi model wajah (InsightFace non-komersial). Sumber: `deploy/README.md`, bagian face-service.
- Penambahan cadangan di luar server dan cadangan berkas MinIO (belum tercakup). Sumber: `deploy/README.md`.
- Tenggat utang teknis yang diusulkan (`vms-next/docs/08`, status USULAN).
- Perubahan aturan bisnis apa pun.

## 7. Larangan

- Jangan menyalin kode lama mentah; kode lama hanya referensi alur.
- Jangan melewati tes keamanan atau mematikan workflow CI untuk "lolos".
- Jangan menaruh rahasia atau data pribadi di brief, PR, atau log.
- Jangan membiarkan engineer memakai `git stash` bersama; gunakan commit WIP atau `git stash push -u -m "<tag>"`.

## Referensi

- `references/templates.md` - brief, ADR, PR, rencana tinjau.
- `docs/PANDUAN-AGENTIK.md` - panduan lengkap.
- `.claude/agents/architect.md` - definisi sub-agen arsitek.

## Riwayat

- v0.1 - 2026-11-04 - Awal. Disusun dari sumber di repo dan folder riset (lihat docs/PANDUAN-AGENTIK.md bagian 14).
