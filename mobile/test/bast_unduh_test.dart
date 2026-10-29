import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:shadcn_ui/shadcn_ui.dart';
import 'package:vms_mobile/core/providers.dart';
import 'package:vms_mobile/core/theme/theme.dart';
import 'package:vms_mobile/data/app_database.dart';
import 'package:vms_mobile/data/sync_engine.dart';
import 'package:vms_mobile/features/auth/auth_controller.dart';
import 'package:vms_mobile/features/auth/auth_state.dart';
import 'package:vms_mobile/features/plans/bast_sign_screen.dart';
import 'package:vms_mobile/features/plans/daily_plan_screen.dart';
import 'package:vms_mobile/shared/app_frame.dart';

import 'support/fake_backend.dart';

/// Unduh work completion (.docx) di layar BAST memanggil ekspor BAST di server. Bagian serah terima di
/// jadwal harian hanya tampil untuk ketua tim jadwal itu; anggota biasa tidak melihatnya.

class _SignedInAs extends AuthController {
  _SignedInAs(this.employeeId);
  final String employeeId;

  @override
  AuthState build() => AuthAuthenticated(
    AuthUser(
      id: 'u-$employeeId',
      username: '$employeeId@contoh.test',
      role: UserRole.member,
      employeeId: employeeId,
    ),
  );
}

Map<String, dynamic> _item() => {
  'item_id': 'i1',
  'completion_id': 'c1',
  'title': 'Tiang A',
  'task_phase': 'INSTALLATION',
  'work_type_name': 'Galian',
  'target_qty': 10,
  'completed_qty': 0,
  'status': 'TODO',
};

Map<String, dynamic> _plan() => {
  'daily_plan_id': 'a',
  'work_date': '2026-10-21',
  'status': 'ONGOING',
  'site_name': 'Lokasi a',
  'site_lat': '1.6650000',
  'site_lng': '101.4478000',
  'attendance_radius_m': 150,
  'team_name': 'Tim MEP',
  'leader_name': 'Agus',
  'leader_employee_id': 'e1', // ketua tim jadwal ini
  'item_count': 1,
  'done_count': 0,
  'clock_in_time': '08:00:00',
  'clock_out_time': '16:00:00',
  'pm_name': 'Budi',
  'pm_phone': null,
  'items': [_item()],
};

Map<String, dynamic> _order() => {
  'completion_id': 'c1',
  'project_title': 'Pasang CCTV',
  'client_name': 'PT Gardu',
  'order_number': 'PO-1',
  'summary_notes': '',
  'obstacles': '',
  'realization_photos_json': <Object>[],
  'signature_hash': null,
  'leader_signed_at': null,
  'pm_signed_at': null,
};

void main() {
  late AppDatabase db;
  late FakeBackend backend;
  late SyncEngine engine;

  setUpAll(() => initializeDateFormatting('id_ID'));

  setUp(() {
    db = memoryDb();
    backend = FakeBackend();
    engine = engineWith(db, backend);
    backend.routes['/work-plans/daily/a'] = (_) => _plan();
    backend.routes['/attendance'] = (_) => {'items': <Object>[], 'total': 0};
    backend.routes['/report'] = (o) =>
        throw httpError(o, 404, {'error': {'code': 'NOT_FOUND', 'message': 'belum ada laporan'}});
    backend.routes['/work-completions/c1'] = (_) => _order();
    backend.routes['/exports/work-completions/c1'] = (_) => <int>[80, 75, 3, 4];
  });

  tearDown(() async {
    await db.close();
  });

  Future<void> settle(WidgetTester tester) async {
    for (var i = 0; i < 30; i++) {
      await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 50)));
      await tester.pump(const Duration(milliseconds: 50));
      if (i >= 10 && find.byType(CircularProgressIndicator).evaluate().isEmpty) break;
    }
    await tester.pumpAndSettle();
  }

  Future<void> pumpApp(WidgetTester tester, String employeeId, Widget home) async {
    await tester.runAsync(() async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            syncEngineProvider.overrideWithValue(engine),
            authControllerProvider.overrideWith(() => _SignedInAs(employeeId)),
          ],
          child: ShadApp(
            theme: VmsShadTheme.light,
            materialThemeBuilder: (context, _) => VmsTheme.light,
            builder: vmsAppFrame,
            home: home,
          ),
        ),
      );
      await Future<void>.delayed(const Duration(milliseconds: 100));
    });
    await settle(tester);
  }

  testWidgets('ketua mengunduh work completion (.docx) lewat ekspor BAST', (tester) async {
    await pumpApp(tester, 'e1', const BastSignScreen(completionId: 'c1'));

    final download = find.text('Unduh work completion (.docx)');
    expect(download, findsOneWidget);
    await tester.ensureVisible(download);
    await tester.tap(download);
    await settle(tester);

    final post = backend.requests.where((r) => r.method == 'POST' && r.path.endsWith('/exports/work-completions/c1'));
    expect(post, hasLength(1));
    expect(Map<String, dynamic>.from(post.single.data as Map)['template'], 'BAST');
  });

  testWidgets('ketua tim melihat bagian serah terima di jadwalnya', (tester) async {
    await pumpApp(tester, 'e1', const DailyPlanScreen(dailyPlanId: 'a'));
    expect(find.text('Serah terima pekerjaan'), findsOneWidget);
  });

  testWidgets('anggota biasa (bukan ketua) tidak melihat bagian serah terima dan tombol unduh', (tester) async {
    await pumpApp(tester, 'e2', const DailyPlanScreen(dailyPlanId: 'a'));
    expect(find.text('Serah terima pekerjaan'), findsNothing);
    expect(find.text('Unduh work completion (.docx)'), findsNothing);
    expect(backend.requests.any((r) => r.path.contains('/work-completions/c1')), isFalse);
  });
}
