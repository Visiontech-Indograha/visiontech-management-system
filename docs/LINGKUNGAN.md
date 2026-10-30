# Lingkungan: dev, beta, produksi

| | Dev (PC sendiri) | Beta (server) | Produksi (server) |
|---|---|---|---|
| Tujuan | menulis kode, tes cepat | uji nyata sebelum rilis | pengguna sungguhan |
| DB | `vms-dev-db` (:55433), tes `vms-test-db` (:55432) | `vms_db_beta` | `vms_db_prod` |
| MinIO | `vms-dev-minio` (API :19000, konsol :19001) | `vms_minio_beta` | `vms_minio_prod` |
| Wajah | mati (`FACE_ENROLLMENT_REQUIRED=false`) | profil `wajah`, mati bawaan | selalu hidup |
| Data | seed uji (`scripts/akun-uji-lokal.txt`) | data uji | data nyata |
| Deploy | manual (`api-lokal.sh`, `npm run dev`) | otomatis dari cabang `beta` | otomatis dari cabang `prod` |

Dev **tidak** memakai DB/MinIO server. Semua port dev terikat `127.0.0.1`.

## Mulai dev (sekali, aman diulang)
```bash
bash scripts/dev-up.sh          # DB + MinIO lokal, skema bila kosong, api/.env, migrasi
bash scripts/api-lokal.sh       # API :8010 (reload otomatis)
cd web && npm run dev
```
Akun uji: `cd api && .venv/Scripts/python.exe ../scripts/seed_uji_lokal.py --ya-hapus-semua`.
Menguji wajah: jalankan face-service lokal (`face-service/README.md`), isi `FACE_SERVICE_TOKEN`, lalu `FACE_ENROLLMENT_REQUIRED=true`.
Tanpa face-service (dev): `FACE_FAKE_MODE=true` (hanya `APP_ENV=development`; di lingkungan lain API menolak start).
Pendaftaran menyimpan embedding sintetis dan swafoto apa pun dari karyawan terdaftar cocok (skor 95). Isi akun uji:
`cd api && FACE_FAKE_MODE=true .venv/Scripts/python.exe ../scripts/seed-wajah-dev.py` (menolak bila DB bukan localhost).
Absen tanpa verifikasi wajah (tidak diperiksa, belum terdaftar, layanan mati) bertanda `face_status` dan masuk antrian review.

## Uji di server
Push ke `development` → PR ke `beta` (deploy otomatis; APK beta via `apk.yml`) → uji dari HP → PR `beta` → `prod`.
Face beta: `docker compose --profile wajah up -d face` (matikan lagi setelah selesai). Data produksi tidak masuk beta.
Berkas yang diunggah saat dev ada di MinIO lokal; rekaman DB dev yang merujuk berkas MinIO server tidak akan menemukannya.
