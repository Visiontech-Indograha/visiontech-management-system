# Peta port dan penamaan Docker

Lihat keadaan nyata kapan saja: `bash deploy/status-layanan.sh` (lingkungan, layanan, commit, port host→dalam, kesehatan).
Citra membawa label: `vms.layanan`, `vms.lingkungan`, `vms.port-dalam`, `org.opencontainers.image.revision`.

## Nama (sudah konsisten)
- Kontainer: `vms_<layanan>` (produksi), `vms_beta_<layanan>` (beta), `vms_<layanan>_test` (uji), `vms-dev-<layanan>` (PC dev).
- Citra: `vms-mvp-<layanan>` (produksi), `vms-beta-<layanan>` (beta). Tag `rollback` = versi sebelumnya.

## Port sekarang (host → dalam kontainer) dan keanehan
| Layanan | Produksi | Beta | Uji | Dev (PC) | Catatan |
|---|---|---|---|---|---|
| API | 8000→8000 | 8001→8000 | – | 8010 | **8001 di beta = API, tetapi 8001 juga port dalam face** → ambigu |
| Web | 8080→80 | 8081→80 | – | 5173 | |
| Face | (tanpa port host) 8001 | 8001 | – | 8001 (opsional) | port dalam sama untuk semua |
| DB | 5433→5432 | 5435→5432 (lokal) | 5434→5432 | 55433 / 55432 | sebagian terbuka ke LAN |
| MinIO | 9000, 9001 | 9002, 9003 (lokal) | – | 19000, 19001 | |

Jalur publik: Cloudflare (`portal.visiontechindo.com`) dan Tailscale Funnel (`:10000` → beta API `127.0.0.1:8001`,
`:8443`) menunjuk ke port di atas. **Mengubah angka port produksi/beta harus bersamaan dengan memperbarui target tunnel itu.**

## Usulan penomoran (diterapkan bertahap, bukan sekaligus)
Pola: ribuan/ratusan menandai lingkungan, dua digit terakhir menandai layanan.

| Layanan | Produksi | Beta | Uji | Dev |
|---|---|---|---|---|
| Web | 8080 | 8180 | 8280 | 5173 |
| API | 8010 | 8110 | 8210 | 8010 |
| DB | 5410 | 5420 | 5430 | 55433 |
| MinIO API | 9010 | 9020 | 9030 | 19000 |

Aturan: semua port selain Web **terikat `127.0.0.1`** (akses luar lewat web/proxy atau Tailscale), jadi angkanya tidak
perlu dihafal pengguna. Urutan penerapan: (1) ikat ke `127.0.0.1` dulu, (2) setelah itu ganti angka satu lingkungan
(beta dulu) bersama target tunnel, (3) produksi terakhir pada jam sepi.
