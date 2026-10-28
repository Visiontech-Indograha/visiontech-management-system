import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/features/plans/overtime_hours.dart';

void main() {
  // 2026-10-28 20:30 WIB = 13:30 UTC
  final now = DateTime.utc(2026, 10, 28, 13, 30);

  test('selisih dari jam pulang dibulatkan ke 0,5 jam', () {
    expect(suggestedOvertimeHours(workDate: '2026-10-28', clockOutTime: '16:00:00', nowUtc: now), 4.5);
    expect(suggestedOvertimeHours(workDate: '2026-10-28', clockOutTime: '19:50:00', nowUtc: now), 0.5);
  });

  test('null bila bukan hari ini, belum lewat jam pulang, atau < 30 menit', () {
    expect(suggestedOvertimeHours(workDate: '2026-10-27', clockOutTime: '16:00:00', nowUtc: now), isNull);
    expect(suggestedOvertimeHours(workDate: '2026-10-28', clockOutTime: '21:00:00', nowUtc: now), isNull);
    expect(suggestedOvertimeHours(workDate: '2026-10-28', clockOutTime: '20:10:00', nowUtc: now), isNull);
  });

  test('dibatasi maks 12 jam dan tahan format rusak', () {
    expect(suggestedOvertimeHours(workDate: '2026-10-28', clockOutTime: '00:00:00', nowUtc: now), 12);
    expect(suggestedOvertimeHours(workDate: '2026-10-28', clockOutTime: 'xx', nowUtc: now), isNull);
  });
}
