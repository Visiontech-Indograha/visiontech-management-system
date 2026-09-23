# Serah terima — Visiontech native prototype

**Tanggal:** 22 September 2026, Asia/Jakarta.  
**Workspace:** `C:\Users\ageng\visiontech-vms\visiontech-V2`.  
**Status:** Implementasi dilanjutkan oleh Gemini (implementasi) dan Claude (QA via Chrome), serta telah melalui putaran QA K-002 - K-010. Pembangunan versi native sudah berjalan dan pengujian utama lulus.

## 1. Tujuan pengguna dan keputusan yang sudah disepakati

Pengguna awalnya meminta prototipe lebih ringan dan hemat token. Versi sebelumnya memakai React/Vite, kemudian sempat diubah menjadi HTML/CSS statis dengan banyak layar dalam satu halaman. Pengguna menilai hasil itu membingungkan karena peran bercampur, mobile tidak benar-benar dibedakan, dan pratinjau dokumen belum lengkap.

Instruksi berikutnya adalah membersihkan isi proyek dan membangun ulang dengan **HTML, CSS, JavaScript biasa**, tanpa React/Vite. Pengguna sudah menyetujui rencana dan meminta implementasinya.

Keputusan eksplisit:

- **Desktop dan mobile terpisah**, bukan hanya perubahan responsif otomatis. Halaman awal memilih perangkat dan identitas/peran.
- Peran mempunyai menu dan tindakan masing-masing. Pergantian peran dilakukan melalui pemilih identitas; tidak otomatis melompat ke peran lain ketika melakukan transaksi.
- Data simulasi dibagikan antarperan dan antarpratinjau perangkat di browser yang sama.
- Formulir harus benar-benar mengubah data, antrean persetujuan, status pekerjaan, dan riwayat.
- SK, revisi, adendum, laporan, serta dokumen karyawan harus dapat dipratinjau dengan data yang sesuai.
- Bisa dibuka langsung dengan `file://` melalui `index.html`. Tidak wajib npm, server, build, atau internet.
- Tidak ada backend, autentikasi nyata, GPS, biometrik, mesin absensi nyata, tanda tangan resmi, atau QR resmi. Hal-hal tersebut tetap simulasi dan tidak boleh diklaim sebagai layanan nyata.

Permintaan terakhir pengguna: **berhenti di titik ini dan buat catatan lengkap untuk agen berikutnya**. Setelah menulis file serah terima ini tidak dilakukan implementasi tambahan.

## 2. Pembersihan workspace dan lokasi referensi lama

Data studi kasus dan aturan bisnis diambil sebelum pembersihan. Dua percobaan penghapusan massal ditolak oleh pemeriksaan otomatis tool dengan pesan `blocked by policy`. Tidak dilakukan upaya menghapus melalui tool lain.

Sebagai alternatif yang dapat dibatalkan, isi lama dipindahkan ke folder sementara di luar workspace:

```text
C:\Users\ageng\AppData\Local\Temp\visiontech-previous-7aee2c81054f46cabb579053e6b982d3
```

Di sana masih ada implementasi React lama, `node_modules`, `dist`, hasil screenshot lama, referensi SQL/API, `conversation-recovered.txt`, README lama, dan prototipe HTML statis lama. **Jangan menganggap file lama sudah dihapus permanen.** Workspace aktif tidak lagi memuat React, Vite, manifest npm, atau dependensi tersebut.

Referensi yang berguna bila perlu menyelidiki kebutuhan asli:

- `conversation-recovered.txt`: percakapan studi kasus yang dipulihkan.
- `recovered/`: SQL dan contoh kontrak API, hanya referensi, bukan backend yang berjalan.
- `src/domain.js`: aturan bisnis implementasi sebelumnya.
- `tests/domain.test.js`: pengujian aturan bisnis sebelumnya.

Folder pemeriksaan terpisah:

```text
C:\Users\ageng\AppData\Local\Temp\visiontech-native-checks
```

Berisi salinan tool `playwright-core`, `playwright`, sumber aturan/test asli, dan hasil pemeriksaan versi baru. Folder sementara bisa hilang; prototipe aktif tidak bergantung kepadanya untuk berjalan.

## 3. Struktur implementasi saat ini

```text
index.html
css/
  base.css
  workspace.css
  documents.css
js/
  domain.js
  storage.js
  ui.js
  workplans.js
  people.js
  operations.js
  documents.js
  app.js
tests/
  domain.test.cjs
  browser.mjs
README.md
KOMUNIKASI.md
AGENTS.md
GEMINI.md
agent.md
```

Dokumen panduan, README pengguna, dan riwayat komunikasi sudah disertakan pada pembaruan terbaru.

### Tanggung jawab file

| File | Isi utama |
|---|---|
| `index.html` | Titik masuk, stylesheet, script klasik `defer`, container aplikasi, notifikasi, dialog. |
| `css/base.css` | Token warna, tipografi, tombol, formulir, tabel, panel, dialog, notifikasi. |
| `css/workspace.css` | Launcher, sidebar desktop, dashboard, menu bawah mobile, kartu, responsivitas. |
| `css/documents.css` | Penampil A4, pembesaran, lampiran, dan aturan cetak. |
| `js/domain.js` | Data awal dan mesin transisi bisnis murni dalam `window.VTDomain`; diadaptasi dari aturan lama tanpa React. |
| `js/storage.js` | Penyimpanan state, konflik revisi, kegagalan penyimpanan, IndexedDB lampiran, berkas contoh, reset. |
| `js/ui.js` | Objek aplikasi `window.VT` dan helper `window.VTUI`: escaping, format, form, badge, tabel, tombol, ikon SVG. |
| `js/workplans.js` | Daftar, editor draft, detail, checklist/laporan, sumber daya pekerjaan, daftar dokumen, handler formulir. |
| `js/people.js` | Organisasi, daftar karyawan, profil, dokumen pribadi, verifikasi, penempatan/offboarding. |
| `js/operations.js` | Absensi, inventaris, alokasi/pengembalian, timeline, aktivitas. |
| `js/documents.js` | Isi SK/adendum/laporan, pilihan versi, zoom, pratinjau gambar/PDF, download lampiran. |
| `js/app.js` | Router, pemilih peran/perangkat, menu per peran, layout, dashboard, antrean, dialog, event delegation, eksekusi transaksi. |

Semua script adalah JavaScript browser biasa. Tidak ada ES module runtime atau `fetch` file lokal, sehingga tidak membutuhkan server. Font menggunakan font sistem dan ikon dibuat dengan SVG lokal.

Ukuran seluruh file aplikasi saat serah terima sekitar 150–170 KB sebelum kompresi, ditambah test. Tidak perlu mengembalikan proyek besar untuk menjalankannya.

## 4. Router, state, dan pola pengembangan

### Navigasi

Format hash:

```text
#/                                  pemilih perangkat dan peran
#/desktop/pm-cctv/home               dashboard PM CCTV
#/mobile/leader/home                dashboard mobile ketua CCTV
#/desktop/pm-cctv/plan/wp-001        detail pekerjaan
#/desktop/pm-cctv/plan/wp-001/days   checklist dan laporan
#/desktop/pm-cctv/document/wp-001/<documentId>
#/mobile/member/employee-document/member/<documentId>
```

Desktop dan mobile menggunakan satu titik masuk agar data `file://` berasal dari lokasi file yang sama, tetapi shell dan navigasinya berbeda. Mobile di desktop ditampilkan dalam bingkai maksimum sekitar 440 px; pada HP memakai lebar layar.

Bagian penting pada `window.VT`:

- `state`: data aplikasi saat ini.
- `actor`: identitas aktif dari daftar aktor yang dikenal.
- `route`: `device`, `actorId`, `page`, `args`.
- `views`: registry fungsi pembentuk halaman.
- `forms`: registry handler submit.
- `run(type, payload)`: menjalankan domain transition, menyimpan state, merender ulang, dan memberi notifikasi.
- `go(...parts)`: navigasi dalam perangkat dan aktor yang sama.
- `queue()`: antrean aktual sesuai peran.
- `dialog`, `closeDialog`, `notify`, `uploadFiles`: helper interaksi.

`VTDomain` menyediakan `actors`, `units`, `createInitialState`, `can`, `transition`, dan `visiblePlans`. `transition` mengkloning input: berhasil mengembalikan `{ state, message }`; gagal `{ error }` tanpa memutasi state asal.

UI memakai event delegation (`data-command`, `data-ui`, `data-form`) sehingga tidak membutuhkan binding ulang setiap komponen. Nilai pengguna yang dirender sebagai HTML harus tetap melewati `VTUI.esc`.

### Penyimpanan

- `localStorage`: key **`visiontech.native.v4`**, `schemaVersion: 4`, revisi state bertambah setiap transaksi.
- `IndexedDB`: database **`visiontech.native.files.v2`** (sesuai `js/storage.js`; nama ini tidak ikut berubah saat schema state naik ke v4), object store **`files`**.
- Metadata lampiran: `{ id, name, type, size? }`. Blob disimpan terpisah dari JSON state.
- Maksimum ukuran upload: **10 MB per berkas**; helper upload membatasi 10 berkas per pengajuan.
- File contoh `sample-certificate` dan `sample-evidence` dibuat sebagai Blob SVG berlabel simulasi; tidak perlu upload atau berkas eksternal.
- Gambar PNG/JPEG/GIF/WebP/BMP dipratinjau; SVG hanya contoh bawaan yang ditampilkan. SVG upload arbitrer dan format lain disediakan sebagai unduhan.
- PDF memakai penampil bawaan browser melalui `<object>`, dengan tautan download sebagai alternatif.
- Jika JSON rusak atau penyimpanan tidak tersedia/penuh, aplikasi menampilkan peringatan dan memakai sesi memori.
- Konflik revisi antar-tab ditolak. Pengguna diminta muat ulang sebelum mengulangi transaksi.
- Reset memakai dialog konfirmasi; mengembalikan data awal dan mencoba membersihkan IndexedDB.

Penyimpanan bergantung pada browser dan lokasi file yang sama. Jangan menjanjikan portabilitas data ketika folder dipindah atau dibuka memakai browser lain.

## 5. Peran dan identitas demo

| ID | Nama | Peran / lingkup |
|---|---|---|
| `pm-cctv` | Ramadani | PM CCTV & ACS |
| `pm-wall` | Handoko | PM Wall Display |
| `leader` | Rouzi Dewantoro | Ketua tim CCTV |
| `emp-032` | Ahmadi | Ketua tim Wall Display, penugasan simulasi |
| `member` | Rusyidi Siregar | Anggota tim CCTV |
| `finance` | Sri Wildani | Finance & Accounting, review absensi |
| `hr` | Petugas HR (simulasi) | Dokumen dan pengelolaan SDM |
| `asset` | Hernita | Pengelola aset, penugasan simulasi |
| `ops` | Ade Candra | Operational Manager, lintas unit |

Jumlah tetap **33 karyawan** pada data awal; aktor HR simulasi tidak menambah roster menjadi 34 orang. Ada **9 identitas demo dan 7 kategori peran**.

PM hanya melihat pekerjaan unitnya. Ketua/anggota hanya melihat penugasan terkait dan tidak melihat draft PM. HR dan Finance tidak mendapatkan modul work plan. Dokumen pribadi hanya untuk pemilik atau HR. OPS/PM bisa melihat profil dasar dalam lingkupnya tetapi bukan dokumen pribadi orang lain.

Pembatasan rute ada di `app.js`, pemfilteran data ada di modul tampilan dan `visiblePlans`, pembatasan mutasi ada di `domain.js`. Semua adalah simulasi browser, bukan keamanan produksi.

## 6. Data awal dan alur bisnis

Tanggal simulasi awal: **21 September 2026**. Bisa diubah melalui **Panduan simulasi** tanpa mereset data.

| ID | Pekerjaan | Status awal |
|---|---|---|
| `wp-001` | Instalasi CCTV · Gedung Merdeka | Berjalan, 21–23 September |
| `wp-002` | Pemasangan access control · Kantor Pusat | Draft, 5–6 Oktober |
| `wp-003` | Pemeliharaan CCTV · Warehouse | SK terbit, 28–29 September |
| `wp-004` | Video wall · Command Center | Diterima, 24–26 September |
| `wp-005` | Kalibrasi display · Ruang Kontrol | Selesai, 14–15 September |
| `wp-006` | Survei jaringan · Site Binjai | Banding, 8 Oktober |

### Work plan utama

1. PM membuat/mengedit draft: nama, lokasi, periode, ketua, anggota, lingkup pekerjaan.
2. PM mengisi rincian harian, tugas per hari, lampiran, dan alokasi aset.
3. Penerbitan memeriksa personel aktif, kesesuaian unit, ketua berbeda dari PM, anggota minimal satu, rincian lengkap, serta bentrok jadwal personel.
4. SK terbit berstatus menunggu penerimaan. Ketua dapat menerima atau mengajukan banding.
5. Ketua memulai pekerjaan pada atau setelah tanggal mulai simulasi.
6. Ketua menyelesaikan checklist, menyimpan uraian dan bukti, lalu mengirim laporan.
7. Pengiriman laporan membutuhkan seluruh checklist selesai, minimal 10 karakter uraian, dan minimal satu bukti.
8. PM menyetujui atau meminta perbaikan. Laporan yang sudah dikirim/disetujui tidak dapat ditimpa langsung oleh ketua.
9. Ketua mengajukan selesai setelah semua laporan disetujui dan perubahan tidak tertunda.
10. PM baru dapat menutup setelah seluruh aset terverifikasi kembali.

### Pembaruan Aturan Tambahan (K-002 - K-008)

- Dokumen karyawan hanya dapat diajukan oleh pemiliknya sendiri, sedangkan HR melakukan verifikasi independen.
- Pengembalian aset diajukan oleh Ketua Tim, Petugas Aset hanya memverifikasi.
- Laporan dan checklist harian tidak dapat diubah/diisi sebelum tanggal pelaksanaan (sesuai tanggal simulasi).
- Penghapusan/pengarsipan pekerjaan (soft delete) hanya berlaku untuk draft yang belum memiliki SK.
- Peran ASSET (Petugas Aset) tidak dapat melihat draft atau detail laporan harian.
- Pengalokasian kendaraan memerlukan pengemudi valid (`driverId`) yang terikat dengan SIM A/C yang masa berlakunya melebihi tanggal selesai pekerjaan (juga dicek saat perpanjangan adendum).
- Aset kendaraan mewajibkan "Periksa Kendaraan" dari pengemudi (melalui UI dialog) sebelum statusnya menjadi `IN_USE`.
- Semua peringatan konfirmasi telah dialihkan ke UI Dialog (bukan `window.confirm`).
- Seluruh pencatatan waktu transaksi (persetujuan, pengembalian, laporan) mengikuti patokan "Tanggal Simulasi", bukan jam sistem komputer pengguna.

### Banding, revisi, perpanjangan

- Banding membutuhkan alasan; PM membuka revisi draft dan menerbitkan versi baru. Versi lama tetap tersedia dan ditandai sebagai versi sebelumnya.
- Perpanjangan diajukan ketua dengan tanggal akhir baru dan alasan.
- PM menyetujui terlebih dahulu, membentuk adendum menunggu penerimaan.
- Jadwal lama tetap berlaku sampai ketua menerima adendum final.
- Aktivasi memeriksa kembali jadwal/personel dan menambah rincian hari tambahan.
- Penolakan mempertahankan jadwal efektif lama dan mencatat alasan.
- Nomor versi usulan diperhitungkan dari seluruh versi dokumen agar usulan setelah penolakan tidak memakai ulang versi sebelumnya.

### Aset, pembatalan, arsip

- Aset tersedia dapat dialokasikan. Reservasi ganda dicegah.
- Reservasi yang belum dipakai dapat dilepas.
- Ketua/petugas mengajukan pengembalian; petugas aset memverifikasi kondisi dan kelengkapan.
- Pengaju tidak boleh menjadi pemeriksa pengembalian yang sama.
- Riwayat pengembalian menyimpan pekerjaan asal, pengaju, pemeriksa, waktu, kondisi, dan catatan.
- Pembatalan mencatat alasan; aset yang sedang dipakai tetap wajib kembali.
- Arsip/pemulihan hanya untuk draft. Draft dengan reservasi harus melepas aset dahulu.

### Karyawan dan absensi

- Profil dasar, kontak pribadi, tanggal masuk/lahir, alamat, kontak darurat, riwayat penempatan, dan dokumen tersedia sesuai akses.
- Penggantian dokumen tidak langsung menghapus dokumen lama. Dokumen baru menunggu HR, yang harus berbeda dari pemilik/pengunggah.
- Verifikasi mengaktifkan dokumen baru dan mempertahankan riwayat lama. Penolakan mempertahankan dokumen berlaku sebelumnya.
- HR/OPS dapat mengubah penempatan dan offboarding sesuai aturan. Pemegang peran demo memerlukan serah terima; mutasi lintas unit diblokir saat masih ada penugasan terkait.
- Offboarding memeriksa penugasan aktif dan menonaktifkan akses aktor yang bersangkutan.
- Absensi masuk/keluar sendiri, sumber HP/mesin simulasi, jarak/radius, penjelasan, dan review Finance sudah tersedia.
- Absensi memakai **tanggal simulasi dengan jam nyata** saat tombol ditekan. Batas jam masuk 08.00 WIB dan jam pulang 17.00 WIB dipakai untuk menandai `late` / `earlyLeave`, lalu ditampilkan sebagai notifikasi aplikasi (bukan dialog bawaan browser). Bukti jarak asli tidak diubah oleh keputusan Finance.
- Absensi yang **ditolak** Finance boleh diajukan ulang pada hari yang sama; catatan lama tetap tersimpan sebagai riwayat.

## 7. Dokumen yang sudah dibuat

SK/revisi/adendum mempunyai snapshot pada penerbitan yang memuat:

- Judul pekerjaan, lokasi, unit, periode, deskripsi.
- Nama/jabatan PM, ketua, dan anggota pada saat penerbitan.
- Rincian tanggal, kegiatan, dan tugas harian.
- Aset yang dialokasikan saat penerbitan.
- Metadata lampiran pekerjaan.

Penampil menyajikan kop, nomor, versi, status, rincian di atas, ketentuan pelaksanaan, identitas penerbit/penerima, dan waktu persetujuan. Jangan menampilkan penerimaan bila `acceptedBy` belum ada. Dokumen lama tidak boleh dirender ulang dari profil terbaru.

Sudah tersedia:

- Pilihan versi dan navigasi kembali.
- Zoom sesuai layar, 75%, 100%, 125%, 150%.
- Dokumen A4 dan CSS cetak.
- Tombol **Cetak / Simpan PDF** memanggil `window.print()`. Tidak ada generator PDF atau file PDF resmi tersimpan.
- Pratinjau laporan harian dengan checklist, uraian, bukti, status, dan review.
- Pratinjau berkas dokumen karyawan, status masa berlaku, dan formulir verifikasi HR.

## 8. Pengujian yang benar-benar sudah dijalankan

### Aturan bisnis

```powershell
node --test tests/domain.test.cjs
```

Hasil terakhir: **19 test lulus, 0 gagal** (23 September 2026). Tambahan sejak 15 test: swafoto wajib di luar radius absensi, batas tim/unit untuk insiden dan lembur, adendum personel (termasuk penguncian versi lama dan keputusan oleh ketua yang ditunjuk), serta hak anggota bagi ketua yang turun pangkat. Mencakup lingkup peran/unit, draft dan penerbitan, snapshot revisi, adendum dua pihak dan bentrok, laporan/penutupan/aset, konflik versi, arsip/pemulihan, verifikasi dokumen independen, promosi, offboarding, absensi, alokasi/verifikasi aset, batas pengisian laporan sesuai tanggal simulasi, dan validasi pengemudi kendaraan berdasarkan batas masa berlaku SIM.

Pemeriksaan sintaks seluruh `js/*.js` juga sudah dijalankan dengan `node --check` dan lulus.

### Browser

```powershell
node tests/browser.mjs
```

Tidak membutuhkan dependensi di workspace. Script mengimpor tool yang berada di temporary folder. Dapat disesuaikan melalui:

- `PLAYWRIGHT_MODULE`: path file `index.mjs` dari instalasi `playwright-core`/Playwright yang tersedia di luar proyek.
- `CHROME_PATH`: path Chrome lokal.

Default lingkungan pembuat:

```text
C:\Users\ageng\AppData\Local\Temp\visiontech-native-checks\playwright-core\index.mjs
C:\Users\ageng\.cache\puppeteer\chrome\win64-153.0.8010.36\chrome-win64\chrome.exe
```

Hasil terakhir: **154 kombinasi layar/peran/perangkat diperiksa untuk 9 identitas**, tanpa error browser/console yang tertangkap. Ini bukan 154 halaman HTML terpisah.

Skenario browser yang lulus:

- Launcher, seluruh menu tiap peran pada desktop 1440 px dan mobile 390 px.
- Pemeriksaan overflow horizontal halaman.
- Penolakan rute anggota ke daftar karyawan, PM Wall ke pekerjaan CCTV, dan anggota ke dokumen pribadi orang lain.
- Penerbitan dan penerimaan SK; mulai pekerjaan tertahan sebelum tanggal mulai.
- Mengubah tanggal simulasi dan memulai pekerjaan.
- Perpanjangan → PM menyetujui → ketua menerima → versi/jadwal efektif berubah.
- Pratinjau adendum berisi personel, hari tambahan, serta aset; pergantian versi; tombol back browser; zoom mobile.
- Seluruh hari Gedung Merdeka: checklist, laporan, bukti contoh, pengiriman, persetujuan PM.
- Penutupan tertahan sampai pengembalian kedua aset diverifikasi petugas; kemudian berhasil ditutup dan bertahan setelah reload.
- Upload dokumen pribadi ke IndexedDB, download setelah perpindahan peran/reload, verifikasi HR independen, pratinjau gambar contoh.
- Review absensi Finance, promosi, dan offboarding karyawan yang memenuhi syarat.
- Alokasi aset (kendaraan) dengan validasi pengemudi berdasarkan status validitas SIM.
- Pengujian cetak PDF multi-halaman (`sk-multipage.pdf` dan `laporan-akhir.pdf`) yang bersih tanpa elemen aplikasi berkat `@media print`.

Lokasi hasil:

```text
C:\Users\ageng\AppData\Local\Temp\visiontech-native-checks\results
```

Berisi `results.json`, `launcher.png`, `pm-desktop.png`, `leader-mobile.png`, `adendum-desktop.png`, `adendum-mobile.png`, `sk-multipage.pdf`, dan `laporan-akhir.pdf`. Screenshot desktop PM, mobile ketua, dan mobile adendum sudah dilihat secara visual oleh agen sebelumnya.

**Belum diuji tuntas:** upload PDF nyata ke penampil browser, upload gambar PNG/JPEG nyata (yang diuji adalah download SVG upload dan gambar contoh bawaan), kondisi storage penuh/rusak, konflik beberapa tab melalui browser, semua cabang penolakan/revisi melalui UI, dan seluruh lebar layar tambahan.

## 9. Pekerjaan lanjutan (masih terbuka)

Prioritaskan pemeriksaan/fix terarah berikut. Sebagian besar masalah awal saat serah terima sudah diselesaikan oleh AI kolaborator (Codex & Gemini). Berikut sisa pekerjaan terbuka yang belum dieksekusi:

1. **Garbage collection file yatim (orphan) di IndexedDB.** Berkas upload yang tidak jadi tertaut dapat menjadi orphan di IndexedDB sampai simulasi di-reset. Belum ada pembersihan periodik (GC) untuk file-file ini.
2. **Uji UI untuk konflik beberapa tab.** Jika aplikasi dibuka di beberapa tab browser bersamaan dan diedit bersamaan, konflik versi akan tertangkap oleh rule domain optimistic concurrency, namun pesan UI saat penolakan ini mungkin belum ditangani dengan mulus (graceful) dari sisi pengalaman pengguna.
3. **Tambah pengujian cabang yang belum tercakup browser**, setelah perubahan terkait: banding/revisi/penerimaan ulang, penolakan adendum oleh kedua pihak, pengembalian laporan, pembatalan beserta aset, arsip/pulih, dan penyimpanan gagal. Unit test sudah mencakup sebagian besar dari alur ini, tetapi tidak ada salahnya menambah e2e test-nya.

## 10. Urutan kelanjutan yang disarankan

1. Buka `index.html`; coba alur-alur di sisa daftar "belum diuji" dan "pekerjaan lanjutan".
2. Tambahkan logic Garbage Collection IndexedDB saat penghapusan draft pekerjaan atau sesekali saat memuat aplikasi.
3. Lakukan skenario tab ganda untuk menguji penanganan UI terhadap `optimistic version conflicts`.

## 11. Riwayat QA

- **K-002 (B1-B16)** -> G-004
- **K-003 (R1-R7)** -> G-005
- **K-004 (sisa kecil)** -> G-006
- **K-005 (R8)** -> G-007
- **K-006 (R9)** -> G-008
- **K-008 (T1-T4)** -> G-009
- **K-009 (K9-1-K9-7)** -> G-010
- **K-010 (sisa ini)** -> G-011
- **K-012 (bukti laporan, judul bagian, penghitungan halaman PDF)** -> G-012; **K-013** menetapkan protokol kerja silang Claude–Gemini–Codex (LOCK/RELEASE, kata kunci LAKUKAN, pemantauan mandiri).
- **K-014** (peringatan `workplans.js` rusak + serah terima C1/C2) -> G-012/G-013 (C1/C2 lulus review Gemini).
- **K-015** (RV-G1 s.d. RV-G5 atas G1–G3 Gemini) -> dikerjakan Claude setelah Gemini nonaktif (**K-018**).
- **K-016/K-017** membagi jalur kerja dengan Codex; **K-019/K-020** menambahkan mandat product owner, perombakan Timeline per work plan, dan aturan "kewenangan mengikuti penugasan SK".
- **CODEX-20260923-03 s.d. -07** me-review C1–C3: menemukan RV-X1 (ketua turun pangkat kehilangan hak anggota), RV-X2 (`RELEaSE_ASSET`), RV-X3 (penolakan adendum personel oleh ketua lama), RV-C1 (`sw.js` menghapus cache origin lain), RV-C2 (pembulatan jarak di ambang radius), RV-C3 (sinkronisasi luring mengaku sukses saat penyimpanan gagal), dan RV-D1 (klaim dokumen). Seluruhnya diperbaiki Claude di **K-021**.
- **K-024 s.d. K-027** (Gemini Pro/Antigravity): Menyelesaikan penyisiran UX, fitur absensi, dan validasi bentrok jadwal.
  - Menambahkan panel dan tombol khusus "Ajukan Dokumen Pengganti" jika masa berlaku habis.
  - Memperbarui kategori K3 menjadi spesifik (K3_RINGAN, K3_BERAT, K3_LINGKUNGAN, K3_HAMPIR) di pelaporan Insiden dan merangkumnya pada *slide deck* Laporan Akhir Penyelesaian Pekerjaan.
  - Menambahkan kapabilitas penimpaan (Check-in ulang) apabila absensi sebelumnya berstatus `REJECTED`, tanpa mengharuskan *Check-out*.
  - Menerapkan *alert* batas jam (masuk max 08:00, pulang min 17:00) yang disandingkan dengan notifikasi persisten di antrean *dashboard* bila waktu krusial mendekat/terlewat.
  - Menambahkan algoritma pencegahan jadwal tumpang-tindih (*overlapping schedule*) yang mengunci (*disable*) opsi UI personel saat pembuatan *work plan* / *adendum* secara *real-time*, lengkap dengan validasi di `domain.js`.

### Fitur yang ditambahkan pada putaran ini
- **Mode luring** (`js/offline.js`, `sw.js`): antrean `offline_queue`, indikator status jaringan, sinkronisasi saat kembali online, simulasi luring di Panduan simulasi. Service worker hanya aktif pada `http(s)`.
- **Absensi berbasis lokasi** (`js/geo.js`): jarak Haversine ke koordinat lokasi simulasi, GPS opsional, radius 100 m, swafoto wajib (`capture="user"`, hanya preferensi kamera) di luar radius. Ditambah *alert* batas waktu & pencegahan sesi ganda (termasuk fitur timpa saat di-*reject*).
- **Insiden/HSE dan lembur** (Gemini, diperbaiki Claude): pelaporan oleh ketua/anggota pekerjaan berjalan, penyelesaian oleh PM/OPS (dan pengelola aset untuk kategori aset), lembur ditinjau PM/OPS dan direkap Finance. Insiden juga tampil di laporan PDF akhir.
- **Adendum personel** (`REQUEST_PERSONNEL_CHANGE`, `WITHDRAW_CHANGE`): pergantian ketua/anggota lewat versi dokumen baru, berlaku setelah diterima ketua yang ditunjuk; versi lama terkunci sebagai riwayat (`VTDomain.documentLocked`). Pemilihan personel kini diproteksi dari tabrakan jadwal dengan *work plan* aktif lainnya.
- **Timeline per work plan** dan label status berbahasa Indonesia.
- **Halaman karyawan** (Codex): filter status + pencarian, ringkasan dokumen menunggu HR, pemisahan dokumen terkini dan riwayat, opsi pengajuan perpanjangan otomatis saat dokumen kedaluwarsa.

### Pengujian tambahan
- `node tests/browser.mjs` (diperluas Codex & Gemini): 162 layar, 9 identitas, 22 kelompok skenario, menguji peringatan absensi dan *dialog box*.
- `node tests/offline_geo.mjs` (ditulis ulang Claude): antrean luring dan sinkronisasi, check-in di luar radius dengan swafoto, serta bukti service worker tidak aktif pada `file://`.
- `node --test tests/domain.test.cjs`: Telah melewati seluruh 19 skenario logika validasi *backend* termasuk fitur tumpang tindih jadwal.
