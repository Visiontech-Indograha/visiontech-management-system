import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/features/auth/auth_state.dart';
import 'package:vms_mobile/features/auth/change_password_screen.dart';

void main() {
  test('validasi sandi baru sama dengan API', () {
    expect(validateNewPassword('lama1234', 'abc12'), isNotNull);
    expect(validateNewPassword('lama1234', 'abcdefgh'), isNotNull);
    expect(validateNewPassword('lama1234', '12345678'), isNotNull);
    expect(validateNewPassword('abc12345', 'abc12345'), isNotNull);
    expect(validateNewPassword('lama1234', 'baru1234'), isNull);
  });

  test('AuthUser membaca must_change_password (default false)', () {
    expect(AuthUser.fromJson({'user_id': 'u'}).mustChangePassword, isFalse);
    final u = AuthUser.fromJson({'user_id': 'u', 'must_change_password': true});
    expect(u.mustChangePassword, isTrue);
    expect(u.withMustChange(false).mustChangePassword, isFalse);
  });
}
