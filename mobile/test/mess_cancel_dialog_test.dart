import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:vms_mobile/core/providers.dart';
import 'package:vms_mobile/features/mess/mess_screen.dart';

import 'support/fake_backend.dart';

Map<String, dynamic> _stay(String status) => {
  'mess_stay_id': 's1',
  'mess_id': 'm1',
  'mess_name': 'Mess Melati',
  'city': 'Pekanbaru',
  'address': 'Jl. Contoh',
  'status': status,
  'stay_start_date': '2099-01-01',
  'stay_end_date': '2099-01-05',
};

Future<void> _pump(WidgetTester tester, String status) async {
  final db = memoryDb();
  addTearDown(db.close);
  final backend = FakeBackend();
  backend.routes['/mess/me'] = (_) => [_stay(status)];
  final container = ProviderContainer(
    overrides: [syncEngineProvider.overrideWithValue(engineWith(db, backend))],
  );
  addTearDown(container.dispose);
  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: const MaterialApp(home: MessScreen()),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() => initializeDateFormatting('id_ID'));

  testWidgets('hunian Disetujui: dialog berjudul Batalkan hunian', (tester) async {
    await _pump(tester, 'APPROVED');
    await tester.tap(find.text('Batalkan hunian'));
    await tester.pumpAndSettle();
    expect(find.text('Batalkan hunian?'), findsOneWidget);
    expect(find.text('Batalkan pengajuan?'), findsNothing);
    expect(find.text('Ya, batalkan hunian'), findsOneWidget);
    expect(find.text('Tidak jadi'), findsOneWidget);
  });

  testWidgets('pengajuan Menunggu: dialog berjudul Batalkan pengajuan', (tester) async {
    await _pump(tester, 'REQUESTED');
    await tester.tap(find.text('Batalkan pengajuan'));
    await tester.pumpAndSettle();
    expect(find.text('Batalkan pengajuan?'), findsOneWidget);
    expect(find.text('Batalkan hunian?'), findsNothing);
    expect(find.text('Ya, batalkan pengajuan'), findsOneWidget);
  });
}
