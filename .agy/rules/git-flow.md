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

Aturan ini bersifat mutlak untuk mencegah gangguan pada stabilitas sistem *production*.
