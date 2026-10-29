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
import 'package:vms_mobile/features/plans/daily_plan_screen.dart';
import 'package:vms_mobile/features/plans/day_resources_card.dart';
import 'package:vms_mobile/shared/app_frame.dart';

import 'support/fake_backend.dart';

/// Kartu "Kendaraan & alat hari ini" dan "Mess hari ini" pada detail jadwal harian (ketua/anggota).

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

Map<String, dynamic> _plan() => {
  'daily_plan_id': 'a',
  'work_date': '2026-10-21',
  'status': 'ONGOING',
  'site_name': 'Lokasi a',
  'team_name': 'Tim MEP',
  'leader_name': 'Agus',
  'leader_employee_id': 'e1',
  'item_count': 0,
  'done_count': 0,
  'clock_in_time': '08:00:00',
  'clock_out_time': '16:00:00',
  'pm_name': 'Budi',
  'pm_phone': null,
  'items': <Object>[],
};

Map<String, dynamic> _loan({String? returnedAt}) => {
  'assignment_id': 'l1',
  'asset_type': 'VEHICLE',
  'asset_id': 'v1',
  'asset_name': 'Hilux',
  'asset_code': 'B 1234 XY',
  'employee_id': 'e1',
  'employee_name': 'Agus',
  'daily_plan_id': 'a',
  'work_date': '2026-10-21',
  'assignment_status': 'loaned',
  'loaned_at': '2026-10-21T01:00:00Z',
  'returned_at': returnedAt,
};

Map<String, dynamic> _stay({
  String status = 'APPROVED',
  String start = '2026-10-20',
  String end = '2026-10-25',
}) => {
  'mess_stay_id': 's1',
  'mess_id': 'm1',
  'mess_name': 'Mess Pusat',
  'city': 'Pekanbaru',
  'address': 'Jl. Sudirman 1',
  'status': status,
  'stay_start_date': start,
  'stay_end_date': end,
};

void main() {
  test('messStayForDay: hanya hunian APPROVED yang memuat tanggal kerja', () {
    final stays = [
      _stay(status: 'CANCELLED'),
      _stay(start: '2026-10-01', end: '2026-10-19'),
    ];
    expect(messStayForDay(stays, '2026-10-21'), isNull);
    expect(
      messStayForDay([_stay(), ...stays], '2026-10-21')?['mess_name'],
      'Mess Pusat',
    );
    expect(
      messStayForDay([_stay()], '2026-10-25')?['mess_name'],
      'Mess Pusat',
      reason: 'batas akhir inklusif',
    );
    expect(messStayForDay([_stay()], 'bukan-tanggal'), isNull);
  });

  group('detail jadwal harian', () {
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
      backend.routes['/report'] = (o) => throw httpError(o, 404, {
        'error': {'code': 'NOT_FOUND', 'message': 'belum ada laporan'},
      });
    });

    tearDown(() async => db.close());

    Future<void> pumpPlan(WidgetTester tester) async {
      await tester.runAsync(() async {
        await tester.pumpWidget(
          ProviderScope(
            overrides: [
              syncEngineProvider.overrideWithValue(engine),
              authControllerProvider.overrideWith(() => _SignedInAs('e2')),
            ],
            child: ShadApp(
              theme: VmsShadTheme.light,
              materialThemeBuilder: (context, _) => VmsTheme.light,
              builder: vmsAppFrame,
              home: const DailyPlanScreen(dailyPlanId: 'a'),
            ),
          ),
        );
        await Future<void>.delayed(const Duration(milliseconds: 100));
      });
      for (var i = 0; i < 30; i++) {
        await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 50)),
        );
        await tester.pump(const Duration(milliseconds: 50));
        if (i >= 10 && find.byType(CircularProgressIndicator).evaluate().isEmpty) {
          break;
        }
      }
      await tester.pumpAndSettle();
    }

    testWidgets(
      'anggota melihat kendaraan dan alat yang dipegang untuk hari itu',
      (tester) async {
        backend.routes['/work-plans/daily/a/assets'] = (_) => [
          _loan(),
          _loan()
            ..['asset_type'] = 'TOOL'
            ..['asset_name'] = 'Bor beton'
            ..['asset_code'] = 'TL-007',
        ];
        backend.routes['/mess/me'] = (_) => [];
        await pumpPlan(tester);

        expect(find.text('Kendaraan & alat hari ini'), findsOneWidget);
        expect(
          find.textContaining('Hilux (B 1234 XY) · dipegang Agus'),
          findsOneWidget,
        );
        expect(find.textContaining('Bor beton (TL-007)'), findsOneWidget);
        expect(find.text('Mess hari ini'), findsNothing);
      },
    );

    testWidgets(
      'kartu aset disembunyikan bila jadwal tidak bisa dimuat (bukan anggota)',
      (tester) async {
        backend.routes['/work-plans/daily/a/assets'] = (o) =>
            throw httpError(o, 403, {
              'error': {'code': 'FORBIDDEN', 'message': 'bukan anggota'},
            });
        backend.routes['/mess/me'] = (_) => [];
        await pumpPlan(tester);

        expect(find.textContaining('Tim MEP'), findsOneWidget);
        expect(find.text('Kendaraan & alat hari ini'), findsNothing);
      },
    );

    testWidgets(
      'mess yang berlaku pada tanggal kerja tampil di detail jadwal',
      (tester) async {
        backend.routes['/work-plans/daily/a/assets'] = (_) => <Object>[];
        backend.routes['/mess/me'] = (_) => [_stay()];
        await pumpPlan(tester);

        expect(find.text('Mess hari ini'), findsOneWidget);
        expect(find.textContaining('Mess Pusat · Pekanbaru'), findsOneWidget);
        expect(find.textContaining('Jl. Sudirman 1'), findsOneWidget);
        expect(
          find.text('Tidak ada kendaraan atau alat untuk jadwal ini.'),
          findsOneWidget,
        );
      },
    );
  });
}
