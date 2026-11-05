# Transaksi, locking, dan idempotensi (API VMS)

Sumber: PDF bagian 3.3 (baris 231-279), bagian 4.4 (baris 414-493), bagian 11.1 (baris 1523-1553). Target: `vms-next/docs/01` (Database), `docs/06` (Idempotensi), ADR 0001 keputusan 7. Bukti kode: worktree `origin/beta`.

## 1. Batas transaksi

- **Service memegang batas transaksi** (commit/rollback). Repository hanya SQL dan tidak commit. Ini sudah berlaku: tidak ada `.commit()` di folder `repositories` (riset 01 T9).
- Satu request = satu transaksi kecuali ada alasan. Jangan commit di tengah jalur yang bisa gagal sebagian, kecuali memakai SAVEPOINT yang disengaja (contoh: sinkron offline per operasi).
- Efek samping ke luar (notifikasi, file, panggilan HTTP) dilakukan **setelah** commit. Contoh: `flush_events(db)` dipanggil setelah `await db.commit()` (`api/app/database/session.py`, blok request context).

## 2. Isolasi

- PostgreSQL memakai READ COMMITTED secara bawaan (PDF 3.3 tabel isolasi). Cukup untuk sebagian besar kasus jika kondisi ditulis di UPDATE, bukan dibaca dulu lalu ditulis.
- REPEATABLE READ atau SERIALIZABLE hanya bila ada alasan terukur; SERIALIZABLE wajib siap retry.

## 3. Pola yang dipakai (bukti)

### 3.1 Pessimistic lock (SELECT ... FOR UPDATE)
Sudah dipakai di sekitar 12 titik:
- `asset_repository.py:292` (serah terima aset, komentar "dua serah terima bersamaan tidak lolos").
- `auth_session_repository.py:175` (`FOR UPDATE OF s`, rotasi refresh token).
- `plan_item_repository.py:69` (rollover, komentar "dua keputusan rollover bersamaan tidak lolos").
- `leave_repository.py:146`, `overtime_service.py:39`, `offboarding_repository.py:49,152`, `employee_repository.py:67`.

Pakai `FOR UPDATE` bila transisi bergantung pada status yang dibaca dan ada logika di antara baca dan tulis.

### 3.2 Compare-and-set (kondisi pada UPDATE)
Lebih ringan dan cukup untuk transisi status sederhana:
```sql
UPDATE work_plan_daily
SET status = :new_status, update_at = NOW()
WHERE daily_plan_id = CAST(:id AS uuid)
  AND status = ANY(:allowed)
  AND delete_at IS NULL
RETURNING daily_plan_id;
```
- `rowcount` 0 → 409 "status sudah berubah, muat ulang". Di bulk approve, 409 dihitung "dilewati", bukan galat (riset F-12).
- Sudah memakai pola ini: `daily_plan_repository.set_status` (`allowed=`), `work_completion_core_repository.update_status` (`expected=`), `mess_repository.decide` dan `set_status`, `work_order_repository.apply_survey_to_items` dan `submit_survey`. Hasil `bool` dicek di service, lalu `AppError(..., status=409)`.

Contoh untuk `mypy --strict` (`api/mypy.ini`), sesuai pola repository VMS:
```python
async def set_status(
    self, plan_id: UUID | str, new_status: str, allowed: tuple[str, ...]
) -> bool:
    # UUID → str(...) (parameter SQL), tuple → list(...) (ANY), hasil scalar bertipe Any → cek `is not None`.
    updated = await self.scalar(
        """
        UPDATE work_plan_daily SET status = :new_status, update_at = now()
        WHERE daily_plan_id = CAST(:id AS uuid) AND status = ANY(:allowed) AND delete_at IS NULL
        RETURNING daily_plan_id
        """,
        {"id": str(plan_id), "new_status": new_status, "allowed": list(allowed)},
    )
    return updated is not None
```
Parameter opsional (`X | None`) dikirim eksplisit: `str(x) if x is not None else None`. Kirim `str(...)` untuk UUID, seperti kode repository yang ada. `params` bertipe `dict[str, Any]`, jadi mypy tidak menangkap UUID mentah; pemeriksaan ini hanya lewat konvensi dan tes.

### 3.3 Optimistic lock (kolom version)
PDF 3.3 baris 268-271. Tambah `version INT NOT NULL DEFAULT 1` lalu `WHERE version = :expected` dan `SET version = version + 1`. Berguna untuk form edit yang lama. VMS belum punya kolom version di tabel transaksi utama; tambahkan hanya bila ada konflik nyata.

### 3.4 TOCTOU (time-of-check to time-of-use)
Pola salah: baca status → cek di Python → UPDATE tanpa kondisi. Dua request bersamaan lolos cek yang sama, lalu UPDATE terakhir menang. Akibat: dua baris audit, dua notifikasi, status tidak sesuai aksi pertama.
- Perbaikan 1: kondisi di UPDATE (3.2).
- Perbaikan 2: `FOR UPDATE` di awal service (pola `overtime_service.py:39`).
- Tes: dua request paralel, hanya satu sukses (bagian 6).

## 4. Idempotency-Key

### 4.1 Mengapa
Klien dapat mengirim ulang (jaringan lambat, tombol ditekan dua kali, retry Dio). Tanpa idempotensi, dua pengajuan lembur, cuti, atau pinjaman aset tercipta. Unique index hanya mencegah sebagian kasus dan tidak mengembalikan respons yang sama (riset 01 T6).

### 4.2 Kondisi sekarang
- 189 endpoint mutasi, 0 membaca `Idempotency-Key` (riset 01 F-03; verifikasi: `grep -rni idempotency api/app` hanya menemukan `attendance_offline_service.py:164-173` untuk `client_op_id`).
- Operasi offline: `client_op_id` dicek sebelum dijalankan dan hasil sebelumnya dikembalikan (`attendance_offline_service.py:173`).

### 4.3 Desain Target (ADR 0001 keputusan 7; `docs/06`)
- **Sumber kebenaran**: tabel `idempotency_keys` di PostgreSQL.
  ```
  idempotency_keys(
    user_id uuid NOT NULL,
    key     text NOT NULL,            -- UUID dari klien, panjang dibatasi
    method  text NOT NULL,
    path    text NOT NULL,            -- template route
    body_sha256 bytea NOT NULL,
    status_code int,
    response_json jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, key)
  )
  ```
  TTL 24 jam. Bersihkan dengan job terjadwal (`DELETE ... WHERE created_at < now() - interval '24 hours'`). Pakai `DELETE` batch, bukan tanpa batas.
- **Dalam transaksi yang sama** dengan aksinya: `INSERT ... ON CONFLICT (user_id, key) DO NOTHING` dulu. Jika insert berhasil, jalankan aksi lalu `UPDATE` respons, lalu commit. Jika conflict, baca baris lalu:
  - body hash sama dan sudah selesai → kembalikan respons tersimpan (200 atau status asli). Bukan 409.
  - body hash beda → 422 "Kunci idempotensi dipakai untuk permintaan lain".
  - belum selesai (baris ada tanpa respons) → 409 "permintaan sedang diproses".
- **Redis `SET NX`** (opsional, ADR 0001 keputusan 7): hanya kunci cepat anti-balapan di depan. Keputusan akhir tetap di PostgreSQL.
- **Yang tidak disimpan**: respons login dan refresh (`docs/06`).
- **Wajib** untuk endpoint tulis terotentikasi dari klien offline dan endpoint keuangan atau kuota. Mode opsional dulu untuk APK lama yang belum mengirim header (aturan kontrak `ListParams`: tanpa header = perilaku lama).

PDF 11.1 menguji 4×409. Desain Target memakai 200 untuk duplikat identik, dan 409 hanya untuk permintaan yang masih berjalan atau body berbeda (koreksi riset 01 bagian 6; praktik umum pada Stripe, dokumentasi publik `docs.stripe.com/api/idempotent_requests`, akses 2026-11-04 bila dipakai sebagai rujukan).

## 5. Konsistensi lintas sistem (outbox, saga)

- Untuk satu database, transaksi lokal sudah cukup. PDF bagian 19 (DDD, CQRS, saga) tidak diperlukan (ADR 0001 keputusan 15: di luar scope).
- Notifikasi dan push: tulis baris `notifications` di transaksi yang sama, kirim push setelah commit. Kegagalan push tidak boleh membatalkan aksi (`push_status` di `docs/03`).
- File: unggah ke MinIO sebelum commit bisa meninggalkan objek yatim. Unggah dulu, lalu catat `file_object`; bersihkan objek yatim lewat job (lihat `vms-storage-minio`).

## 6. Pengujian konkurensi (wajib untuk jalur kritis)

Contoh pola (PDF 11.1, baris 1531-1553), diadaptasi ke VMS. Jangan jalankan sebelum diminta:
```python
async def test_dua_approve_bersamaan_hanya_satu_sukses(client, jadwal_id, token_pm):
    headers = {"Authorization": f"Bearer {token_pm}"}
    hasil = await asyncio.gather(
        *[client.post(f"/api/v1/daily-plans/{jadwal_id}/approve", headers=headers) for _ in range(2)]
    )
    kode = sorted(r.status_code for r in hasil)
    assert kode.count(200) == 1
    assert kode.count(409) == 1
```
- Gunakan barrier (`asyncio.Event`) agar benar-benar bersamaan, dan batasi pengulangan agar tidak flaky (riset 01 F-14).
- Target awal tiga tes: dua approve bersamaan, dua rollover bersamaan, dua serah terima aset bersamaan.

## 7. Checklist

- [ ] Transisi status memakai `FOR UPDATE` atau `UPDATE … AND status = ANY(...)` dengan `rowcount`.
- [ ] Commit hanya di service; efek samping setelah commit.
- [ ] Endpoint tulis dari klien offline/retry punya `Idempotency-Key` (atau alasan tertulis).
- [ ] Respons duplikat identik = respons tersimpan, bukan 409.
- [ ] Ada tes konkurensi untuk transisi yang diubah.
- [ ] Tidak ada query di dalam transaksi yang memanggil layanan luar tanpa timeout.
