import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:vms_mobile/core/providers.dart';
import 'package:vms_mobile/data/sync_engine.dart';
import 'package:vms_mobile/data/vms_api.dart';
import 'package:vms_mobile/features/leaves/leaves_screen.dart';

/// T-7: label cuti harus ikut berubah setelah PM menyetujui di web (muat ulang saat aplikasi aktif lagi,
/// saat peristiwa waktu nyata masuk, dan lewat tarik-untuk-segarkan).
class _FakeApi implements VmsApi {
  String status = 'PENDING';
  int leaveCalls = 0;

  @override
  Future<List<Map<String, dynamic>>> myLeaves(String employeeId) async {
    leaveCalls++;
    return [
      {
        'leave_id': 'l1',
        'start_date': '2030-01-07',
        'end_date': '2030-01-07',
        'total_days': 1,
        'status': status,
      },
    ];
  }

  @override
  Future<Map<String, dynamic>> leaveBalance(String employeeId) async => {
        'annual_quota': 12,
        'used_days': 0,
        'remaining_days': 12,
      };

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeSync implements SyncEngine {
  _FakeSync(this._fake);
  final _FakeApi _fake;

  @override
  VmsApi get api => _fake;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

Future<ProviderContainer> _pump(WidgetTester tester, _FakeApi fake) async {
  final container = ProviderContainer(overrides: [
    syncEngineProvider.overrideWithValue(_FakeSync(fake)),
  ]);
  addTearDown(container.dispose);
  await tester.pumpWidget(UncontrolledProviderScope(
    container: container,
    child: const MaterialApp(home: LeavesScreen()),
  ));
  await tester.pumpAndSettle();
  return container;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() => initializeDateFormatting('id_ID'));

  testWidgets('label berubah setelah aplikasi kembali aktif (resumed)', (tester) async {
    final fake = _FakeApi();
    await _pump(tester, fake);
    expect(find.text('Menunggu PM'), findsOneWidget);

    fake.status = 'APPROVED_BY_PM';
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pumpAndSettle();

    expect(find.text('Menunggu PM'), findsNothing);
    expect(find.text('Disetujui PM, menunggu HR'), findsOneWidget);
  });

  testWidgets('label berubah saat peristiwa waktu nyata masuk', (tester) async {
    final fake = _FakeApi();
    final container = await _pump(tester, fake);

    fake.status = 'APPROVED_BY_PM';
    container.read(liveEventTickProvider.notifier).bump();
    await tester.pumpAndSettle();

    expect(find.text('Menunggu PM'), findsNothing);
    expect(find.text('Disetujui PM, menunggu HR'), findsOneWidget);
  });

  testWidgets('tarik untuk segarkan memuat ulang daftar', (tester) async {
    final fake = _FakeApi();
    await _pump(tester, fake);
    fake.status = 'APPROVED_BY_PM';
    await tester.drag(find.byType(ListView), const Offset(0, 300));
    await tester.pumpAndSettle();

    expect(find.text('Menunggu PM'), findsNothing);
  });

  testWidgets('layar cuti ketua/anggota tidak menampilkan tombol persetujuan', (tester) async {
    await _pump(tester, _FakeApi());
    expect(find.textContaining('Tinjau'), findsNothing);
    expect(find.textContaining('Setujui'), findsNothing);
    expect(find.textContaining('Tolak'), findsNothing);
  });
}
