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

## 3. Alur Perencanaan Kerja Mingguan & Harian (Work Plan)

```mermaid
flowchart TD
    StartPlan(["PM Buka Menu Work Plan"]) --> NewWeekly["PM Buat Work Plan Weekly (Tabel work_plan_weekly)"]
    NewWeekly --> FillWeekly["Pilih Divisi, Tim Pelaksana, Minggu ke-n, & Periode"]
    FillWeekly --> AddDaily["PM Tambahkan Jadwal Harian (Tabel work_plan_daily)"]
    AddDaily --> SetSite["Set Titik Lokasi Site (Latitude, Longitude, Radius Presensi, Jam Kerja)"]
    SetSite --> AddItems["PM Tambahkan Daftar Tugas (Tabel work_plan_item)"]
    AddItems --> AssignType["Pilih work_type & Syarat Foto SOP (image_requirement)"]
    AssignType --> PubPlan["PM Terbitkan SK (Status: APPROVED / ONGOING)"]
    PubPlan --> NotifyTL(["Team Leader & Teknisi Melihat Jadwal di Mobile"])
```

---

## 4. Alur Engine Rollover & Geser Hari Tugas Lapangan

```mermaid
flowchart TD
    TLStart(["Leader & Tim Tiba di Lokasi"]) --> ExecItem["Pengerjaan Item Tugas (work_plan_item)"]
    ExecItem --> CheckFinish{"Tugas Selesai Sesuai Target?"}
    
    CheckFinish -- "Ya (100%)" --> MarkDone["Update status = 'DONE', completed_qty = target_qty"]
    MarkDone --> UploadProof["Unggah Foto SOP (image_requirement)"]
    
    CheckFinish -- "Tidak (Terkendala Hujan/Izin)" --> RequestRoll["Leader Ajukan Geser Hari (status = 'PENDING_ROLLOVER')"]
    RequestRoll --> InputReason["Isi delay_reason & completed_qty parsial"]
    InputReason --> SetWait["Set rollover_approval_status = 'WAITING_PM'"]
    
    SetWait --> PMReview{"Persetujuan PM"}
    PMReview -- "Ditolak" --> PMReject["Status kembali IN_PROGRESS / Penyesuaian"]
    PMReview -- "Disetujui Geser Besok" --> PMSApproveDay["Set status = 'SHIFTED_DAY'"]
    PMSApproveDay --> CreateNextDayItem["Sistem Buat Item Baru di Jadwal Besok (origin_item_id = item lama)"]
    
    PMReview -- "Disetujui Minggu Depan" --> PMApproveWeek["Set status = 'ALLOCATED_NEXT_WEEK'"]
    PMApproveWeek --> LinkNextWeek["Hubungkan ke allocated_to_weekly_id"]
```

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
    ExportChoice -- "WORD_DOCX" --> GenDocx["Isi Template Baku DOCX Berlogo"]
    ExportChoice -- "PPTX" --> GenPptx["Generate Slide Presentasi Mingguan PPTX"]
    ExportChoice -- "PDF" --> GenPdf["Generate PDF Resmi dengan QR Verifikasi"]
    ExportChoice -- "EXCEL_XLSX" --> GenExcel["Generate Rekap BOQ & Uang Makan XLSX"]
    
    GenDocx & GenPptx & GenPdf & GenExcel --> SaveRegistry["Catat ke document_template_export"]
    SaveRegistry --> ReadyDownload(["Dokumen Siap Diunduh oleh Manajemen"])
```
