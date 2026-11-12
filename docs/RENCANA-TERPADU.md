# Rencana terpadu (12 Nov 2026)

Satu daftar untuk semua temuan, kekurangan, dan utang teknis. Detail butir: backlog-temuan (57 butir) di arsip sesi, `docs/SERAH-TERIMA-AI.md`, `docs/rencana/` (struktur kode, audit kegunaan). Aturan kerja: `docs/SERAH-TERIMA-AI.md` (aturan 30 detik, merge hanya bila semua cek CI lulus, E2E lewat UI tanpa injeksi, agen memuat skill lewat alat Skill).

## Gelombang 1 (paralel, jalur terpisah)
| Jalur | Isi | Agen |
|---|---|---|
| E1 web | T-1 dropdown PM kosong untuk PM, T-2 tanggal terbalik di Absensi (422 jadi pesan awam), T-3 dialog Alokasikan jelaskan order tak muncul + hapus teks teknis | web-engineer |
| E2 web | Tombol ekspor: pilih PDF/Word/PPTX per jenis laporan, laporan bulanan (setelah #493/#494 merge), label tombol sesuai format | web-engineer |
| E3 mobile | Fase 0 mobile: riverpod_lint + very_good_analysis bertahap, tanpa memindah berkas | general-purpose + vms-mobile |
| E4 api | Selidiki `test_hapus_terjadwal.py` (14 tes gagal di basis tanpa perubahan), akar bukan skip | general-purpose + vms-api |
| E5 qa | E2E di beta (A4-A7, aset, mess, K3, offboarding, peran ganda), hapus data uji | qa |

## Gelombang 2 (setelah G1 merge)
- Absen web pekerja kantor: toleransi akurasi lokasi (+ IP kantor bila ada), petunjuk cahaya, status "menunggu verifikasi HR", retry wajah. Pengukuran FAR/FRR face-service lebih dulu; alignment, multi-bingkai, templat pendaftaran ganda.
- Struktur kode Fase 1 (penyatuan komponen duplikat web), lalu Fase 2-3 mobile (berkas raksasa, repository).
- Penerima eksternal aset (ADR 0003), inspeksi kendaraan, pengingat dokumen kendaraan (6 PR), lampiran lembur/berkas mess.

## Gelombang 3 (utang besar)
- RLS lalu enkripsi face_embedding (nomor migrasi mulai v2_0041; v2_0040 milik K3), persetujuan biometrik wajah + kebijakan privasi (teks hukum dari pemilik), restore modul + UI Arsip, Fase 4-5 struktur, golden mobile via workflow Linux, hapus `pages/projects` yatim, Usability Test 5 orang per peran.

## Menunggu pemilik
Rilis prod 1.8.5 ("prod 1.8.5 ya"), langkah server/sudo (cadangan Windows pobonguar, peran vms_api, cron retensi, VITE_APP_ENV beta), daftar wajah Teknisi1 di HP, teks hukum persetujuan wajah, hapus cabang `golden-update/*`.

## Pembersihan
Worktree agen, DB `kt_*` di vms-test-db, data uji `QA-E2E-`/`QA-E2E2-`/`QA-E2E3-`/`QA-UJI-`, berkas sandi sementara.
