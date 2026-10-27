import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/features/records/my_records_screens.dart';

void main() {
  test('label status lembur dan dokumen', () {
    expect(overtimeStatusLabel('PENDING'), 'Menunggu persetujuan');
    expect(overtimeStatusLabel('APPROVED'), 'Disetujui');
    expect(overtimeStatusLabel('REJECTED'), 'Ditolak');
    expect(documentStatusLabel('active'), 'Berlaku');
    expect(documentStatusLabel('expired'), 'Kedaluwarsa');
  });

  test('dokumen segera habis dalam 30 hari', () {
    final today = DateTime(2026, 10, 27);
    expect(documentExpiresSoon({'status': 'active', 'expired_at': '2026-11-20'}, today), isTrue);
    expect(documentExpiresSoon({'status': 'active', 'expired_at': '2027-03-01'}, today), isFalse);
    expect(documentExpiresSoon({'status': 'active', 'expired_at': '2026-10-01'}, today), isTrue);
    expect(documentExpiresSoon({'status': 'extended', 'expired_at': '2026-10-30'}, today), isFalse);
    expect(documentExpiresSoon({'status': 'active', 'expired_at': null}, today), isFalse);
  });
}
