/// Status tampilan item pekerjaan. Foto atau jumlah > 0 (belum lengkap) berarti "Sedang dikerjakan";
/// jumlah target tercapai berarti selesai. Status pindah hari tetap ditampilkan apa adanya.
/// Di hari yang sudah COMPLETED (ditutup), item yang belum selesai berlabel "Belum selesai", bukan "Sedang dikerjakan".
String itemDisplayState({
  required String raw,
  required num done,
  required num target,
  required int photoCount,
  String? dayStatus,
}) {
  if (raw == 'CANCELLED' || raw == 'CANCELED') return 'CANCELLED';
  if (raw == 'DONE' || (target > 0 && done >= target)) return 'DONE';
  if (raw == 'SHIFTED_DAY' || raw == 'PENDING_ROLLOVER') return raw;
  if (done > 0 || photoCount > 0) {
    return dayStatus == 'COMPLETED' ? 'ITEM_PARTIAL' : 'ITEM_IN_PROGRESS';
  }
  return raw;
}

/// Alasan tombol "Kirim laporan untuk menutup hari" nonaktif yang belum dijelaskan di layar, atau null.
String? closeDayBlockReason({
  required bool hasReport,
  required bool reportPending,
  required int pendingRollovers,
  int unfinishedItems = 0,
}) {
  // Pindah hari yang menunggu PM sudah dijelaskan spanduk di atas tombol; tidak diulang di sini.
  if (pendingRollovers > 0) return null;
  if (unfinishedItems > 0) {
    return 'Masih ada pekerjaan belum selesai. Selesaikan atau ajukan pindah hari dulu, atau minta PM menutup hari kerja.';
  }
  if (!hasReport) return 'Kirim laporan harian di atas dulu. Setelah terkirim, hari kerja bisa ditutup.';
  if (reportPending) return 'Menunggu koneksi untuk mengirim laporan.';
  return null;
}
