import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/features/plans/daily_plan_screen.dart';

void main() {
  test('koreksi terbuka dicari dari riwayat, yang selesai diabaikan', () {
    expect(openCorrectionOf(const []), isNull);
    expect(
      openCorrectionOf([
        {'status': 'ACCEPTED'},
        {'status': 'REJECTED'},
      ]),
      isNull,
    );
    final open = {'status': 'REVISING', 'review_note': 'Lampirkan foto'};
    expect(
      openCorrectionOf([
        {'status': 'ACCEPTED'},
        open,
      ]),
      open,
    );
  });

  test('judul dan keterangan status koreksi', () {
    expect(correctionStateTitle('REQUESTED'), 'Koreksi menunggu keputusan atasan');
    expect(correctionStateTitle('REVISING'), 'Atasan meminta revisi laporan');
    expect(correctionStateTitle('IN_REVIEW'), 'Revisi menunggu pemeriksaan atasan');
    expect(
      correctionStateSubtitle({'status': 'REVISING', 'review_note': 'Lampirkan foto'}),
      'Catatan atasan: Lampirkan foto',
    );
    expect(
      correctionStateSubtitle({'status': 'REVISING', 'review_note': null}),
      'Perbarui laporan dan hasil kerja, lalu kirim revisi',
    );
    expect(
      correctionStateSubtitle({'status': 'REQUESTED', 'reason': 'Jumlah salah'}),
      'Alasan: Jumlah salah',
    );
  });
}
