/// Logika murni inspeksi kendaraan (batas sama dengan skema API VehicleInspectionCreate).
const inspeksiMaxFoto = 10;
const inspeksiMaxCatatan = 1000;
const inspeksiMaxOdometer = 10000000;

String inspeksiStatusLabel(String status) => switch (status) {
  'SUBMITTED' => 'Menunggu pemeriksaan',
  'VERIFIED' => 'Sudah diperiksa HSE',
  'REJECTED' => 'Ditolak HSE',
  _ => status,
};

String inspeksiPeriodeLabel(String p) => switch (p) {
  'DAILY' => 'Harian',
  'WEEKLY' => 'Mingguan',
  'MONTHLY' => 'Bulanan',
  _ => p,
};

String inspeksiHasilLabel(String v) => switch (v) {
  'BAIK' => 'Baik',
  'PERLU_PERBAIKAN' => 'Perlu perbaikan',
  'RUSAK' => 'Rusak',
  _ => v,
};

/// Isi permintaan kirim. Butir yang belum dijawab dibuang.
Map<String, dynamic> buildInspeksiBody({
  required String vehicleId,
  required String periodType,
  required Map<String, String> checklist,
  required List<String> photoIds,
  String? notes,
  int? odometerKm,
}) {
  final catatan = notes?.trim() ?? '';
  return {
    'vehicle_id': vehicleId,
    'period_type': periodType,
    'checklist_json': {...checklist},
    'photos_json': photoIds.take(inspeksiMaxFoto).toList(),
    if (catatan.isNotEmpty)
      'notes': catatan.length > inspeksiMaxCatatan
          ? catatan.substring(0, inspeksiMaxCatatan)
          : catatan,
    'odometer_km': ?odometerKm,
  };
}

/// Pesan bila form belum layak kirim, null bila siap.
String? inspeksiBelumSiap({
  required String? vehicleId,
  required int jumlahButir,
  required int terjawab,
}) {
  if (vehicleId == null) return 'Pilih kendaraan dulu.';
  if (terjawab < jumlahButir) {
    return 'Masih ada ${jumlahButir - terjawab} butir yang belum diisi.';
  }
  return null;
}
