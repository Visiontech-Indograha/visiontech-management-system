# 14 · Daftar Pustaka dan Teknologi

**Status: dikunci.** Daftar ini adalah keputusan. Pustaka di luar daftar ini **tidak
ditambahkan tanpa alasan tertulis** (lihat §6).

Versi sengaja tidak dipatok di dokumen ini — dipatok di `pyproject.toml`, `package.json`,
dan `pubspec.yaml` saat fase 0, lalu dikunci dengan lockfile.

---

## 1. Backend (`api/`) — Python 3.12

### Inti
| Pustaka | Untuk apa |
|---|---|
| `fastapi` | Kerangka web |
| `uvicorn[standard]` | Server ASGI |
| `sqlmodel` | ORM + skema |
| `sqlalchemy[asyncio]` | Mesin di balik SQLModel |
| `asyncpg` | Driver PostgreSQL |
| `alembic` | Migrasi (mode async) |
| `pydantic`, `pydantic-settings` | Validasi & konfigurasi |

### Basis data khusus
| Pustaka | Untuk apa |
|---|---|
| `geoalchemy2` | Tipe PostGIS (`geography`) |
| `pgvector` | Tipe `vector(512)` |
| `shapely` | Pengolahan geometri di sisi Python bila perlu |

### Keamanan
| Pustaka | Untuk apa |
|---|---|
| `argon2-cffi` | Hash kata sandi (argon2id) |
| `pyjwt[crypto]` | JWT EdDSA |
| `cryptography` | Ed25519, hash, operasi kunci |
| `python-multipart` | Unggahan multipart |
| `slowapi` | Pembatasan laju |

### Berkas & kompresi gambar
| Pustaka | Untuk apa |
|---|---|
| `minio` | Klien MinIO |
| `pillow` | Kompresi dan pemrosesan gambar |
| `pillow-heif` | Membaca HEIC dari iPhone |

Tidak ada pustaka kompresi PDF atau Office: dokumen disimpan apa adanya (A-20, dokumen 13 §5).

### Laporan
| Pustaka | Untuk apa |
|---|---|
| `jinja2` | Templat dokumen |
| `weasyprint` | HTML → PDF |
| `qrcode[pil]` | Membuat QR tanda tangan |

### Utilitas
| Pustaka | Untuk apa |
|---|---|
| `httpx` | Klien HTTP (ke face-service, KMS) |
| `structlog` | Log JSON |
| `typer` | CLI (`seed`, `create-admin`, `cleanup`) |
| `tenacity` | Coba ulang dengan jeda bertambah |
| `rfc8785` *(atau implementasi JCS setara)* | Kanonikalisasi JSON untuk hash tanda tangan |

### Pengembangan & uji
| Pustaka | Untuk apa |
|---|---|
| `pytest`, `pytest-asyncio`, `pytest-cov` | Pengujian |
| `pytest-postgresql` | PostgreSQL nyata untuk uji |
| `factory-boy`, `faker` | Data uji |
| `ruff` | Lint + format |
| `mypy` | Pemeriksaan tipe |
| `pre-commit` | Gerbang sebelum commit |

---

## 2. Web (`web/`) — React 19 + TypeScript

### Inti
| Paket | Untuk apa |
|---|---|
| `react`, `react-dom` | Kerangka |
| `typescript` | Mode strict |
| `vite` | Build |
| `react-router-dom` | Rute |

### UI
| Paket | Untuk apa |
|---|---|
| **shadcn/ui** | Pustaka komponen — **disalin ke repo**, bukan dependensi |
| `tailwindcss`, `postcss`, `autoprefixer` | Gaya |
| `@radix-ui/*` | Dasar shadcn (ikut otomatis) |
| `class-variance-authority` | Varian komponen |
| `clsx`, `tailwind-merge` | Penggabungan kelas |
| `lucide-react` | Ikon |
| `sonner` | Notifikasi (pengganti `alert()`) |
| `tailwindcss-animate` | Animasi shadcn |

### Data & state
| Paket | Untuk apa |
|---|---|
| `@tanstack/react-query` | State server |
| `zustand` | State klien |
| `axios` | Klien HTTP + interceptor refresh |
| `@tanstack/react-table` | Tabel data |

### Form
| Paket | Untuk apa |
|---|---|
| `react-hook-form` | Form |
| `zod` | Skema validasi |
| `@hookform/resolvers` | Penghubung keduanya |

### Utilitas
| Paket | Untuk apa |
|---|---|
| `date-fns`, `date-fns-tz` | Tanggal, lokal `id`, zona `Asia/Jakarta` |
| `recharts` | Grafik (hanya bila perlu) |

### Pengembangan & uji
| Paket | Untuk apa |
|---|---|
| `vitest`, `@testing-library/react`, `@testing-library/user-event` | Uji komponen |
| `@playwright/test` | Uji ujung-ke-ujung |
| `eslint`, `typescript-eslint`, `eslint-plugin-react-hooks` | Lint |
| `eslint-plugin-boundaries` | Menegakkan arah ketergantungan folder (dokumen 11 §3) |
| `prettier`, `prettier-plugin-tailwindcss` | Format |
| `openapi-typescript` | Membangkitkan tipe API |

---

## 3. Mobile (`mobile/`) — Flutter

### Inti
| Paket | Untuk apa |
|---|---|
| `flutter` | Kerangka (channel stable) |
| `shadcn_ui` | Pustaka komponen |
| `go_router` | Navigasi |
| `flutter_riverpod` | State |

### Data
| Paket | Untuk apa |
|---|---|
| `dio` | HTTP + interceptor |
| `drift`, `sqlite3_flutter_libs` | Basis data lokal (antrean luring) |
| `flutter_secure_storage` | Token |
| `shared_preferences` | Preferensi ringan |
| `freezed`, `json_serializable`, `build_runner` | Model & serialisasi |

### Perangkat
| Paket | Untuk apa |
|---|---|
| `camera`, `image_picker` | Swafoto |
| `geolocator` | Lokasi |
| `permission_handler` | Izin |
| `flutter_image_compress` | Kompresi sebelum unggah |
| `connectivity_plus` | Status jaringan |
| `device_info_plus`, `package_info_plus` | Identitas perangkat & versi aplikasi |
| `path_provider` | Folder lokal |

### Uji
| Paket | Untuk apa |
|---|---|
| `flutter_test`, `integration_test` | Uji |
| `mocktail` | Tiruan |
| `flutter_lints` | Lint |

---

## 4. Layanan wajah (`face-service/`) — Python 3.12 *(fase 8)*

| Pustaka | Untuk apa |
|---|---|
| `fastapi`, `uvicorn` | API internal |
| `insightface` | Model ArcFace, embedding 512 dimensi |
| `onnxruntime` | Menjalankan model (CPU) |
| `opencv-python-headless` | Pengolahan gambar |
| `numpy` | Vektor |
| `pillow` | Baca gambar |

Deteksi keaslian wajah (*liveness*) ditentukan di fase 8 setelah pengujian; kandidat utama
adalah model anti-spoofing pasif yang berjalan di perangkat. Ini satu-satunya keputusan
teknologi yang sengaja ditunda, karena memilihnya tanpa mengujinya di lapangan tidak ada
gunanya.

---

## 5. Infrastruktur

| Komponen | Pilihan |
|---|---|
| Basis data | PostgreSQL 18 + PostGIS 3.6 + pgvector |
| Penyimpanan objek | MinIO |
| Web server / proxy | Caddy |
| Jaringan admin | **Tailscale** (sudah terpasang di server) |
| Container | Docker + Docker Compose |
| CI | GitHub Actions |
| Pemantauan | Uptime Kuma (kesehatan) + log JSON |
| Cadangan | `pg_dump` + WAL archiving + `mc mirror` |

---

## 6. Aturan menambah pustaka baru

Selama pembangunan pasti muncul kebutuhan yang tidak ada di daftar ini. Aturannya:

**Boleh langsung ditambahkan tanpa bertanya** bila memenuhi **semua** syarat:
1. Menyelesaikan masalah nyata yang sedang dikerjakan, bukan masalah yang dibayangkan.
2. Dirawat aktif (rilis dalam 12 bulan terakhir).
3. Lisensinya mengizinkan penggunaan komersial (MIT, Apache-2.0, BSD).
4. Tidak menduplikasi pustaka yang sudah ada di daftar.
5. Ukurannya wajar — tidak menarik 2 MB hanya untuk satu fungsi kecil.

**Wajib dicatat di dokumen 10 Bagian C** bila:
- Menggantikan pustaka yang sudah ada di daftar ini.
- Menyentuh keamanan (kriptografi, autentikasi, penyimpanan rahasia).
- Menambah layanan atau proses baru yang harus dijalankan di server.

**Tidak boleh ditambahkan sama sekali:**
- Pustaka UI kedua di web atau di mobile. Satu pustaka komponen, itu saja. Inilah yang
  membuat `vti_frontend` sulit dirawat.
- Pengelola state kedua di sisi yang sama.
- ORM atau query builder kedua.
- Pustaka yang meminta mengirim data ke layanan pihak ketiga tanpa keputusan tertulis.

---

## 7. Pemeliharaan

- Lockfile (`uv.lock` / `package-lock.json` / `pubspec.lock`) **selalu** ikut di-commit.
- Pembaruan keamanan diperiksa bulanan; pembaruan besar ditinjau per kuartal.
- `pip-audit` dan `npm audit` berjalan di CI; kerentanan tingkat tinggi menggagalkan build.
- Pustaka yang berhenti dirawat masuk daftar penggantian sebelum menjadi masalah, bukan
  sesudahnya.
