import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/core/attendance_reminders.dart';

void main() {
  // 2026-10-26 07:00 WIB = 00:00 UTC.
  DateTime wib(int h, int m) => DateTime.utc(2026, 10, 26, h - 7, m);

  test('absen masuk: pengingat tiap 5 menit 07:30–08:00 WIB (7 slot)', () {
    final slots = checkInSlots('2026-10-26', wib(6, 50));
    expect(slots.length, 7);
    expect(slots.first, wib(7, 30));
    expect(slots.last, wib(8, 0));
    expect(slots[1].difference(slots[0]), const Duration(minutes: 5));
  });

  test('absen masuk: slot yang sudah lewat tidak dijadwalkan', () {
    final slots = checkInSlots('2026-10-26', wib(7, 42));
    expect(slots.first, wib(7, 45));
    expect(slots.length, 4);
    expect(checkInSlots('2026-10-26', wib(8, 1)), isEmpty);
  });

  test('absen pulang: masuk 07:00 → pengingat 16:00 sampai 17:00 (13 slot)', () {
    final slots = checkOutSlots(wib(16, 0), wib(15, 0));
    expect(slots.length, 13);
    expect(slots.first, wib(16, 0));
    expect(slots.last, wib(17, 0));
  });

  test('absen pulang terlambat: jam wajib 17:00 → sampai 18:00', () {
    final slots = checkOutSlots(wib(17, 0), wib(16, 59));
    expect(slots.first, wib(17, 0));
    expect(slots.last, wib(18, 0));
  });
}
