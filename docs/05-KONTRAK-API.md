# 05 · Kontrak API

Ini **rencana permukaan API**, bukan spesifikasi OpenAPI final. Spesifikasi lengkap
dibangkitkan dari kode (FastAPI → `openapi.json`) dan tipe TypeScript dibangkitkan darinya,
supaya web dan server tidak pernah diam-diam berbeda.

Basis: `/api/v1`

---

## 1. Konvensi

| Hal | Aturan |
|---|---|
| Penamaan | Jamak, huruf kecil, tanda hubung: `/work-plans`, `/employee-documents` |
| Identitas | UUID di jalur: `/work-plans/{plan_id}` |
| Aksi bisnis | Sub-sumber daya kata kerja: `POST /work-plans/{id}/publish` |
| Halaman | `?page=1&size=50`, balasan `{items, total, page, size}` |
| Penyaringan | Parameter eksplisit; **tidak** ada filter bebas yang masuk SQL |
| Waktu | ISO-8601 dengan zona: `2026-09-23T08:04:12+07:00` |
| Versi baris | `row_version` wajib dikirim pada setiap pembaruan `work_plan` |
| Idempotensi | Header `Idempotency-Key` atau `client_op_id` pada aksi dari lapangan |

**Kenapa aksi bisnis tidak memakai `PATCH`.** `POST /work-plans/{id}/publish` menyatakan
maksudnya; `PATCH {status: "PUBLISHED"}` menyembunyikan aturan di balik perubahan kolom dan
membuka pintu bagi klien untuk melompati langkah. Seluruh 49 transaksi prototipe dipetakan
menjadi aksi bernama seperti ini.

---

## 2. Format galat

Satu bentuk untuk semua:

```json
{
  "error": {
    "code": "PLAN_NOT_ACCEPTED",
    "message": "Pekerjaan belum diterima ketua tim, jadi belum bisa dimulai.",
    "details": { "plan_id": "...", "status": "PUBLISHED" }
  }
}
```

- `code` untuk program, `message` **untuk manusia dalam Bahasa Indonesia**, `details` untuk
  penelusuran.
- Pesan tidak boleh berupa terjemahan status HTTP. "409 Conflict" tidak menjelaskan apa pun
  kepada ketua tim yang sedang berdiri di lokasi proyek.

| HTTP | Kapan |
|---|---|
| 400 / 422 | Masukan tidak valid |
| 401 | Belum login atau token kedaluwarsa |
| 403 | Login tetapi tidak berwenang |
| 404 | Tidak ada — **juga** dipakai untuk berkas yang tidak boleh dilihat, agar keberadaannya tidak terungkap |
| 409 | Konflik keadaan (versi baris, dokumen terkunci, aset bentrok) |
| 429 | Terlalu sering (login, verifikasi QR) |
| 500 | Galat server; tidak pernah membocorkan jejak tumpukan |

---

## 3. Daftar endpoint

### 3.1 Autentikasi
| Metode | Jalur | Catatan |
|---|---|---|
| POST | `/auth/login` | Balas access token + refresh (web: cookie HttpOnly; mobile: body) |
| POST | `/auth/refresh` | Rotasi; token lama yang dipakai ulang mencabut seluruh rantai |
| POST | `/auth/logout` | Mencabut sesi ini |
| POST | `/auth/logout-all` | Mencabut semua perangkat |
| POST | `/auth/change-password` | Mencabut semua sesi lain |
| GET | `/auth/me` | Profil + peran + daftar izin untuk menyusun menu |

`/auth/me` mengembalikan **daftar izin**, bukan nama peran saja. Web menyusun menunya dari
daftar itu, sehingga tidak ada logika peran yang digandakan di frontend.

### 3.2 Karyawan dan dokumen pribadi
| Metode | Jalur |
|---|---|
| GET/POST | `/employees`, `/employees/{id}` |
| PATCH | `/employees/{id}` · POST `/employees/{id}/promote`, `/offboard`, `/restore` |
| GET/POST | `/employees/{id}/documents` |
| POST | `/employee-documents/{id}/verify` (HR) |
| GET | `/employee-documents/expiring?within=30` |

### 3.3 Pekerjaan (SK)
| Metode | Jalur | Transaksi prototipe |
|---|---|---|
| POST | `/work-plans` | `CREATE_PLAN` |
| PATCH | `/work-plans/{id}` | `EDIT_DRAFT` |
| POST | `/work-plans/{id}/publish` | `PUBLISH` |
| POST | `/work-plans/{id}/accept` | `ACCEPT` |
| POST | `/work-plans/{id}/appeal` | `APPEAL` |
| POST | `/work-plans/{id}/revise` | `REVISE` |
| POST | `/work-plans/{id}/start` | `START` |
| POST | `/work-plans/{id}/cancel` · `/restore` | `CANCEL_PLAN`, `RESTORE_PLAN` |
| POST | `/work-plans/{id}/request-completion` | `REQUEST_COMPLETE` |
| POST | `/work-plans/{id}/approve-completion` | `APPROVE_COMPLETE` |
| GET | `/work-plans/{id}/documents` | daftar SK/revisi/adendum |

### 3.4 Perubahan (perpanjangan & personel)
| Metode | Jalur | Transaksi |
|---|---|---|
| POST | `/work-plans/{id}/changes` | `REQUEST_CHANGE`, `REQUEST_PERSONNEL_CHANGE` |
| POST | `/changes/{id}/approve` · `/reject` | `APPROVE_CHANGE`, `REJECT_CHANGE` |
| POST | `/changes/{id}/accept` | `ACCEPT_CHANGE` (ketua masuk) |
| POST | `/changes/{id}/withdraw` | `WITHDRAW_CHANGE` (PM) |
| GET | `/work-plans/{id}/personnel-conflicts?from=&to=` | penandaan bentrok sebelum mengajukan |

### 3.5 Absensi
| Metode | Jalur |
|---|---|
| POST | `/attendance/check-in` · `/attendance/check-out` |
| GET | `/attendance?plan_id=&employee_id=&from=&to=&status=` |
| POST | `/attendance/{id}/explain` (karyawan) |
| POST | `/attendance/{id}/review` (Finance) |
| GET | `/attendance/export?from=&to=` (CSV untuk Finance) |

### 3.6 Laporan
| Metode | Jalur |
|---|---|
| PUT | `/work-plans/{id}/days/{day_id}` (tugas + teks) |
| POST | `/work-plans/{id}/days/{day_id}/submit` · `/review` |
| PUT/POST | `/work-plans/{id}/weekly/{week}` + `/submit` + `/review` |
| GET | `/work-plans/{id}/final-report` |

### 3.7 Aset
| Metode | Jalur |
|---|---|
| GET | `/assets?kind=&status=&available_from=&available_to=` |
| POST | `/assets/{id}/reserve` · `/release` · `/return` · `/verify-return` · `/check` |

### 3.8 Insiden dan lembur
| Metode | Jalur |
|---|---|
| GET/POST | `/incidents` · POST `/incidents/{id}/resolve` |
| GET/POST | `/overtime` · POST `/overtime/{id}/review` |

Keduanya **wajib** tersaring unit bisnis pengguna di sisi server.

### 3.9 Tanda tangan dan verifikasi
| Metode | Jalur | Akses |
|---|---|---|
| POST | `/documents/{id}/sign` | PM/HR berwenang |
| POST | `/signatures/{id}/revoke` | dengan alasan, tercatat |
| GET | `/verify/{token}` | **publik**, tanpa login, dibatasi lajunya |
| GET | `/documents/{id}/pdf` | mengembalikan PDF bertanda tangan |

### 3.10 Wajah *(fase 8)*
| Metode | Jalur |
|---|---|
| POST | `/biometric-consents` (HR mencatat) · DELETE untuk menarik |
| POST | `/employees/{id}/face-enrollments` |
| POST | `/attendance/check-in` dengan `face_image` — tidak ada endpoint pencocokan terpisah |

Tidak ada endpoint publik "cocokkan wajah ini". Pencocokan hanya terjadi di dalam alur
absensi, dengan karyawan yang sudah mengaku identitasnya (1:1), bukan pencarian 1:N bebas.

### 3.11 Berkas
| Metode | Jalur |
|---|---|
| POST | `/files` (multipart; divalidasi & di-*re-encode*) |
| GET | `/files/{id}` → 302 ke URL bertanda tangan ≤ 5 menit |

### 3.12 Sinkronisasi luring
| Metode | Jalur |
|---|---|
| POST | `/sync/operations` (batch, tiap item punya `client_op_id`) |
| GET | `/sync/status?since=` |

### 3.13 Pemantauan (OPS) dan audit
| Metode | Jalur |
|---|---|
| GET | `/timeline?from=&to=` — **dikelompokkan per pekerjaan** |
| GET | `/recaps/overtime` · `/recaps/attendance` |
| GET | `/audit-events?entity=&from=&to=` |

---

## 4. Autentikasi pada permintaan

```
Authorization: Bearer <access token EdDSA>
```

Isi klaim: `sub`, `org`, `roles`, `sid`, `jti`, `iat`, `exp`, `aud`.
`sub` dan `org` disetel ke `app.user_id` / `app.organization_id` di setiap transaksi.

**Access token tidak boleh memuat daftar izin yang panjang.** Peran bisa dicabut di tengah
umur token; izin diperiksa dari basis data pada setiap permintaan. Token hanya membawa
identitas.

---

## 5. Pembatasan laju

| Endpoint | Batas | Alasan |
|---|---|---|
| `/auth/login` | 5 gagal / 15 menit per (login + IP) | Mencegah tebak kata sandi |
| `/verify/{token}` | 30 / menit per IP | Halaman publik; mencegah penyisiran token |
| `/files` (unggah) | 60 / menit per pengguna | Mencegah banjir dari perangkat bermasalah |
| `/sync/operations` | 10 batch / menit per perangkat | |

---

## 6. Yang diuji sebagai kontrak

1. **Matriks RBAC otomatis**: setiap endpoint × setiap peran → status yang diharapkan.
   Endpoint baru tanpa baris di matriks membuat CI gagal. Ini penangkal paling efektif untuk
   kebocoran otorisasi, dan sistem ini punya 7 peran — terlalu banyak untuk diperiksa manual.
2. **Kesesuaian tipe**: `openapi.json` dibangkitkan tiap build; bila tipe frontend tidak lagi
   cocok, CI gagal.
3. **Galat berbahasa manusia**: uji memastikan tidak ada `message` yang berisi jejak tumpukan,
   nama tabel, atau teks bahasa Inggris mentah.
