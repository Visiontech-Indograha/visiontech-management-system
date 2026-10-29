import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/features/mess/mess_screen.dart';

Map<String, dynamic> _stay(String status, String start, String end) => {
  'status': status,
  'stay_start_date': start,
  'stay_end_date': end,
};

void main() {
  final today = DateTime(2026, 10, 27);

  test('label status mess berbahasa Indonesia', () {
    expect(messStatusLabel('REQUESTED'), 'Menunggu persetujuan');
    expect(messStatusLabel('REJECTED'), 'Ditolak');
  });

  test('aksi hunian: pengajuan & hunian mendatang bisa dibatalkan, yang berjalan bisa diselesaikan', () {
    expect(messStayAction(_stay('REQUESTED', '2026-11-01', '2026-11-05'), today), 'cancel');
    expect(messStayAction(_stay('APPROVED', '2026-11-01', '2026-11-05'), today), 'cancel');
    expect(messStayAction(_stay('APPROVED', '2026-10-25', '2026-10-30'), today), 'end');
    expect(messStayAction(_stay('APPROVED', '2026-10-01', '2026-10-05'), today), isNull);
    expect(messStayAction(_stay('REJECTED', '2026-11-01', '2026-11-05'), today), isNull);
  });

  test('"Ajukan lagi" menemukan mess lewat kunci mess_id dari API (bukan id)', () {
    final places = [{'mess_id': 'abd0', 'mess_name': 'Mess Uji Pekanbaru'}, {'mess_id': '1c75', 'mess_name': 'Mes Tebing'}];
    expect(findMessPlace(places, 'abd0')?['mess_name'], 'Mess Uji Pekanbaru');
    expect(findMessPlace(places, 'tidak-ada'), isNull);
    expect(findMessPlace(places, null), isNull);
  });
}
