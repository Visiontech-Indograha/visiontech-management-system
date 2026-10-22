import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:geolocator_platform_interface/geolocator_platform_interface.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:shadcn_ui/shadcn_ui.dart';
import 'package:vms_mobile/core/location_helper.dart';
import 'package:vms_mobile/core/photo_capture.dart';
import 'package:vms_mobile/core/providers.dart';
import 'package:vms_mobile/core/theme/theme.dart';
import 'package:vms_mobile/data/app_database.dart';
import 'package:vms_mobile/data/sync_engine.dart';
import 'package:vms_mobile/features/attendance/attendance_screen.dart';
import 'package:vms_mobile/features/auth/auth_controller.dart';
import 'package:vms_mobile/features/auth/auth_state.dart';
import 'package:vms_mobile/features/plans/daily_plans_screen.dart';
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

Map<String, dynamic> _day(String id, String status, {String date = '2026-10-21'}) => {
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
    // Swafoto absen selalu diminta (V2): uji tanpa plugin kamera.
    photoCaptureOverride = (_) async {
      final dir = await Directory.systemTemp.createTemp('vms-swafoto');
      return (File('${dir.path}/swafoto.jpg')..writeAsBytesSync([1, 2, 3]), null);
    };
    db = memoryDb();
    backend = FakeBackend();
    engine = engineWith(db, backend);
  });

  tearDown(() async {
    photoCaptureOverride = null;
    await db.close();
  });

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
    // Beri waktu I/O nyata (berkas swafoto, DB lokal, unggah palsu) sampai indikator proses hilang,
    // baru tunggu animasi selesai — rantai async V2 (kamera → unggah → kirim) lebih panjang dari 100 ms.
    for (var i = 0; i < 30; i++) {
      await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 50)));
      await tester.pump(const Duration(milliseconds: 50));
      if (find.byType(CircularProgressIndicator).evaluate().isEmpty) break;
    }
    await tester.pumpAndSettle();
  }

  group('Jadwal harian', () {
    testWidgets('menampilkan jadwal minggu ini beserta ringkasan titik', (tester) async {
      backend.routes['/work-plans/daily'] = (_) => [_day('a', 'APPROVED'), _day('b', 'ONGOING', date: '2026-10-22')];
      await show(tester, const DailyPlansScreen());

      expect(find.text('Lokasi a'), findsOneWidget);
      expect(find.text('Lokasi b'), findsOneWidget);
      expect(find.textContaining('1 dari 2 pekerjaan selesai'), findsNWidgets(2));
      final q = backend.requests.firstWhere((r) => r.path.endsWith('/work-plans/daily')).queryParameters;
      expect(q.keys, containsAll(['start', 'end']));
    });

    testWidgets('kosong: pesan jadwal muncul setelah disetujui PM', (tester) async {
      backend.routes['/work-plans/daily'] = (_) => <Object>[];
      await show(tester, const DailyPlansScreen());
      expect(find.text('Tidak ada jadwal minggu ini'), findsOneWidget);
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
      backend.routes['/offices'] = (_) => [site];
      backend.routes['/work-plans/daily'] = (_) => <Object>[];
      backend.routes['/files/upload'] = (_) => {'file_id': 'f-selfie'};
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
        // Wajah V2: swafoto selalu dikirim; server yang mencocokkan wajah.
        expect((sent.data as Map)['selfie_file_id'], 'f-selfie');
        expect((sent.data as Map).containsKey('face_probe_id'), isFalse);
        expect(find.text('Absen masuk tercatat.'), findsOneWidget);
      },
    );

    testWidgets('lokasi tugas hari ini (jadwal disetujui) didahulukan dan dikirim sebagai daily_plan_id', (tester) async {
      online();
      backend.routes['/work-plans/daily'] = (_) => [_day('d1', 'APPROVED')];
      GeolocatorPlatform.instance = _FakeGps(_at(1.6650, 101.4478, accuracy: 8));
      await show(tester, const AttendanceScreen());
      expect(find.text('Lokasi tugas: Lokasi d1'), findsWidgets);

      await tapCheckIn(tester);
      final sent = backend.requests.where((r) => r.path.endsWith('/check-in')).single;
      expect((sent.data as Map)['site_id'], 'd1');
    });

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
