# 16 · Glosarium

Istilah yang dipakai di seluruh dokumen dan di dalam kode. Ditulis supaya orang yang baru
masuk tidak perlu menebak.

---

## Istilah bisnis

| Istilah | Arti | Di kode |
|---|---|---|
| **SK** | Surat Keputusan penugasan. Dokumen resmi yang menugaskan sebuah tim mengerjakan satu pekerjaan | `plan_document` (kind `INITIAL_ORDER`) |
| **Pekerjaan / Work plan** | Satu penugasan lengkap: tim, jadwal, tugas harian, laporan | `work_plan` |
| **Revisi** | Dokumen pengganti SK yang terbit karena ketua mengajukan banding | `plan_document` (kind `REVISION`) |
| **Adendum perpanjangan** | Dokumen tambahan yang memperpanjang jangka waktu pekerjaan | `plan_document` (kind `ADDENDUM`) |
| **Adendum personel** | Dokumen tambahan yang mengubah susunan tim atau mengganti ketua | `plan_document` (kind `PERSONNEL_ADDENDUM`) |
| **Banding / Appeal** | Ketua menolak SK dengan alasan, meminta PM merevisinya | transaksi `APPEAL` |
| **Snapshot** | Salinan beku isi dokumen pada saat terbit. Tidak pernah berubah | kolom `snapshot` (JSONB) |
| **Dokumen terkunci** | Versi dokumen yang sudah digantikan versi lebih baru | `document_is_locked()` |
| **Unit bisnis** | Divisi: CCTV_ACS, WALL_DISPLAY, FINANCE_ACCOUNTING, OPERATIONS, BIZDEV_COMMERCIAL | `business_unit` |
| **Geofence** | Lingkaran di sekitar lokasi proyek. Absen di luarnya ditandai untuk diperiksa | `site.location` + `radius_m` |
| **Swafoto** | Foto diri saat absen, diberi watermark waktu dan lokasi | `attendance.selfie_file_id` |
| **Lembur** | Jam kerja di luar jadwal, diajukan ketua, diperiksa Finance | `overtime_log` |
| **Insiden K3** | Kejadian keselamatan kerja. Lima kategori | `incident_report` |
| **Offboarding** | Proses karyawan keluar; mencabut seluruh akses dan sesi | transaksi `OFFBOARD` |

## Peran

| Peran | Siapa | Catatan penting |
|---|---|---|
| **PM** | Manajer proyek, **per unit bisnis** | Hanya melihat pekerjaan di unitnya |
| **LEADER** | Ketua tim **menurut SK yang berlaku** | Bukan label akun — berasal dari penugasan |
| **MEMBER** | Anggota tim menurut SK | Sama, berasal dari penugasan |
| **FINANCE** | Akuntansi | Memeriksa absensi bertanda dan lembur |
| **HR** | Pengelola SDM | Verifikasi dokumen pribadi, promosi, offboarding |
| **ASSET** | Logistik | Melepas dan memeriksa pengembalian aset |
| **OPS** | Manajer operasional | Pemantauan lintas unit, umumnya baca saja |

---

## Istilah teknis

| Istilah | Arti |
|---|---|
| **RLS** | *Row Level Security* — PostgreSQL menyaring baris berdasarkan konteks sesi. Jaring pengaman bila kode lupa memfilter |
| **`SET LOCAL`** | Menyetel variabel yang hanya berlaku dalam satu transaksi. Dasar kerja RLS di sini |
| **Penguncian optimistis** | Klien mengirim `row_version` yang dibacanya; bila sudah berubah, penyimpanan ditolak |
| **Idempoten** | Operasi yang bila diulang menghasilkan hal sama, bukan duplikat. Penting untuk sinkronisasi luring |
| **`client_op_id`** | UUID yang dibuat perangkat untuk setiap aksi luring, supaya pengiriman ulang tidak menggandakan data |
| **Embedding** | Deretan angka (512) yang mewakili wajah. Bukan foto, dan tidak bisa dikembalikan menjadi foto |
| **HNSW** | Jenis indeks pgvector untuk pencarian kemiripan yang cepat |
| **Kemiripan kosinus** | Ukuran kemiripan dua vektor, 0–1. Makin mendekati 1 makin mirip |
| **FAR / FRR** | *False Accept Rate* (orang lain lolos) / *False Reject Rate* (orang benar ditolak). Dipakai mengkalibrasi ambang wajah |
| **Liveness** | Deteksi apakah yang di depan kamera orang sungguhan, bukan foto |
| **JCS / RFC 8785** | Cara membakukan bentuk JSON agar hash-nya selalu sama |
| **KMS** | *Key Management Service* — tempat kunci privat disimpan; kunci tidak pernah keluar dari sana |
| **`kid`** | Penanda kunci di dalam JWT/tanda tangan, supaya kunci lama tetap bisa memverifikasi tanda tangan lama |
| **Rotasi refresh token** | Setiap pemakaian refresh token menghasilkan token baru; token lama mati |
| **Reuse detection** | Deteksi refresh token lama yang dipakai lagi — tanda pencurian; seluruh rantai perangkat dicabut |
| **Partisi bulanan** | Tabel besar dipecah per bulan supaya kueri dan pemeliharaan tetap cepat |
| **Exclusion constraint** | Batasan PostgreSQL yang mencegah dua baris beririsan, mis. satu aset di dua pekerjaan pada rentang yang sama |
| **Magic bytes** | Beberapa byte awal berkas yang menunjukkan jenis aslinya — lebih dipercaya daripada ekstensi nama |
| **URL bertanda tangan** | Tautan berumur pendek ke berkas di MinIO, hanya dibuat setelah otorisasi diperiksa |
| **Tailnet** | Jaringan privat Tailscale. Layanan di dalamnya tidak terlihat dari internet |

---

## Istilah frontend

| Istilah | Arti |
|---|---|
| **Mobile-first** | Menulis gaya untuk ponsel dulu, lalu menambah untuk layar lebih besar |
| **Atomic design** | Penataan komponen: atoms → molecules → organisms → templates → pages |
| **Atom** | Komponen paling kecil: tombol, input, badge |
| **Molecule** | Gabungan beberapa atom: kolom pencarian, keadaan kosong |
| **Organism** | Blok besar: tabel data, form lengkap |
| **Template** | Kerangka halaman tanpa isi |
| **State server** | Data yang sumbernya API — dikelola TanStack Query |
| **State klien** | Data yang hanya hidup di layar: filter, langkah wizard, draf — dikelola Zustand |
| **Selector** | Mengambil sebagian kecil dari store supaya komponen tidak ikut render saat bagian lain berubah |
| **shadcn/ui** | Pustaka komponen yang disalin ke dalam repo, bukan dipasang sebagai dependensi |
| **cva** | *class-variance-authority* — mendefinisikan varian komponen secara rapi |
| **Skeleton** | Kerangka abu-abu berbentuk isi yang sedang dimuat |

---

## Status yang sering muncul

### Pekerjaan (`plan_status`)
`DRAFT` (rancangan) · `PUBLISHED` (sudah terbit, menunggu ketua) · `ACCEPTED` (diterima ketua) ·
`APPEALED` (ketua mengajukan banding) · `IN_PROGRESS` (sedang berjalan) ·
`COMPLETION_REVIEW` (menunggu persetujuan penyelesaian) · `COMPLETED` (selesai) ·
`CANCELLED` (dibatalkan)

### Dokumen (`document_status`)
`AWAITING_ACCEPTANCE` (menunggu penerimaan) · `EFFECTIVE` (berlaku) ·
`SUPERSEDED` (digantikan versi baru) · `REJECTED` (ditolak) · `WITHDRAWN` (ditarik penerbit)

### Absensi (`attendance_status`)
`AUTO_VALID` (sah otomatis) · `NEEDS_REVIEW` (perlu diperiksa manusia) ·
`APPROVED` (disetujui Finance) · `REJECTED` (ditolak)

### Tanda tangan (`signature_state`)
`VALID` (sah) · `REVOKED` (dicabut) · `KEY_EXPIRED` (kunci kedaluwarsa) ·
`DOCUMENT_CHANGED` (isi dokumen berubah setelah ditandatangani) · `UNKNOWN` (tidak dikenal)

### Wajah (`face_check_result`)
`MATCH` (cocok) · `NO_MATCH` (tidak cocok) · `LOW_QUALITY` (gambar tidak memadai) ·
`NOT_ENROLLED` (belum mendaftar) · `SKIPPED` (dilewati, mis. layanan mati)

**Catatan penamaan:** nilai enum selalu Bahasa Inggris di kode; label Bahasa Indonesia untuk
pengguna disimpan di satu berkas (`lib/format/labels.ts`), tidak pernah ditulis langsung di
dalam komponen.
