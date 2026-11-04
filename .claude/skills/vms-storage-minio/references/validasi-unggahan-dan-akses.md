# Validasi unggahan dan akses berkas (vms-storage-minio)

Sumber: `api/app/modules/system/controllers/files_controller.py` (diperiksa 2026-11-04), `api/app/modules/system/routes/files_route.py`, `api/app/modules/system/routes/media_stream_route.py`, `api/app/core/security.py`, `api/app/main.py`. Acuan: riset 02 §3.2-3.3 (POST policy AWS SigV4, `content-length-range`, `starts-with`), OWASP API Top 10 2023 (API4 Unrestricted Resource Consumption, API8 Security Misconfiguration; https://api-security.owasp.org/editions/2023/en/0x11-t10/, akses 2026-11-04), `docs/06` (OWASP: batas ukuran dan jenis berkas dengan magic bytes, URL presigned berumur pendek, header keamanan).

## 1. Urutan validasi (sudah ada)

| Langkah | Bukti | Kode status |
|---|---|---|
| Baca dengan batas `MAX_FILE_SIZE + 1` | `files_controller.py:55` | 413 `FILE_TOO_LARGE` (`:58-62`) |
| Berkas kosong | `:63-67` | 400 `FILE_EMPTY` |
| Tipe dari magic bytes | `:69-71` (`filetype.guess`) | 415 `INVALID_FILE_TYPE` bila tidak di allowlist (`:72-75`) |
| Gambar bisa didekode | `:77-87` | 415 untuk HEIC, 422 `IMAGE_CORRUPT` untuk rusak |
| Dedup SHA-256 per pemilik | `:89-99` | Respons "sudah ada", tanpa membocorkan berkas pengguna lain |

Allowlist (`files_controller.py:29-37`): `image/jpeg`, `image/png`, `image/webp`, `image/heic`, `application/pdf`, `application/msword`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`.

Catatan:
- `file.read(MAX_FILE_SIZE + 1)` membaca ke memori. Untuk berkas besar, pertimbangkan unggah bertahap atau POST policy (ADR 0003 C-8, usulan 3-4 hari, setelah validasi dipusatkan).
- `image/heic` masuk allowlist, tetapi dekoder HEIC tidak dipastikan ada (`image.py`). Kode menolak HEIC yang tidak bisa didekode dengan pesan "Format HEIC belum didukung".

## 2. Target: validasi terpusat

Usulan `core/upload_policy.py` (riset 02 C-1). Satu sumber untuk semua endpoint unggah:

```python
# Contoh bentuk (bukan kode final). Angka harus diukur dulu dari kamera HP lapangan.
@dataclass(frozen=True)
class UploadRule:
    nama: str                    # "swafoto_absensi", "foto_titik_survei", "dokumen_karyawan"
    mime_diizinkan: frozenset[str]
    ukuran_maks: int             # byte
    perlu_dekode_gambar: bool

ATURAN = {
    "swafoto_absensi": UploadRule("swafoto_absensi", frozenset({"image/jpeg", "image/png", "image/webp"}), 10 * MB, True),
    "dokumen_karyawan": UploadRule("dokumen_karyawan", frozenset({"application/pdf", "image/jpeg", "image/png"}), 10 * MB, False),
}
```
- Endpoint memanggil `validasi(bytes, ATURAN[...])` sebelum `upload_file`.
- Pesan galat berbahasa Indonesia dengan kode stabil (`FILE_TOO_LARGE`, dst.).
- Batas yang sama dikirim ke web dan mobile (aturan proyek): tampilkan batas di form dan validasi sebelum unggah.
- Riset 02 C-1 mencatat risiko: batas terlalu kecil memblokir foto lapangan. Ukur ukuran foto kamera HP sebelum menetapkan batas.

## 3. Yang harus dihindari

- **Mempercayai `Content-Type` dari klien**. `upload_file(object_name, file_data, content_type)` (`storage.py:65`) menerima `content_type` dari pemanggil. Pastikan pemanggil hanya meneruskan MIME hasil deteksi magic bytes.
- **Nama berkas dari klien** sebagai bagian `storage_key`. Gunakan UUID. Nama asli boleh disimpan di kolom `file_name` untuk tampilan, setelah dibersihkan.
- **Path traversal**: jangan gabungkan path dari input. `media_stream_route.py` memakai `_resolve_file_path` dengan pengecekan folder; pertahankan pola ini.
- **Galat yang membocorkan**: jangan tampilkan `storage_key`, nama bucket, atau pesan MinIO mentah.
- **Ekstensi ganda** (`foto.jpg.exe`): magic bytes menolaknya, tetapi tetap jangan pakai ekstensi untuk keputusan.
- **Gambar dengan skrip** (SVG) tidak diizinkan di allowlist. Tetap pastikan SVG tidak pernah disajikan sebagai `image/svg+xml` untuk berkas pengguna. (`media_stream_route.py:45` menghasilkan SVG placeholder untuk berkas contoh; itu buatan server, aman.)

## 4. Malware dan karantina (Target)

Riset 02 C-2:
1. Tambah layanan ClamAV (daemon `clamd`) di compose dengan batas memori. Ukur RAM dulu, karena database sinyatur bisa ratusan MB.
2. Unggahan masuk ke `quarantine/<uuid>` dan `file_object.scan_status='pending'`.
3. Worker memindai (lewat TCP ke `clamd`), lalu `copy` ke `files/<uuid>` bila bersih (`clean`) atau hapus bila terinfeksi (`infected`).
4. `/files/{id}/url` menolak selain `clean`. Pengguna melihat pesan "berkas sedang diperiksa".
5. Lifecycle `quarantine/` dihapus setelah 1 hari (riset 02 C-5).

Risiko: RAM pada server 4 GB; perlu uji beban.

## 5. Akses: tiket dan URL

Alur sekarang (bukti):
1. Klien memanggil `GET /api/v1/files/{id}/url?variant=thumb|view|full` (`files_route.py:60-66`).
2. Controller memeriksa akses ke berkas itu (`handle_get_file_url`, riset 01 V-17 "URL dibuat hanya setelah otorisasi per berkas").
3. Dikembalikan URL bertiket. Tiket EdDSA, TTL 5 menit (`security.py:125`), jendela cache 1800 detik (`security.py:128`).
4. Browser atau aplikasi mengambil berkas dari `/files/{id}/content` atau sejenis, dengan tiket yang diverifikasi `verify_file_access_ticket` (`security.py:151`).

Aturan:
- **Pemeriksaan akses per berkas**, bukan hanya login. Berkas milik orang lain dijawab 404 (`docs/06`).
- **Tiket terikat** ke `sub` (pengguna), `fid` (berkas), `org`, `var` (varian), dan `aud` (`security.py:131-151`). Tiket untuk berkas lain ditolak.
- **Presigned MinIO** (`storage.py:174`) tidak dipakai rute mana pun. Bila dipakai, batas 15 menit (`docs/06`, ADR 0003 A8).
- **Cache browser**: `private, max-age=1500` (`files_controller.py:28`) untuk berkas pribadi. Jangan ubah ke `public`.

## 6. Header respons berkas

| Header | Nilai | Bukti/Target |
|---|---|---|
| `Cache-Control` berkas pribadi | `private, max-age=1500` atau `no-store` | `files_controller.py:28` |
| `X-Content-Type-Options` | `nosniff` | `files_controller.py:190`, `media_stream_route.py:74` |
| `Content-Disposition` | `inline` atau `attachment` dengan nama aman | `media_stream_route.py:_serve` memakai `content_disposition(...)` |
| `Cache-Control` berkas contoh | `public, max-age=3600` | `media_stream_route.py:74` (hanya berkas contoh) |
| `Content-Security-Policy` | Dari proxy web | `web/Caddyfile:12` (riset 01 T12) |

## 7. Rute `/media/*` (publik, sempit)

- Hanya membaca `api/uploads/<folder rujukan>/` (`media_stream_route.py:1-10`). Tanpa naik folder, tanpa pencarian nama.
- Hanya jenis gambar dan PDF (`PUBLIC_SUFFIXES`).
- Berkas pribadi tidak boleh masuk folder ini. `api/uploads` ikut ke image (`api/Dockerfile:27`). Tambahkan `.dockerignore` dan pisahkan berkas contoh dari berkas pengguna.
- Upload lewat `/media/upload` sudah dihapus (`media_stream_route.py:12`).

## 8. Tes yang diusulkan (jangan dijalankan sebelum diminta)

- `GET /uploads/<apa pun>` → 404 (mount dihapus). Ada di `api/tests/modules/system/test_media_stream.py` pada commit `0c0f98eb` (hotfix). Gabungkan ke beta.
- Unggahan dengan `Content-Type: image/png` tetapi isi PDF → 415 atau tipe PDF yang benar, sesuai allowlist.
- Unggahan 10 MB + 1 byte → 413. Unggahan kosong → 400.
- Gambar terpotong → 422 `IMAGE_CORRUPT`.
- Berkas milik pengguna A, `GET /files/{id}/url` oleh pengguna B → 404.
- Tiket untuk `fid` lain → ditolak.
- Dua unggahan identik dari pemilik sama → respons dedup, satu baris `file_object`.
- Tes memakai bucket uji (`db_guard.py:28-35`), bukan produksi.

## 9. Checklist

- [ ] Ukuran dibaca dengan batas; magic bytes menentukan tipe.
- [ ] Batas per jenis dan pesan galat seragam; batas sama dengan web dan mobile.
- [ ] Nama objek UUID; nama klien tidak dipakai sebagai path.
- [ ] Akses per berkas di `/files/{id}/url`; tiket terikat ke berkas.
- [ ] Tidak ada mount statis; `api/uploads` hanya berkas contoh.
- [ ] Header cache dan `nosniff` sesuai jenis berkas.
- [ ] Karantina malware (bila sudah diaktifkan) dan `scan_status` dicek sebelum akses.
