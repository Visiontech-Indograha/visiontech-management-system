# 39 — Rencana desain ulang UI/UX (web & HP)

Tujuan: mempermudah, bukan menambah ribet. Bahasa sehari-hari (lihat padanan di memori `vms-bahasa-sederhana`).

## Prinsip
1. Satu layar = satu tugas utama; tombol utama besar di bawah (HP) / kanan atas (web).
2. Jenis pekerjaan selalu terpisah & berwarna: Survei · Persiapan · Instalasi · Replacement · Maintenance.
3. Status pakai kata kerja: "Belum mulai", "Sedang dikerjakan", "Menunggu PM", "Selesai".
4. Kontak PM ↔ ketua tim (telepon/WA) selalu terlihat di layar jadwal & pekerjaan.
5. PM hanya melihat divisi & anggota timnya sendiri.

## Urutan layar (satu per satu, screenshot sebelum/sesudah, minta persetujuan)
1. Web — Jadwal harian PM (`DailyWeekMatrix`, `DailyPlanDetailDialog`, `DailyItemsPanel`):
   kartu per hari berisi tim, jenis pekerjaan, "X dari Y selesai", tombol "Lihat hasil kerja".
2. HP — Jadwal saya (`daily_plans_screen.dart`): kartu hari ini di atas, filter jenis, tombol "Mulai kerja".
3. HP — Mengerjakan satu pekerjaan (`item_progress_screen.dart`): langkah 1-2-3
   (foto sebelum → jumlah dikerjakan → foto sesudah), peringatan "Tunggu dulu: …" jelas di atas.
4. Lanjutan: Survei (HP & web), Serah terima pekerjaan, Rekap material, Dokumen.

## Status (2026-10-22, sesi 2)
Selesai & diuji langsung (web PM + HP ketua):
- Web: jadwal jadi **kalender bulanan**; jenis pekerjaan tertulis & berwarna di tiap tanggal; klik tanggal → detail
  lengkap dengan persen progres nyata (`progress_pct` API). Navigasi minggu dihapus.
- Warna (token palet Visiontech): Survei info, Persiapan netral, Instalasi success, Replacement warning,
  Maintenance brand/navy. Status: berjalan biru, terlambat merah, selesai hijau, selesai sebagian kuning.
- HP: tombol refresh dihapus (tarik ke bawah); kartu jadwal baru (blok tanggal berwarna status, label jenis, bilah
  progres); layar **Kerjakan pekerjaan** 3 langkah (foto → jumlah ± → catatan) + tombol simpan tetap di bawah;
  notifikasi berwarna; skeleton loading; animasi muncul kartu & bilah progres; splash & ikon logo asli.
- API: `progress_pct` (jadwal), `depends_on_done` (pekerjaan yang ditunggu sudah selesai?).

- Web "Pekerjaan klien": bahasa sederhana, saringan keadaan & jenis, warna, persen nyata (`progress_pct`, `phases`
  di API); PM hanya melihat divisinya (data uji lama dipindah ke PM divisi; seed diperbarui).
- PPTX bertema brand (`builders/pptx_theme.py`): sampul navy-emas + lambang tim, kartu angka, tabel status berwarna,
  slide foto berbingkai, penutup — dipakai laporan pekerjaan klien, rekap divisi, dan **laporan mingguan tim**
  (`POST /exports/team-week`, ketua/anggota tim atau PM/OM divisinya). HP: tombol "Laporan minggu ini (.pptx)" di
  Jadwal kerja dan "Unduh laporan slide" di Serah terima.
- Perbaikan server: header nama berkas non-ASCII (mis. "—") membuat foto 500 → `shared/content_disposition.py`.

Belum: layar Survei (HP & web), Rekap material, Dokumen; snapshot OpenAPI & tes untuk endpoint baru.
