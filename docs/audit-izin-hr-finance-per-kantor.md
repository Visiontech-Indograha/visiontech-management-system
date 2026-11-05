# Audit izin HR/Finance per kantor (di luar absensi)

Dasar: ADR 0002. Aturan: orang yang memegang sebuah izin HANYA lewat peran HR (`ADMIN_HR_GA`) atau `FINANCE`
dibatasi ke kantor sendiri (`employee.office_id`) + kantor penugasan peran itu; SA, OM, dan ADMIN lama tidak dibatasi.
Cakupan dihitung per peran pembawa izin (`office_scope.office_restriction`), jadi OM yang juga HR tetap dibatasi pada
izin yang hanya dibawa HR. Flag `ROLE_ASSIGNMENT_ENABLED` mati = perilaku lama persis (fungsi mengembalikan "tanpa batas").
Di luar jangkauan = 404 (keberadaan data tidak dibocorkan).

Izin yang dibawa HR: `manage:users`, `verify:documents`, `manage:employee_documents`, `manage:assets`, `manage:mess`,
`view:mess`, `review:mess`, `manage:offboarding`, `view:offboarding`, `view:teams`. Finance: `review:overtime`,
`review:attendance`, `export:attendance`, `manage:sites`, `view:all_attendance`.

| Endpoint | Terikat kantor | Diubah | Alasan |
|---|---|---|---|
| `PUT /employees/{id}`, `POST/PUT/DELETE /employees/{id}/addresses...`, `POST /employees/{id}/archive`, `POST /employees/{id}/restore` | ya (employee.office_id) | ya | dependency `require_permission_for_employee`; PUT juga menolak pindah ke kantor di luar jangkauan |
| `POST /employees` | ya (body.office_id) | ya | kantor karyawan baru harus di jangkauan |
| `GET /employees`, `GET /employees/{id}` | sebagian | ya (hanya kolom sensitif) | direktori tetap terbuka (izin dasar semua pegawai); kontak/alamat/PKWT HR hanya untuk kantor jangkauan (`sens_offices`) |
| `GET /employees/next-no` | tidak (urutan nomor global) | tidak | bukan data per kantor |
| `/employees/{id}/account/*` (11 rute) | ya | ya | `require_permission_for_employee` |
| `GET/DELETE /face/enrollments/{id}...` | ya | ya | idem |
| `GET/POST /employees/{id}/documents`, deactivate, delete | ya | ya | `DocumentService._reachable` memakai `ensure_employee_in_scope` |
| `GET /documents/expiring` | ya | ya | filter kantor di SQL |
| `POST/PUT/DELETE /job-positions` | tidak (master global) | tidak | tidak punya kantor |
| `GET /teams*` (`view:teams`) | tidak (divisi/tim) | tidak | cakupan divisi/tim, perlu desain sendiri (ADR bagian 12 poin 5) |
| `GET /mess`, `GET /mess/{id}`, `POST /mess`, `PUT/DELETE /mess/{id}`, `/decision`, `/cancel`, `/end` | ya (lewat karyawan penghuni) | ya | filter daftar + `get_stay(user)` |
| `POST/PUT/DELETE /mess/places` | tidak (tabel `company_mess` tanpa kantor) | tidak | tidak ada kolom kantor |
| `GET /offboarding`, `/pkwt-expiring`, `GET /{id}`, `POST`, verifikasi item, approve, cancel | ya | ya | filter kantor + cek karyawan; SA/OM tetap semua |
| `POST/PUT/DELETE /offices` (`manage:sites`) | PUT/DELETE ya, POST tidak | PUT/DELETE ya | Finance hanya mengubah/menghapus kantor di jangkauannya; kantor baru belum punya kantor |
| `GET /overtime`, rekap lembur, `POST /overtime/{id}/review` (`review:overtime`) | ya | ya | filter kantor + cek karyawan |
| Cuti: `GET/POST /leaves*`, review, saldo (cek peran, bukan izin) | ya | ya | akses lewat peran HR dibatasi (`_hr_scope_ok`); jalur PM dan cuti sendiri tidak berubah |
| `/assets/*` (`manage:assets`: alat, kendaraan, pinjaman, pengajuan) | ya (`tool/vehicle.office_id`) | TIDAK | predikat cakupan aset gabungan divisi/pemegang/kantor di ~20 rute; perlu PR sendiri agar tidak regresi |
| `POST /attendance/{id}/review`, `GET /attendance/export` | ya | sudah (PR absensi) | memakai `attendance_office_scope` |
| `GET /home/summary` | ya (hitungan) | sebagian | hitungan mess ikut dibatasi; hitungan aset/lembur mengikuti service asalnya |
| `/users/{id}/role-assignments` | tidak | tidak | khusus SUPER_ADMIN |

## Pemeriksaan `current_user.role` langsung

| Lokasi | Dampak | Tindakan |
|---|---|---|
| `actor.role` pada jejak audit (accounts, employees, face, overtime, work_plans, work_completion, attendance) | hanya label audit (peran utama) | dibiarkan |
| `hse_service.get_active_popup`: `str(current_user.role)` | popup K3 per peran hanya mencocokkan peran UTAMA; peran tambahan tidak melihat kampanye untuk perannya | DILAPORKAN, tidak diubah (perlu ubah SQL kampanye; butuh keputusan pemilik) |
| `auth_service.login`: `user.role in FIELD_ROLES/OFFICE_ROLES` | platform masuk (web/HP) ditentukan peran utama | DILAPORKAN, sengaja (peran utama = jenis akun) |
| `account_service`, `face_service`: `account.role` / `employee.role` | peran akun TARGET (bukan pelaku) | aman |

Semua pemeriksaan lain memakai `has_role(...)` (daftar `roles` = utama + tambahan) atau `permissions` (union), sehingga sudah melihat peran tambahan.

## Catatan
- Pembatasan diterapkan di service/dependency, bukan RLS. PM yang juga HR dibatasi pada alur mess/offboarding sebagai HR (konservatif).
- Tes: `api/tests/modules/role_assignments/test_hr_office_scope.py`.

## Hasil audit OM+HR per izin (QA P3-1)

Aturan (ADR 0002): cakupan dihitung PER IZIN yang diperiksa rute. Izin yang tidak dibawa OM = OM+HR dibatasi ke
kantor tugas HR; izin yang juga dibawa OM = OM+HR semua kantor. `office_restriction` sudah menghitung ini dari
pembawa izin; yang menyimpang adalah pemanggil yang menambah `wide_roles=("SUPER_ADMIN","OPERATIONAL_MANAGER")` atau
selalu memakai satu izin (`MANAGE_*`) untuk semua rute, sehingga OM+HR melebar pada rute `MANAGE_*`.

| Endpoint | Izin di rute | Dibawa OM | OM+HR sebelum | OM+HR seharusnya / sekarang |
|---|---|---|---|---|
| `PUT /employees/{id}`, alamat, arsip, pulihkan, `POST /employees` | `manage:users` | tidak | kantor tugas HR | sama (sudah benar) |
| `/employees/{id}/account/*`, `/face/enrollments/*` | `manage:users` | tidak | kantor tugas HR | sama (sudah benar) |
| `GET /employees` kolom sensitif | peran SA/OM atau `manage:users` | OM ya (lewat peran) | semua kantor | sama: OM membawa hak lihat sensitif, jadi semua kantor (HR tunggal tetap dibatasi) |
| `/employees/{id}/documents*`, `/documents/expiring` | `manage:employee_documents` | tidak | kantor tugas HR | sama (sudah benar) |
| `GET /mess`, `GET /mess/{id}` | `view:mess` | ya | semua kantor | semua kantor (benar); tetap dibatasi untuk HR tunggal/dua kantor |
| `POST /mess`, `PUT/DELETE /mess/{id}` | `manage:mess` | tidak | SEMUA kantor (salah) | DIPERBAIKI: kantor tugas HR (404 di luar) |
| `POST /mess/{id}/decision` | `review:mess` | ya | semua kantor | semua kantor (benar) |
| `POST /mess/{id}/cancel`, `/end` | peran (HR/OM/SA atau pemilik) | ya (peran OM) | semua kantor | semua kantor (benar) |
| `GET /offboarding`, `/pkwt-expiring`, `GET /{id}`, `POST /{id}/approve` | `view:offboarding` | ya | semua kantor | semua kantor (benar) |
| `POST /offboarding`, verifikasi item, `POST /{id}/cancel` | `manage:offboarding` | tidak | SEMUA kantor (salah) | DIPERBAIKI: kantor tugas HR (404 di luar) |
| `PUT/DELETE /offices/{id}` | `manage:sites` | ya | semua kantor | semua kantor (benar) |
| `GET /overtime`, `POST /overtime/{id}/review` | `review:overtime` | ya | semua kantor | semua kantor (benar) |
| Cuti `GET/POST /leaves*`, review | peran (PM/HR/OM/SA), tanpa izin | ya (peran OM berwenang meninjau semua kantor) | semua kantor | semua kantor (benar). Bukan temuan: otoritas datang dari peran OM. HR tanpa OM dibatasi |
| `GET /home/summary` | hitungan lewat service mess/offboarding | mengikuti service | hitungan mess/offboarding semua kantor | hitungan memakai izin lihat (OM+HR semua kantor); HR tunggal tetap dibatasi |

Perubahan kode: `MessService` dan `OffboardingService` menerima izin per operasi (lihat/tinjau = `view:*`/`review:*`,
kelola = `manage:*`); `wide_roles` OM dihapus di sana. `office_restriction` mendapat `division_roles`
(PM tidak dihitung pembawa pelebar, agar PM+HR tetap dibatasi pada alur HR seperti sebelumnya). Flag mati = perilaku
lama persis.

Tes matriks (OM+HR, HR dua kantor, HR tunggal, OM tunggal; flag mati = paritas):
`api/tests/modules/role_assignments/test_om_hr_scope_matrix.py`.
