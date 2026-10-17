-- ============================================================================
-- VISIONTECH MANAGEMENT SYSTEM (VMS) - MASTER SEED DATA (POSTGRESQL) V2
-- 113 Baris Data Uji Lengkap (Skenario Realistis Operasional)
-- ============================================================================

BEGIN;

-- 1. Seed office (3 Kantor: 1 Kantor Utama Medan [07:00-16:00], 2 Kantor Cabang [07:30-16:30])
INSERT INTO office (office_id, name, is_main_office, address, latitude, longitude, attendance_radius_m, city_boundary_radius_m, clock_in_time, clock_out_time, in_city_meal_rate, out_city_meal_rate) VALUES
('11111111-0000-4000-a000-000000000001', 'Kantor Utama Visiontech Medan', TRUE, 'Jl. Gatot Subroto No. 120, Medan', 3.5952000, 98.6722000, 100, 15000, '07:00:00', '16:00:00', 35000.00, 65000.00),
('11111111-0000-4000-a000-000000000002', 'Kantor Cabang Tebing Tinggi', FALSE, 'Jl. Sudirman No. 45, Tebing Tinggi', 3.3285000, 99.1625000, 100, 15000, '07:30:00', '16:30:00', 35000.00, 65000.00),
('11111111-0000-4000-a000-000000000003', 'Kantor Cabang Rantauprapat', FALSE, 'Jl. Ahmad Yani No. 88, Rantauprapat', 2.0991000, 99.8256000, 100, 15000, '07:30:00', '16:30:00', 35000.00, 65000.00)
ON CONFLICT (office_id) DO NOTHING;

-- 2. Seed employee (8 Karyawan mewakili seluruh Role + 1 Karyawan sedang Offboarding)
INSERT INTO employee (employee_id, office_id, full_name, employee_no, join_date, pkwt_end_date, profile_photo_path, face_embedding, offboarding_status) VALUES
('22222222-0000-4000-a000-000000000001', '11111111-0000-4000-a000-000000000001', 'Budi Santoso', 'VMS-EMP-001', '2024-01-10 08:00:00+07', NULL, '/uploads/profiles/budi.jpg', '[0.12, -0.08, 0.44, 0.91]', 'active'),
('22222222-0000-4000-a000-000000000002', '11111111-0000-4000-a000-000000000001', 'Randi Pratama', 'VMS-EMP-002', '2024-02-01 08:00:00+07', NULL, '/uploads/profiles/randi.jpg', '[0.21, 0.15, -0.33, 0.78]', 'active'),
('22222222-0000-4000-a000-000000000003', '11111111-0000-4000-a000-000000000001', 'Hendrik Wijaya', 'VMS-EMP-003', '2024-03-15 08:00:00+07', '2027-03-15 17:00:00+07', '/uploads/profiles/hendrik.jpg', '[-0.11, 0.42, 0.19, 0.65]', 'active'),
('22222222-0000-4000-a000-000000000004', '11111111-0000-4000-a000-000000000002', 'Dian Kusuma', 'VMS-EMP-004', '2024-04-01 08:00:00+07', '2027-04-01 17:00:00+07', '/uploads/profiles/dian.jpg', '[0.09, -0.27, 0.51, 0.38]', 'active'),
('22222222-0000-4000-a000-000000000005', '11111111-0000-4000-a000-000000000001', 'Siti Aminah', 'VMS-EMP-005', '2024-05-10 08:00:00+07', NULL, '/uploads/profiles/siti.jpg', '[0.34, 0.12, -0.09, 0.82]', 'active'),
('22222222-0000-4000-a000-000000000006', '11111111-0000-4000-a000-000000000001', 'Agus Setiawan', 'VMS-EMP-006', '2025-01-15 08:00:00+07', '2027-01-15 17:00:00+07', '/uploads/profiles/agus.jpg', '[-0.45, 0.31, 0.22, 0.60]', 'active'),
('22222222-0000-4000-a000-000000000007', '11111111-0000-4000-a000-000000000002', 'Riko Saputra', 'VMS-EMP-007', '2025-02-01 08:00:00+07', '2027-02-01 17:00:00+07', '/uploads/profiles/riko.jpg', '[0.18, 0.64, -0.17, 0.49]', 'active'),
('22222222-0000-4000-a000-000000000008', '11111111-0000-4000-a000-000000000001', 'Doni Firmansyah', 'VMS-EMP-008', '2025-10-20 08:00:00+07', '2026-10-20 17:00:00+07', '/uploads/profiles/doni.jpg', '[0.52, -0.19, 0.08, 0.71]', 'in_process')
ON CONFLICT (employee_id) DO NOTHING;

-- 3. Seed users (8 Akun Login terpisah dari tabel employee - Konfirmasi 1B)
INSERT INTO users (user_id, employee_id, username, email, password_hash, system_role, is_active) VALUES
('29999999-0000-4000-a000-000000000001', '22222222-0000-4000-a000-000000000001', 'superadmin', 'admin@visiontech.co.id', '$argon2id$v=19$m=65536,t=3,p=4$ldNRoAZ1ZP85rMv/CvKC4w$0kNdrnB4fAtMMoGZYxxfJBape7gJskOsyMI2X9ZOwFY', 'SUPER_ADMIN', TRUE),
('29999999-0000-4000-a000-000000000002', '22222222-0000-4000-a000-000000000002', 'om_randi', 'randi.om@visiontech.co.id', '$argon2id$v=19$m=65536,t=3,p=4$ldNRoAZ1ZP85rMv/CvKC4w$0kNdrnB4fAtMMoGZYxxfJBape7gJskOsyMI2X9ZOwFY', 'OPERATIONAL_MANAGER', TRUE),
('29999999-0000-4000-a000-000000000003', '22222222-0000-4000-a000-000000000003', 'pm_hendrik', 'hendrik.pm@visiontech.co.id', '$argon2id$v=19$m=65536,t=3,p=4$ldNRoAZ1ZP85rMv/CvKC4w$0kNdrnB4fAtMMoGZYxxfJBape7gJskOsyMI2X9ZOwFY', 'PROJECT_MANAGER', TRUE),
('29999999-0000-4000-a000-000000000004', '22222222-0000-4000-a000-000000000004', 'pm_dian', 'dian.pm@visiontech.co.id', '$argon2id$v=19$m=65536,t=3,p=4$ldNRoAZ1ZP85rMv/CvKC4w$0kNdrnB4fAtMMoGZYxxfJBape7gJskOsyMI2X9ZOwFY', 'PROJECT_MANAGER', TRUE),
('29999999-0000-4000-a000-000000000005', '22222222-0000-4000-a000-000000000005', 'hr_siti', 'siti.hr@visiontech.co.id', '$argon2id$v=19$m=65536,t=3,p=4$ldNRoAZ1ZP85rMv/CvKC4w$0kNdrnB4fAtMMoGZYxxfJBape7gJskOsyMI2X9ZOwFY', 'ADMIN_HR_GA', TRUE),
('29999999-0000-4000-a000-000000000006', '22222222-0000-4000-a000-000000000006', 'tl_agus', 'agus.tl@visiontech.co.id', '$argon2id$v=19$m=65536,t=3,p=4$ldNRoAZ1ZP85rMv/CvKC4w$0kNdrnB4fAtMMoGZYxxfJBape7gJskOsyMI2X9ZOwFY', 'TEAM_LEADER', TRUE),
('29999999-0000-4000-a000-000000000007', '22222222-0000-4000-a000-000000000007', 'tech_riko', 'riko.tech@visiontech.co.id', '$argon2id$v=19$m=65536,t=3,p=4$ldNRoAZ1ZP85rMv/CvKC4w$0kNdrnB4fAtMMoGZYxxfJBape7gJskOsyMI2X9ZOwFY', 'EMPLOYEE', TRUE),
('29999999-0000-4000-a000-000000000008', '22222222-0000-4000-a000-000000000008', 'tech_doni', 'doni.tech@visiontech.co.id', '$argon2id$v=19$m=65536,t=3,p=4$ldNRoAZ1ZP85rMv/CvKC4w$0kNdrnB4fAtMMoGZYxxfJBape7gJskOsyMI2X9ZOwFY', 'EMPLOYEE', TRUE)
ON CONFLICT (user_id) DO NOTHING;

-- 4. Seed user_sessions (4 Sesi Aktif di Web React & Android Flutter)
INSERT INTO user_sessions (session_id, user_id, token_family_id, refresh_token_hash, platform, device_name, ip_address, is_revoked, expires_at) VALUES
('39999999-0000-4000-a000-000000000001', '29999999-0000-4000-a000-000000000002', 'f0000001-0000-4000-a000-000000000001', 'a1b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0001', 'web_react', 'Chrome 130 Windows 11 (OM Randi)', '103.10.66.12', FALSE, '2026-10-24 08:00:00+07'),
('39999999-0000-4000-a000-000000000002', '29999999-0000-4000-a000-000000000003', 'f0000001-0000-4000-a000-000000000002', 'a1b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0002', 'web_react', 'Edge Windows 11 (PM Hendrik)', '103.10.66.15', FALSE, '2026-10-24 08:00:00+07'),
('39999999-0000-4000-a000-000000000003', '29999999-0000-4000-a000-000000000006', 'f0000001-0000-4000-a000-000000000003', 'a1b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0003', 'android_flutter', 'Samsung Galaxy S23 (Leader Agus)', '114.122.10.44', FALSE, '2026-11-15 08:00:00+07'),
('39999999-0000-4000-a000-000000000004', '29999999-0000-4000-a000-000000000007', 'f0000001-0000-4000-a000-000000000004', 'a1b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0004', 'android_flutter', 'Redmi Note 13 Pro (Teknisi Riko)', '114.122.10.89', FALSE, '2026-11-15 08:00:00+07')
ON CONFLICT (session_id) DO NOTHING;

-- 5. Seed division (2 Divisi di bawah 1 OM Randi - Konfirmasi 4B)
INSERT INTO division (division_id, om_id, pm_id, name, status) VALUES
('33333333-0000-4000-a000-000000000001', '22222222-0000-4000-a000-000000000002', '22222222-0000-4000-a000-000000000003', 'Divisi Konstruksi Sipil & FTTx', TRUE),
('33333333-0000-4000-a000-000000000002', '22222222-0000-4000-a000-000000000002', '22222222-0000-4000-a000-000000000004', 'Divisi Mekanikal Elektrikal & IoT', TRUE)
ON CONFLICT (division_id) DO NOTHING;

-- Update division_id pada employee
UPDATE employee SET division_id = '33333333-0000-4000-a000-000000000001' WHERE employee_id IN ('22222222-0000-4000-a000-000000000003', '22222222-0000-4000-a000-000000000006', '22222222-0000-4000-a000-000000000007', '22222222-0000-4000-a000-000000000008');
UPDATE employee SET division_id = '33333333-0000-4000-a000-000000000002' WHERE employee_id IN ('22222222-0000-4000-a000-000000000004');

-- 6. Seed team (3 Tim di bawah Divisi Sipil & MEP yang tersebar di Kantor Utama & Kantor Cabang - Konfirmasi 4A)
INSERT INTO team (team_id, office_id, division_id, leader_employee_id, name, status) VALUES
('44444444-0000-4000-a000-000000000001', '11111111-0000-4000-a000-000000000001', '33333333-0000-4000-a000-000000000001', '22222222-0000-4000-a000-000000000006', 'Tim Alpha Sipil (Medan)', TRUE),
('44444444-0000-4000-a000-000000000002', '11111111-0000-4000-a000-000000000002', '33333333-0000-4000-a000-000000000001', '22222222-0000-4000-a000-000000000006', 'Tim Bravo Sipil (Cabang Tebing Tinggi)', TRUE),
('44444444-0000-4000-a000-000000000003', '11111111-0000-4000-a000-000000000002', '33333333-0000-4000-a000-000000000002', '22222222-0000-4000-a000-000000000004', 'Tim Charlie MEP (Cabang Tebing Tinggi)', TRUE)
ON CONFLICT (team_id) DO NOTHING;

-- 7. Seed member (5 Baris Keanggotaan Tim)
INSERT INTO member (member_id, team_id, employee_id, is_active) VALUES
('49999999-0000-4000-a000-000000000001', '44444444-0000-4000-a000-000000000001', '22222222-0000-4000-a000-000000000006', TRUE),
('49999999-0000-4000-a000-000000000002', '44444444-0000-4000-a000-000000000001', '22222222-0000-4000-a000-000000000008', TRUE),
('49999999-0000-4000-a000-000000000003', '44444444-0000-4000-a000-000000000002', '22222222-0000-4000-a000-000000000006', TRUE),
('49999999-0000-4000-a000-000000000004', '44444444-0000-4000-a000-000000000002', '22222222-0000-4000-a000-000000000007', TRUE),
('49999999-0000-4000-a000-000000000005', '44444444-0000-4000-a000-000000000003', '22222222-0000-4000-a000-000000000004', TRUE)
ON CONFLICT (member_id) DO NOTHING;

-- 8. Seed address (5 Alamat Domisili Karyawan)
INSERT INTO address (address_id, employee_id, address_line, city, postal_code) VALUES
('51111111-0000-4000-a000-000000000001', '22222222-0000-4000-a000-000000000002', 'Jl. Setia Budi No. 19', 'Medan', '20132'),
('51111111-0000-4000-a000-000000000002', '22222222-0000-4000-a000-000000000003', 'Jl. Ringroad Komplek Tasbi Blok C', 'Medan', '20133'),
('51111111-0000-4000-a000-000000000003', '22222222-0000-4000-a000-000000000006', 'Jl. Marelan Raya Pasar 2', 'Medan', '20255'),
('51111111-0000-4000-a000-000000000004', '22222222-0000-4000-a000-000000000007', 'Jl. Pahlawan No. 12', 'Tebing Tinggi', '20632'),
('51111111-0000-4000-a000-000000000005', '22222222-0000-4000-a000-000000000008', 'Jl. Denai No. 77', 'Medan', '20226')
ON CONFLICT (address_id) DO NOTHING;

-- 9. Seed employee_file (5 Surat & Sertifikat Karyawan)
INSERT INTO employee_file (employee_file_id, employee_id, type, path_file, status, active_at, expired_at) VALUES
('52222222-0000-4000-a000-000000000001', '22222222-0000-4000-a000-000000000006', 'SERTIFIKAT_K3', '/files/emp/agus_k3.pdf', 'active', '2025-01-15 00:00:00+07', '2028-01-15 00:00:00+07'),
('52222222-0000-4000-a000-000000000002', '22222222-0000-4000-a000-000000000006', 'SIM_A', '/files/emp/agus_sima.pdf', 'active', '2024-06-01 00:00:00+07', '2029-06-01 00:00:00+07'),
('52222222-0000-4000-a000-000000000003', '22222222-0000-4000-a000-000000000007', 'SERTIFIKAT_TEKNIS', '/files/emp/riko_fiber.pdf', 'active', '2025-02-01 00:00:00+07', '2028-02-01 00:00:00+07'),
('52222222-0000-4000-a000-000000000004', '22222222-0000-4000-a000-000000000008', 'KONTRAK_PKWT', '/files/emp/doni_pkwt.pdf', 'active', '2025-10-20 00:00:00+07', '2026-10-20 00:00:00+07'),
('52222222-0000-4000-a000-000000000005', '22222222-0000-4000-a000-000000000008', 'KTP', '/files/emp/doni_ktp.pdf', 'active', '2020-01-01 00:00:00+07', NULL)
ON CONFLICT (employee_file_id) DO NOTHING;

-- 10. Seed tool (6 Alat Kantor: 4 Pribadi [Baju, Laptop, Sepatu] + 2 Umum [Bor, Tangga] - Konfirmasi 3B)
INSERT INTO tool (tool_id, office_id, division_id, ownership_type, category, name, tool_code, status) VALUES
('61111111-0000-4000-a000-000000000001', '11111111-0000-4000-a000-000000000001', '33333333-0000-4000-a000-000000000001', 'PERSONAL_LOAN', 'LAPTOP', 'Laptop ThinkPad T14 (Pinjaman Doni)', 'TL-LPT-001', 'loaned'),
('61111111-0000-4000-a000-000000000002', '11111111-0000-4000-a000-000000000001', '33333333-0000-4000-a000-000000000001', 'PERSONAL_LOAN', 'SEPATU', 'Sepatu Safety Kings Size 42 (Pinjaman Doni)', 'TL-SPT-001', 'ready'),
('61111111-0000-4000-a000-000000000003', '11111111-0000-4000-a000-000000000001', '33333333-0000-4000-a000-000000000001', 'PERSONAL_LOAN', 'BAJU', 'Wearpack Safety Visiontech L (Pinjaman Riko)', 'TL-BJU-001', 'loaned'),
('61111111-0000-4000-a000-000000000004', '11111111-0000-4000-a000-000000000001', '33333333-0000-4000-a000-000000000001', 'PERSONAL_LOAN', 'LAPTOP', 'Laptop Asus ExpertBook (Pinjaman Agus)', 'TL-LPT-002', 'loaned'),
('61111111-0000-4000-a000-000000000005', '11111111-0000-4000-a000-000000000001', '33333333-0000-4000-a000-000000000001', 'SHARED_TOOL', 'BOR', 'Mesin Bor Beton Bosch Rotary Hammer', 'TL-BOR-001', 'loaned'),
('61111111-0000-4000-a000-000000000006', '11111111-0000-4000-a000-000000000002', '33333333-0000-4000-a000-000000000001', 'SHARED_TOOL', 'TANGGA', 'Tangga Teleskopik Aluminium 5 Meter', 'TL-TNG-001', 'allocated')
ON CONFLICT (tool_id) DO NOTHING;

-- 11. Seed vehicle (4 Kendaraan: Roda 2, Roda 4, Bak Terbuka dengan status ready, allocated, loaned - Konfirmasi 3A)
INSERT INTO vehicle (vehicle_id, office_id, division_id, vehicle_type, name, number_plate, status) VALUES
('62222222-0000-4000-a000-000000000001', '11111111-0000-4000-a000-000000000001', '33333333-0000-4000-a000-000000000001', 'Truck', 'Mitsubishi L300 Pickup Bak Terbuka', 'BK 8821 XA', 'loaned'),
('62222222-0000-4000-a000-000000000002', '11111111-0000-4000-a000-000000000002', '33333333-0000-4000-a000-000000000001', 'Car', 'Toyota Avanza Operasional Proyek', 'BK 1452 ZN', 'allocated'),
('62222222-0000-4000-a000-000000000003', '11111111-0000-4000-a000-000000000001', '33333333-0000-4000-a000-000000000002', 'Motorcycle', 'Honda CRF 150L Operasional Survey', 'BK 3319 OP', 'ready'),
('62222222-0000-4000-a000-000000000004', '11111111-0000-4000-a000-000000000003', '33333333-0000-4000-a000-000000000001', 'Truck', 'Isuzu Traga Bak Terbuka Rantauprapat', 'BK 9104 RP', 'ready')
ON CONFLICT (vehicle_id) DO NOTHING;

-- 12. Seed vehicle_file (4 Dokumen Surat Kendaraan: STNK, BPKB, KIR)
INSERT INTO vehicle_file (vehicle_file_id, vehicle_id, type, path_file, status, active_at, expired_at) VALUES
('63333333-0000-4000-a000-000000000001', '62222222-0000-4000-a000-000000000001', 'STNK', '/files/vehicles/l300_stnk.pdf', 'active', '2026-01-10 00:00:00+07', '2027-01-10 00:00:00+07'),
('63333333-0000-4000-a000-000000000002', '62222222-0000-4000-a000-000000000001', 'KIR', '/files/vehicles/l300_kir.pdf', 'active', '2026-06-01 00:00:00+07', '2026-12-01 00:00:00+07'),
('63333333-0000-4000-a000-000000000003', '62222222-0000-4000-a000-000000000002', 'STNK', '/files/vehicles/avanza_stnk.pdf', 'active', '2026-03-15 00:00:00+07', '2027-03-15 00:00:00+07'),
('63333333-0000-4000-a000-000000000004', '62222222-0000-4000-a000-000000000001', 'BPKB', '/files/vehicles/l300_bpkb.pdf', 'active', '2023-01-10 00:00:00+07', '2033-01-10 00:00:00+07')
ON CONFLICT (vehicle_file_id) DO NOTHING;

-- 13. Seed vehicle_inspection (3 Riwayat Inspeksi Kendaraan)
INSERT INTO vehicle_inspection (vehicle_inspection_id, vehicle_id, inspector_employee_id, type, path_file) VALUES
('64444444-0000-4000-a000-000000000001', '62222222-0000-4000-a000-000000000001', '22222222-0000-4000-a000-000000000006', 'day', '/files/inspections/l300_daily_oct17.jpg'),
('64444444-0000-4000-a000-000000000002', '62222222-0000-4000-a000-000000000002', '22222222-0000-4000-a000-000000000007', 'month', '/files/inspections/avanza_monthly_oct.jpg'),
('64444444-0000-4000-a000-000000000003', '62222222-0000-4000-a000-000000000003', '22222222-0000-4000-a000-000000000005', 'repair', '/files/inspections/crf_service_oct.jpg')
ON CONFLICT (vehicle_inspection_id) DO NOTHING;

-- 14. Seed work_type (3 Jenis Pekerjaan Kontraktor terikat Divisi)
INSERT INTO work_type (work_type_id, division_id, name, description) VALUES
('71111111-0000-4000-a000-000000000001', '33333333-0000-4000-a000-000000000001', 'Penarikan Kabel Fiber Optik & Tiang', 'Pekerjaan galian, penancapan tiang, dan penarikan kabel udara/tanah'),
('71111111-0000-4000-a000-000000000002', '33333333-0000-4000-a000-000000000002', 'Instalasi Panel Listrik & Perangkat IoT', 'Pemasangan box panel, terminasi MCB, dan integrasi sensor/mikrokontroler'),
('71111111-0000-4000-a000-000000000003', '33333333-0000-4000-a000-000000000001', 'Pengecoran Pondasi & Sipil Gedung', 'Pekerjaan bekisting, pembesian, dan pengecoran struktur sipil')
ON CONFLICT (work_type_id) DO NOTHING;

-- 15. Seed image_requirement (7 Syarat Foto SOP untuk 3 work_type - Konfirmasi 2A & 2B: 1 work_type punya banyak syarat foto)
INSERT INTO image_requirement (image_requirement_id, work_type_id, name, path_image, is_mandatory, sort_order) VALUES
('72222222-0000-4000-a000-000000000001', '71111111-0000-4000-a000-000000000001', 'Foto Sebelum (Titik Tiang & APD Tim)', '/sop_examples/fo_before_sop.jpg', TRUE, 1),
('72222222-0000-4000-a000-000000000002', '71111111-0000-4000-a000-000000000001', 'Foto Proses Penarikan & Kedalaman Galian', '/sop_examples/fo_progress_sop.jpg', TRUE, 2),
('72222222-0000-4000-a000-000000000003', '71111111-0000-4000-a000-000000000001', 'Foto Sesudah & Redaman OPM Terukur', '/sop_examples/fo_after_sop.jpg', TRUE, 3),
('72222222-0000-4000-a000-000000000004', '71111111-0000-4000-a000-000000000002', 'Foto Sebelum (Lokasi Panel Kosong)', '/sop_examples/iot_before_sop.jpg', TRUE, 1),
('72222222-0000-4000-a000-000000000005', '71111111-0000-4000-a000-000000000002', 'Foto Sesudah (Wiring Rapi & Indikator Menyala)', '/sop_examples/iot_after_sop.jpg', TRUE, 2),
('72222222-0000-4000-a000-000000000006', '71111111-0000-4000-a000-000000000003', 'Foto Sebelum (Pembesian & Bekisting)', '/sop_examples/sipil_before_sop.jpg', TRUE, 1),
('72222222-0000-4000-a000-000000000007', '71111111-0000-4000-a000-000000000003', 'Foto Sesudah Pengecoran Selesai', '/sop_examples/sipil_after_sop.jpg', TRUE, 2)
ON CONFLICT (image_requirement_id) DO NOTHING;

-- 16. Seed work_plan_weekly (2 Work Plan Mingguan: Minggu ke-42 & Minggu ke-43 Tahun 2026)
INSERT INTO work_plan_weekly (weekly_plan_id, division_id, team_id, week_number, year, start_date, end_date, created_by_id, approved_by_pm_id, status) VALUES
('81111111-0000-4000-a000-000000000001', '33333333-0000-4000-a000-000000000001', '44444444-0000-4000-a000-000000000001', 42, 2026, '2026-10-12', '2026-10-18', '22222222-0000-4000-a000-000000000006', '22222222-0000-4000-a000-000000000003', 'ONGOING'),
('81111111-0000-4000-a000-000000000002', '33333333-0000-4000-a000-000000000001', '44444444-0000-4000-a000-000000000002', 43, 2026, '2026-10-19', '2026-10-25', '22222222-0000-4000-a000-000000000006', '22222222-0000-4000-a000-000000000003', 'APPROVED')
ON CONFLICT (weekly_plan_id) DO NOTHING;

-- 17. Seed work_plan_daily (4 Jadwal Harian: Dalam Kota & Luar Kota)
INSERT INTO work_plan_daily (daily_plan_id, weekly_plan_id, work_date, site_name, site_lat, site_lng, attendance_radius_m, clock_in_time, clock_out_time, status) VALUES
('82222222-0000-4000-a000-000000000001', '81111111-0000-4000-a000-000000000001', '2026-10-16', 'Site Proyek Medan Barat (Dalam Kota)', 3.6010000, 98.6800000, 150, '07:00:00', '16:00:00', 'PARTIAL'),
('82222222-0000-4000-a000-000000000002', '81111111-0000-4000-a000-000000000001', '2026-10-17', 'Site Proyek Medan Barat - Lanjutan (Dalam Kota)', 3.6010000, 98.6800000, 150, '07:00:00', '16:00:00', 'ONGOING'),
('82222222-0000-4000-a000-000000000003', '81111111-0000-4000-a000-000000000001', '2026-10-17', 'Site Proyek Kawasan Industri Tebing Tinggi (Luar Kota)', 3.3300000, 99.1650000, 200, '07:30:00', '16:30:00', 'ONGOING'),
('82222222-0000-4000-a000-000000000004', '81111111-0000-4000-a000-000000000002', '2026-10-19', 'Site Proyek Tebing Tinggi Tahap 2 (Minggu Depan)', 3.3300000, 99.1650000, 200, '07:30:00', '16:30:00', 'PLANNED')
ON CONFLICT (daily_plan_id) DO NOTHING;

-- 18. Seed work_plan_item (5 Item Pekerjaan: Termasuk Geser Hari yang Disetujui PM & Pengajuan Alokasi Minggu Depan - Konfirmasi 6B)
INSERT INTO work_plan_item (item_id, daily_plan_id, weekly_plan_id, work_type_id, title, target_qty, completed_qty, progress_percent, status, rollover_approval_status, approved_by_pm_id, origin_item_id, shifted_to_daily_id, allocated_to_weekly_id, delay_reason) VALUES
('83333333-0000-4000-a000-000000000001', '82222222-0000-4000-a000-000000000001', '81111111-0000-4000-a000-000000000001', '71111111-0000-4000-a000-000000000001', 'Penarikan Kabel FO Sektor A (1000 Meter)', 1000.00, 600.00, 60.00, 'SHIFTED_DAY', 'APPROVED_BY_PM', '22222222-0000-4000-a000-000000000003', NULL, '82222222-0000-4000-a000-000000000002', NULL, 'Hujan deras pukul 14:30, sisa 400m digeser ke besok'),
('83333333-0000-4000-a000-000000000002', '82222222-0000-4000-a000-000000000002', '81111111-0000-4000-a000-000000000001', '71111111-0000-4000-a000-000000000001', 'Lanjutan Penarikan Kabel FO Sektor A (Sisa 400 Meter)', 400.00, 400.00, 100.00, 'DONE', 'NONE', NULL, '83333333-0000-4000-a000-000000000001', NULL, NULL, NULL),
('83333333-0000-4000-a000-000000000003', '82222222-0000-4000-a000-000000000003', '81111111-0000-4000-a000-000000000001', '71111111-0000-4000-a000-000000000002', 'Instalasi 5 Titik Panel Sensor IoT Gudang', 5.00, 5.00, 100.00, 'DONE', 'NONE', NULL, NULL, NULL, NULL, NULL),
('83333333-0000-4000-a000-000000000004', '82222222-0000-4000-a000-000000000003', '81111111-0000-4000-a000-000000000001', '71111111-0000-4000-a000-000000000003', 'Pengecoran Pondasi Tiang Utama Gate B', 4.00, 1.00, 25.00, 'PENDING_ROLLOVER', 'WAITING_PM', NULL, NULL, NULL, '81111111-0000-4000-a000-000000000002', 'Menunggu izin akses crane dari pengelola kawasan industri'),
('83333333-0000-4000-a000-000000000005', '82222222-0000-4000-a000-000000000004', '81111111-0000-4000-a000-000000000002', '71111111-0000-4000-a000-000000000001', 'Penarikan Backbone Antar Gedung Kawasan Industri', 1500.00, 0.00, 0.00, 'TODO', 'NONE', NULL, NULL, NULL, NULL, NULL)
ON CONFLICT (item_id) DO NOTHING;

-- 19. Seed company_mess_stay (3 Catatan Lokasi Mes & Siapa yang Menginap - Konfirmasi 5C)
INSERT INTO company_mess_stay (mess_stay_id, mess_name, city, address, latitude, longitude, employee_id, weekly_plan_id, stay_start_date, stay_end_date) VALUES
('84444444-0000-4000-a000-000000000001', 'Mes Kontraktor Visiontech Tebing Tinggi', 'Tebing Tinggi', 'Jl. Kartini No. 14, Tebing Tinggi', 3.3291000, 99.1610000, '22222222-0000-4000-a000-000000000006', '81111111-0000-4000-a000-000000000001', '2026-10-16', '2026-10-18'),
('84444444-0000-4000-a000-000000000002', 'Mes Kontraktor Visiontech Tebing Tinggi', 'Tebing Tinggi', 'Jl. Kartini No. 14, Tebing Tinggi', 3.3291000, 99.1610000, '22222222-0000-4000-a000-000000000007', '81111111-0000-4000-a000-000000000001', '2026-10-16', '2026-10-18'),
('84444444-0000-4000-a000-000000000003', 'Mes Visiontech Rantauprapat', 'Rantauprapat', 'Jl. Sisingamangaraja No. 21, Rantauprapat', 2.0985000, 99.8240000, '22222222-0000-4000-a000-000000000004', NULL, '2026-10-15', '2026-10-20')
ON CONFLICT (mess_stay_id) DO NOTHING;

-- 20. Seed asset_assignment (5 Transaksi Peminjaman Alat & Kendaraan)
INSERT INTO asset_assignment (assignment_id, asset_type, tool_id, vehicle_id, employee_id, daily_plan_id, assignment_status, loaned_at, returned_at, handover_photo_path) VALUES
('85555555-0000-4000-a000-000000000001', 'TOOL', '61111111-0000-4000-a000-000000000001', NULL, '22222222-0000-4000-a000-000000000008', NULL, 'loaned', '2025-10-21 09:00:00+07', NULL, '/uploads/handover/doni_laptop.jpg'),
('85555555-0000-4000-a000-000000000002', 'TOOL', '61111111-0000-4000-a000-000000000002', NULL, '22222222-0000-4000-a000-000000000008', NULL, 'ready', '2025-10-21 09:00:00+07', '2026-10-16 15:00:00+07', '/uploads/handover/doni_sepatu_return.jpg'),
('85555555-0000-4000-a000-000000000003', 'TOOL', '61111111-0000-4000-a000-000000000003', NULL, '22222222-0000-4000-a000-000000000007', NULL, 'loaned', '2025-02-02 09:00:00+07', NULL, '/uploads/handover/riko_wearpack.jpg'),
('85555555-0000-4000-a000-000000000004', 'TOOL', '61111111-0000-4000-a000-000000000005', NULL, '22222222-0000-4000-a000-000000000006', '82222222-0000-4000-a000-000000000002', 'loaned', '2026-10-17 06:50:00+07', NULL, '/uploads/handover/agus_bor_proyek.jpg'),
('85555555-0000-4000-a000-000000000005', 'VEHICLE', NULL, '62222222-0000-4000-a000-000000000001', '22222222-0000-4000-a000-000000000006', '82222222-0000-4000-a000-000000000002', 'loaned', '2026-10-17 06:45:00+07', NULL, '/uploads/handover/agus_l300_pickup.jpg')
ON CONFLICT (assignment_id) DO NOTHING;

-- 21. Seed employee_offboarding (2 Kasus Offboarding - Konfirmasi 1A)
INSERT INTO employee_offboarding (offboarding_id, employee_id, reason_type, submission_date, effective_date, is_all_assets_returned, approved_by_pm_id, approved_by_hr_id, status, notes) VALUES
('86666666-0000-4000-a000-000000000001', '22222222-0000-4000-a000-000000000008', 'PKWT_EXPIRED', '2026-10-15 10:00:00+07', '2026-10-20', FALSE, '22222222-0000-4000-a000-000000000003', NULL, 'CLEARANCE_PENDING', 'Kontrak PKWT berakhir 20 Okt 2026. Menunggu pengembalian Laptop ThinkPad T14.'),
('86666666-0000-4000-a000-000000000002', '22222222-0000-4000-a000-000000000007', 'PKWT_EXPIRED', '2026-01-10 10:00:00+07', '2026-01-31', TRUE, '22222222-0000-4000-a000-000000000003', '22222222-0000-4000-a000-000000000005', 'COMPLETED', 'Riwayat offboarding periode kontrak lama sebelum diperpanjang.')
ON CONFLICT (offboarding_id) DO NOTHING;

-- 22. Seed offboarding_clearance_item (3 Item Ceklis Pengembalian Barang Offboarding)
INSERT INTO offboarding_clearance_item (clearance_item_id, offboarding_id, assignment_id, return_condition, handover_photo_path, verified_by_id, verified_at) VALUES
('87777777-0000-4000-a000-000000000001', '86666666-0000-4000-a000-000000000001', '85555555-0000-4000-a000-000000000002', 'GOOD', '/uploads/handover/doni_sepatu_return.jpg', '22222222-0000-4000-a000-000000000005', '2026-10-16 15:10:00+07'),
('87777777-0000-4000-a000-000000000002', '86666666-0000-4000-a000-000000000001', '85555555-0000-4000-a000-000000000001', 'PENDING', NULL, NULL, NULL),
('87777777-0000-4000-a000-000000000003', '86666666-0000-4000-a000-000000000002', '85555555-0000-4000-a000-000000000003', 'GOOD', '/uploads/handover/riko_wearpack.jpg', '22222222-0000-4000-a000-000000000005', '2026-01-30 16:00:00+07')
ON CONFLICT (clearance_item_id) DO NOTHING;

-- 23. Seed attendance (4 Skenario Uji Absensi Nyata - Konfirmasi 5A & 5B)
INSERT INTO attendance (attendance_id, employee_id, attendance_date, target_location_type, office_id, daily_plan_id, scheduled_in, scheduled_out, clock_in_at, clock_out_at, in_lat, in_lng, face_match_score, face_photo_path, distance_to_target_m, is_within_attendance_radius, out_of_radius_photo_path, out_of_radius_note, om_approval_status, distance_from_main_office_m, city_zone_status, meal_allowance_amount) VALUES
('88888888-0000-4000-a000-000000000001', '22222222-0000-4000-a000-000000000005', '2026-10-17', 'OFFICE', '11111111-0000-4000-a000-000000000001', NULL, '07:00:00', '16:00:00', '2026-10-17 06:54:12+07', '2026-10-17 16:05:00+07', 3.5955000, 98.6725000, 98.40, '/uploads/att/siti_face_oct17.jpg', 47, TRUE, NULL, NULL, 'AUTO_VALID', 47, 'DALAM_KOTA', 35000.00),
('88888888-0000-4000-a000-000000000002', '22222222-0000-4000-a000-000000000004', '2026-10-17', 'OFFICE', '11111111-0000-4000-a000-000000000002', NULL, '07:30:00', '16:30:00', '2026-10-17 07:22:10+07', '2026-10-17 16:35:00+07', 3.3288000, 99.1627000, 96.80, '/uploads/att/dian_face_oct17.jpg', 40, TRUE, NULL, NULL, 'AUTO_VALID', 61979, 'LUAR_KOTA', 65000.00),
('88888888-0000-4000-a000-000000000003', '22222222-0000-4000-a000-000000000006', '2026-10-17', 'WORK_PLAN_DAILY', '11111111-0000-4000-a000-000000000001', '82222222-0000-4000-a000-000000000002', '07:00:00', '16:00:00', '2026-10-17 06:58:00+07', NULL, 3.6050000, 98.6850000, 95.20, '/uploads/att/agus_face_oct17.jpg', 711, FALSE, '/uploads/att/agus_out_radius_proof.jpg', 'Akses masuk mobil L300 ditutup pengecoran jalan desa, parkir 700m dari titik tiang', 'PENDING_OM', 1790, 'DALAM_KOTA', 35000.00),
('88888888-0000-4000-a000-000000000004', '22222222-0000-4000-a000-000000000007', '2026-10-17', 'WORK_PLAN_DAILY', '11111111-0000-4000-a000-000000000002', '82222222-0000-4000-a000-000000000003', '07:30:00', '16:30:00', '2026-10-17 07:19:45+07', NULL, 3.3305000, 99.1655000, 97.50, '/uploads/att/riko_face_oct17.jpg', 79, TRUE, NULL, NULL, 'AUTO_VALID', 62162, 'LUAR_KOTA', 65000.00)
ON CONFLICT (attendance_id) DO NOTHING;

-- 24. Seed work_completion & document_template_export (3 Laporan + 4 File Eksport Word, PPTX, PDF, Excel - Konfirmasi 6A & 6C)
INSERT INTO work_completion (completion_id, report_scope, daily_plan_id, weekly_plan_id, summary_notes, obstacles, realization_photos_json, leader_signer_id, leader_signature_path, leader_signed_at, pm_signer_id, pm_signature_path, pm_signed_at, signature_hash) VALUES
('91111111-0000-4000-a000-000000000001', 'DAILY', '82222222-0000-4000-a000-000000000001', '81111111-0000-4000-a000-000000000001', 'Penarikan kabel FO Sektor A tercapai 600m dari 1000m. Sisa 400m telah disetujui PM digeser ke 17 Okt.', 'Hujan deras mulai pukul 14:30 WIB', '[{"req_id": "72222222-0000-4000-a000-000000000001", "url": "/uploads/completion/fo_16okt_before.jpg"}, {"req_id": "72222222-0000-4000-a000-000000000002", "url": "/uploads/completion/fo_16okt_prog.jpg"}]', '22222222-0000-4000-a000-000000000006', '/signatures/tl_agus_sig.png', '2026-10-16 16:30:00+07', '22222222-0000-4000-a000-000000000003', '/signatures/pm_hendrik_sig.png', '2026-10-16 17:15:00+07', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
('91111111-0000-4000-a000-000000000002', 'DAILY', '82222222-0000-4000-a000-000000000002', '81111111-0000-4000-a000-000000000001', 'Penyelesaian sisa 400m kabel FO Sektor A tuntas 100%. Redaman OPM normal -18 dBm.', 'Tidak ada kendala', '[{"req_id": "72222222-0000-4000-a000-000000000003", "url": "/uploads/completion/fo_17okt_after.jpg"}]', '22222222-0000-4000-a000-000000000006', '/signatures/tl_agus_sig.png', '2026-10-17 16:10:00+07', '22222222-0000-4000-a000-000000000003', '/signatures/pm_hendrik_sig.png', '2026-10-17 16:45:00+07', 'f4c0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b999'),
('91111111-0000-4000-a000-000000000003', 'WEEKLY', NULL, '81111111-0000-4000-a000-000000000001', 'Rekapitulasi Mingguan Week 42: FO Sektor A selesai 100%, Panel IoT Gudang selesai 100%, Pondasi Gate B (25%) diajukan rollover ke Week 43.', 'Izin crane kawasan industri baru keluar Senin depan', '[{"req_id": "72222222-0000-4000-a000-000000000005", "url": "/uploads/completion/iot_week42_done.jpg"}]', '22222222-0000-4000-a000-000000000006', '/signatures/tl_agus_sig.png', '2026-10-17 17:00:00+07', '22222222-0000-4000-a000-000000000003', '/signatures/pm_hendrik_sig.png', '2026-10-17 17:30:00+07', 'a9b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b111')
ON CONFLICT (completion_id) DO NOTHING;

INSERT INTO document_template_export (export_id, completion_id, template_type, master_template_path, export_format, file_output_url, generated_by_id) VALUES
('92222222-0000-4000-a000-000000000001', '91111111-0000-4000-a000-000000000002', 'DAILY_TEMPLATE', '/templates/master_daily_report_vms.docx', 'WORD_DOCX', '/exports/2026_10/Daily_Completion_17Okt2026.docx', '22222222-0000-4000-a000-000000000006'),
('92222222-0000-4000-a000-000000000002', '91111111-0000-4000-a000-000000000002', 'DAILY_TEMPLATE', '/templates/master_daily_report_vms.docx', 'PDF', '/exports/2026_10/Daily_Completion_17Okt2026.pdf', '22222222-0000-4000-a000-000000000003'),
('92222222-0000-4000-a000-000000000003', '91111111-0000-4000-a000-000000000003', 'WEEKLY_TEMPLATE', '/templates/master_weekly_presentation_vms.pptx', 'PPTX', '/exports/2026_10/Weekly_Presentation_W42_2026.pptx', '22222222-0000-4000-a000-000000000003'),
('92222222-0000-4000-a000-000000000004', '91111111-0000-4000-a000-000000000003', 'WEEKLY_TEMPLATE', '/templates/master_weekly_boq_vms.xlsx', 'EXCEL_XLSX', '/exports/2026_10/Weekly_Recap_And_Meal_W42_2026.xlsx', '22222222-0000-4000-a000-000000000005')
ON CONFLICT (export_id) DO NOTHING;

-- 25. Seed app_activity_logs (6 Baris Audit Log Ringan yang otomatis masuk ke Partisi Oktober 2026)
INSERT INTO app_activity_logs (log_id, created_at, actor_user_id, actor_role, platform, action, entity_table, entity_id, changed_diff, ip_address, gps_location) VALUES
('93333333-0000-4000-a000-000000000001', '2026-10-16 16:00:00+07', '29999999-0000-4000-a000-000000000006', 'TEAM_LEADER', 'android_flutter', 'REQUEST_ROLLOVER', 'work_plan_item', '83333333-0000-4000-a000-000000000001', '{"status": {"old": "IN_PROGRESS", "new": "PENDING_ROLLOVER"}, "completed_qty": {"old": 0, "new": 600}}', '114.122.10.44', '3.6010,98.6800'),
('93333333-0000-4000-a000-000000000002', '2026-10-16 16:20:00+07', '29999999-0000-4000-a000-000000000003', 'PROJECT_MANAGER', 'web_react', 'APPROVE_ROLLOVER', 'work_plan_item', '83333333-0000-4000-a000-000000000001', '{"status": {"old": "PENDING_ROLLOVER", "new": "SHIFTED_DAY"}, "rollover_approval_status": {"old": "WAITING_PM", "new": "APPROVED_BY_PM"}}', '103.10.66.15', '3.5952,98.6722'),
('93333333-0000-4000-a000-000000000003', '2026-10-16 15:10:00+07', '29999999-0000-4000-a000-000000000005', 'ADMIN_HR_GA', 'web_react', 'OFFBOARD_CLEARANCE', 'offboarding_clearance_item', '87777777-0000-4000-a000-000000000001', '{"return_condition": {"old": "PENDING", "new": "GOOD"}}', '103.10.66.10', '3.5952,98.6722'),
('93333333-0000-4000-a000-000000000004', '2026-10-17 06:58:00+07', '29999999-0000-4000-a000-000000000006', 'TEAM_LEADER', 'android_flutter', 'CLOCK_IN_OUT_OF_RADIUS', 'attendance', '88888888-0000-4000-a000-000000000003', '{"distance_to_target_m": 711, "is_within_attendance_radius": false, "om_approval_status": "PENDING_OM"}', '114.122.10.44', '3.6050,98.6850'),
('93333333-0000-4000-a000-000000000005', '2026-10-17 17:30:00+07', '29999999-0000-4000-a000-000000000003', 'PROJECT_MANAGER', 'web_react', 'SIGN_REPORT', 'work_completion', '91111111-0000-4000-a000-000000000003', '{"pm_signed_at": "2026-10-17T17:30:00+07:00"}', '103.10.66.15', '3.5952,98.6722'),
('93333333-0000-4000-a000-000000000006', '2026-10-17 17:35:00+07', '29999999-0000-4000-a000-000000000003', 'PROJECT_MANAGER', 'web_react', 'EXPORT_DOC', 'document_template_export', '92222222-0000-4000-a000-000000000003', '{"export_format": "PPTX", "file_output_url": "/exports/2026_10/Weekly_Presentation_W42_2026.pptx"}', '103.10.66.15', '3.5952,98.6722')
ON CONFLICT (log_id, created_at) DO NOTHING;

-- 26. Seed system_backup_registry (2 Riwayat Backup Siklus 1 Bulan & 6 Bulan)
INSERT INTO system_backup_registry (backup_id, backup_cycle, period_start, period_end, file_path_url, compressed_size_mb, sha256_checksum, status) VALUES
('94444444-0000-4000-a000-000000000001', 'SIX_MONTH_ARCHIVE', '2026-03-01', '2026-08-31', 's3://vms-cold-backup/archive_6m_2026_H1.dump.zst', 107.29, '1111222233334444555566667777888899990000aaaabbbbccccddddeeeeffff', 'VERIFIED'),
('94444444-0000-4000-a000-000000000002', 'MONTHLY_SNAPSHOT', '2026-09-01', '2026-09-30', 's3://vms-cold-backup/snapshot_1m_2026_09.dump.zst', 17.88, '9999888877776666555544443333222211110000ffffaaaaccccbbbbaaaadddd', 'VERIFIED')
ON CONFLICT (backup_id) DO NOTHING;

COMMIT;
