# Arsitektur mobile dan sinkron offline

## 1. Lapisan

| Lapisan | Isi | Aturan |
|---|---|---|
| `core/` | Dio client, token, konstanta, router, tema, helper foto, pesan galat | Tanpa logika fitur |
| `data/` | Drift (`app_database.dart`), `sync_engine.dart`, `offline_attendance.dart`, `vms_api.dart`, `connectivity_sync.dart` | Satu-satunya tempat yang bicara ke jaringan dan database |
| `features/<fitur>/` | Layar, Notifier, widget fitur | Membaca data dari provider; tidak memanggil Dio langsung |
| `shared/ui/` | Komponen desain berbasis token | Tanpa logika bisnis |

Arah impor: `features` -> `data`, `core`, `shared`. `data` tidak mengimpor `features`. `core` tidak mengimpor `features`.

## 2. Repository dan provider (pola)

```dart
// data/leave_repository.dart (pola)
class LeaveRepository {
  LeaveRepository(this._engine, this._api);
  final SyncEngine _engine;
  final VmsApi _api;

  Future<List<Leave>> fetchAll() => _engine.fetchList<Leave>(
        key: 'leaves',
        remote: () => _api.leaves(),
        fromJson: Leave.fromJson,
      );

  Future<bool> submit(LeaveDraft d) => _engine.submit(
        'LEAVE_CREATE',
        d.toJson(),
      );
}
```

Catatan: nama fungsi di atas adalah pola, bukan API nyata. Periksa `sync_engine.dart` untuk signature `fetchList`, `fetchMap`, dan `cachePut`/`cacheGet` sebelum menulis kode.

## 3. Outbox (kondisi nyata)

Bukti: `mobile/lib/data/sync_engine.dart`.

- Tabel Drift `PendingSyncOperations` menyimpan op: `client_op_id` (UUID v4, dibuat di HP), jenis op, payload, `attemptCount`, `deadLetter`, `lastError`, dan file lokal.
- `submit` (baris 111-130): enqueue, lalu `_push()`. Galat jaringan (`isNetworkFailure`) ditelan. Penolakan server menandai `deadLetter` lalu melempar `SyncRejectedException`.
- `_push` (baris 132 ke bawah): kirim absen offline lewat endpoint sendiri (`offlineAttendance.push()`), lalu kirim antrean `POST /sync/operations` (batas 200 op per permintaan, `api/app/modules/system/schemas/sync_schema.py:18`).
- `_markDead` (baris sekitar 231): menandai op ditolak.
- Server menyimpan `client_op_id`. Op yang sudah pernah diproses dikembalikan hasilnya, tidak dijalankan ulang (`sync_service.py:112-137`).

Yang belum ada:
- Backoff eksponensial antar percobaan. Tidak ditemukan di `lib/` (grep kosong).
- Batas percobaan sebelum dead-letter untuk galat sementara.
- Layar daftar op gagal yang menjelaskan apa yang perlu dilakukan pengguna (`features/sync/sync_queue_screen.dart` ada; isinya belum diperiksa di skill ini).

## 4. Rancangan outbox yang disarankan (untuk fitur baru atau perbaikan)

Gunakan istilah yang sudah ada: `client_op_id` untuk op offline. Jangan membuat header kedua untuk jalur yang sama, kecuali API sudah menerima `Idempotency-Key` untuk endpoint online (belum ada: 0 penanganan di `api/app`; bukti riset `01` F-03).

Kolom tambahan yang disarankan pada `PendingSyncOperations` (perlu migrasi Drift, `schemaVersion` naik, dan tes migrasi):
- `nextAttemptAt` (DateTime): kapan boleh dicoba lagi.
- `status`: `pending`, `sending`, `sent`, `dead`. (Saat ini memakai `deadLetter` bool.)
- Backoff contoh: 5 detik, 30 detik, 2 menit, 10 menit, lalu batas. Batas nilai harus disepakati dengan pemilik.

Aturan:
- Galat jaringan dan 5xx: kembali ke pending dengan `nextAttemptAt` baru (sementara).
- Galat 4xx validasi: dead-letter, tampilkan alasan dalam Bahasa Indonesia.
- Galat 401 (sesi habis): hentikan antrean, minta login. Jangan menandai dead.
- Urutan FIFO per perangkat tetap dijaga (riset `01` F-08).
- Setelah sukses, hapus op dan file lokal yang terkait (foto) hanya setelah server mengonfirmasi.

Perubahan ini menyentuh data. Ikuti aturan memori: rancangan di `docs/38`, tes migrasi hanya atas perintah pengguna.

## 5. Konflik

- Strategi konflik per domain belum terdokumentasi di kode (riset `01` F-32, perlu cek `docs/38` di repo `vms-next`).
- Default yang aman untuk VMS (usulan, perlu persetujuan pemilik): absensi, jadwal, dan persetujuan bersifat server-authoritative. HP hanya mengirim niat (op), server memutuskan. Profil bisa last-write-wins.
- UI menampilkan hasil server setelah sinkron, dengan keterangan "belum tersinkron" untuk op pending.

## 6. Antrean foto

- Simpan path dan metadata di Drift. Jangan simpan blob.
- Kompres dan watermark di isolate sebelum masuk antrean (`core/photo_capture.dart`).
- Upload per item dengan Dio `FormData`. Catat progres per item.
- Hapus berkas lokal hanya setelah `sent`.
- Pantau total ukuran antrean dan tampilkan di layar sinkron.
- Saat ini gambar sebagian masih dikirim sebagai bagian op. Periksa `localFiles` di `submit`.

## 7. Offline attendance

- `offline_attendance.dart` menyimpan antrean absen. Riset menyebut antrean disimpan di `flutter_secure_storage` (baris 43). Secure storage tidak dirancang untuk data besar. Perlu cek ukuran dan pindahkan ke Drift bila perlu (riset `01` F-32).
- Absen dikirim lewat endpoint sendiri dengan tanda tangan (lihat `offlineAttendance.push()`).
- Aturan batas per hari (dua kali ditolak) ada di `attendance_screen.dart` (`_maxAttemptsPerDay = 2`). Pastikan aturan server dan HP sama.

## 8. Cache baca

- `fetchList` dan `fetchMap` memakai cache Drift. Bila jaringan gagal, data cache tampil (stale-while-error). Ini membuat fitur bisa dibaca offline.
- Beri tanda "data terakhir diperbarui" di layar yang memakai cache.
- Setelah online, refresh otomatis lewat `connectivity_sync.dart` dan `appliedRevision`.

## 9. Mode offline di tiap fitur: checklist

- [ ] Baca dari cache saat offline (tidak kosong palsu).
- [ ] Tulis lewat `submit` dengan `client_op_id`. Tidak ada `dio.post` langsung untuk tulisan.
- [ ] Tampilkan status "menunggu sinkron" per item.
- [ ] Galat sementara tidak membuat pengguna mengulang pekerjaan secara manual tanpa alasan.
- [ ] Op ditolak punya pesan Indonesia dan tindakan (misalnya "ajukan ulang").
- [ ] Tes: op terkirim, op duplikat (idempoten), op ditolak, offline lalu online.
