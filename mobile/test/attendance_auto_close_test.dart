import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/features/attendance/session_labels.dart';

void main() {
  test('sesi yang ditutup otomatis dikenali dari keterangan sistem', () {
    expect(isAutoClosedSession({'explanation': 'Lupa absen pulang (ditutup otomatis oleh sistem pada pukul 19:00)'}), isTrue);
  });
  test('sesi biasa atau dengan penjelasan karyawan tidak dianggap otomatis', () {
    expect(isAutoClosedSession({'explanation': null}), isFalse);
    expect(isAutoClosedSession({'explanation': 'GPS melenceng'}), isFalse);
    expect(isAutoClosedSession({}), isFalse);
  });
}
