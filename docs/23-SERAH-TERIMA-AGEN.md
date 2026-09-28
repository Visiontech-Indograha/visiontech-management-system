# 23 · Serah Terima Antaragen (keadaan 2026-09-28)

Baca ini **setelah** `CLAUDE.md` dan `docs/MULAI-DI-SINI.md`. Isinya keadaan terakhir, cara kerja
yang sudah disepakati dengan pemilik, dan pekerjaan yang masih terbuka. **Perbarui berkas ini**
setiap kali Anda menutup sesi dengan perubahan berarti.

## 1. Aturan kerja dari pemilik (wajib)

- Balas pemilik dalam **Bahasa Indonesia**, dengan laporan singkat.
- **Jangan memakai subagen atau Workflow** kecuali diminta, karena kuota token pemilik terbatas.
  Kerjakan sendiri, hemat, dan tanpa polling berulang.
- Setiap permintaan pemilik atau PM **dicatat** di `docs/19-CATATAN-REVISI-PEMILIK.md` (nomor R-xx berikutnya: **R-24**).
- Commit dan push ke `development`.
  - `prod` hanya digabung bila pemilik meminta. Caranya fast-forward:
    `git push origin development:prod`, setelah memastikan `origin/prod` adalah leluhur `development`.
  - Checkout `prod` di laptop gagal karena ada perubahan lokal yang sengaja tidak di-commit, jadi pakai perintah push di atas.
- **Jangan pernah commit**: `.env`, `migrate_baca.py`, `test_db.py`, `docker-compose.yml`, `db/Dockerfile`,
  `.claude/launch.json`. Stage berkas satu per satu, jangan `git add -A`. Jangan pakai `git stash`.
- Pindai rahasia pada diff sebelum push. CHANGELOG harus UTF-8.
- **Jangan menampilkan kredensial di chat.**
  - Kata sandi akun server: `.local_tests/server-logins.txt`.
  - Akun lokal: `.local_tests/real-logins.txt`.
  - Keduanya git-ignored.
  - URL webhook Discord juga tidak boleh dicetak.
- Jangan ubah `prototype/`. Jangan ubah pengaturan perangkat HP.
- Aksi yang merusak atau yang dijalankan di server: minta konfirmasi dan buat backup dulu.
- Prioritas: fitur MVP.

## 2. Lingkungan

| Hal | Nilai |
|---|---|
| Repo | `github.com/Visiontech-Indograha/visiontech-management-system` (pindah dari `consep33t/…` 2026-09-28) |
| Folder kerja | `C:\Users\ageng\visiontech-vms\visiontech-dev\vms` (Windows, Git Bash) |
| Mobile | berkas biasa di repo utama (`mobile/`); repo lama `vti-vms-mobile` **tidak dipakai** |
| Flutter SDK | `/c/src/flutter/bin` (tidak di PATH): `export PATH=/c/src/flutter/bin:$PATH` |
| Uji API | `api/.venv` (Python 3.12) terhadap PostgreSQL nyata; suite penuh ±680 uji, ±40 menit |
| Server | SSH `ageng@100.117.92.14` (Tailscale), folder `~/deploy/vms-mvp` |
| URL produksi (UAT) | `https://visiontech-bar.tail827174.ts.net` (HP harus tersambung Tailscale) |
| Deploy | otomatis ≤ 1 menit setelah commit baru di `prod`; lihat `deploy/README.md` |
| HP uji | adb `0E64810I21100255` |

Membuat APK uji (rilis, ke server):

```bash
cd mobile && export PATH=/c/src/flutter/bin:$PATH
flutter build apk --release --dart-define=API_BASE_URL=https://visiontech-bar.tail827174.ts.net
cp build/app/outputs/flutter-apk/app-release.apk ../.local_tests/VMS-uji-server.apk
```

Yang dibagikan ke penguji adalah APK, bukan `.aab`: file `.aab` hanya untuk Play Store dan tidak bisa dipasang langsung.

## 3. Yang selesai terakhir

| Kode | Isi | Commit |
|---|---|---|
| R-21 | Kartu "Akun kantor" / PM "Segera hadir" di HP; penanda gagal login dan cooldown 15 mnt (HP, web, Direktori HR); perbaikan pesan galat login HP | `276b011e` (sudah di `prod` & server) |
| R-21 | Rencana uji nyata di produksi | `docs/22-RENCANA-UJI-PRODUKSI.md` |
| R-22 | Repo pindah: remote laptop, remote server, `autodeploy.sh` | `cd60871c` (di server) |
| R-22 | `/ready` cek DB; autodeploy lapor ✅ hanya setelah siap pakai 3× berturut-turut; embed Discord rapi | commit R-22 (lihat `git log`) |
| R-23 | Ketua dapat menerima SK terbit di mobile; PM mendapat petunjuk agar ketua membuka mobile | lihat `git log` |

## 4. Terbuka — kerjakan / tanyakan berikutnya

1. **Lanjutkan R-23**: sederhanakan form pembuatan SK, kandidat personel sesuai OM/PM dan bebas bentrok,
   lokasi tunggal, serta alokasi kendaraan saat pembuatan. Penerimaan mobile dan petunjuk PM sudah selesai.
2. **Salin `autodeploy.sh` baru ke server** setelah commit R-22 masuk `prod`. Skrip di server adalah
   salinan dan tidak ikut ter-update. Perintahnya ada di `deploy/README.md` bagian "Memasang
   perubahan skrip". Deploy yang membawa R-22 masih dilaporkan oleh skrip lama; format baru baru
   berlaku mulai deploy berikutnya.
3. **UAT seminggu** mengikuti `docs/22`. Temuan dicatat di tabel Temuan di docs/22, lalu ke docs/19.
   Belum ada skenario yang diuji di HP nyata.
4. Keputusan pemilik yang masih ditunggu:
   - **M1-02**: siapa yang memberi peran global.
   - **RLS R3/R4**: lihat docs/19 bagian "Menunggu keputusan" (Q-xx).
5. Menu PM di HP (R-09) masih "Segera hadir". Desainnya ditunda sampai pemilik memutuskan.
6. Jam server: NTP aktif dan tersinkron (dicek 2026-09-28). `StartedAt` kontainer DB pernah tercatat
   ±2 jam di depan, kemungkinan sisa lonjakan jam sebelum NTP. Pantau saja.

## 5. Cara memverifikasi cepat

- API: `cd api && .venv/Scripts/python -m pytest -q -p no:warnings`, lalu `ruff check`, `mypy app`
- Web: `cd web && npm run -s lint && npm run -s typecheck && npm test`
- Mobile: `flutter analyze && flutter test`
- Server:
  - `ssh ageng@100.117.92.14 'curl -s localhost:8000/ready; tail -5 $(ls -td ~/deploy/vms-mvp/logs/deploy-* | head -1)'`
  - Versi yang berjalan: `docker inspect -f '{{.State.StartedAt}}' vms_api`, bandingkan dengan `git -C ~/deploy/vms-mvp/src log -1`.
