@Tags(['golden'])
library;

import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart' show Override;
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:shadcn_ui/shadcn_ui.dart';
import 'package:vms_mobile/core/providers.dart';
import 'package:vms_mobile/core/theme/theme.dart';
import 'package:vms_mobile/data/app_database.dart';
import 'package:vms_mobile/data/sync_engine.dart';
import 'package:vms_mobile/features/attendance/attendance_screen.dart';
import 'package:vms_mobile/features/auth/auth_controller.dart';
import 'package:vms_mobile/features/auth/auth_state.dart';
import 'package:vms_mobile/features/auth/login_screen.dart';
import 'package:vms_mobile/features/hse/k3_campaign.dart';
import 'package:vms_mobile/features/hse/k3_campaign_view.dart';
import 'package:vms_mobile/features/leaves/leaves_screen.dart';
import 'package:vms_mobile/features/plans/daily_plans_screen.dart';
import 'package:vms_mobile/features/sync/sync_queue_screen.dart';
import 'package:vms_mobile/shared/app_frame.dart';

import '../support/fake_backend.dart';

/// Golden hanya dibandingkan di Linux (CI). Lihat README.md di folder ini.
final bool _bandingkan = Platform.isLinux || Platform.environment['VMS_GOLDEN'] == '1';
final bool _skip = !_bandingkan; // hanya dibandingkan di Linux (CI)

class _SignedIn extends AuthController {
  @override
  AuthState build() => const AuthAuthenticated(
    AuthUser(id: 'u1', username: 'teknisi@contoh.test', role: UserRole.member, employeeId: 'e1'),
  );
}

class _LoggedOut extends AuthController {
  @override
  AuthState build() => const AuthUnauthenticated();
}

Map<String, dynamic> _day(String id, String status, String date) => {
  'daily_plan_id': id,
  'work_date': date,
  'status': status,
  'site_name': 'Lokasi $id',
  'site_lat': '1.6650000',
  'site_lng': '101.4478000',
  'attendance_radius_m': 150,
  'team_name': 'Tim MEP',
  'leader_name': 'Agus',
  'leader_employee_id': 'e1',
  'item_count': 2,
  'done_count': 1,
};

void main() {
  late AppDatabase db;
  late FakeBackend backend;
  late SyncEngine engine;

  setUpAll(() => initializeDateFormatting('id_ID'));

  setUp(() {
    attendanceClock = () => DateTime.utc(2026, 10, 2, 3);
    db = memoryDb();
    backend = FakeBackend();
    engine = engineWith(db, backend, clock: attendanceClock);
  });

  tearDown(() async {
    attendanceClock = DateTime.now;
    await db.close();
  });

  Future<void> tampil(
    WidgetTester tester,
    Widget screen, {
    required String berkas,
    List<Override> extra = const [],
    bool signedIn = true,
  }) async {
    tester.view.physicalSize = const Size(360, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.runAsync(() async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            syncEngineProvider.overrideWithValue(engine),
            authControllerProvider.overrideWith(signedIn ? _SignedIn.new : _LoggedOut.new),
            ...extra,
          ],
          child: MediaQuery(
            data: const MediaQueryData(size: Size(360, 800), textScaler: TextScaler.linear(1.3)),
            child: ShadApp(
              theme: VmsShadTheme.light,
              materialThemeBuilder: (context, _) => VmsTheme.light,
              builder: vmsAppFrame,
              home: screen,
            ),
          ),
        ),
      );
      for (var i = 0; i < 12; i++) {
        await Future<void>.delayed(const Duration(milliseconds: 50));
        await tester.pump(const Duration(milliseconds: 50));
      }
    });
    await tester.pump(const Duration(seconds: 1));
    await expectLater(find.byType(ShadApp).first, matchesGoldenFile('$berkas.png'));
  }

  testWidgets('login dengan tombol sidik jari', (tester) async {
    await tampil(
      tester,
      const LoginScreen(),
      berkas: 'login_sidik_jari',
      signedIn: false,
      extra: [deviceLoginAvailableProvider.overrideWith((ref) async => true)],
    );
  }, skip: _skip);

  testWidgets('login tanpa sidik jari', (tester) async {
    await tampil(
      tester,
      const LoginScreen(),
      berkas: 'login_sandi',
      signedIn: false,
      extra: [deviceLoginAvailableProvider.overrideWith((ref) async => false)],
    );
  }, skip: _skip);

  testWidgets('beranda absen', (tester) async {
    backend.routes['/attendance'] = (_) => {'items': <Object>[], 'total': 0};
    backend.routes['/offices'] = (_) => [
      {
        'id': 's1',
        'name': 'Kantor Visiontech Dumai',
        'radius_m': 100,
        'location': {'lat': 1.6650, 'lng': 101.4478},
      },
    ];
    backend.routes['/work-plans/daily'] = (_) => <Object>[];
    await tampil(tester, const AttendanceScreen(), berkas: 'absen');
  }, skip: _skip);

  testWidgets('daftar jadwal', (tester) async {
    backend.routes['/work-plans/daily'] = (_) => [
      _day('a', 'APPROVED', '2026-10-21'),
      _day('b', 'ONGOING', '2026-10-22'),
    ];
    await tampil(tester, const DailyPlansScreen(), berkas: 'jadwal');
  }, skip: _skip);

  testWidgets('cuti', (tester) async {
    backend.routes['/leave-balances/e1'] = (_) => {'annual_quota': 12, 'used_days': 2, 'remaining_days': 10};
    backend.routes['/leaves'] = (_) => [
      {'leave_id': 'l1', 'start_date': '2030-01-07', 'end_date': '2030-01-08', 'total_days': 2, 'status': 'PENDING'},
    ];
    await tampil(tester, const LeavesScreen(), berkas: 'cuti');
  }, skip: _skip);

  testWidgets('popup wajib baca K3', (tester) async {
    const k3 = K3Campaign(
      id: 'c1',
      title: 'Keselamatan di ketinggian',
      contentText: 'Pakai sabuk pengaman setiap bekerja di atas dua meter.',
      mediaIds: ['f0', 'f1'],
      mediaCaptions: ['Contoh sabuk', 'Titik kait'],
      cooldownSeconds: 20,
    );
    await tampil(
      tester,
      K3CampaignView(
        campaign: k3,
        onConfirm: (_) {},
        photoBuilder: (_, id) => ColoredBox(color: Colors.blueGrey, child: Center(child: Text('foto $id'))),
      ),
      berkas: 'k3_popup',
    );
  }, skip: _skip);

  testWidgets('sinkron: antrean berisi operasi menunggu', (tester) async {
    await tester.runAsync(() => engine.submit(OfflineOp.taskToggle, {'task_id': 't1'}));
    await tampil(tester, const SyncQueueScreen(), berkas: 'sinkron_menunggu');
  }, skip: _skip);

  testWidgets('sinkron: antrean kosong', (tester) async {
    await tampil(tester, const SyncQueueScreen(), berkas: 'sinkron_kosong');
  }, skip: _skip);
}
