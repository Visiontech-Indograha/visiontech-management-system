import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/features/auth/auth_state.dart';
import 'package:vms_mobile/features/records/my_records_screens.dart';

void main() {
  test('nama jenis dokumen ramah dibaca', () {
    expect(documentTypeLabel('SERTIFIKAT_K3'), 'Sertifikat K3');
    expect(documentTypeLabel('SIM_B1'), 'SIM B I');
    expect(documentTypeLabel('SURAT_TUGAS'), 'SURAT TUGAS');
  });

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

  test('nama tampilan memakai nama lengkap, cadangannya bagian depan email', () {
    final withName = AuthUser.fromJson({'email': 'a@b.id', 'full_name': 'Uji Ketua 1.1'});
    expect(withName.displayName, 'Uji Ketua 1.1');
    expect(AuthUser.fromJson({'email': 'ketua11@uji.test'}).displayName, 'ketua11');
  });
}
