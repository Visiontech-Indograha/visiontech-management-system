import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/features/auth/auth_state.dart';

AuthUser user(String role, String mode) => AuthUser.fromJson({
  'user_id': 'u1',
  'email': 'a@visiontech.id',
  'role': role,
  'employee_id': 'e1',
  'attendance_mode': mode,
});

void main() {
  test('pekerja kantor diarahkan absen lewat web, lapangan lewat HP', () {
    expect(user('PM', 'OFFICE').absensiLewatWeb, isTrue);
    expect(user('MEMBER', 'FIELD').absensiLewatWeb, isFalse);
  });

  test('administrator boleh absen dari HP walau jenis absennya kantor', () {
    expect(user('ADMIN', 'OFFICE').absensiLewatWeb, isFalse);
  });
}
