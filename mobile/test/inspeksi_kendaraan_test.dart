import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/features/hse/inspeksi_kendaraan.dart';

void main() {
  test('isi kirim sesuai batas API', () {
    final b = buildInspeksiBody(
      vehicleId: 'v1',
      periodType: 'DAILY',
      checklist: {'rem': 'BAIK'},
      photoIds: List.generate(12, (i) => 'f$i'),
      notes: '  ${'a' * 1200} ',
      odometerKm: 500,
    );
    expect((b['photos_json'] as List).length, 10);
    expect((b['notes'] as String).length, 1000);
    expect(b['odometer_km'], 500);
    final kosong = buildInspeksiBody(
      vehicleId: 'v',
      periodType: 'DAILY',
      checklist: {},
      photoIds: [],
      notes: ' ',
    );
    expect(kosong.containsKey('notes'), false);
  });

  test('pesan belum siap dan label awam', () {
    expect(inspeksiBelumSiap(vehicleId: null, jumlahButir: 3, terjawab: 0), 'Pilih kendaraan dulu.');
    expect(inspeksiBelumSiap(vehicleId: 'v', jumlahButir: 3, terjawab: 1), 'Masih ada 2 butir yang belum diisi.');
    expect(inspeksiBelumSiap(vehicleId: 'v', jumlahButir: 3, terjawab: 3), isNull);
    expect(inspeksiHasilLabel('PERLU_PERBAIKAN'), 'Perlu perbaikan');
    expect(inspeksiStatusLabel('VERIFIED'), 'Sudah diperiksa HSE');
  });
}
