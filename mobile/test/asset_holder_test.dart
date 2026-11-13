import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/features/assets/asset_holder.dart';

void main() {
  test('karyawan biasa', () {
    final r = <String, dynamic>{'employee_id': 'e1', 'employee_name': 'Sari'};
    expect(assetHolderLabel(r), 'Sari');
    expect(isExternalHolder(r), isFalse);
  });
  test('penerima eksternal: employee_id null', () {
    final r = <String, dynamic>{'employee_id': null, 'employee_name': ' Budi '};
    expect(isExternalHolder(r), isTrue);
    expect(assetHolderLabel(r), 'Budi (penerima luar)');
  });
  test('nama dan id null tidak crash', () {
    final r = <String, dynamic>{'employee_id': null, 'employee_name': null};
    expect(assetHolderLabel(r), 'Penerima tanpa nama (penerima luar)');
    expect(assetHolderName(<String, dynamic>{}), 'Penerima tanpa nama');
  });
}
