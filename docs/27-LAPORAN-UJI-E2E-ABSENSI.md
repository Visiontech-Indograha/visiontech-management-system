# 27 · Laporan Uji E2E — Absensi R-33 & R-34 (web + HP)

## 1. Informasi umum

| | |
|---|---|
| Nama aplikasi | VMS — Visiontech Management System (web + aplikasi lapangan Android) |
| Modul / fitur | R-33: gerbang login per kategori akun, kanal web/HP, penjelasan & swafoto di luar radius, cakupan peninjau (PM → lapangan unitnya, Finance → kantor, OPS → Finance), ajukan ulang 1× lalu terkunci, lokasi kerja per unit. R-34: absen luring bertanda tangan (jangkar jam server, idempoten, absen pulang ditahan sampai disetujui) |
| Tanggal pengujian | 2026-10-02 |
| Penguji | Claude (agen), atas permintaan pemilik — semua langkah lewat klik di layar, kecuali yang ditandai *API/skrip* |
| Kode yang diuji | Branch `prod` @ `31cf0b82` (PR #6), dibangun ulang di lokal: citra API & web (Caddy) dari `git archive origin/prod`, APK debug dari `mobile/` branch yang sama |
| Lingkungan | **Build produksi di lokal.** API :8000 & web :8080 (Docker, jaringan `vms-lokal-net`), DB uji PostgreSQL 18 (`vms_db_test_local18`), MinIO lokal. Web: peramban bawaan aplikasi (Chromium). HP: emulator Android `Pixel_10_Pro_XL` (API `10.0.2.2:8000`). Bukan server produksi |
| Data uji | Data awal lokal (`.local_tests/real-logins.txt`, tidak di Git): 6 akun kantor (HR, Finance, Asset, OPS, 2 PM) + 8 akun lapangan unit SRV & INF. Lokasi: Kantor Pusat (r 150 m), Proyek Pemetaan Bandung (SRV, r 300 m), Proyek Fiber Optik Bekasi (INF, r 250 m). Absensi hari uji dikosongkan dulu (cadangan `pg_dump`) |
| Alat bantu | Web: posisi GPS disimulasikan dengan mengganti `navigator.geolocation`, webcam dengan stream kanvas (peramban bawaan tidak memberi izin lokasi/kamera). HP: `adb emu geo fix`, mode pesawat `cmd connectivity airplane-mode`, kamera emulator |

## 2. Skenario pengujian — web

| ID | Deskripsi | Langkah | Data uji | Hasil yang diharapkan | Hasil aktual | Status |
|---|---|---|---|---|---|---|
| W1 | Akun lapangan tidak bisa masuk web | `/login` → email & sandi akun lapangan → Masuk | Andi (lapangan SRV) | Ditolak, diarahkan ke aplikasi HP | "Akun Anda bukan kategori akun kantor. Silakan gunakan aplikasi HP Visiontech." | Pass |
| W2 | Absen kantor di dalam radius, lalu pulang | Absensi → Absen masuk → Absen pulang | Siti (HR), posisi Kantor Pusat 0 m | Valid otomatis; kartu menampilkan jam masuk & pulang | "Valid otomatis · 0 m", masuk 15.34, pulang 15.34, "Absensi hari ini selesai" | Pass |
| W3 | Absen di luar radius: penjelasan + swafoto webcam | Absen masuk → isi penjelasan → Absen masuk → Ambil foto | Bayu (Asset), 1,1 km dari kantor | Penjelasan wajib, swafoto wajib, status Perlu review, tombol pulang tidak ada | Kolom "Penjelasan (wajib)" muncul, dialog swafoto, "Perlu review · 1106 m", pesan "Absen pulang bisa dilakukan setelah absen masuk disetujui" | Pass |
| W4 | Finance menolak absen kantor; catatan wajib | Tinjau → lihat swafoto → Tolak tanpa catatan → isi catatan → Simpan | Agus (Finance) meninjau Bayu | Tanpa catatan ditolak form; lalu status Ditolak | "Catatan pemeriksaan wajib diisi."; setelah diisi → Ditolak | Pass |
| W5 | Ajukan ulang dari dalam radius | Login Bayu → "Ajukan absen ulang" + alasan | Bayu, posisi kantor 0 m | Lokasi dicek ulang → Valid otomatis | Valid otomatis 0 m, penjelasan tercatat | Pass |
| W6 | Ditolak 2× → hari itu terkunci | Rina absen di luar radius → Agus tolak → Rina ajukan ulang dari luar radius → Agus tolak lagi | Rina (PM), 1,1 km | Tidak ada tombol absen; pesan terkunci | "Absensi hari ini ditolak 2 kali dan tidak dapat diajukan lagi." tanpa tombol | Pass |
| W7 | OPS meninjau Finance; tidak ada yang meninjau absen sendiri | Login Lestari → Tinjau absen Agus → Setujui. Cek tombol pada absen milik sendiri | Lestari (OPS), Agus (Finance), Rina | OPS hanya bisa meninjau Finance; absen sendiri hanya "Ubah penjelasan" | Lestari hanya punya tombol Tinjau pada Agus → Disetujui. Rina & Agus melihat absen sendiri tanpa tombol Tinjau. *API:* OPS, Finance, dan PM unit lain meninjau absen lapangan SRV → 403 "di luar kewenangan peninjauan Anda" | Pass |
| W8 | PM membuat lokasi proyek; HR tidak boleh | Rina: Lokasi kerja → Tambah lokasi → simpan. Siti: buka `/sites` | Rina (PM SRV), Siti (HR) | Lokasi baru di unit SRV; HR ditolak | Lokasi "Proyek Uji E2E Lembang" tersimpan dengan unit SRV (dicek di DB); Rina tidak melihat lokasi INF. Siti → halaman "Akses ditolak"; *API* `POST /sites` → 403 | Pass |
| W9 | Cakupan daftar & rekap | Absensi (Semua status) dan Rekap absensi | Rina (PM SRV), Lestari (OPS) | PM hanya diri sendiri + lapangan unitnya; OPS semua; rekap menampilkan jam masuk/keluar; absen luring diberi tanda | Rina: dirinya + Andi, Budi, Citra, Dewi; "· absen luring" pada Citra & Dewi; rekap "Masuk 16.04 · Keluar 16.05". Lestari: 11 karyawan termasuk INF & kantor | Pass |

## 3. Skenario pengujian — HP (emulator)

| ID | Deskripsi | Langkah | Data uji | Hasil yang diharapkan | Hasil aktual | Status |
|---|---|---|---|---|---|---|
| M1 | Akun kantor tidak bisa masuk HP | Login di aplikasi | Siti (HR) | Ditolak | "Akun Anda tidak termasuk kategori staf lapangan. Silakan masuk lewat web." | Pass |
| M2 | Absen online di dalam radius, lalu pulang | Absen masuk → Absen pulang | Andi, Bandung 0 m | Valid → pulang tercatat | Valid, masuk 15:47, pulang 15:48, "Absensi hari ini selesai" | Pass |
| M3 | Absen online di luar radius | Absen masuk → dialog "Absen di luar zona" → penjelasan → kamera swafoto (watermark koordinat & jam) → ambil | Budi, 2 km dari Bandung | Perlu review, tombol pulang tidak ada | "Perlu review", swafoto tersimpan, tidak ada tombol pulang | Pass |
| M4 | Tolak → ajukan ulang dari dalam radius; tolak 2× → terkunci | Rina menolak Budi di web → Budi "Ajukan absen ulang" + alasan dari 0 m. Kasus kedua: Fajar di luar radius, ditolak Dimas (*API*), ajukan ulang dari luar radius, ditolak lagi | Budi (SRV), Fajar (INF) | Budi valid; Fajar terkunci | Budi: "Valid" masuk 16:00. Fajar: "Absensi hari ini ditolak 2 kali dan tidak dapat diajukan lagi", tanpa tombol | Pass |
| M5 | Luring di dalam radius → sinkron otomatis | Mode pesawat → Absen masuk → matikan mode pesawat | Citra, Bandung 0 m | Kartu "Tersimpan luring"; online → terkirim sendiri, Valid; web menandai luring | "Tersimpan luring", "1 data menunggu"; setelah online → Valid, DB `offline = true`, web "· absen luring" | Pass |
| M6 | Luring di luar radius: masuk + pulang saat pesawat | Mode pesawat → Absen masuk (penjelasan + swafoto) → Absen pulang → online → Rina Tinjau di web → Setujui | Dewi, 2 km | Masuk Perlu review, pulang ditahan; dialog Tinjau menampilkan kotak luring & pulang tertahan; setelah disetujui jam pulang terisi | HP: "Absen masuk & pulang tersimpan luring". Online: Perlu review, pulang kosong. Dialog: "Absen luring (direkam tanpa sinyal…)" + "Absen pulang 02 Okt 2026 16.05 WIB berlaku bila absensi ini disetujui". Disetujui → DB pulang 16:05, HP "Disetujui · 16:04 – 16:05" | Pass |
| M7 | Online tapi server gagal sementara | Mode pesawat → absen di luar radius (swafoto) → API dimatikan → online → "Sinkronkan sekarang" → API dinyalakan → sinkron | Eko, 1,7 km dari Bekasi | Antrean tetap (tidak masuk "Perlu tindakan"); terkirim setelah pulih; foto tertunda dihitung benar; berkas luring dihapus setelah terkirim | Saat gagal: Data tertunda 1, Foto tertunda 1, Perlu tindakan 0, "Tidak ada koneksi". Setelah pulih: 0/0/0, "Sinkronisasi berhasil"; DB masuk 16:08 (jam HP, bukan jam terima), `offline = true`, swafoto ada; folder `offline_attendance` kosong | Pass |
| M8 | Data diubah, jam HP palsu, kirim ulang | *Skrip simulasi perangkat* `offline_sim.py` (kunci P-256 sendiri): payload diubah setelah ditandatangani; jam perangkat +3 jam; kirim ulang peristiwa yang sama | Hendra (INF) | Diubah → ditolak; jam dari jangkar server; duplikat dikenali | `422 OFFLINE_TAMPERED`; masuk tercatat 16:10 (jam nyata, `time_trusted`), jam HP +3 jam diabaikan; kirim ulang → duplikat (200, tidak membuat baris baru); pulang 16:11 | Pass |

Jam emulator sengaja tidak diubah (pernah membuat emulator macet); M8 memakai skrip yang menandatangani payload
sama persis seperti aplikasi.

## 4. Catatan & rekomendasi

| # | Temuan | Tingkat | Tindak lanjut |
|---|---|---|---|
| T-1 | Tidak ada bug pada alur absensi di build produksi | — | Tidak ada perbaikan kode |
| T-2 | GPS emulator berhenti mengirim posisi setelah dipakai lama (`adb emu geo fix` menjawab OK, tetapi lokasi tidak berubah); tombol absen berputar menunggu GPS | Lingkungan uji, bukan aplikasi | Cold boot emulator (`-no-snapshot-load`) memulihkannya. Saran kecil: batas 30 detik pada `getCurrentPosition` tidak terasa di emulator karena permintaan lewat layanan lokasi Google — perlu dicek di HP nyata apakah pesan "Gagal mendapatkan lokasi" muncul |
| T-3 | Kartu "Absen hari ini" menampilkan sesi valid kemarin yang lupa diabsen pulang | — | Sesuai O-10 (sesi valid terbuka harus ditutup dulu); bukan bug |
| T-4 | Swafoto absen **online** tetap disimpan di folder aplikasi `Visiontech/Swafoto Absensi`; yang luring dihapus setelah terkirim | — | Sesuai R-16 (folder khusus aplikasi, terhapus bersama aplikasi) |

## 5. Uji di server produksi

Belum dijalankan. Lihat rencana di bagian bawah laporan ini setelah dijalankan (akun UJI di server dibuat pemilik
lewat `.local_tests/buat-akun-uji.bat`; login di server dilakukan pemilik sendiri).
