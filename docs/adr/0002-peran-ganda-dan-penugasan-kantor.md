# ADR 0002: Peran ganda dan penugasan kantor
Status: Usulan
Tanggal: 2026-11-05
Pemilik keputusan bisnis: pemilik VMS (bagian "Keputusan pemilik" sudah final; bagian lain menunggu persetujuan).

## 1. Konteks

Keadaan sekarang (diverifikasi di kode):
- `users.system_role` hanya satu nilai; `users.employee_id` UNIQUE; kantor karyawan di `employee.office_id`.
- Izin dipetakan per peran di `api/app/core/permissions.py` (`_SYSTEM_ROLE_EXTRA`, `permissions_for_roles`).
- Cakupan kantor absensi dihitung di SQL oleh `attendance_office_scope` (`api/app/shared/access/office_scope.py`): SUPER_ADMIN dan OPERATIONAL_MANAGER (peran sistem, atau penjabat OM lewat `division.om_id`) melihat semua kantor; peran lain hanya `employee.office_id`.
- Jabatan kedua baru bisa dimodelkan lewat `division.om_id` (hanya untuk OM). HR untuk dua kantor, atau OM yang juga HR, belum bisa.
- JWT EdDSA dengan `kid`; migrasi Alembic head `v2_0028`.

Kebutuhan: satu orang memegang dua peran dan banyak kantor, tanpa berpindah peran saat masuk.

### Keputusan pemilik (final, tidak diubah ADR ini)
1. Satu orang boleh memegang DUA peran sekaligus dan BANYAK kantor (mis. HR untuk dua kantor; OM yang juga HR).
2. SATU LOGIN: izin semua peran digabung (union).
3. OM melihat semua kantor. Peran HR milik orang yang juga OM hanya berlaku untuk kantor yang ditugaskan (HR tidak ikut melebar).
4. HR/Finance tanpa penugasan tambahan: hanya kantor sendiri (`employee.office_id`). SUPER_ADMIN semua kantor.
5. OM mendapat izin `export:attendance`.
6. Aplikasi lama tetap jalan: bentuk respons `/app/android/update` dan `/api/v1/version` tidak berubah; token/login lama tetap berlaku; tanpa perubahan wajib di klien lama.

## 2. Pilihan

### A. Tabel penugasan `user_role_assignment` (peran + kantor), satu baris per peran per kantor (dipilih)
Pro: bisa diaudit per baris; indeks dan FK kantor menjaga integritas; mudah dipakai di SQL (`EXISTS`); bisa diperluas (masa berlaku, catatan); soft delete menyimpan riwayat.
Kontra: tabel baru, join tambahan di cakupan (kecil, diindeks); perlu migrasi pengisian.

### B. Kolom array di `users` (`extra_roles text[]`, `office_ids uuid[]`)
Pro: perubahan skema kecil; tanpa join.
Kontra: tanpa FK (kantor terhapus tidak terdeteksi); peran dan kantor terpisah sehingga tidak bisa menyatakan "HR hanya kantor A, Finance hanya kantor B"; audit per perubahan kasar; indeks GIN rumit; riwayat hilang.

### C. Satu akun per peran (dua login untuk satu orang)
Pro: tanpa perubahan kode.
Kontra: melanggar keputusan "satu login"; `users.employee_id` UNIQUE menghalangi; dua kata sandi; ditolak.

## 3. Keputusan yang direkomendasikan

Pilihan A. `users.system_role` tetap sebagai peran UTAMA (kompatibel mundur). Peran tambahan dan cakupan kantor ada di tabel penugasan. Izin efektif = union izin peran utama + semua peran tambahan aktif. Perubahan hanya oleh SUPER_ADMIN dan selalu masuk audit log.

## 4. Skema usulan

Tabel `user_role_assignment`:
| Kolom | Tipe | Catatan |
|---|---|---|
| `assignment_id` | uuid PK | UUIDv7 (fungsi default proyek) |
| `user_id` | uuid NOT NULL FK users | |
| `role` | system_role_enum NOT NULL | peran yang ditugaskan |
| `office_id` | uuid NULL FK office | NULL = semua kantor (hanya sah untuk SUPER_ADMIN dan OPERATIONAL_MANAGER) |
| `source` | text NOT NULL | `PRIMARY` (hasil pengisian dari data lama), `MANUAL` |
| `created_at`, `created_by` | timestamptz, uuid FK users | |
| `delete_at`, `delete_by` | timestamptz NULL, uuid NULL | soft delete |

Constraint dan indeks:
- UNIQUE parsial `(user_id, role, COALESCE(office_id, '00000000-0000-0000-0000-000000000000')) WHERE delete_at IS NULL`.
- CHECK: `office_id IS NULL` hanya bila `role IN ('SUPER_ADMIN','OPERATIONAL_MANAGER')`; selain itu `office_id` wajib.
- Indeks `(user_id) WHERE delete_at IS NULL` (jalur panas: muat izin saat login/cek); indeks `(office_id, role) WHERE delete_at IS NULL`.
- Kantor atau user yang dinonaktifkan: penugasan tidak dihapus, tetapi diabaikan oleh kueri (join ke user/kantor aktif).
- Tanpa RLS baru pada tahap ini; akses tulis hanya lewat service SUPER_ADMIN.

## 5. Aturan union izin dan cakupan kantor

Izin: `izin_efektif = union(izin(system_role), izin(role tiap penugasan aktif))`. Satu login, tanpa pilih peran.

Cakupan kantor (per izin): kantor yang boleh dilihat = union dari
- semua kantor bila punya SUPER_ADMIN, atau OPERATIONAL_MANAGER (peran utama, penugasan OM, atau penjabat `division.om_id`);
- untuk peran lain (HR, Finance, dst.): kantor pada penugasan peran itu; bila peran itu adalah peran utama dan tidak ada penugasan, cukup `employee.office_id`.
Penting: cakupan melebar HANYA untuk izin yang dibawa peran OM. Izin yang hanya dibawa peran HR dibatasi ke kantor HR orang itu, walau orangnya juga OM.

| Kasus | Peran | Kantor efektif | Catatan |
|---|---|---|---|
| SA | SUPER_ADMIN | semua | semua izin |
| OM | OPERATIONAL_MANAGER | semua | + `export:attendance` (baru) |
| HR satu kantor | ADMIN_HR_GA | `employee.office_id` | tanpa penugasan, sama seperti sekarang |
| HR dua kantor | ADMIN_HR_GA | kantor sendiri + kantor tugas | satu penugasan HR per kantor tambahan |
| OM + HR | OM utama, HR tambahan (kantor K) | izin OM: semua kantor; izin khusus HR (kelola user, dokumen, aset, mess, offboarding): hanya K | HR tidak melebar |
| Finance | FINANCE | `employee.office_id` (+ penugasan bila ada) | saat ini lihat/ekspor kantor sendiri |
| Penjabat OM divisi + HR | HR utama, `division.om_id` | OM: semua kantor; HR: kantor sendiri | perilaku sekarang dipertahankan |
| HR + Finance | dua peran, kantor K | union izin pada kantor K | izin Finance hanya di K |
| PM + HR | PM utama, HR di K | izin PM menurut cakupan PM sekarang (divisi/tim); izin HR di K | cakupan PM tidak berubah |

Implementasi cakupan: fragmen SQL satu sumber (perluasan `attendance_office_scope`) memakai `EXISTS` ke tabel penugasan; fungsi izin Python memakai pemetaan peran yang sama agar daftar, rekap, ekspor, dan swafoto konsisten.

## 6. Dampak JWT dan kompatibilitas mundur

- Token lama (tanpa klaim penugasan) tetap valid; `kid` dan algoritma tidak berubah. Izin efektif dihitung server dari DB (bukan dari klaim), sehingga token lama langsung memakai penugasan baru dan pencabutan berlaku seketika.
- Klaim baru (opsional, tidak dipakai server untuk otorisasi): daftar peran untuk tampilan klien baru. Klien lama mengabaikannya. Harus dicek di `core/security.py`/pembuat token agar penambahan klaim tidak melewati batas ukuran token.
- Bentuk respons `/api/v1/version` dan `/app/android/update` tidak diubah. Bila respons profil/login perlu daftar peran, tambahkan FIELD BARU opsional, tanpa mengubah atau menghapus field yang ada.
- Cache izin (bila ada) harus dibatalkan saat penugasan berubah (TTL pendek atau invalidasi saat tulis).
- Masa berlaku token lama tidak diubah; tidak perlu paksa login ulang.

## 7. Migrasi expand-contract (tanpa mengubah akses siapa pun)

1. Expand (migrasi Alembic baru setelah `v2_0028`): buat tabel, indeks, constraint. Kode lama tidak membaca tabel.
2. Isi: untuk tiap user aktif, satu baris `source='PRIMARY'` dari `system_role` (+ `employee.office_id`; SA/OM `office_id` NULL). Tidak ada baris tambahan; penjabat `division.om_id` tetap dibaca dari tabel divisi. Skrip idempoten (`ON CONFLICT DO NOTHING`).
3. Uji paritas: kueri cakupan baru vs lama harus menghasilkan himpunan yang sama untuk SEMUA user (tes otomatis dan laporan selisih = 0) sebelum rilis.
4. Kode baca memakai union (peran utama + tabel) di belakang flag; tanpa penugasan MANUAL hasilnya identik dengan sekarang.
5. Contract: bukan sekarang. `users.system_role` tetap dipertahankan (peran utama, dipakai klien lama). Tidak ada kolom dihapus.
Rollback: matikan flag; tabel dibiarkan.

## 8. Wewenang dan audit

- Hanya SUPER_ADMIN yang boleh menambah/mencabut penugasan (izin baru `manage:role_assignments`, tidak diberikan ke peran lain, termasuk OM dan HR).
- Setiap perubahan (tambah, cabut, ganti kantor) ditulis ke audit log dalam transaksi yang sama: pelaku, user target, peran, kantor, nilai sebelum/sesudah.
- Tidak boleh mengubah penugasan diri sendiri (cegah eskalasi diam-diam); minimal satu SUPER_ADMIN aktif tetap ada.

## 9. Risiko eskalasi hak dan mitigasi

| Risiko | Mitigasi |
|---|---|
| Union membuat izin lebih luas dari maksud | Tabel kasus di atas jadi tes wajib; cakupan per izin, bukan per orang |
| OM+HR: HR ikut melebar ke semua kantor | Cakupan dihitung per peran pembawa izin; tes khusus OM+HR |
| Penugasan peran tinggi (SA) lewat endpoint | SA tidak dapat ditugaskan lewat tabel; tetap peran utama, diubah jalur khusus |
| Akun disalahgunakan menambah diri | Hanya SA; tidak bisa ke diri sendiri; audit; peringatan bila peran bertambah |
| Penugasan tersisa saat user/kantor nonaktif | Kueri menggabung status aktif; tes |
| Cache izin basi | Invalidasi saat tulis, TTL pendek |
| Kebocoran lintas kantor lewat endpoint lupa difilter | Audit GET-only per peran x kantor (QA); objek di luar cakupan 404 |

## 10. Pembagian kerja dan urutan

1. db: migrasi expand + pengisian + uji paritas (PR 1).
2. api: model/repository penugasan, fungsi izin union, perluasan `attendance_office_scope`, izin `manage:role_assignments`, `export:attendance` untuk OM, endpoint kelola penugasan (SA saja), audit, flag; snapshot OpenAPI (PR 2-3).
3. web: layar kelola penugasan (SA), teks Indonesia sederhana, `applyFieldErrors`; tampilan peran ganda (PR 4). Tipe lewat generator.
4. mobile: tidak wajib berubah; hanya bila menampilkan peran ganda, pakai field baru opsional (PR terpisah, opsional).
5. qa: matriks tes, audit kebocoran GET-only, uji klien lama (PR 5/rilis).
Urutan: db -> api (flag mati) -> qa paritas -> web -> nyalakan flag. Rilis MINOR (fitur, tanpa API break).

## 11. Matriks tes yang harus ada

- Kombinasi peran x kantor x endpoint absensi (daftar, rekap, ekspor, uang makan, swafoto): SA, OM, HR 1 kantor, HR 2 kantor, OM+HR, Finance, HR+Finance, penjabat OM+HR, PM+HR, EMPLOYEE (tanpa akses). Kantor dalam dan luar cakupan (luar = 404/kosong).
- OM memiliki `export:attendance`; peran lain tidak berubah.
- Paritas migrasi: cakupan lama == baru untuk semua user data uji.
- Token lama (tanpa klaim baru) berfungsi; token dengan `kid` lama; refresh token lama.
- Pencabutan penugasan langsung berlaku pada token yang sama.
- Hanya SA bisa menetapkan; OM/HR ditolak 403; tidak bisa ke diri sendiri; audit tercatat tiap perubahan.
- CHECK/UNIQUE: duplikat, `office_id` NULL untuk peran non-OM/SA ditolak, soft delete lalu tambah ulang.
- Aplikasi lama: snapshot respons `/api/v1/version` dan `/app/android/update` tidak berubah; APK lama login dan absen tetap jalan.
- Arsitektur: tanpa `LIKE '%…'` baru, rute baru punya `require_permission` (`test_route_guards.py`).

## 12. Pertanyaan terbuka untuk pemilik (dengan saran)

1. Berapa batas peran per orang? Saran: maksimal 2 peran tambahan di luar peran utama (sesuai "dua peran"), dicek server. Alasan: mencegah penumpukan hak yang sulit diaudit.
2. Kombinasi yang dilarang? Saran: larang SUPER_ADMIN digabung peran lain (sudah punya semua) dan larang Finance+HR bila pemisahan tugas penting. Alasan: pemisahan tugas uang vs data karyawan. Bila pemilik butuh, boleh diizinkan.
3. Apakah penugasan perlu tanggal berakhir (mis. pengganti cuti)? Saran: ya, kolom `berlaku_sampai` opsional di fase 2, bukan fase 1. Alasan: mengurangi hak yang terlupa; tidak menghambat rilis awal.
4. Apakah penugasan kantor juga berlaku untuk Finance? Saran: ya, mekanisme sama. Alasan: konsisten, tanpa kode khusus.
5. Peran PM/HSE/TEAM_LEADER sebagai peran tambahan? Saran: fase 1 hanya HR, Finance, OM; lainnya menyusul. Alasan: cakupan PM berbasis divisi/tim, bukan kantor, sehingga butuh desain sendiri.
6. Izin yang hanya milik HR pada orang OM+HR (kelola user dll.): benar hanya kantor tugas? Saran: ya, sesuai keputusan pemilik; tampilkan di layar "berlaku untuk kantor X". Alasan: menghindari kejutan.
7. Siapa pengganti bila SA tunggal berhalangan? Saran: minimal dua SUPER_ADMIN. Alasan: hanya SA yang boleh menetapkan penugasan.

## 13. Konsekuensi

Plus: jabatan ganda dan multi-kantor terkelola rapi dan terekam; klien lama tidak terdampak. Minus: satu tabel dan satu join indeks tambahan di jalur cakupan; kerja tes lebih banyak. Tidak ada kode atau migrasi pada PR ini (hanya dokumen).
