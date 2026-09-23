---
name: Strict Git Flow
description: Mencegah agen AI melakukan komit langsung ke branch production.
---

# Aturan Pengelolaan Git (Git Flow)

## Instruksi Wajib untuk AI:
1. **Dilarang keras** melakukan `git commit` atau `git push` secara langsung ke branch `prod` atau `main`.
2. Jika Anda perlu membuat perubahan kode atau fitur baru, Anda **wajib** berpindah ke branch `development` atau membuat branch fitur baru dari `development` (contoh: `feature/nama-fitur`).
3. Selalu periksa branch aktif menggunakan `git branch` sebelum melakukan modifikasi file besar atau `git commit`.
4. Jika posisi saat ini berada di `prod`, peringatkan Pengguna dan otomatis jalankan `git checkout development` sebelum melanjutkan tugas yang mengubah kode.
5. Jika tugas mengharuskan penerapan ke production, berikan instruksi kepada Pengguna untuk membuat *Pull Request* (PR) di GitHub, jangan pernah mem-bypass PR.

## Wajib Commit dan Push Setiap Tugas Selesai

6. **Setiap satu tugas kecil selesai = satu commit.** Tugas dianggap selesai hanya bila uji
   yang relevan hijau dan `CHANGELOG.md` sudah diperbarui (lihat `changelog.md`). Jangan
   menumpuk beberapa tugas dalam satu commit, dan jangan mengakhiri sesi dengan perubahan
   yang belum di-commit.
7. **Setelah commit, wajib push** ke branch yang sama di `origin`
   (`git push origin development` atau `git push -u origin feature/<nama>`). Pekerjaan yang
   hanya ada di komputer lokal dianggap belum selesai.
8. **Sebelum push, wajib periksa rahasia** pada semua commit yang akan dikirim:
   ```bash
   git log origin/<branch>..<branch> -p | grep -nEi "password|secret|webhooks/[0-9]|PRIVATE KEY|postgres(ql)?(\+asyncpg)?://[^:]+:[^@]+@"
   ```
   (atau `gitleaks detect` bila terpasang). Bila ada kata sandi, token, URL webhook, atau
   kunci asli: **jangan push.** Pindahkan nilainya ke `.env` (tidak masuk Git), ganti di kode
   dengan pembacaan dari `core/config.py` tanpa nilai bawaan rahasia, dan laporkan ke
   Pengguna — rahasia yang sudah masuk riwayat commit harus diganti (rotasi) dan riwayatnya
   dibersihkan, bukan sekadar dihapus di commit baru.
9. Push hanya ke `development` atau `feature/*`. **Dilarang** `git push --force` ke branch
   bersama, dan dilarang push ke `prod`/`main` (aturan 1).
10. Bila push gagal (konflik, jaringan, izin), jangan dipaksa: laporkan galatnya ke
    Pengguna dan biarkan commit tetap aman di lokal.

Aturan ini bersifat mutlak untuk mencegah gangguan pada stabilitas sistem *production*.
