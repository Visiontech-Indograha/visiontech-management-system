---
name: changelog
description: >
  Aturan wajib bagi semua AI dan developer untuk selalu memperbarui CHANGELOG.md
  sebelum melakukan commit pada proyek VMS. Tidak ada pengecualian.
---

# Aturan CHANGELOG — Wajib untuk Semua AI

> **Prioritas: TERTINGGI.** Melupakan CHANGELOG sama dengan menyembunyikan pekerjaan.  
> Tidak ada commit yang boleh masuk tanpa entri CHANGELOG yang sesuai.

## 1. Kapan Harus Menulis

Tulis ke `CHANGELOG.md` **sebelum menjalankan `git commit`** setiap kali:

| Situasi | Wajib? |
|---|---|
| Menambah endpoint / fitur baru | ✅ Ya |
| Memperbaiki bug | ✅ Ya |
| Mengubah skema database | ✅ Ya |
| Mengubah aturan AI (`.agy/rules/`) | ✅ Ya |
| Mengubah konfigurasi / infra / CI | ✅ Ya |
| Menambah / mengubah token desain | ✅ Ya |
| Refactor internal tanpa perubahan perilaku | ⚠️ Singkat saja |
| Hanya memperbarui komentar / typo | ❌ Boleh skip |

## 2. Lokasi

File: `CHANGELOG.md` di root proyek (`vms/CHANGELOG.md`).  
Selalu edit file ini, **jangan buat file changelog baru**.

## 3. Struktur Entri

Semua perubahan baru masuk di bawah bagian `## [Unreleased]`.  
Gunakan sub-judul berdasarkan jenis perubahan:

```markdown
## [Unreleased]

### ✨ Ditambahkan
- Deskripsi fitur baru. Sebutkan endpoint, file, atau komponen yang terlibat.

### 🔧 Diperbaiki
- Deskripsi bug yang diperbaiki. Sebutkan penyebab dan solusinya secara singkat.

### ⚠️ Diubah
- Deskripsi perubahan yang memengaruhi perilaku yang sudah ada (breaking atau non-breaking).

### 🗑️ Dihapus
- Deskripsi fitur / endpoint / file yang dihapus dan alasannya.

### 🏗️ Infrastruktur
- Perubahan pada CI/CD, Docker, aturan AI, konfigurasi build, dll.
```

## 4. Format Penulisan

**Gunakan bahasa Indonesia.** Semua entri ditulis dalam Bahasa Indonesia.

**Format satu baris:**
```
- `METODE /path` — penjelasan singkat apa yang dilakukan. Sebutkan aturan bisnis kunci bila ada.
```

**Contoh benar:**
```markdown
### ✨ Ditambahkan
- `POST /attendance/check-in` — check-in dengan validasi jarak PostGIS; GPS palsu (Simulasi) 
  dan wajah tidak cocok (`NO_MATCH`) langsung menjadi `NEEDS_REVIEW`, bukan ditolak.
- `VmsTheme.light` di `mobile/lib/core/theme/vms_theme.dart` — tema Material 3 penuh 
  dengan token dari `docs/design/tokens.json`.

### 🔧 Diperbaiki  
- **`plan_transitions.py`**: `issued_by` sekarang diisi `employee_id` (bukan `user_id`) 
  sesuai FK di tabel `vms.plan_document`.
```

**Contoh salah (jangan lakukan ini):**
```markdown
- Update kode    ← tidak informatif
- Fix bug        ← tidak menyebut bug apa
- Added stuff    ← bahasa Inggris, tidak spesifik
```

## 5. Penanda Tanggal

Tambahkan tanggal dan konteks pada setiap kelompok perubahan besar:
```markdown
#### Nama Fitur — Backend (Fase N) — YYYY-MM-DD
```

Tanggal menggunakan format `YYYY-MM-DD` (ISO 8601).

## 6. Saat Rilis Versi

Saat kode naik ke `prod`, ubah `[Unreleased]` menjadi versi bertanggal:
```markdown
## [0.1.0] — 2026-10-15

...isi entri...

## [Unreleased]
*(kosong, siap untuk entri berikutnya)*
```

Versi mengikuti **Semantic Versioning**:
- `MAJOR` — perubahan tidak kompatibel ke belakang (migrasi DB besar, perubahan auth)
- `MINOR` — fitur baru yang kompatibel
- `PATCH` — perbaikan bug saja

## 7. Baris Terakhir

Selalu perbarui baris terakhir file:
```markdown
*File ini diperbarui terakhir: YYYY-MM-DD oleh [Nama AI atau Developer]*
```

## 8. Urutan Kerja AI

Setiap AI **wajib** mengikuti urutan ini:

1. **Kerjakan** perubahan kode.
2. **Tulis entri** di `CHANGELOG.md` (bagian `[Unreleased]`) yang menggambarkan apa yang baru dikerjakan.
3. **Jalankan** `git add CHANGELOG.md` bersamaan dengan file kode yang diubah.
4. **Commit** — pesan commit dan entri changelog harus konsisten.

> ❌ **Dilarang**: commit tanpa memperbarui CHANGELOG.  
> ❌ **Dilarang**: menulis entri setelah commit.  
> ❌ **Dilarang**: menghapus entri changelog lama.  
> ❌ **Dilarang**: menulis `- Update changelog` sebagai entri changelog (rekursif tidak berguna).
