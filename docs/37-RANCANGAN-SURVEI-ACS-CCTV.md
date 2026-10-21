# 37 — Rancangan Survei ACS & CCTV (format laporan baku + rencana mingguan berbasis survei)

Status: **USULAN — menunggu persetujuan pemilik** (2026-10-21).
Sumber format: `Assessment survei installasi ACS di Kantor Lab Duri.docx` (ACS) dan
`Survey Report New CCTV MGT Minas.docx` (CCTV) dari pemilik. Keputusan terkait: docs/36 §3 (daily-first, fase item
`SURVEY`, jangan menambah tabel/kolom tanpa persetujuan).

## 1. Masalah yang diselesaikan

1. Laporan survei harus **sama persis** dengan dua dokumen contoh: kop & footer, blok judul (tanggal/lokasi/tujuan),
   tabel aktivitas, narasi, gambar layout, dokumentasi per titik (tabel foto 2 kolom + remark), material, Bill of
   Material, penutup & tanda tangan.
2. Rencana pemasangan **baru bisa disusun setelah survei masuk**: butuh scaffolding/bucket truck? tangga panjang?
   panjang kabel? material apa saja? Jadi "rencana mingguan" tidak bisa diisi penuh di awal.
3. Divisi ACS belum ada di DB; PM-nya sama dengan PM divisi CCTV.

## 2. Dua format, satu struktur

Kedua dokumen berstruktur sama; bedanya hanya isi kolom:

| Bagian | ACS (Lab Duri) | CCTV (MGT Minas) |
|---|---|---|
| Kop / footer | "REPORT SURVEY — INSTALLASI BARU CCTV-ACS", logo; footer klien + "Commercial in Confidence" | kop logo |
| Blok judul | TANGGAL · LOCATION · PURPOSE | ACTION DATE · LOCATION · PURPOSE |
| Aktivitas | tabel Tanggal · Deskripsi Survey + narasi tim | sama |
| Layout | 1 gambar + keterangan warna (existing / propose) | 1+ gambar |
| Tabel khusus | — | **Hitungan instalasi FO** per kamera (galian, kabel FO, power, subduct, pipa, patch cord, …) |
| Dokumentasi per titik | judul "Pintu akses …", foto **Tampak Luar · Tampak Dalam**, remark, **material per titik** | judul "Titik Pemasangan CCTV nn", foto **Posisi CCTV · View CCTV Camera**, remark |
| Bill of Material | No · Nama Material · Qty · Satuan · Remark | No · Device/Material · Estimate Qty |
| Penutup | kalimat penutup + "Salam hormat, <nama>" | kalimat penutup + tim + nama |

**Format mengikuti divisi work type**: work type survei di divisi ACS → format ACS; di divisi CCTV → format CCTV.
Dokumen contoh disimpan sebagai **master template** (`api/app/shared/documents/templates/survey_acs.docx`,
`survey_cctv.docx`): kop, footer, gaya, ukuran kertas & margin diambil langsung dari file contoh, isi diganti data
survei — sehingga tampilan identik, bukan ditiru ulang.

## 3. Alur (PM → ketua tim → PM)

```
PM  : buat work type "Survei ACS/CCTV" (fase SURVEY) — slot foto per titik (image_requirement):
      ACS = Tampak Luar, Tampak Dalam · CCTV = Posisi CCTV, View CCTV Camera
      + katalog material (work_type_default_materials) sebagai pilihan cepat BoM
PM  : susun minggu = paket jadwal harian (daily-first). Hari 1 berisi item survei → TERBITKAN.
      Hari berikutnya boleh dibuat sebagai DRAFT (belum terbit) — diisi setelah survei.
TL  : terima jadwal → di lokasi menambah TITIK sendiri (mis. "Pintu akses Samping", "CCTV 03"):
        · foto per slot (wajib sesuai format), remark (daftar poin)
        · kebutuhan pemasangan (centang): tangga panjang, scaffolding/bucket truck, grounding, galian, box panel …
        · material per titik (ACS) / ukuran kabel per kamera (CCTV: galian, FO, power, subduct, pipa, …)
      + layout (foto/gambar) + aktivitas (tanggal & deskripsi) → KIRIM SURVEI
PM  : tinjau survei → setujui / kembalikan dengan catatan.
      Disetujui → BoM otomatis dijumlah dari material titik (bisa disunting PM) → laporan .docx/.pdf siap.
PM  : "Rencanakan dari survei": sistem menyiapkan item lanjutan per titik pada hari DRAFT berikutnya:
        · PREPARATION bila ada kebutuhan alat/izin (scaffolding, bucket truck, grounding oleh facility owner)
        · INSTALLATION per titik (lokasi = nama titik, material dari survei, depends_on = item survei)
      PM menyesuaikan lalu TERBITKAN hari-hari itu.
```

Jadi minggu tetap paket 7 hari, tetapi hari setelah survei **terkunci (DRAFT) sampai survei disetujui** — sesuai
kenyataan bahwa rencana pemasangan bergantung hasil lapangan.

## 4. Penyimpanan (relasional, tanpa tabel/kolom baru)

`work_completion_bom.completion_id` NOT NULL → survei selalu menempel pada **order** (`work_completion`). Ini cocok
dengan dokumen: satu laporan survei = satu order klien.

| Data | Tempat |
|---|---|
| Divisi ACS | baris baru `division` (pm_id & om_id = milik divisi CCTV) |
| Format slot foto | `image_requirement` (work_type_id, name, sort_order, is_mandatory) |
| Katalog material | `work_type_default_materials` |
| Laporan (klien, lokasi, tujuan, narasi, layout) | `work_completion`: client_name, site_address, project_title, summary_notes, realization_photos_json (layout) |
| Tugas survei dari PM | `work_plan_item` fase SURVEY, `completion_id` = order (induk) |
| **Titik** (dibuat ketua tim) | `work_plan_item` fase SURVEY, `depends_on_item_id` = tugas survei, `completion_id` = order, `location_name`/`title` = nama titik, `notes` = remark, foto per slot `realization_photos_json` = `[{file_id, requirement_id}]` |
| Material / kebutuhan / kabel per titik | `work_completion_bom` (`work_plan_item_id` = titik, `category` = MATERIAL / KEBUTUHAN / KABEL) |
| BoM laporan | jumlah baris MATERIAL per nama material (atau baris BoM tingkat order yang disunting PM) |
| Tabel hitungan FO (CCTV) | rekap baris KABEL per titik (kolom = nama ukuran: Galian, Kabel FO, Kabel Power, …) |
| Status survei | `work_plan_item.status` tugas survei (IN_PROGRESS → DONE saat dikirim) + persetujuan PM |
| Item lanjutan | `work_plan_item` (PREPARATION/INSTALLATION, depends_on_item_id = titik, location_name = titik) |
| Ekspor | `document_template_export` (template_type = SURVEY_ACS / SURVEY_CCTV) |

## 5. Lingkup implementasi (M11-S)

1. Data: divisi ACS + work type contoh (Survei ACS, Survei CCTV) beserta slot foto & katalog material.
2. API: skema survei (titik, slot, kebutuhan, material/kabel), endpoint TL simpan/kirim, PM setujui/kembalikan,
   "rencanakan dari survei", BoM survei, ekspor .docx/.pdf dari master template.
3. Mobile (TL): layar survei — tambah titik, ambil foto per slot (kamera berbukti lokasi), remark, kebutuhan,
   material/kabel, layout, kirim (luring didukung via antrean sinkron).
4. Web (PM): kelola work type survei, tinjau survei, BoM, unduh laporan, rencanakan dari survei.
5. Uji + Postman folder baru.

## 9. Jenis titik & BoM dinamis (21-10-2026)

**Tujuan:** satu survei bisa berisi beberapa jenis titik (Pintu Akses, Pintu Emergency + Alarm, Barrier Gate,
Titik Kamera CCTV, …), masing-masing dengan slot foto, foto panduan, katalog material, dan pemasangan lanjutannya sendiri.

| Perubahan skema (disetujui pemilik) | Isi |
|---|---|
| `work_type.kind` | `WORK` (bawaan) / `SURVEY_TASK` / `SURVEY_POINT` |
| `work_type.follow_up_work_type_id` | jenis titik → work type pemasangan (dipakai "rencanakan dari survei") |
| `work_plan_item.point_status` | titik survei: `EXISTING` / `PROPOSED` (bawaan) → warna penanda layout |

Tanpa kolom baru: jumlah bawaan katalog (`work_type_default_materials.default_qty` sudah ada); tanda "di luar katalog"
dihitung saat dibaca; material umum lokasi = baris `work_completion_bom` dengan `work_plan_item_id` = tugas survei;
riwayat perubahan BoM = `app_activity_logs` aksi `SURVEY_BOM_CHANGED`.

**Aturan:** jenis titik yang diizinkan = semua `SURVEY_POINT` di divisi survei (divisi tanpa jenis titik → jenis bawaan
= work type tugas survei, perilaku lama). BoM bisa diubah ketua tim saat DRAFT atau PM saat SUBMITTED; terkunci setelah
APPROVED. Material di luar katalog: satuan dari daftar baku; PM bisa "Simpan ke katalog".

**Analisis dampak ke fitur lain:**
- Item jadwal biasa & item lanjutan survei menolak work type `SURVEY_POINT` (`plan_item_repository.work_type_division`,
  `survey_repository.work_type_division` hanya `WORK`); daftar jenis di form item jadwal web menyaring `SURVEY_POINT`.
- BoM order, BoQ (.xlsx), dan rekap periodik kini mengabaikan baris `KEBUTUHAN`/`KABEL` survei (sebelumnya ikut
  terjumlah — bug lama).
- Titik lama dipindah ke jenis titik pertama divisinya oleh `scripts/seed_jenis_titik_survei.py`; nama slot sama sehingga
  foto lama tetap cocok (nama slot dibaca juga dari work type tugas survei).
- Migrasi idempoten di `migration_v3.DDL_STATEMENTS` (dijalankan saat start) + `db/06_master_schema_v2.sql` untuk instalasi baru.
- Kontrak API berubah: `SurveyOut.slots/catalog` → `point_types`; tambah `general_lines`, `can_edit_bom`, `bom[].group`;
  endpoint baru `POST /{task}/lines`, `PUT|DELETE /lines/{bom_id}`, `POST /{task}/catalog`. Snapshot OpenAPI perlu diperbarui.
