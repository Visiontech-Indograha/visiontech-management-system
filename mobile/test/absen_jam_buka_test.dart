import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/features/attendance/attendance_screen.dart';

void main() {
  test('gerbang 06:45 hanya dilewati bila build dev DAN flag skip aktif', () {
    expect(attendanceHoursSkipped(devBuild: true, skipFlag: true), isTrue);
    expect(attendanceHoursSkipped(devBuild: true), isFalse);
    // Build non-dev: flag diabaikan.
    expect(attendanceHoursSkipped(skipFlag: true), isFalse);
    expect(attendanceHoursSkipped(), isFalse);
  });

  testWidgets('pesan jam buka tampil sebagai dialog dan tetap ada setelah 2 detik', (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: Builder(
        builder: (context) => Scaffold(
          body: TextButton(
            onPressed: () => tampilkanJamBukaAbsen(context),
            child: const Text('buka'),
          ),
        ),
      ),
    ));
    await tester.tap(find.text('buka'));
    await tester.pump();
    await tester.pump(const Duration(seconds: 2));

    expect(find.byType(AlertDialog), findsOneWidget);
    expect(find.text('Absensi masuk baru dibuka mulai pukul 06:45 WIB.'), findsOneWidget);

    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();
    expect(find.byType(AlertDialog), findsNothing);
  });
}
