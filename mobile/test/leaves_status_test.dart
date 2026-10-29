import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/features/leaves/leaves_screen.dart';

void main() {
  test('label status cuti', () {
    expect(leaveStatusLabel('PENDING'), 'Menunggu PM');
    expect(leaveStatusLabel('APPROVED_BY_HR'), 'Disetujui');
    expect(leaveStatusLabel('CANCELLED'), 'Dibatalkan');
  });

  test('PENDING, APPROVED_BY_PM, dan APPROVED_BY_HR bisa dibatalkan', () {
    expect(leaveCancellable('PENDING'), isTrue);
    expect(leaveCancellable('APPROVED_BY_PM'), isTrue);
    expect(leaveCancellable('APPROVED_BY_HR'), isTrue);
    expect(leaveCancellable('REJECTED'), isFalse);
  });
}
