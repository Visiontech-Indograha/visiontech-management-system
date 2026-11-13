import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/core/error_message.dart';
import 'package:vms_mobile/features/auth/auth_state.dart';
import 'package:vms_mobile/features/leaves/leave_backdate.dart';

import 'support/fake_backend.dart';

void main() {
  // 10 Nov 2026 18:00 UTC = 11 Nov 2026 01:00 WIB (hari Jakarta sudah ganti).
  final now = DateTime.utc(2026, 11, 10, 18);

  test('hari ini memakai zona Jakarta', () {
    expect(jakartaToday(now), DateTime(2026, 11, 11));
  });

  test('karyawan biasa: paling awal hari ini dikurangi 3', () {
    for (final r in [UserRole.member, UserRole.leader, UserRole.pm]) {
      expect(leaveEarliestStart(r, now), DateTime(2026, 11, 8), reason: '$r');
    }
  });

  test('HR, OM, Super Admin tidak dibatasi 3 hari', () {
    for (final r in [UserRole.hr, UserRole.ops, UserRole.superAdmin]) {
      expect(leaveBackdateExempt(r), isTrue);
      expect(leaveEarliestStart(r, now).isBefore(DateTime(2026, 11, 8)), isTrue);
    }
    expect(leaveBackdateExempt(UserRole.member), isFalse);
  });

  test('jam suntikan dipakai bila tanpa argumen', () {
    final lama = leaveClock;
    addTearDown(() => leaveClock = lama);
    leaveClock = () => now;
    expect(leaveEarliestStart(UserRole.member), DateTime(2026, 11, 8));
  });

  test('pesan sama persis dengan API', () {
    expect(
      leaveBackdateMessage,
      'Tanggal mulai cuti paling lambat 3 hari ke belakang. Hubungi HR untuk cuti yang lebih lama.',
    );
  });

  test('422 dari API tampil dalam bahasa awam', () {
    final e = httpError(RequestOptions(path: '/leaves'), 422, {
      'error': {'code': 'VALIDATION_ERROR', 'message': leaveBackdateMessage},
    });
    expect(apiErrorMessage(e), contains('paling lambat 3 hari ke belakang'));
  });
}
