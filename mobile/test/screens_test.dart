import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:geolocator_platform_interface/geolocator_platform_interface.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:shadcn_ui/shadcn_ui.dart';
import 'package:vms_mobile/core/location_helper.dart';
import 'package:vms_mobile/core/providers.dart';
import 'package:vms_mobile/core/theme/theme.dart';
import 'package:vms_mobile/data/app_database.dart';
import 'package:vms_mobile/data/sync_engine.dart';
import 'package:vms_mobile/features/attendance/attendance_screen.dart';
import 'package:vms_mobile/features/auth/auth_controller.dart';
import 'package:vms_mobile/features/auth/auth_state.dart';
import 'package:vms_mobile/features/plans/work_plans_screen.dart';
import 'package:vms_mobile/features/sync/sync_queue_screen.dart';
import 'package:vms_mobile/shared/app_frame.dart';

import 'support/fake_backend.dart';

/// Uji widget layar utama (dulu belum ada — MVP mengejar tampilan dulu):
/// memuat, kosong, galat/luring, berhasil; plus aturan K-12 di layar absensi.

class _SignedIn extends AuthController {
  @override
  AuthState build() => const AuthAuthenticated(
    AuthUser(
      id: 'u1',
      username: 'teknisi@contoh.test',
      role: UserRole.member,
      employeeId: 'e1',
    ),
  );
}

/// GPS palsu: selalu mengembalikan [position] tanpa menyentuh plugin.
class _FakeGps extends GeolocatorPlatform {
  _FakeGps(this.position);
  Position position;

  @override
  Future<bool> isLocationServiceEnabled() async => true;
  @override
  Future<LocationPermission> checkPermission() async =>
      LocationPermission.whileInUse;
  @override
  Future<LocationPermission> requestPermission() async =>
      LocationPermission.whileInUse;
  @override
  Future<Position> getCurrentPosition({
    LocationSettings? locationSettings,
  }) async => position;
}

Position _at(double lat, double lng, {required double accuracy}) => Position(
  latitude: lat,
  longitude: lng,
  timestamp: DateTime(2026, 9, 27, 8),
  accuracy: accuracy,
  altitude: 0,
  altitudeAccuracy: 0,
  heading: 0,
  headingAccuracy: 0,
  speed: 0,
  speedAccuracy: 0,
);

Map<String, dynamic> _plan(String id, String status) => {
  'id': id,
  'title': 'SK $id',
  'number': 'SK-202609-$id',
  'status': status,
  'location_text': 'Gudang Dumai',
  'period_start': '2026-09-01',
  'period_end': '2026-09-30',
  'site_id': null,
  'leader_employee_id': 'e1',
  'row_version': 7,
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
  });

  tearDown(() async => db.close());

  Future<void> show(WidgetTester tester, Widget screen) async {
    await tester.runAsync(() async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            syncEngineProvider.overrideWithValue(engine),
            authControllerProvider.overrideWith(_SignedIn.new),
          ],
          child: ShadApp(
            theme: VmsShadTheme.light,
            materialThemeBuilder: (context, _) => VmsTheme.light,
            builder: vmsAppFrame, // sama dengan main.dart (ScaffoldMessenger untuk SnackBar)
            home: screen,
          ),
        ),
      );
      await Future<void>.delayed(const Duration(milliseconds: 100));
    });
    await tester.pumpAndSettle();
  }

  Future<void> settle(WidgetTester tester) async {
    await tester.runAsync(
      () => Future<void>.delayed(const Duration(milliseconds: 100)),
    );
    await tester.pumpAndSettle();
  }

  group('Daftar SK', () {
    testWidgets('menampilkan SK terbit/berjalan, menyembunyikan draf', (
      tester,
    ) async {
      backend.routes['/work-plans'] = (_) => [
        _plan('a', 'IN_PROGRESS'),
        _plan('b', 'PUBLISHED'),
        _plan('c', 'DRAFT'),
      ];
      await show(tester, const WorkPlansScreen());

      expect(find.text('SK a'), findsOneWidget);
      expect(find.text('SK b'), findsOneWidget);
      expect(find.text('SK c'), findsNothing);
      expect(find.text('2 rencana kerja · 1 sedang berjalan'), findsOneWidget);
    });

    testWidgets('luring: menampilkan data tersimpan beserta tandanya', (
      tester,
    ) async {
      backend.routes['/work-plans'] = (_) => [_plan('a', 'IN_PROGRESS')];
      await show(tester, const WorkPlansScreen());
      expect(find.text('SK a'), findsOneWidget);

      backend.offline();
      await tester.tap(find.byTooltip('Muat ulang'));
      await settle(tester);

      expect(find.text('SK a'), findsOneWidget);
      expect(find.text('Luring — menampilkan data tersimpan.'), findsOneWidget);
    });

    testWidgets(
      'luring tanpa data tersimpan: pesan galat yang bisa ditindaklanjuti',
      (tester) async {
        await show(tester, const WorkPlansScreen());
        // Temuan R-18: dulu "Luring — menampilkan data tersimpan." + "Belum ada SK untuk Anda".
        expect(find.text(SyncEngine.offlineNoDataMessage), findsOneWidget);
        expect(find.text('Belum ada rencana kerja untuk Anda'), findsNothing);
        expect(find.text('Luring — menampilkan data tersimpan.'), findsNothing);
      },
    );

    testWidgets('ketua dapat menerima SK terbit dari layar mobile', (
      tester,
    ) async {
      backend.routes['/work-plans'] = (_) => [_plan('a', 'PUBLISHED')];
      backend.routes['/work-plans/a/days'] = (_) => <Object>[];
      backend.routes['/work-plans/a/accept'] = (_) => {
        ..._plan('a', 'ACCEPTED'),
        'row_version': 8,
      };
      await show(tester, const WorkPlansScreen());

      await tester.tap(find.text('SK a'));
      await settle(tester);
      expect(find.text('Terima rencana kerja'), findsOneWidget);

      await tester.tap(find.text('Terima rencana kerja'));
      await tester.pumpAndSettle();
      expect(find.text('Terima surat kerja ini?'), findsOneWidget);
      await tester.tap(find.widgetWithText(FilledButton, 'Terima'));
      await settle(tester);

      final request = backend.requests.singleWhere(
        (r) => r.path.endsWith('/work-plans/a/accept'),
      );
      expect(request.data, {'row_version': 7, 'reason': ''});
      expect(find.text('Diterima'), findsWidgets);
    });
  });

  group('Absensi', () {
    const site = {
      'id': 's1',
      'name': 'Kantor Visiontech Dumai',
      'radius_m': 100,
      'location': {'lat': 1.6650, 'lng': 101.4478},
    };

    void online() {
      backend.routes['/attendance'] = (_) => {'items': <Object>[], 'total': 0};
      backend.routes['/sites'] = (_) => [site];
      backend.routes['/work-plans'] = (_) => <Object>[];
      backend.routes['/attendance/check-in'] = (o) => {
        'id': 'a1',
        'status': 'AUTO_VALID',
      };
    }

    Future<void> tapCheckIn(WidgetTester tester) async {
      await tester.ensureVisible(find.text('Absen masuk'));
      await tester.tap(find.text('Absen masuk'));
      await settle(tester);
    }

    testWidgets(
      'K-12: akurasi GPS > 100 m ditolak sebelum swafoto/pengiriman',
      (tester) async {
        online();
        GeolocatorPlatform.instance = _FakeGps(
          _at(1.6650, 101.4478, accuracy: 150),
        );
        await show(tester, const AttendanceScreen());
        expect(find.text('Kantor Visiontech Dumai'), findsWidgets);

        await tapCheckIn(tester);

        expect(find.text(gpsAccuracyMessage(150)), findsOneWidget);
        expect(
          backend.requests.where((r) => r.path.endsWith('/check-in')),
          isEmpty,
        );
      },
    );

    testWidgets(
      'di dalam radius dengan GPS akurat: absen masuk terkirim beserta akurasinya',
      (tester) async {
        online();
        GeolocatorPlatform.instance = _FakeGps(
          _at(1.6650, 101.4478, accuracy: 8),
        );
        await show(tester, const AttendanceScreen());

        await tapCheckIn(tester);

        final sent = backend.requests
            .where((r) => r.path.endsWith('/check-in'))
            .single;
        expect((sent.data as Map)['site_id'], 's1');
        expect((sent.data as Map)['accuracy_m'], 8);
        expect((sent.data as Map).containsKey('selfie_file_id'), isFalse);
        expect(find.text('Absen masuk tercatat.'), findsOneWidget);
      },
    );

    testWidgets(
      'terikat SK tetapi memilih kantor: peringatan tampil, absen tetap terkirim ke kantor',
      (tester) async {
        online();
        const project = {
          'id': 's2',
          'name': 'Proyek CCTV Rumbai',
          'radius_m': 100,
          'location': {'lat': 1.6650, 'lng': 101.4478},
        };
        backend.routes['/sites'] = (_) => [site, project];
        backend.routes['/work-plans'] = (_) => [
          {'id': 'wp1', 'status': 'IN_PROGRESS', 'site_id': 's2'},
        ];
        GeolocatorPlatform.instance = _FakeGps(
          _at(1.6650, 101.4478, accuracy: 8),
        );
        await show(tester, const AttendanceScreen());
        // Lokasi SK dipilih otomatis → tanpa peringatan.
        expect(find.text('Proyek CCTV Rumbai'), findsWidgets);
        expect(
          find.byKey(const Key('peringatan-bukan-lokasi-sk')),
          findsNothing,
        );

        await tester.tap(find.text('Proyek CCTV Rumbai').first);
        await settle(tester);
        await tester.tap(find.text('Kantor Visiontech Dumai').last);
        await settle(tester);
        expect(
          find.byKey(const Key('peringatan-bukan-lokasi-sk')),
          findsOneWidget,
        );
        expect(find.textContaining('Proyek CCTV Rumbai'), findsWidgets);

        await tapCheckIn(tester);
        final sent = backend.requests
            .where((r) => r.path.endsWith('/check-in'))
            .single;
        expect((sent.data as Map)['site_id'], 's1');
      },
    );

    Map<String, Object?> record(String workDate, {String? out}) => {
      'id': 'a-$workDate',
      'work_date': workDate,
      'site_label': 'Kantor Visiontech Dumai',
      'check_in_at': '${workDate}T01:00:00Z',
      'check_out_at': out,
      'status': 'AUTO_VALID',
    };

    testWidgets(
      'O-10: sesi terbuka kemarin (lewat tengah malam) tetap bisa absen pulang',
      (tester) async {
        online();
        backend.routes['/attendance'] = (_) => {
          'items': [record('2000-01-01')],
          'total': 1,
          'today': '2000-01-02',
        };
        await show(tester, const AttendanceScreen());
        expect(find.text('Absen pulang'), findsOneWidget);
        expect(find.text('Absen masuk'), findsNothing);
      },
    );

    testWidgets('O-10: "hari ini" mengikuti tanggal server, bukan jam HP', (
      tester,
    ) async {
      online();
      backend.routes['/attendance'] = (_) => {
        'items': [record('2099-01-01', out: '2099-01-01T10:00:00Z')],
        'total': 1,
        'today': '2099-01-01',
      };
      await show(tester, const AttendanceScreen());
      expect(
        find.text('Absensi hari ini selesai. Terima kasih!'),
        findsOneWidget,
      );
      expect(find.text('Absen masuk'), findsNothing);
    });
  });

  group('Antrian sinkronisasi', () {
    testWidgets('kosong: semua data sudah terkirim', (tester) async {
      await show(tester, const SyncQueueScreen());
      expect(find.text('Semua data sudah terkirim'), findsOneWidget);
    });

    testWidgets('operasi luring tampil dengan labelnya dan status menunggu', (
      tester,
    ) async {
      await tester.runAsync(
        () => engine.submit(OfflineOp.taskToggle, {'task_id': 't1'}),
      );
      await show(tester, const SyncQueueScreen());
      expect(find.textContaining('Centang tugas'), findsOneWidget);
      expect(
        find.text('Menunggu dikirim otomatis saat ada sinyal.'),
        findsOneWidget,
      );
    });
  });
}
