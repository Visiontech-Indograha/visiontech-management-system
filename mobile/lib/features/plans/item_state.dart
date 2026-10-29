/// Status tampilan item pekerjaan. Foto atau jumlah > 0 (belum lengkap) berarti "Sedang dikerjakan";
/// jumlah target tercapai berarti selesai. Status pindah hari tetap ditampilkan apa adanya.
String itemDisplayState({
  required String raw,
  required num done,
  required num target,
  required int photoCount,
}) {
  if (raw == 'DONE' || (target > 0 && done >= target)) return 'DONE';
  if (raw == 'SHIFTED_DAY' || raw == 'PENDING_ROLLOVER') return raw;
  if (done > 0 || photoCount > 0) return 'ITEM_IN_PROGRESS';
  return raw;
}

/// Alasan tombol "Kirim laporan untuk menutup hari" nonaktif, atau null bila tombol bisa dipakai.
String? closeDayBlockReason({
  required bool hasReport,
  required bool reportPending,
  required int pendingRollovers,
}) {
  if (pendingRollovers > 0) {
    return '$pendingRollovers pekerjaan menunggu keputusan PM untuk pindah hari. Hari kerja belum bisa ditutup.';
  }
  if (!hasReport) return 'Kirim laporan harian di atas dulu. Setelah terkirim, hari kerja bisa ditutup.';
  if (reportPending) return 'Menunggu koneksi untuk mengirim laporan.';
  return null;
}
