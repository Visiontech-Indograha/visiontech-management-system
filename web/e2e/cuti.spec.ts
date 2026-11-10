import { test } from "./fixtures";

// Alur UI yang sudah dikenal: Cuti dan Izin > Ajukan cuti / izin > Kirim Pengajuan; pemeriksa memilih
// Tinjau Permohonan > Setujui Permohonan (dua tahap: atasan lalu HR); Batalkan cuti (hanya bila sudah disetujui).
test.fixme(
  "ajukan cuti, ditinjau orang lain, lalu dibatalkan, semuanya lewat UI",
  async () => {
    // jalur UI belum ada: (1) akun kedua dengan peran kantor yang berhak meninjau cuti (pemohon tidak boleh
    // menyetujui cuti sendiri; peran kantor tidak bisa diberikan dari UI tanpa flag server ROLE_ASSIGNMENT_ENABLED);
    // (2) menghapus/membatalkan pengajuan yang masih menunggu (tombol Batalkan hanya muncul setelah disetujui),
    // sehingga pengajuan uji tidak bisa dibersihkan lewat UI. Layar: Direktori > Akun login, dan Cuti dan Izin.
    // Peran yang berhak: SUPER_ADMIN.
  },
);
