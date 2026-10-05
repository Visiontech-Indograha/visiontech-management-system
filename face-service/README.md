# face-service

Layanan **inferensi** wajah untuk VMS (docs/06 P8-1). Gambar masuk, **embedding 512-d** keluar. Tidak ada basis data,
tidak ada penyimpanan gambar, tidak ada CORS web: hanya API VMS yang memanggilnya lewat jaringan internal.

| | |
|---|---|
| Model | InsightFace paket `buffalo_s`: detektor `det_500m` + pengenal `w600k_mbf` (MobileFaceNet 512-d) |
| Kenapa bukan `buffalo_l` | HP memakai model pengenal yang **sama** (`w600k_mbf`) untuk mencocokkan saat luring; satu kolom `face_enrollment.embedding` tidak boleh memuat dua model (`db/05_face.sql`). Model ini juga muat di server 2 CPU / 4 GB. |
| Endpoint | `GET /health`, `POST /embed` (multipart `file`, header `X-Face-Token`) |
| Respons `/embed` | `faces` (jumlah wajah), `embedding` (hanya bila tepat 1 wajah), `quality` 0..1, `detection_score`, `model_name`, `model_version` |

## Lisensi model (PENTING)
Paket pralatih InsightFace berlisensi **riset non-komersial**. Untuk produksi perusahaan diperlukan lisensi komersial
dari InsightFace atau model lain yang berlisensi memadai. Keputusan ini ada pada pemilik produk; sampai itu jelas, gunakan
hanya untuk pengembangan, uji, dan kalibrasi.

## Konfigurasi
| Variabel | Arti |
|---|---|
| `FACE_SERVICE_TOKEN` | **Wajib.** Rahasia bersama dengan API (`FACE_SERVICE_TOKEN` di `api.env`). Tidak ada nilai bawaan. |
| `FACE_MODEL_PACK` | Paket InsightFace, bawaan `buffalo_s` |
| `INSIGHTFACE_ROOT` | Folder model (di Docker: `/models`, sudah dibakukan ke citra) |
| `FACE_MAX_CONCURRENCY` | Inferensi serentak maksimum, bawaan 2 |

## Menjalankan lokal
```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # Windows; Linux: .venv/bin/pip
FACE_SERVICE_TOKEN=rahasia-uji uvicorn main:app --port 8001
```
Model terunduh otomatis ke `~/.insightface` pada pemakaian pertama (124 MB).

## Docker / server
```bash
docker build -t vms-face:1 face-service
```
Potongan `compose.yml` (jaringan internal saja, **tanpa `ports:`**, batas memori):
```yaml
  face:
    image: vms-face:1
    restart: unless-stopped
    env_file: face.env            # berisi FACE_SERVICE_TOKEN=... (jangan di Git)
    mem_limit: 1g
    networks: [default]           # satu jaringan dengan `api`; API memanggil http://face:8001
```
API memakai `FACE_SERVICE_URL=http://face:8001` dan `FACE_SERVICE_TOKEN` yang sama.

## Bila layanan mati
Absensi tetap berjalan: API mencatat hasil `SKIPPED` dan memeriksa ulang saat layanan pulih (`reverify`). Wajah tidak
pernah menjadi satu-satunya penentu absen (docs/08 §6).
