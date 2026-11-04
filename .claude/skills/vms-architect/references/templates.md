# Template arsitek

## Brief ke engineer

```
# Brief: <judul singkat>
Lapisan: web | mobile | api | db | devops
Cabang: feature/<nama> (dari development), worktree terisolasi
Tujuan (1-2 kalimat, bahasa awam): ...
Konteks: ADR <nomor> / bagian docs <nomor> / CHANGELOG <versi>
Berkas yang BOLEH disentuh: ...
Berkas yang TIDAK boleh disentuh: ...
Perilaku yang diharapkan (contoh nyata, bukan abstrak): ...
Tes yang harus lulus (perintah + hasil yang diharapkan):
  - bash scripts/verify.sh web   (atau sesuai lapisan) -> LULUS
  - tes baru: ... (tulis dulu, lalu implementasi)
Tes DB: HANYA bila pemilik memerintahkan. DB uji 127.0.0.1:55432 (vms_test). Jangan 55433.
Larangan: tanpa commit trailer AI; stage per path; tanpa git add -A / stash; tanpa merge ke beta/prod; tanpa rahasia.
Laporan balik: format di .claude/agents/<peran>.md bagian Format laporan.
```

## ADR (Architecture Decision Record)

```
# ADR <nomor>: <judul keputusan>
Status: Usulan | Diterima | Ditolak | Diganti oleh ADR <n>
Tanggal: YYYY-MM-DD
Konteks: masalah dan batasan (server 4 GB, jumlah pengguna, tenggat).
Pilihan yang dipertimbangkan:
  A. ... (kelebihan / kekurangan)
  B. ...
Keputusan: pilihan yang dipakai dan alasannya.
Konsekuensi: yang berubah, biaya, risiko, dan apa yang harus diuji.
Keputusan pemilik: (tanggal + ringkasan jawaban, bila ada)
Sumber: berkas atau tautan yang dirujuk.
```

## Ringkasan tinjau PR (dikirim ke pemilik atau ke engineer)

```
PR: <tautan/nomor> - <judul>
Keputusan: SETUJU | PERBAIKI | TOLAK
Sesuai brief: ya/tidak (selisih: ...)
Bukti tes: <perintah> -> <hasil>
Temuan (urut dampak):
  1. [wajib] ... (berkas:baris)
  2. [saran] ...
Langkah berikut: QA / perbaikan / menunggu keputusan pemilik
```

## Keputusan untuk pemilik (bahasa awam)

```
Keputusan: <satu kalimat>
Pilihan:
  1. <pilihan> - dampak: <biaya / waktu / risiko>
  2. <pilihan> - dampak: ...
Rekomendasi arsitek: <pilihan nomor> karena ...
Yang terjadi bila belum diputuskan: ...
Batas waktu: <tanggal bila ada>
```

## Catatan rilis

```
Versi: X.Y.Z (<MAJOR|MINOR|PATCH>, alasan)
Tanggal:
Ringkasan untuk pengguna (Bahasa Indonesia sederhana):
Perubahan teknis: (PR bernomor)
Langkah untuk pemilik: (mis. pasang APK beta, cek Discord, cadangan)
Risiko dan rollback: (image sebelumnya dipulihkan otomatis bila cek siap gagal)
Versi minimum APK: min_build = ... (WAJIB / tidak)
```
