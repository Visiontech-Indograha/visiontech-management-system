# Hasil uji web perbaikan (sebagian; terblokir di tengah jalan)

## A) Foto titik survei WO-202611-003
- Dua PNG uji diunggah lewat POST /files/upload (token pm1@uji-nyata.test): file_id e4fc413d-b33e-4199-ba34-7eb67a2e5361 dan 2929fe36-56ab-46db-9180-1c680847641c.
- Route resmi pengisi work_order_survey_points: POST /work-orders/{id}/submit-survey (SurveyPointIn.photos = larik objek bebas). Dikirim ulang dengan 2 titik yang sama + photos [{file_id, slot}]. Tabel kini berisi photos_json terisi untuk titik A dan B (status TODO; id titik baru karena submit membuat ulang titik).
- Catatan: PUT /work-plans/surveys/points/{id} (skema PointPhoto butuh requirement_id) menulis ke work_plan_item, BUKAN work_order_survey_points; jadi bukan jalur untuk WO review.
- Web membaca: usePointPhotoUrl menerima string / {url|file_url|file_id|id}; file_id UUID diubah jadi URL bertiket via useFileUrl. Format {file_id,slot} sesuai, seharusnya tampil. BELUM DIVERIFIKASI di browser (popup marker, galeri, lightbox).

## B) Foto profil via API resmi
- PUT /employees/me/photo dengan file_id hasil upload: hr@uji-nyata.test (79faf317-2630-460c-9850-2e0031a09618), pm1@uji-nyata.test (a04248be-d772-4586-b266-815e344f45ee). Respons 200.
- Akun berpath lama (/uploads/profiles/*.jpg: randi.om@, hendrik.pm@, dian.pm@, siti.hr@, agus.tl@, riko.tech@, doni.tech@, fajar.tech@, bayu.tech@, ilham.tech@ visiontech.co.id) TIDAK diubah: sandi tidak diketahui (dilarang menebak).
- Verifikasi tampilan di web (Akun & sidebar) belum dilakukan.

## C) Modal Finance (Chrome, selesai); HR/Office belum
Screenshot di e2e-reports/screenshots/FINANCE/ (.jpg): web_modal_cuti_ajukan, web_modal_aset_berkas, web_modal_lokasi_tambah, web_modal_absensi_tinjau, web_modal_konfirmasi_keluar.
- Semua modal muat di viewport 1536x711, tidak terpotong; Lokasi kerja (tinggi 620px) menggulir di dalam.
- Direktori untuk Finance hanya baca (tanpa Tambah/profil modal). Rekap lembur, Berkas saya tanpa modal.
- Temuan kecil: modal Berkas aset punya tombol ganda "Batal" dan "Tutup".
- Tab Chrome sendiri (id 125549909) TIDAK sempat ditutup (ekstensi Chrome terputus); mohon tutup manual.
- Baris hse_campaign_acknowledgments buatan uji (finance@ 08:36, hr@ 08:47 UTC) sudah dihapus.
- Server Vite web (port 5173) saya jalankan karena mati; masih berjalan.

## D) Viewport 390px: BELUM DIKERJAKAN
Penyebab: Playwright MCP mengunci profil browser (Chrome milik sesi ini, pid 1164, tak bisa dilepas; percobaan menutupnya ditolak sistem izin). Modal HR (Direktori tambah, Cuti, Aset, Mess, Offboarding, Tim, Berkas) dan Office belum dibuka.
