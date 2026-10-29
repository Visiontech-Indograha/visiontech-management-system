# 05. Matriks uji

Dibuat dari kode per 2026-10-29. Kasus diturunkan dari transisi di `02-state-machine.md` dan sequence di `03-sequence.md`. Kolom Hasil sengaja dikosongkan untuk diisi penguji.

Kolom:

- **ID**: prefiks area (MS master, JD jadwal, AB absen, PR progres, RO rollover, KO koreksi, LB lembur, SV survei, BA order dan BAST, VP verifikasi publik, EK ekspor, IZ izin umum, BT batas input, HM perilaku manusia).
- **Tipe**: UI web, HP (Flutter), atau API (pemanggilan langsung ke endpoint, misalnya via Postman CLI atau pytest).
- **Prioritas**: P1 wajib sebelum rilis, P2 penting, P3 sekadar kelengkapan.
- Kode galat: 401 belum login, 403 izin atau relasi, 404 tidak terlihat, 409 status tidak sesuai, 422 validasi.
- Kasus dengan tanda [VERIFIKASI] belum pasti harapannya, lihat `README.md`.

## A. Master data dan jenis pekerjaan

| ID | Langkah | Aktor | Harapan | Tipe | Prioritas | Hasil |
|---|---|---|---|---|---|---|
| MS-01 | Buat jenis pekerjaan di divisi sendiri dengan dua slot foto | PM divisi A | 201, muncul di /work-types | UI web | P1 | |
| MS-02 | Buat jenis pekerjaan dengan divisi_id milik divisi lain | PM divisi A | 403 FORBIDDEN | API | P1 | |
| MS-03 | Buat jenis pekerjaan dengan nama yang sama di divisi yang sama | PM | 409 DUPLICATE | API | P2 | |
| MS-04 | Buat jenis pekerjaan dengan dua label slot foto kembar | PM | 422 | API | P2 | |
| MS-05 | Label slot foto berisi spasi saja | PM | 422 Label slot foto wajib diisi | API | P2 | |
| MS-06 | Foto contoh berasal dari organisasi lain | PM | 422 (ensure_same_org) | API | P1 | |
| MS-07 | Tipe titik SURVEY_POINT dengan pemasangan lanjutan berjenis SURVEY | PM | 422 | API | P2 | |
| MS-08 | Tambah material template ke jenis pekerjaan divisi lain | PM | 403 | API | P2 | |
| MS-09 | Buat klien atau proyek dengan peran HR (tanpa CREATE_PLAN) | HR | 403 | API | P2 | |
| MS-10 | Ubah nama proyek berstatus COMPLETED | PM | 409 PROJECT_CLOSED | API | P2 | |
| MS-11 | Hapus proyek yang sudah dipakai jadwal | PM | 409 PROJECT_IN_USE | API | P2 | |
| MS-12 | Buat jadwal memakai proyek berstatus DRAFT | PM | 422 Proyek tidak sedang berjalan | API | P1 | |

## B. Jadwal harian

| ID | Langkah | Aktor | Harapan | Tipe | Prioritas | Hasil |
|---|---|---|---|---|---|---|
| JD-01 | Buat jadwal DRAFT untuk tim aktif, tanggal besok | PM divisi | 201, status DRAFT | UI web | P1 | |
| JD-02 | Buat jadwal untuk tanggal kemarin | PM | 422 | API | P2 | |
| JD-03 | Buat dua jadwal untuk tim dan tanggal yang sama | PM | 409 TEAM_DAY_TAKEN | API | P1 | |
| JD-04 | PM divisi B membuat jadwal untuk divisi A | PM divisi B | 403 Hanya PM/OM divisi ini | API | P1 | |
| JD-05 | OPS (punya CREATE_PLAN, bukan PM atau OM divisi) membuat jadwal | OPS | 403 | API | P2 | |
| JD-06 | Submit jadwal yang sudah APPROVED | PM | 409 INVALID_STATE | API | P2 | |
| JD-07 | Setujui jadwal yang tanggalnya sudah lewat | PM | 422 | API | P1 | |
| JD-08 | Setujui matriks 5 jadwal, satu milik divisi lain | PM | 200, approved 4, skipped 1 | API | P1 | |
| JD-09 | Tolak jadwal SUBMITTED tanpa alasan | PM | 422 | API | P2 | |
| JD-10 | Tolak jadwal APPROVED dengan alasan | PM | 200, status DRAFT, alasan tersimpan | UI web | P1 | |
| JD-11 | Ubah jadwal APPROVED (PUT) | PM | 409 | API | P1 | |
| JD-12 | Hapus jadwal yang sudah punya absensi | PM | 409 DAILY_PLAN_IN_USE | API | P1 | |
| JD-13 | Ketua tim mulai jadwal yang masih DRAFT | Ketua | 409 | API | P1 | |
| JD-14 | PM mencoba memulai hari kerja | PM | 403 | API | P1 | |
| JD-15 | Ketua mulai jadwal untuk tanggal besok | Ketua | 422 Jadwal baru bisa dimulai pada tanggalnya | API | P2 | |
| JD-16 | Ketua tim lain mencoba memulai jadwal tim ini | Ketua tim lain | 404 | API | P1 | |
| JD-17 | Selesaikan hari kerja tanpa laporan harian | Ketua | 422 REPORT_REQUIRED | API | P1 | |
| JD-18 | Anggota (bukan ketua) menyelesaikan hari kerja | Anggota | 403 | API | P1 | |
| JD-19 | Anggota melihat jadwal tim yang masih DRAFT | Anggota | 404 | API | P1 | |
| JD-20 | Anggota melihat jadwal tim yang sudah APPROVED | Anggota | 200 | HP | P1 | |
| JD-21 | Anggota tim lain melihat jadwal APPROVED tim ini | Anggota tim lain | 404 | API | P1 | |
| JD-22 | Salin jadwal ke tanggal yang sudah ada jadwal tim | PM | 409 | API | P2 | |
| JD-23 | Akses GET /work-plans/daily tanpa token | Publik | 401 | API | P2 | |

## C. Absen (masuk, pulang, offline, tinjau)

| ID | Langkah | Aktor | Harapan | Tipe | Prioritas | Hasil |
|---|---|---|---|---|---|---|
| AB-01 | Absen masuk: swafoto, GPS 20 m, dalam radius, jadwal APPROVED hari ini | Ketua | 200, status AUTO_VALID | HP | P1 | |
| AB-02 | Absen masuk saat jadwal tim belum APPROVED | Anggota | 409 PLAN_NOT_APPROVED | HP | P1 | |
| AB-03 | Absen masuk tanpa swafoto | Anggota | 422 | API | P1 | |
| AB-04 | Absen masuk dengan akurasi GPS 150 m | Anggota | 422 GPS_INACCURATE | HP | P1 | |
| AB-05 | Absen web dengan akurasi 250 m, lalu 350 m | Pekerja kantor | 250 m diterima; 350 m ditolak 422 | UI web | P2 | |
| AB-06 | Absen di luar radius tanpa penjelasan | Anggota | 422 EXPLANATION_REQUIRED | HP | P1 | |
| AB-07 | Absen di luar radius dengan penjelasan | Anggota | 200, status NEEDS_REVIEW | HP | P1 | |
| AB-08 | Absen sebelum jam buka (ATTENDANCE_OPEN_TIME) | Anggota | 422 CHECKIN_TOO_EARLY [VERIFIKASI nilai produksi] | API | P2 | |
| AB-09 | Absen saat cuti disetujui | Anggota | 409 ON_APPROVED_LEAVE | API | P2 | |
| AB-10 | Absen masuk kedua pada hari yang sama | Anggota | 409 ALREADY_CHECKED_IN | API | P1 | |
| AB-11 | Absen masuk saat sesi kemarin belum check-out | Anggota | 409 OPEN_SESSION | API | P1 | |
| AB-12 | Absen ketiga pada hari yang sama setelah dua kali ditolak | Anggota | 409 ATTENDANCE_DAY_LOCKED | API | P2 | |
| AB-13 | Wajah tidak cocok saat online | Anggota | 422 FACE_MISMATCH | HP | P1 | |
| AB-14 | Wajah belum terdaftar, saklar FACE_ENROLLMENT_REQUIRED aktif | Anggota | 409 FACE_NOT_ENROLLED | HP | P1 | |
| AB-15 | Pekerja kantor absen lewat HP (kanal MOBILE) | Pekerja OFFICE | 403 WRONG_ATTENDANCE_CHANNEL | API | P2 | |
| AB-16 | Absen di lokasi jadwal padahal bukan anggota tim jadwal | Non-anggota | 403 SITE_NOT_ALLOWED | API | P1 | |
| AB-17 | Check-out tanpa sesi terbuka | Anggota | 409 NO_OPEN_SESSION | API | P2 | |
| AB-18 | Absen offline dengan tanda tangan perangkat salah | HP | ditolak OFFLINE_TAMPERED | API | P1 | |
| AB-19 | Absen offline dengan jam lebih dari 7 hari lalu | HP | ditolak OFFLINE_TOO_OLD | API | P2 | |
| AB-20 | Kirim absen offline dengan client_op_id yang sama dua kali | HP | hanya satu baris tercatat (idempoten) | API | P1 | |
| AB-21 | PM meninjau absensi milik sendiri | PM | 403 | API | P1 | |
| AB-22 | Tinjau absensi tanpa catatan | PM | 422 Catatan pemeriksaan wajib diisi | API | P2 | |
| AB-23 | Tinjau absensi yang sudah APPROVED | PM | 409 INVALID_STATE | API | P2 | |
| AB-24 | HR (ADMIN_HR_GA) meninjau absensi | HR | 403 (tanpa REVIEW_ATTENDANCE di route) | API | P2 | |
| AB-25 | ADMIN legacy menghapus absensi (lihat T1) | ADMIN | Harapan 403 sesuai niat DELETE_ANY [VERIFIKASI] | API | P1 | |
| AB-26 | FINANCE meninjau absensi NEEDS_REVIEW (lihat T3) | FINANCE | Harapan 200 bila diizinkan, hasil aktual perlu dicek [VERIFIKASI] | API | P1 | |

## D. Progres item dan foto

| ID | Langkah | Aktor | Harapan | Tipe | Prioritas | Hasil |
|---|---|---|---|---|---|---|
| PR-01 | Isi progres 50 persen dengan foto tidak wajib | Ketua | 200, status IN_PROGRESS | HP | P1 | |
| PR-02 | Progres 100 persen tanpa foto wajib | Anggota | 422 PHOTOS_REQUIRED, menyebut slot yang kurang | HP | P1 | |
| PR-03 | Progres 100 persen dengan semua foto wajib | Anggota | 200, status DONE | HP | P1 | |
| PR-04 | Progres melebihi target | Anggota | 422 | API | P1 | |
| PR-05 | Progres saat jadwal masih APPROVED (belum dimulai) | Anggota | 409 INVALID_STATE | API | P1 | |
| PR-06 | Progres item yang prasyaratnya belum DONE | Anggota | 409 PREREQUISITE_NOT_DONE | API | P1 | |
| PR-07 | Progres item milik tim lain | Anggota tim lain | 404 | API | P1 | |
| PR-08 | Kirim file_id foto yang sudah dihapus | HP | 422 | API | P2 | |
| PR-09 | Progres item berstatus PENDING_ROLLOVER | Anggota | 409 | API | P1 | |
| PR-10 | Turunkan qty pada item DONE (lihat T6) | Anggota | Harapan belum pasti [VERIFIKASI] | API | P2 | |
| PR-11 | Unggah foto saat sinyal naik turun, lalu coba ulang | HP | foto tidak dobel, progres tersimpan sekali | HP | P1 | |
| PR-12 | PM mengubah item saat jadwal ONGOING | PM | 200, tercatat ITEM_UPDATED_ON_ACTIVE_DAY | API | P2 | |

## E. Rollover (pindah hari)

| ID | Langkah | Aktor | Harapan | Tipe | Prioritas | Hasil |
|---|---|---|---|---|---|---|
| RO-01 | Minta pindah hari dengan qty 40 persen dan alasan | Ketua | 200, PENDING_ROLLOVER, WAITING_PM | HP | P1 | |
| RO-02 | Minta pindah hari saat qty sudah mencapai target | Ketua | 422 | API | P2 | |
| RO-03 | Minta pindah hari dua kali untuk item sama | Ketua | 409 | API | P1 | |
| RO-04 | PM setujui ke tanggal baru (jadwal tujuan dibuat otomatis) | PM | 200, item lama SHIFTED_DAY, item baru TODO dengan sisa volume | UI web | P1 | |
| RO-05 | PM setujui ke tanggal sebelum tanggal asal | PM | 422 | API | P1 | |
| RO-06 | PM setujui ke tanggal yang sudah lewat | PM | 422 | API | P2 | |
| RO-07 | PM setujui ke jadwal tim lain | PM | 422 Tim tujuan harus sama | API | P1 | |
| RO-08 | PM tolak pindah hari | PM | 200, REJECTED_BY_PM, status IN_PROGRESS atau TODO | UI web | P1 | |
| RO-09 | PM tolak item yang tidak sedang WAITING_PM | PM | 409 | API | P2 | |
| RO-10 | PM setujui pindah hari proaktif tanpa request | PM | 200, APPROVED_BY_PM | API | P2 | |
| RO-11 | Pindah ke jadwal tujuan yang sudah COMPLETED | PM | 409 | API | P2 | |
| RO-12 | Ketua minta pindah hari untuk jadwal DRAFT | Ketua | 404 (jadwal belum dirilis) | API | P2 | |
| RO-13 | Ketua minta ulang setelah ditolak | Ketua | 200, WAITING_PM lagi | HP | P2 | |
| RO-14 | Setelah pindah, item yang bergantung ikut terhubung ulang | PM | dependen menunjuk item baru | API | P2 | |

## F. Koreksi laporan

| ID | Langkah | Aktor | Harapan | Tipe | Prioritas | Hasil |
|---|---|---|---|---|---|---|
| KO-01 | Minta koreksi untuk jadwal COMPLETED | Ketua | 201, REQUESTED, notifikasi ke PM | HP | P1 | |
| KO-02 | Minta koreksi untuk jadwal ONGOING | Ketua | 409 | API | P1 | |
| KO-03 | Minta koreksi kedua saat ada yang terbuka | Ketua | 409 CORRECTION_OPEN | API | P1 | |
| KO-04 | PM setujui koreksi | PM | 200, REVISING, jadwal ONGOING | UI web | P1 | |
| KO-05 | Kirim revisi tanpa laporan harian | Ketua | 422 REPORT_REQUIRED | API | P1 | |
| KO-06 | Kirim revisi dengan laporan | Ketua | 200, IN_REVIEW, revisi bertambah | HP | P1 | |
| KO-07 | PM terima revisi | PM | 200, ACCEPTED, jadwal COMPLETED | UI web | P1 | |
| KO-08 | PM kembalikan revisi | PM | 200, REVISING | UI web | P1 | |
| KO-09 | Dua tab PM memutuskan koreksi yang sama | PM | satu 200, satu 409 | UI web | P1 | |
| KO-10 | Ketua menutup jadwal lagi saat koreksi REVISING (lihat T7) | Ketua | Harapan 409 atau ditolak [VERIFIKASI] | API | P1 | |
| KO-11 | PM tolak permintaan koreksi | PM | 200, REJECTED, jadwal tetap COMPLETED | UI web | P2 | |
| KO-12 | Anggota minta koreksi | Anggota | 403 | API | P2 | |

## G. Lembur

| ID | Langkah | Aktor | Harapan | Tipe | Prioritas | Hasil |
|---|---|---|---|---|---|---|
| LB-01 | Ajukan 3 jam saat ONGOING | Anggota | 201, PENDING_PM | HP | P1 | |
| LB-02 | Ajukan 13 jam | Anggota | 422 | API | P1 | |
| LB-03 | Ajukan 0 jam | Anggota | 422 | API | P2 | |
| LB-04 | Ajukan saat jadwal APPROVED | Ketua | 409 | HP | P1 | |
| LB-05 | Ajukan kedua saat pengajuan pertama masih PENDING | Anggota | 409 | API | P1 | |
| LB-06 | PM yang juga anggota tim memutus lemburnya sendiri | PM | 403 | API | P2 | |
| LB-07 | PM divisi lain memutus lembur | PM divisi B | 403 | API | P1 | |
| LB-08 | PM menyetujui lembur | PM | 200, APPROVED, notifikasi ke pengaju | UI web | P1 | |
| LB-09 | Dua tab PM menyetujui lembur yang sama | PM | satu 200, satu 409 | UI web | P1 | |
| LB-10 | Rekap lembur oleh PM | PM | hanya cakupan yang diizinkan [VERIFIKASI] | UI web | P2 | |
| LB-11 | Rekap lembur oleh HR | HR | 403 | API | P2 | |

## H. Survei

| ID | Langkah | Aktor | Harapan | Tipe | Prioritas | Hasil |
|---|---|---|---|---|---|---|
| SV-01 | Isi titik ACS lengkap dengan foto, lalu kirim | Ketua | 200, SUBMITTED | HP | P1 | |
| SV-02 | Kirim survei tanpa titik | Ketua | 422 | HP | P1 | |
| SV-03 | Kirim survei tanpa foto slot wajib | Ketua | 422 PHOTOS_REQUIRED | HP | P1 | |
| SV-04 | Ubah titik setelah survei dikirim | Ketua | 409 | API | P1 | |
| SV-05 | Isi survei saat jadwal masih DRAFT | Ketua | 409 | API | P2 | |
| SV-06 | PM meninjau survei yang belum dikirim | PM | 409 | API | P2 | |
| SV-07 | PM kembalikan survei | PM | 200, DRAFT, ketua bisa mengisi ulang | UI web | P1 | |
| SV-08 | Buat rencana dari survei yang belum APPROVED | PM | 409 | API | P1 | |
| SV-09 | Buat rencana ke jadwal yang sudah APPROVED | PM | 409 | API | P1 | |
| SV-10 | Buat rencana ke jadwal divisi lain | PM | 422 | API | P2 | |
| SV-11 | Ekspor laporan survei saat masih DRAFT | PM | 409 SURVEY_NOT_SUBMITTED | API | P2 | |
| SV-12 | Anggota (bukan ketua) mengubah BoM | Anggota | 403 | API | P2 | |
| SV-13 | Anggota tim lain melihat survei tim ini | Anggota tim lain | 404 | API | P2 | |

## I. Order klien, ACC, dan BAST

| ID | Langkah | Aktor | Harapan | Tipe | Prioritas | Hasil |
|---|---|---|---|---|---|---|
| BA-01 | PM membuat order atas nama PM lain | PM | 403 | API | P1 | |
| BA-02 | OM membuat order di divisinya | OM | 201 | UI web | P1 | |
| BA-03 | ADMIN membuat order | ADMIN | 403 (cek peran di service) | API | P2 | |
| BA-04 | Ubah order yang sudah ditandatangani PM | PM | 409 ORDER_LOCKED | API | P1 | |
| BA-05 | Hapus order yang sudah ditandatangani ketua | PM | 409 | API | P1 | |
| BA-06 | Ketua tanda tangan tanpa ringkasan | Ketua | 422 | HP | P1 | |
| BA-07 | Ketua tanda tangan order yang tidak dikerjakan timnya | Ketua tim lain | 403 | API | P1 | |
| BA-08 | Anggota mencoba tanda tangan BAST | Anggota | 403 | HP | P1 | |
| BA-09 | PM tanda tangan sebelum ketua | PM | 409 LEADER_SIGNATURE_REQUIRED | API | P1 | |
| BA-10 | PM tanda tangan setelah ketua | PM | 200, pm_signed_at terisi, signature_hash terisi | UI web | P1 | |
| BA-11 | Ketua tanda tangan ulang sebelum PM | Ketua | 200, sidik direset | HP | P2 | |
| BA-12 | PNG tanda tangan lebih dari 300 KB | Ketua | 422 | HP | P2 | |
| BA-13 | Data URL tanda tangan bukan PNG | Ketua | 422 | API | P2 | |
| BA-14 | ACC DITOLAK_REWORK | PM | 200, item utama kembali TODO dengan source REWORK | UI web | P1 | |
| BA-15 | Tanda tangan BAST saat ACC masih MENUNGGU_ACC (lihat T10) | Ketua, PM | Harapan belum pasti [VERIFIKASI] | API | P1 | |
| BA-16 | PATCH status COMPLETED sebelum BAST (lihat T10) | PM | Harapan belum pasti [VERIFIKASI] | API | P2 | |
| BA-17 | PATCH status WAITING_ACC | PM | 422 INVALID_STATUS | API | P2 | |
| BA-18 | Anggota luar tim membuka detail order | Anggota luar tim | 404 | API | P1 | |
| BA-19 | HR membuka detail order | HR | 200 | UI web | P2 | |
| BA-20 | Tambah revisi klien dengan opsi survei | PM | 201, revisi dan tugas survei tercatat | UI web | P2 | |

## J. Verifikasi publik BAST

| ID | Langkah | Aktor | Harapan | Tipe | Prioritas | Hasil |
|---|---|---|---|---|---|---|
| VP-01 | Buka QR pada BAST yang sudah ditandatangani PM, h benar | Publik | 200, intact true | UI web | P1 | |
| VP-02 | h salah satu karakter | Publik | 404 | API | P1 | |
| VP-03 | h 63 karakter | Publik | 422 | API | P2 | |
| VP-04 | h mengandung karakter non-hex | Publik | 422 | API | P2 | |
| VP-05 | Data order diubah langsung di DB uji setelah PM tanda tangan | Publik | 200, intact false | API | P1 | |
| VP-06 | Order belum ditandatangani PM, h dari dokumen lama | Publik | 404 | API | P1 | |
| VP-07 | Buka alias /work-completion/:id | Publik | sama dengan VP-01 | UI web | P3 | |
| VP-08 | Buka /verify tanpa parameter h | Publik | 422 | API | P3 | |

## K. Ekspor dokumen

| ID | Langkah | Aktor | Harapan | Tipe | Prioritas | Hasil |
|---|---|---|---|---|---|---|
| EK-01 | Ekspor BAST .docx untuk order | PM | 200, berkas .docx, catatan ekspor tersimpan | UI web | P1 | |
| EK-02 | Ekspor BAST_PDF sebelum PM tanda tangan | PM | 409 NOT_SIGNED | UI web | P1 | |
| EK-03 | Ekspor BAST_PDF setelah PM tanda tangan | PM | 200, berkas .pdf ber-QR | UI web | P1 | |
| EK-04 | Ekspor SURVEY_REPORT untuk order tanpa item survei | PM | 422 NO_SURVEY_ITEMS | API | P2 | |
| EK-05 | Unduh ekspor milik PM lain | PM lain | 404 | API | P1 | |
| EK-06 | Unduh ekspor yang berkasnya hilang dari penyimpanan | PM | 404 FILE_GONE | API | P2 | |
| EK-07 | Rekap periodik dengan rentang 32 hari | PM | 422 | API | P1 | |
| EK-08 | Rekap periodik dengan tanggal akhir sebelum awal | PM | 422 | API | P2 | |
| EK-09 | Rekap periodik oleh FINANCE | FINANCE | 403 | API | P2 | |
| EK-10 | Ekspor slide progres .pptx | PM | 200, berkas .pptx | UI web | P2 | |
| EK-11 | Pratinjau laporan survei | PM | 200, PDF, tidak masuk registri ekspor | UI web | P2 | |

## L. Izin dan sesi umum

| ID | Langkah | Aktor | Harapan | Tipe | Prioritas | Hasil |
|---|---|---|---|---|---|---|
| IZ-01 | Akses endpoint jadwal tanpa token | Publik | 401 | API | P1 | |
| IZ-02 | Token kedaluwarsa saat membuka jadwal | HP | 401 lalu refresh otomatis, lalu berhasil | HP | P1 | |
| IZ-03 | Pakai ulang refresh token lama | API | 401, seluruh keluarga sesi dicabut | API | P1 | |
| IZ-04 | FINANCE membuat jadwal | FINANCE | 403 | API | P1 | |
| IZ-05 | ASSET membuka detail jadwal | ASSET | 404 | API | P2 | |
| IZ-06 | ADMIN_HR_GA membaca jadwal divisi | HR | 200 (logistik) | API | P2 | |
| IZ-07 | Ubah id jadwal di URL menjadi milik tim lain | Anggota | 404 | API | P1 | |
| IZ-08 | Ubah id jadwal yang belum dirilis di URL | Anggota | 404 | API | P1 | |
| IZ-09 | Cabut sesi dari perangkat lain, lalu lanjutkan pemakaian | Pengguna | sesi berikutnya 401 | UI web | P2 | |

## M. Batas input

| ID | Langkah | Aktor | Harapan | Tipe | Prioritas | Hasil |
|---|---|---|---|---|---|---|
| BT-01 | Judul atau nama jenis pekerjaan kosong | PM | 422 | UI web | P2 | |
| BT-02 | Daftar jadwal dengan rentang lebih dari 62 hari | PM | 422 Rentang tanggal tidak valid | API | P2 | |
| BT-03 | Pencarian lokasi dengan kurang dari 3 karakter | PM | 422 | API | P3 | |
| BT-04 | Lembur 12.0 jam lalu 12.5 jam | Anggota | 12.0 diterima, 12.5 ditolak 422 | API | P2 | |
| BT-05 | Progres completed_qty negatif | Anggota | 422 | API | P2 | |
| BT-06 | Latitude 91 pada lokasi jadwal | PM | 422 | API | P3 | |
| BT-07 | Radius lokasi 4 m | PM | 422 (minimum 10) | API | P3 | |
| BT-08 | Alasan pindah hari kosong atau spasi | Ketua | 422 | API | P2 | |
| BT-09 | Catatan tinjau absensi kosong | PM | 422 | API | P1 | |
| BT-10 | Unggah berkas di atas batas ukuran | Ketua | ditolak, batas perlu dipastikan [VERIFIKASI] | HP | P2 | |

## N. Perilaku manusia tidak normal

| ID | Langkah | Aktor | Harapan | Tipe | Prioritas | Hasil |
|---|---|---|---|---|---|---|
| HM-01 | Klik ganda Setujui jadwal | PM | satu 200, sisanya 409, tidak ada perubahan ganda | UI web | P1 | |
| HM-02 | Klik ganda Absen masuk | Anggota | satu sukses, sisanya 409 ALREADY_CHECKED_IN, satu baris saja | HP | P1 | |
| HM-03 | Klik ganda Selesaikan hari kerja | Ketua | satu 200, sisanya 409 | HP | P1 | |
| HM-04 | Klik ganda Kirim survei | Ketua | satu 200, sisanya 409 | HP | P1 | |
| HM-05 | Klik ganda Setujui lembur | PM | satu 200, sisanya 409 | UI web | P1 | |
| HM-06 | Absen masuk saat tanpa sinyal | Anggota | tersimpan offline, terkirim saat online, tidak dobel | HP | P1 | |
| HM-07 | Unggah foto progres saat tanpa sinyal | Anggota | masuk antrean, dicoba ulang, progres tidak hilang | HP | P1 | |
| HM-08 | Tekan Selesaikan hari kerja saat tanpa sinyal | Ketua | gagal dengan pesan, status tetap ONGOING | HP | P1 | |
| HM-09 | Refresh browser saat formulir jadwal terbuka | PM | draf hilang tanpa dobel, tidak ada jadwal ganda | UI web | P2 | |
| HM-10 | Tombol back setelah tanda tangan BAST | Ketua | tidak ada tanda tangan ganda, data tampil terkini | HP | P2 | |
| HM-11 | Refresh halaman verifikasi QR | Publik | hasil sama | UI web | P3 | |
| HM-12 | Aplikasi ditutup saat unggah foto | Anggota | foto kembali di antrean | HP | P2 | |
| HM-13 | Dua tab PM mengubah item yang sama | PM | konflik ditolak 409, tidak menimpa diam-diam [VERIFIKASI] | UI web | P2 | |
| HM-14 | Akurasi GPS turun ke 110 m di tengah absen | Anggota | diminta pindah ke tempat terbuka, absen belum tercatat | HP | P2 | |
