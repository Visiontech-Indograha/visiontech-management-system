# 35 — Flowchart & Panduan Alur Bisnis VMS V2

Dokumen ini memuat diagram alur operasional menyeluruh berbasis **Master DDL 26 Tabel** untuk PT Visiontech Indograha. Diagram ini menjadi panduan fungsional bagi pengembangan API, Web, dan Mobile.

---

## 1. Alur Autentikasi & Sesi Multi-Platform (Web & Mobile)

```mermaid
flowchart TD
    Start(["Pengguna Buka Aplikasi"]) --> Input["Input Email & Kata Sandi"]
    Input --> Submit["Kirim POST /api/v1/auth/login"]
    Submit --> CheckUser{"Pengguna Ada & Aktif di tabel users?"}
    CheckUser -- "Tidak" --> ErrUser["Galat: Kredensial tidak valid"]
    CheckUser -- "Ya" --> CheckRole{"Validasi Platform vs Role"}
    
    CheckRole -- "Platform web_react" --> RoleWeb{"Role Kantor? (SUPER_ADMIN, OM, PM, HR)"}
    RoleWeb -- "Tidak" --> ErrWeb["Tolak: Gunakan Aplikasi Mobile Lapangan"]
    RoleWeb -- "Ya" --> GenSession["Generate Session di tabel user_sessions"]
    
    CheckRole -- "Platform android_flutter" --> RoleMob{"Role Lapangan? (TEAM_LEADER, EMPLOYEE)"}
    RoleMob -- "Tidak" --> ErrMob["Tolak: Akun Kantor, Silakan Akses Web"]
    RoleMob -- "Ya" --> GenSession
    
    GenSession --> ReturnJWT["Kirim Access Token & Refresh Token"]
    ReturnJWT --> Dashboard(["Masuk ke Dashboard Sesuai Peran"])
```

---

## 2. Alur Struktur Organisasi (OM $\rightarrow$ PM $\rightarrow$ Leader $\rightarrow$ Teknisi)

```mermaid
flowchart TD
    OM["Operational Manager (OM)"] -->|"Membawahi beberapa Divisi"| Div1["Divisi Konstruksi Sipil & FTTx"]
    OM -->|"Membawahi beberapa Divisi"| Div2["Divisi ME & IoT"]
    
    Div1 -->|"Dipimpin oleh"| PM1["Project Manager 1 (Hendrik)"]
    Div2 -->|"Dipimpin oleh"| PM2["Project Manager 2 (Dian)"]
    
    PM1 -->|"Mengelola Tim"| TeamA["Tim Alpha Sipil (Kantor Utama)"]
    PM1 -->|"Mengelola Tim"| TeamB["Tim Bravo Sipil (Cabang Tebing Tinggi)"]
    
    TeamA -->|"Dipimpin oleh"| TLA["Team Leader Agus"]
    TeamB -->|"Dipimpin oleh"| TLB["Team Leader Agus / Lainnya"]
    
    TLA -->|"Membawahi Teknisi"| Tech1["Teknisi Riko"]
    TLA -->|"Membawahi Teknisi"| Tech2["Teknisi Doni"]
```

---

## 3. Alur Perencanaan Kerja Daily-First (Order Klien → Survei → Persiapan → Instalasi)

> Keputusan pemilik 2026-10-19/20: **tidak ada tabel minggu** (`work_plan_weekly` dihapus, `db/migration_daily_first.sql`).
> Minggu = rentang tanggal `work_date BETWEEN awal AND akhir`. Visiontech adalah subkontraktor: PM menerima order
> dari klien (mis. PT Pertamina Hulu Rokan) lalu menyusun rencana kerja per tahap.

```mermaid
flowchart TD
    Order(["Order Klien (work_completion): klien, judul proyek, lokasi, divisi, PM"]) --> Daily["PM buat Jadwal Harian (work_plan_daily): tanggal, tim, lokasi site, radius, jam"]
    Daily --> Survey["Item SURVEY per titik (work_plan_item, task_phase = SURVEY)"]
    Survey --> Template["Template per divisi (work_type): syarat foto (image_requirement) + BoM bawaan (work_type_default_materials)"]
    Template --> Findings["Hasil survei per titik: foto posisi & view, remark (notes), kebutuhan alat"]
    Findings --> Need{"Perlu persiapan lapangan?"}
    Need -- "Ya" --> Prep["Item PREPARATION: galian parit, skafolding, grounding, box panel (depends_on_item_id → titik survei)"]
    Need -- "Tidak" --> Main
    Prep --> Main["Item utama per titik: INSTALLATION / REPLACEMENT / MAINTENANCE (is_main_deliverable = TRUE)"]
    Main --> BoM["BoM riil order (work_completion_bom) dari template + hitungan survei"]
    Main --> Approve["PM setujui jadwal (per hari atau sekaligus satu minggu: matriks)"]
    Approve --> Field(["Ketua & teknisi melihat jadwal di aplikasi HP"])
```

- Template berbeda per divisi: "Survei CCTV" (divisi ME & IoT) ≠ "Survei Wall Display" walau namanya mirip
  (`work_type.division_id`, unik per divisi + nama).
- Satu titik = satu item (`location_name`, `site_lat/lng`) agar proyek multi-minggu terlacak per titik
  (mis. minggu ke-3 titik 1–2, minggu ke-4 titik 8).
- Fase baku `task_phase`: `SURVEY`, `PREPARATION`, `INSTALLATION`, `REPLACEMENT`, `MAINTENANCE`; dipilih per item.
- Siklus jadwal harian (`work_plan_daily.status`, Milestone 5): `DRAFT` → (PM/OM ajukan) `SUBMITTED` → (PM/OM divisi
  setujui; per hari atau sekaligus lewat matriks minggu) `APPROVED` → (ketua mulai pada tanggalnya) `ONGOING` →
  (ketua/PM tutup) `COMPLETED`. Dikembalikan PM: `SUBMITTED/APPROVED` → `DRAFT` + `rejection_reason`. Satu jadwal
  per tim per tanggal; jadwal bisa disalin ke tanggal lain (draf). Tim lapangan hanya melihat jadwal yang sudah
  disetujui; lembur diajukan atas jadwal `ONGOING`.

---

## 4. Alur Rollover: Geser Tugas ke Hari / Minggu Berikutnya

```mermaid
flowchart TD
    TLStart(["Ketua & tim di lokasi"]) --> ExecItem["Kerjakan item (work_plan_item)"]
    ExecItem --> CheckFinish{"Selesai sesuai target?"}
    CheckFinish -- "Ya" --> MarkDone["status = DONE, completed_qty = target_qty, unggah foto SOP"]
    CheckFinish -- "Tidak (hujan, izin, material)" --> Request["Ketua ajukan geser: status = PENDING_ROLLOVER, rollover_approval_status = WAITING_PM, delay_reason, completed_qty parsial"]
    Request --> PMReview{"Keputusan PM"}
    PMReview -- "Tolak" --> Reject["REJECTED_BY_PM → item kembali dikerjakan"]
    PMReview -- "Setujui" --> Target{"Tujuan"}
    Target -- "Hari yang sudah ada" --> Shift
    Target -- "Tanggal baru (besok / minggu depan / 2 minggu lagi)" --> AutoDay["Sistem buat work_plan_daily di tanggal itu (salin divisi, tim, lokasi, jam)"]
    AutoDay --> Shift["Item asal: SHIFTED_DAY + shifted_to_daily_id; item baru: origin_item_id = item asal, target_qty = sisa volume"]
    Shift --> Audit["Catatan PM → app_activity_logs (delay_reason ketua tidak ditimpa)"]
```

Aturan (keputusan pemilik 2026-10-20):
1. Tanggal tujuan **harus setelah** tanggal asal.
2. Tim & divisi tujuan **sama** dengan hari asal (pindah tim = penugasan ulang, bukan rollover).
3. **Sisa volume terbawa**: item baru `target_qty = target − completed_qty`; item asal tercatat parsial.
4. **Satu rantai aktif**: item yang sudah `SHIFTED_DAY` tidak bisa digeser lagi — yang digeser item lanjutannya.

---

## 5. Alur Presensi Biometrik Wajah, Radius Site, & Uang Makan

```mermaid
flowchart TD
    UserClockIn(["Karyawan Buka Menu Presensi di Mobile"]) --> CaptureFace["Ambil Swafoto Wajah & Baca Koordinat GPS"]
    CaptureFace --> MatchFace{"Face Matching Score >= Threshold?"}
    MatchFace -- "Gagal" --> RetryFace["Wajah Tidak Cocok, Coba Lagi"]
    MatchFace -- "Cocok" --> CheckTarget{"Target Lokasi: Kantor atau Site Proyek?"}
    
    CheckTarget -- "Kantor" --> CalcOfficeDist["Hitung Jarak ke Kantor Cabang/Pusat"]
    CheckTarget -- "Site Proyek" --> CalcSiteDist["Hitung Jarak ke Koordinat Site work_plan_daily"]
    
    CalcOfficeDist & CalcSiteDist --> CheckRad{"Jarak <= attendance_radius_m?"}
    CheckRad -- "Ya (Dalam Radius)" --> InRadius["is_within_attendance_radius = TRUE"]
    InRadius --> AutoValid["om_approval_status = 'AUTO_VALID'"]
    
    CheckRad -- "Tidak (Luar Radius)" --> OutRadius["is_within_attendance_radius = FALSE"]
    OutRadius --> OutProof["Wajib Unggah Foto Alasan + Catatan out_of_radius_note"]
    OutProof --> PendingOM["om_approval_status = 'PENDING_OM' (Menunggu Approval OM)"]
    
    AutoValid & PendingOM --> CalcMeal["Hitung Jarak ke Kantor Utama Medan (Latitude 3.5952, Longitude 98.6722)"]
    CalcMeal --> Check15km{"Jarak ke Kantor Utama <= 15 km?"}
    Check15km -- "Ya" --> InCity["city_zone_status = 'DALAM_KOTA', Uang Makan: Rp 35.000"]
    Check15km -- "Tidak" --> OutCity["city_zone_status = 'LUAR_KOTA', Uang Makan: Rp 65.000"]
    InCity & OutCity --> SaveAtt(["Simpan Record ke tabel attendance"])
```

---

## 6. Alur Peminjaman Aset (Alat Pribadi vs Umum & Kendaraan)

```mermaid
flowchart TD
    AssetReq(["Kebutuhan Alat / Kendaraan"]) --> ChooseType{"Jenis Aset?"}
    
    ChooseType -- "Alat (tool)" --> ToolType{"Ownership Type?"}
    ToolType -- "PERSONAL_LOAN" --> PTool["Alat Pribadi (Baju, Sepatu, Laptop)"]
    ToolType -- "SHARED_TOOL" --> STool["Alat Bersama Proyek (Bor, Tangga)"]
    
    ChooseType -- "Kendaraan (vehicle)" --> VType["Motorcycle / Car / Truck (Cek Masa STNK/KIR)"]
    
    PTool & STool & VType --> Handover["Proses Serah Terima & Foto Bukti"]
    Handover --> CreateAssign["Insert ke tabel asset_assignment (status = 'loaned')"]
    CreateAssign --> InUse(["Aset Digunakan oleh Karyawan / Tim"])
    
    InUse --> ReturnEvent["Pengembalian Aset"]
    ReturnEvent --> UpdateReturn["Set returned_at = NOW(), status aset = 'ready'"]
```

---

## 7. Alur Penghentian Kerja (Offboarding PKWT) & Clearance Aset

```mermaid
flowchart TD
    PKWTEnd(["Kontrak PKWT Berakhir / Resign"]) --> InitOffboard["HR/Sistem Buat Record employee_offboarding"]
    InitOffboard --> GenClearance["Query asset_assignment yang returned_at IS NULL"]
    GenClearance --> PopItems["Insert ke tabel offboarding_clearance_item"]
    
    PopItems --> CheckAll{"Semua Aset Sudah Dikembalikan?"}
    CheckAll -- "Ada yang Belum (Laptop/Alat Masih Dipinjam)" --> Hold["is_all_assets_returned = FALSE"]
    Hold --> BlockOffboard["Status = 'CLEARANCE_PENDING' (Offboarding Terkunci)"]
    
    BlockOffboard --> PhysicalReturn["Karyawan Mengembalikan Barang ke HR/GA"]
    PhysicalReturn --> VerifyItem["HR Verifikasi Kondisi (GOOD, DAMAGED, LOST)"]
    VerifyItem --> SetItemGood["Update offboarding_clearance_item & asset_assignment"]
    
    SetItemGood --> Recheck{"Semua Item Selesai Diverifikasi?"}
    Recheck -- "Lengkap" --> ApproveClearance["is_all_assets_returned = TRUE"]
    ApproveClearance --> SignApproval["Persetujuan PM & HR (approved_by_pm, approved_by_hr)"]
    SignApproval --> FinalOffboard(["Status = 'COMPLETED', employee.offboarding_status = 'offboarded'"])
```

---

## 8. Alur Pelaporan Selesai & Ekspor Dokumen Resmi

```mermaid
flowchart TD
    WorkEnd(["Pekerjaan Harian / Mingguan Tuntas"]) --> LeaderDraft["Leader Susun Ringkasan & Lampiran Foto"]
    LeaderDraft --> LeaderSign["Leader Bubuhkan TTD Digital di Mobile (leader_signer_id)"]
    LeaderSign --> PMSign["PM Periksa di Web & Bubuhkan TTD Digital (pm_signer_id)"]
    PMSign --> GenHash["Sistem Buat SHA-256 signature_hash"]
    GenHash --> SaveComp["Simpan ke tabel work_completion"]
    
    SaveComp --> ExportChoice{"Pilih Format Ekspor (export_format_enum)"}
    ExportChoice -- "WORD_DOCX" --> GenDocx["Isi Template Baku DOCX Berlogo (BAST & Survey Report)"]
    ExportChoice -- "PPTX" --> GenPptx["Generate Slide Presentasi Mingguan PPTX"]
    ExportChoice -- "PDF" --> GenPdf["Generate PDF Resmi dengan QR Verifikasi"]
    ExportChoice -- "EXCEL_XLSX" --> GenExcel["Generate Rekap BOQ & Uang Makan XLSX"]
    
    GenDocx & GenPptx & GenPdf & GenExcel --> SaveRegistry["Catat ke document_template_export"]
    SaveRegistry --> ReadyDownload(["Dokumen Siap Diunduh oleh Manajemen"])
```

**Survey Report (.docx)** — acuan format: laporan "Survey Report New CCTV MGT Minas" (2026-09): kop Visiontech & klien,
tanggal/lokasi/tujuan, tabel jadwal, uraian aktivitas & tim, layout, hitungan instalasi FO per titik, dokumentasi per titik
(foto posisi + view + remark), Bill of Material estimasi, penutup & penanda tangan. Data: order (`work_completion`),
item `SURVEY` per titik (`notes`, `realization_photos_json`), `work_completion_bom`. Dibangun di Milestone 8.
