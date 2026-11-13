import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:vms_mobile/core/providers.dart';
import 'package:vms_mobile/features/leaves/leaves_screen.dart';

import 'support/fake_backend.dart';

/// Batal pengajuan cuti memakai API sungguhan (VmsApi + Dio tiruan): POST /leaves/{id}/cancel,
/// galat 4xx tampil, dan daftar menyegarkan.
Map<String, dynamic> _leave(String status) => {
  'leave_id': 'l1',
  'start_date': '2030-01-07',
  'end_date': '2030-01-07',
  'total_days': 1,
  'status': status,
  'leave_type': 'ANNUAL',
};

Future<FakeBackend> _pump(WidgetTester tester, FakeBackend backend) async {
  final db = memoryDb();
  addTearDown(db.close);
  backend.routes['balances/'] = (_) => {
    'total_quota': 12,
    'used_quota': 0,
    'remaining_quota': 12,
  };
  final container = ProviderContainer(
    overrides: [syncEngineProvider.overrideWithValue(engineWith(db, backend))],
  );
  addTearDown(container.dispose);
  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: const MaterialApp(home: LeavesScreen()),
    ),
  );
  await tester.pumpAndSettle();
  return backend;
}

Future<void> _batalkan(WidgetTester tester) async {
  await tester.tap(find.text('Batalkan'));
  await tester.pumpAndSettle();
  await tester.tap(find.text('Ya, batalkan'));
  await tester.pumpAndSettle();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() => initializeDateFormatting('id_ID'));

  testWidgets('batal berhasil: POST cancel lalu daftar menampilkan Dibatalkan', (tester) async {
    var status = 'PENDING';
    final backend = FakeBackend();
    backend.routes['/leaves'] = (_) => [_leave(status)];
    backend.routes['/cancel'] = (_) {
      status = 'CANCELLED';
      return _leave(status);
    };
    await _pump(tester, backend);
    expect(find.text('Menunggu atasan'), findsOneWidget);

    await _batalkan(tester);

    final post = backend.requests.where((r) => r.path.endsWith('/leaves/l1/cancel')).toList();
    expect(post, hasLength(1));
    expect(post.single.method, 'POST');
    expect(find.text('Menunggu atasan'), findsNothing);
    expect(find.text('Dibatalkan'), findsOneWidget);
  });

  testWidgets('batal ditolak server (409): pesan Indonesia tampil dan daftar dimuat ulang', (tester) async {
    final backend = FakeBackend();
    var status = 'PENDING';
    backend.routes['/leaves'] = (_) => [_leave(status)];
    backend.routes['/cancel'] = (o) {
      status = 'APPROVED_BY_PM';
      throw httpError(o, 409, {
        'error': {
          'code': 'NOT_CANCELLABLE',
          'message': 'Status cuti sudah berubah; muat ulang lalu coba lagi.',
        },
      });
    };
    await _pump(tester, backend);

    await _batalkan(tester);

    expect(find.text('Status cuti sudah berubah; muat ulang lalu coba lagi.'), findsWidgets);
    expect(find.text('Sudah disetujui atasan, menunggu HR'), findsOneWidget);
  });

  testWidgets('batal tanpa sinyal: pesan jelas, status tetap', (tester) async {
    final backend = FakeBackend();
    backend.routes['/leaves'] = (_) => [_leave('PENDING')];
    await _pump(tester, backend);

    await _batalkan(tester);

    expect(find.textContaining('Tidak ada koneksi'), findsWidgets);
  });
}
