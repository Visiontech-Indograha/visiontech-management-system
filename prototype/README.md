# Visiontech Operational Workspace (VMS v2)

Prototipe interaktif untuk manajemen operasional, penugasan, dan logistik Visiontech Indograha.

## Cara Menjalankan

Aplikasi ini berjalan 100% secara luring (offline) di peramban Anda. Tidak memerlukan server, koneksi internet, Node.js, npm, maupun *build step* apa pun.
1. Ekstrak *source code*.
2. Klik ganda file `index.html` untuk membukanya di peramban modern (Chrome, Edge, Firefox, atau Safari).

## Peran & Hak Akses

Saat pertama dibuka, pemilihan ada di launcher bagian "01 - Pilih tampilan" (Desktop/Mobile), lalu "02 - Masuk sebagai".

| Peran | ID | Nama Aktor (Demo) | Deskripsi Hak Akses & Tugas |
| :--- | :--- | :--- | :--- |
| **Project Manager** | `pm-cctv`<br>`pm-wall` | Ramadani (CCTV) / Handoko (Wall Display) | Membuat draft pekerjaan, menerbitkan SK, merespons kendala & adendum, serta menutup pekerjaan. |
| **Ketua Tim** | `leader`<br>`emp-032` | Rouzi Dewantoro / Ahmadi | Meninjau SK, melakukan *check-in*, mengisi *checklist* & laporan harian, mengajukan perpanjangan, serta mengembalikan aset. |
| **Anggota** | `member` | Rusyidi Siregar | Melakukan presensi masuk/keluar harian, memeriksa kelayakan kendaraan di tab Sumber daya (jika ditunjuk sebagai pengemudi), serta melihat SK. |
| **HR / Personalia** | `hr` | Petugas HR | Memverifikasi unggahan dokumen SIM/Sertifikat karyawan, serta mengubah mutasi jabatan / *offboarding*. |
| **Petugas Aset** | `asset` | Hernita | Mengalokasikan persediaan alat & kendaraan (hanya jika ada pengemudi ber-SIM valid), dan memverifikasi pengembalian aset. |
| **Finance** | `finance` | Sri Wildani | Meninjau pengecualian presensi (jarak lokasi yang terlalu jauh dari batas toleransi). |
| **Operasional** | `ops` | Ade Candra | Memiliki pandangan lintas unit terhadap seluruh laporan, sumber daya, timeline, dan data audit organisasi. |

## Alur Utama Simulasi (Langkah demi Langkah)

1. **Persiapan:** PM menerbitkan SK dari draft work plan.
2. **Penerimaan:** Ketua tim menyetujui SK yang terbit.
3. **Pelaksanaan:** **PENTING:** Gunakan menu **Panduan simulasi** (tautan "Panduan & tanggal simulasi" di footer/ringkasan, dan "Menu lainnya" di mobile) untuk memajukan "Tanggal Simulasi" agar sesuai dengan masa penugasan. Laporan tidak bisa diisi sebelum hari kerja tiba.
4. **Laporan & Absensi:** Anggota melakukan *check-in/out*. Ketua tim mencentang tugas dan mengetik ringkasan laporan.
5. **Perubahan Rencana (waktu):** Ketua tim dapat mengajukan perpanjangan waktu. PM menyetujuinya, lalu Ketua tim menerima Adendum baru tersebut (otomatis memicu verifikasi ulang kedaluwarsa SIM pengemudi).
6. **Perubahan Rencana (personel):** PM menekan **"Adendum personel"** di halaman pekerjaan untuk mengganti ketua tim atau menambah/mengeluarkan anggota, disertai alasan. Adendum personel terbit sebagai versi dokumen baru dan **belum berlaku** sampai diterima. Jika ketua diganti, **ketua barulah** yang menerima atau menolaknya. Anggota yang masih tercatat sebagai pengemudi kendaraan tidak bisa dikeluarkan sebelum kendaraan dilepas atau dikembalikan.
7. **Penutupan & Aset:** Ketua tim mengajukan pengembalian aset (lalu diverifikasi oleh Petugas Aset).
8. **Penyelesaian:** Setelah semua laporan disetujui, tidak ada perubahan tertunda, dan laporan akhir diisi, Ketua tim mengirim Laporan Akhir. PM resmi menutup pekerjaan setelah semua aset terverifikasi kembali.

*Alur Dokumen:* Karyawan (misal Anggota) mengunggah perpanjangan dokumen/SIM -> diverifikasi oleh HR -> status dokumen berubah menjadi Aktif.

*Alur Insiden & Lembur:* Ketua atau anggota menekan tombol merah **"Lapor Insiden/HSE"** pada pekerjaan berjalan (kategori K3 atau Aset, tingkat keparahan, uraian, dan bukti). Insiden masuk antrean PM/Operational Manager, dan untuk kategori Aset juga ke Petugas Aset, lalu ditutup dengan catatan penyelesaian. Ketua tim mengajukan **lembur** (jam dan alasan) yang ditinjau PM/Operational Manager; lembur yang disetujui muncul pada rekap Finance.

## Absensi, Lokasi, dan Mode Luring

- **Jarak lokasi** dihitung dengan rumus Haversine antara titik check-in dan koordinat lokasi proyek. Koordinat dapat diambil dari **GPS perangkat** (jika Anda mengizinkan) atau memakai **preset simulasi** (di lokasi, 150 m, 10 km).
- Radius toleransi **100 m**. Di luar radius, check-in dari HP **wajib melampirkan swafoto** kamera depan, dan hasilnya berstatus "Perlu review" untuk ditinjau Finance.
- **Jam absensi** memakai tanggal simulasi dengan jam nyata saat tombol ditekan. Jika masuk melewati 08.00 WIB atau pulang sebelum 17.00 WIB, muncul peringatan di dalam aplikasi. Absensi yang ditolak Finance boleh diajukan ulang di hari yang sama, dan catatan lamanya tetap tersimpan.
- **Swafoto** memakai `capture="user"`, yang hanya menyatakan preferensi kamera depan. Peramban tertentu tetap mengizinkan memilih berkas dari galeri, jadi ini bukan jaminan foto diambil saat itu juga.
- **Mode luring:** saat jaringan terputus, absensi dan laporan tetap tersimpan di perangkat dan masuk **antrean sinkronisasi** (`offline_queue`), dengan indikator "Luring · N antrean". Saat jaringan pulih, antrean dikosongkan dan tercatat di Jejak aktivitas sebagai "Sinkronisasi transaksi luring". Karena prototipe ini tidak punya server, "sinkronisasi" berarti transaksi tercatat permanen di penyimpanan perangkat ini, bukan terkirim ke sistem pusat. Jika penyimpanan peramban penuh atau ditolak, antrean **tidak** dikosongkan dan muncul peringatan. Mode ini bisa dicoba lewat tombol di **Panduan simulasi** tanpa harus memutus jaringan sungguhan.
- **Service Worker (`sw.js`)** hanya aktif jika aplikasi dibuka lewat `http(s)`/localhost, dan dilewati saat dibuka langsung dari berkas (`file://`).

## Versi Dokumen

Setiap penerbitan SK, revisi, adendum waktu, dan adendum personel menambah **versi baru** pada pekerjaan yang sama. Versi lama otomatis **terkunci sebagai riwayat**: isinya tetap seperti saat diterbitkan dan tidak ikut berubah ketika data karyawan atau jadwal berubah. Pilih versi lewat dropdown di penampil dokumen; versi lama ditandai "terkunci (riwayat)" dan tidak memiliki tombol tindakan.

## Penyimpanan & Keamanan Data

- **Penyimpanan Lokal:** Seluruh data teks persisten tersimpan di `localStorage` peramban Anda dengan kunci `visiontech.native.v4`. Data lampiran berkas tersimpan di `IndexedDB` browser. Semua data aman dan tidak ada transmisi keluar.
- **Pembersihan / Reset:** Untuk mengulang dari awal, gunakan tombol "Reset simulasi" yang tersedia di halaman Panduan simulasi.
- **Snapshot Otomatis:** Setiap SK dan Adendum yang diterbitkan akan dipotret (*snapshot*). Setiap perubahan data karyawan pasca-terbit tidak akan memengaruhi riwayat dokumen cetak lama.
- **Batasan Simulasi:** Prototipe ini murni lingkungan *front-end* HTML/CSS/JS (tanpa *backend*). Beberapa fitur dunia nyata seperti verifikasi biometrik, pengambilan GPS paksa, dan stempel tanda tangan resmi disimulasikan.

## Fitur Cetak (Print to PDF)

Setiap Surat Keputusan (SK), Adendum, Laporan Mingguan, dan Laporan Akhir dapat di-preview dan dicetak ke ukuran kertas A4.
- Tekan **Cetak / Simpan PDF** dari halaman dokumen, lalu ubah orientasi halaman. (SK/adendum/laporan harian = Portrait; laporan akhir presentasi = Landscape).
- *Print stylesheet* (`css/documents.css`) otomatis membersihkan elemen aplikasi sehingga hanya isi laporan/dokumen yang keluar.

## Pengujian Terotomasi (Bagi Developer)

Jika sistem Anda memiliki instalasi Node.js, Anda dapat menguji validitas bisnis *logic*:
1. **Domain Logic:** Jalankan `node --test tests/domain.test.cjs` (memastikan aturan-aturan bisnis dan relasi otorisasi berjalan persis).
2. **End-to-End Test (Playwright):** Jalankan `node tests/browser.mjs`. (Dibutuhkan set variabel lingkungan khusus seperti `PLAYWRIGHT_MODULE`).
3. **Syntax Check:** `node --check js/*.js`.

---

## Rencana Pengembangan Lanjutan (belum diterapkan)

> **Status:** bagian ini berisi **usulan** yang belum diimplementasikan di kode saat ini. Jangan anggap fitur di bawah sudah tersedia sebelum ada perubahan kode dan pengujian yang membuktikannya.
>
> **Angka dan istilah di bagian ini sudah digantikan oleh keputusan yang berlaku:** radius toleransi **100 m** (bukan 500 m); versi SK memakai `plan.documents[]` beserta snapshot (bukan penyimpanan terpisah `sk_versions`); GPS **sudah** dipakai secara opsional dengan fallback simulasi; dan atribut `capture="user"` hanya menyatakan *preferensi* kamera depan — sesuai [spesifikasi HTML Media Capture](https://www.w3.org/TR/html-media-capture/#the-capture-attribute), peramban boleh tetap mengizinkan pemilihan berkas dari galeri, jadi ini bukan pemblokiran galeri dan bukan anti-pemalsuan GPS.
>
> **Catatan kesesuaian dengan prototipe saat ini:**
> - Service Worker tidak berjalan dari `file://`. Mode PWA membutuhkan `http://localhost` atau HTTPS, sehingga bertentangan dengan syarat "cukup klik ganda `index.html`". Tetapkan dulu cara membuka aplikasi yang diinginkan.
> - Prototipe saat ini sengaja **tidak** memakai GPS, kamera, atau biometrik nyata (lihat Batasan Simulasi). Geofencing dan swafoto di bawah akan mengubah batas tersebut.
> - Nama menu di aplikasi adalah **"Panduan simulasi"**, bukan "Pengaturan". Nomor SK memakai format seperti `012/SK-CCTV-ACS/2026`, bukan `SK-001`. Riwayat versi SK/adendum sudah tersimpan per dokumen (`plan.documents[]` dengan snapshot dan status `SUPERSEDED` untuk versi lama).
> - Ekstensi Claude in Chrome tidak dapat mengubah tab Network DevTools menjadi "Offline" atau menjalankan perintah CDP `Emulation.setEmulatedMedia`. Skenario 1 dan 5 perlu disimulasikan dengan cara lain (misalnya memicu event `offline`/`online`, atau memeriksa PDF hasil `page.pdf()` di Playwright).

### Bagian 1: Rincian Perubahan Logika Sistem & UI (Codebase)

Karena aplikasi berjalan murni di front-end (HTML/CSS/JS dengan `localStorage` dan `IndexedDB`), berikut struktur perubahan yang perlu diterapkan pada source code.

#### 1. Perubahan Struktur Basis Data (Storage Schema)

Tambahkan entri baru pada key `visiontech.native.v4` di `localStorage`:

- `offline_queue`: array untuk menyimpan data presensi dan laporan saat jaringan putus.
- `incident_reports`: array khusus laporan darurat (K3/Aset) yang terpisah dari siklus laporan mingguan.
- `overtime_logs`: data jam lembur yang terikat pada ID SK dan ID Karyawan.
- `sk_versions`: objek yang menyimpan riwayat SK (v1, v2, dst.) agar SK lama menjadi immutable (tidak bisa diedit) saat terjadi Adendum SDM/Waktu.

#### 2. Implementasi Service Worker (untuk Mode Luring)

- Buat file `sw.js` untuk caching aset statis (HTML/CSS/JS) agar aplikasi tetap bisa dibuka tanpa internet (PWA — Progressive Web App).
- Tambahkan event listener `online` dan `offline` di JavaScript utama. Saat status berubah menjadi online, jalankan fungsi `syncOfflineData()` yang membaca `offline_queue` dan memindahkannya ke tabel utama.

#### 3. Modifikasi Logika Geofencing & Absensi

- Gunakan Rumus Haversine di JavaScript untuk menghitung jarak antara koordinat check-in karyawan dengan koordinat proyek yang tercatat di SK.
- Jika jarak > radius toleransi (misal 500 meter), munculkan UI prompt wajib swafoto (selfie).
- Gunakan atribut `capture="user"` pada tag `<input type="file" accept="image/*">` agar OS langsung membuka kamera depan dan memblokir opsi galeri foto.

#### 4. Perubahan UI/Dasbor

- **Ketua Tim:** tambah tombol merah darurat "Lapor Insiden/HSE" di halaman laporan utama.
- **Project Manager:** tambah menu "Adendum Personil" di dalam detail SK yang sedang berjalan untuk melakukan drop/replace anggota.
- **Finance & HR:** tambah label peringatan "Kedaluwarsa < 7 Hari" pada tabel master data karyawan.

### Bagian 2: Skrip & Prompt E2E untuk Claude di Chrome

Berikut template instruksi yang dapat disalin langsung ke Claude saat sesi pengujian End-to-End di Chrome. Prompt ini meminta Claude bertindak sebagai QA Automation.

#### Skenario 1: Menguji Offline Mode & Sinkronisasi

> "Claude, kita akan menguji fitur Offline Sync.
> 1. Gunakan Chrome DevTools, navigasi ke tab Network, dan ubah kondisi menjadi 'Offline'.
> 2. Login sebagai 'Ketua Tim' (Rouzi Dewantoro).
> 3. Buat satu laporan harian, centang 2 checklist pekerjaan, dan tekan 'Simpan'.
> 4. Asersikan (pastikan) muncul notifikasi 'Tersimpan secara lokal (Luring)'.
> 5. Cek `localStorage.getItem('visiontech.native.v4')` dan pastikan data masuk ke dalam array `offline_queue`.
> 6. Kembalikan Network ke 'Online'.
> 7. Asersikan bahwa UI otomatis memperbarui status menjadi 'Tersinkronisasi' dan isi `offline_queue` menjadi kosong."

#### Skenario 2: Menguji Geofencing & Pemblokiran Fake GPS

> "Claude, mari uji validasi lokasi presensi.
> 1. Injeksi skrip ini ke console untuk memanipulasi Geolocation API agar mengembalikan lokasi di luar radius proyek (misal: jarak 10 km dari lokasi SK):
>    `navigator.geolocation.getCurrentPosition = success => success({coords: {latitude: -6.200000, longitude: 106.816666}});`
> 2. Login sebagai 'Anggota' (Rusyidi Siregar) dan klik tombol 'Check-In'.
> 3. Asersikan bahwa sistem MENOLAK check-in otomatis dan memunculkan modal peringatan 'Di Luar Radius Toleransi'.
> 4. Pastikan di dalam modal tersebut, elemen `<input type="file" capture="user">` muncul untuk memaksa pengambilan swafoto. Ambil tangkapan layar (screenshot) bukti modal ini."

#### Skenario 3: Menguji "Time Travel" & Masa Berlaku Dokumen

> "Claude, kita akan menguji Time Travel menggunakan fitur 'Tanggal Simulasi'.
> 1. Login sebagai 'Petugas Aset' (Hernita). Catat status SIM milik Pengemudi X (pastikan statusnya 'Aktif').
> 2. Klik menu 'Pengaturan' di footer (di aplikasi saat ini: **Panduan simulasi**), dan ubah 'Tanggal Simulasi' menjadi H+60 hari dari sekarang.
> 3. Refresh halaman Master Aset & Kendaraan.
> 4. Asersikan bahwa status Pengemudi X otomatis berubah menjadi 'SIM Kedaluwarsa' dan tombol 'Alokasikan Kendaraan' padanya menjadi 'Disabled' (tidak bisa diklik).
> 5. Cek console Chrome dan pastikan tidak ada error JavaScript (seperti NaN atau Uncaught Exception) akibat lompatan tanggal ini."

#### Skenario 4: Menguji Keamanan Hak Akses (Immutable SK & Adendum)

> "Claude, mari uji sistem Adendum dan Versioning.
> 1. Login sebagai 'Project Manager' dan buat Adendum Waktu untuk 'SK-001'.
> 2. Saat Adendum disetujui, sistem harus mencetak 'SK-001-REV1'.
> 3. Buka objek data di localStorage. Cari entri 'SK-001' (versi awal).
> 4. Asersikan bahwa atribut `is_locked` atau status pada SK versi awal bernilai `true` atau 'Archived'.
> 5. Coba lakukan modifikasi paksa pada SK awal melalui console dengan `localStorage.setItem(...)`.
> 6. Reload halaman, dan asersikan bahwa UI tetap menggunakan 'SK-001-REV1' sebagai acuan operasional dan tidak mempedulikan data SK lama yang sudah dikunci."

#### Skenario 5: Pengecekan CSS Print (Cetak PDF)

> "Claude, uji layout cetak dokumen SK.
> 1. Buka halaman Detail SK yang sudah disetujui.
> 2. Jalankan perintah CDP (Chrome DevTools Protocol): `Emulation.setEmulatedMedia {media: 'print'}`.
> 3. Ambil tangkapan layar penuh.
> 4. Analisis tangkapan layar tersebut: asersikan bahwa Navbar, Sidebar, tombol 'Cetak PDF', dan Footer benar-benar TIDAK TERLIHAT. Hanya Kop Surat, Nomor SK, Tabel Tugas, dan Tanda Tangan yang boleh muncul di halaman."

### Rangkuman Rekomendasi Eksekusi

- Buat file `e2e_prompts.md` di repositori yang berisi instruksi-instruksi di atas.
- Saat membuka Claude dengan kapabilitas Computer Use atau koneksi Chrome, panggil file tersebut: *"Baca panduan E2E di e2e_prompts.md dan jalankan Skenario 1 sampai 5 secara berurutan, lalu berikan saya laporan kegagalannya beserta screenshot."*
- **Fokus pada edge case:** karena happy path (alur normal) biasanya sudah lancar, tugaskan Claude secara spesifik untuk terus mencari celah di zona transisi (misal: saat jaringan mati-nyala, saat tanggal diubah tepat jam 23:59, atau saat dua role dibuka di dua tab berbeda).
