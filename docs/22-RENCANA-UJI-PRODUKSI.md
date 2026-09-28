# 22 · Rencana Uji Nyata di Produksi (UAT seminggu)

Permintaan pemilik 2026-09-28 (R-21): memastikan **mode luring + sinkron otomatis** berjalan, lalu
menguji **semua alur SK/work plan, semua kejadian, semua peran, dan absensi** secara nyata di server
produksi (`https://visiontech-bar.tail827174.ts.net`, HP wajib tersambung Tailscale).

> Aturan: data uji dibuat di organisasi asli **dengan awalan `UJI-`** pada judul SK/insiden supaya
> mudah disaring & dibersihkan. Backup sebelum mulai: `~/deploy/vms-mvp/backup.sh pra-uat`.
> Setiap temuan dicatat di tabel **Temuan** di bawah (bukan di chat) lalu dimasukkan ke docs/19.

## 0. Yang sudah dipastikan otomatis (sebelum uji manual)

| Hal | Bukti |
|---|---|
| Antrean luring: simpan → kirim ulang tanpa ganda (idempoten `client_op_id`) | `mobile/test/sync_engine_test.dart`, `sync_queue_test.dart` (33 uji) — hijau 2026-09-28 |
| Sinkron otomatis: (a) sinyal pulih, (b) aplikasi kembali dibuka, (c) coba ulang tiap 60 dtk bila antrean berisi, (d) saat aplikasi mulai | `mobile/lib/core/connectivity_sync.dart` |
| Operasi yang **boleh** luring: simpan/kirim laporan harian, centang tugas, lapor insiden, lapor lembur | `OfflineOp` (A-08) |
| Operasi yang **wajib** daring: absen masuk/pulang, terbit/terima SK, persetujuan | A-08 — di HP tampil pesan jelas, tidak diantrekan |
| Kunci login 5× gagal / 15 menit + hitung mundur | `test_auth_flow.py`, `role_and_lock_test.dart`, `auth.test.tsx` |

## 1. Akun & peran yang dipakai

Pakai akun asli (daftar di `.local_tests/server-logins.txt`, jangan dibagikan di chat). Minimal satu orang per peran:

| Peran | Tempat kerja | Yang diuji |
|---|---|---|
| ADMIN (`ageng@visiontech.id`) | Web | Audit, sesi, akun |
| HR | Web | Karyawan baru, akun, offboarding, dokumen pribadi, verifikasi |
| PM | Web (HP: absen + kartu "Segera hadir") | Buat/terbit SK, adendum, persetujuan selesai |
| OPS / FINANCE / ASSET | Web | Review absensi unit, lembur, aset & serah terima |
| LEADER (ketua di SK) | HP + Web | Rencana harian, review laporan anggota |
| MEMBER (anggota di SK) | HP | Terima SK, absen, laporan, insiden, lembur |

## 2. Skenario

Tandai ✅ / ❌ + tanggal + penguji. Kolom **Luring** = ulangi langkah itu dalam mode pesawat.

### A. Login & akun
| # | Langkah | Hasil yang diharapkan | Luring |
|---|---|---|---|
| A1 | Login benar di HP & web | Masuk; peran tampil di Profil | — |
| A2 | Salah sandi 1–4× | Pesan "Sisa N percobaan" | — |
| A3 | Salah sandi ke-5 | "Login dikunci sementara", tombol mati, hitung mundur 15:00; HR melihat badge **Terkunci** di Direktori | — |
| A4 | PM/HR login di HP | Kartu "Menu Project Manager — Segera hadir" / "Akun kantor", tetap bisa absen | — |
| A5 | HR buat akun, reset sandi, nonaktifkan | Sandi sementara tampil sekali; akun nonaktif langsung keluar dari HP | — |

### B. Siklus SK / work plan (PM → anggota → ketua → PM)
| # | Langkah | Hasil | Luring |
|---|---|---|---|
| B1 | PM buat SK `UJI-…`, isi hari, tugas, anggota, titik lokasi (peta) | Draf tersimpan, tidak terlihat di HP anggota | — |
| B2 | PM terbitkan | PDF SK ber-QR terbit; anggota melihat SK di HP | — |
| B3 | Anggota **terima**; satu anggota lain **banding** | Status berubah; PM melihat banding | — |
| B4 | PM revisi → terbit ulang | Versi lama terkunci, versi baru terbit (aturan 2) | — |
| B5 | PM mulai SK | Status Berjalan; absensi dibuka | — |
| B6 | Adendum ganti ketua (changes → approve → accept) | Ketua baru langsung punya hak ketua, ketua lama hanya anggota (aturan 1) | — |
| B7 | Anggota centang tugas & isi laporan harian + foto, lalu kirim | Masuk ke ketua | **Ya** — simpan di mode pesawat, nyalakan data → terkirim sendiri tanpa ganda |
| B8 | Ketua review laporan harian (terima / kembalikan) | Anggota melihat status | — |
| B9 | Laporan mingguan: isi → kirim → review | Tersimpan & bisa diunduh | — |
| B10 | Ketua ajukan selesai → PM kembalikan → ajukan lagi → PM setujui | Laporan akhir PDF bertanda tangan | — |
| B11 | Batalkan SK lain `UJI-…`; arsipkan & pulihkan | Status & audit tercatat | — |

### C. Absensi
| # | Langkah | Hasil | Luring |
|---|---|---|---|
| C1 | Absen masuk di dalam radius + swafoto | Diterima; jam = jam server | Harus **ditolak dengan pesan jelas** (wajib daring) |
| C2 | Absen masuk di luar radius | Butuh penjelasan → masuk antrean review | — |
| C3 | Jam HP diubah manual lalu absen | Jam tercatat tetap jam server (aturan 3) | — |
| C4 | Absen pulang; absen masuk malam lalu pulang lewat tengah malam | Tombol pulang tetap ada (O-10) | — |
| C5 | OPS/ketua review absensi bermasalah | Status berubah, anggota melihat | — |
| C6 | Tidak absen seharian | Peringatan absen hilang (cron) muncul | — |

### D. Kejadian (insiden K3, lembur, aset, dokumen)
| # | Langkah | Hasil | Luring |
|---|---|---|---|
| D1 | Anggota lapor insiden K3 + foto | Masuk daftar insiden web | **Ya** |
| D2 | Pihak berwenang menyelesaikan insiden | Status selesai + audit | — |
| D3 | Anggota lapor lembur | Masuk antrean FINANCE/ketua | **Ya** |
| D4 | Review lembur (setujui/tolak) | Anggota melihat hasil | — |
| D5 | ASSET: reservasi aset ke SK → cek → kembalikan → verifikasi | Riwayat aset lengkap | — |
| D6 | Karyawan unggah dokumen pribadi → HR verifikasi (bukan pengunggah) | Aturan empat mata berlaku | — |
| D7 | Unduh PDF (SK, BAST, laporan akhir) & pindai QR | QR membuka halaman verifikasi | — |

### E. Luring & sinkron — uji khusus di HP
| # | Langkah | Hasil |
|---|---|---|
| E1 | Mode pesawat → buka aplikasi | Masuk dengan profil tersimpan; banner "Luring" + jam data terakhir |
| E2 | Luring: 2 laporan harian + 1 insiden + 1 lembur | Antrean menunjukkan 4 operasi |
| E3 | Nyalakan data, **jangan sentuh apa pun** | Dalam ≤ 60 dtk antrean kosong; data muncul di web **sekali** (tidak ganda) |
| E4 | Kirim saat sinyal putus di tengah unggah foto | Operasi tetap di antrean, terkirim ulang otomatis |
| E5 | Tutup paksa aplikasi saat antrean berisi, buka lagi saat daring | Antrean terkirim saat aplikasi mulai |
| E6 | Operasi ditolak server (mis. SK sudah selesai) | Tampil di layar Antrean dengan alasan, bisa dihapus/diulang |
| E7 | Logout lalu login akun lain di HP yang sama | Antrean akun lama terhapus, tidak terkirim atas nama akun baru |

## 3. Pemantauan selama uji

- Discord `#vms-alerts` (kegagalan login beruntun, galat server) & `#vms-deploy`.
- Backup harian 01.30 → MinIO `vms-backups` (cek ada berkas baru tiap hari).
- Jam server sinkron (NTP) — dasar semua waktu absensi.

## 4. Temuan

| Tgl | Skenario | Peran/HP | Yang terjadi | Status |
|---|---|---|---|---|
| | | | | |

## 5. Selesai uji

1. Semua skenario ✅ atau temuan tercatat dengan keputusan.
2. Data `UJI-…` dibersihkan (backup lebih dulu).
3. Rekap ke pemilik → docs/19.
