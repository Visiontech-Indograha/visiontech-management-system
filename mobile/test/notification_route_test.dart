import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/features/notifications/notifications_screen.dart';

void main() {
  test('jenis notifikasi dipetakan ke layar tujuan', () {
    expect(notificationRoute('leave'), '/leaves');
    expect(notificationRoute('asset'), '/assets');
    expect(notificationRoute('overtime'), '/overtime');
    expect(notificationRoute('plan'), isNull);
    expect(notificationRoute(null), isNull);
  });
}
