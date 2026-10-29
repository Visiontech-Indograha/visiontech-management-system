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
import 'package:vms_mobile/features/plans/daily_plan_screen.dart';
import 'package:vms_mobile/features/plans/daily_plans_screen.dart';
import 'package:vms_mobile/features/plans/item_progress_screen.dart';
import 'package:vms_mobile/features/sync/sync_queue_screen.dart';
import 'package:vms_mobile/shared/app_frame.dart';
import 'package:vms_mobile/shared/ui/vms_ui.dart';

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
    // Jam tetap 10.00 WIB: aturan jam absen tidak bergantung jam CI.
    attendanceClock = () => DateTime.utc(2026, 10, 2, 3);
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
    attendanceClock = DateTime.now;
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
      // Minimal ±0,5 dtk: di CI yang lambat indikator proses belum tentu sudah muncul di putaran awal.
      if (i >= 10 && find.byType(CircularProgressIndicator).evaluate().isEmpty) break;
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
        expect(find.textContaining('Absen pulang'), findsOneWidget);
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

  group('Hari kerja & hasil kerja (B4)', () {
    Map<String, dynamic> planDetail(String status, {List<Map<String, dynamic>> items = const []}) => {
      ..._day('a', status),
      'clock_in_time': '08:00:00',
      'clock_out_time': '16:00:00',
      'pm_name': 'Budi',
      'pm_phone': null,
      'items': items,
    };

    Map<String, dynamic> planItem(String status) => {
      'item_id': 'i1',
      'title': 'Tiang A',
      'task_phase': 'INSTALLATION',
      'work_type_name': 'Galian',
      'target_qty': 10,
      'completed_qty': 0,
      'status': status,
    };

    final reportOk = {'summary': 'Selesai galian', 'obstacles': '', 'submitted_at': '2026-10-21T03:00:00Z'};

    void routeReport({bool exists = true}) {
      backend.routes['/report'] = (o) => exists
          ? reportOk
          : throw httpError(o, 404, {'error': {'code': 'NOT_FOUND', 'message': 'belum ada laporan'}});
    }

    testWidgets('Mulai hari kerja nonaktif dan dijelaskan bila absen masuk belum tercatat', (tester) async {
      backend.routes['/work-plans/daily/a'] = (_) => planDetail('APPROVED');
      routeReport(exists: false);
      backend.routes['/attendance'] = (_) => {'items': <Object>[], 'total': 0};
      backend.routes['/start'] = (_) => planDetail('ONGOING');
      await show(tester, const DailyPlanScreen(dailyPlanId: 'a'));

      expect(find.textContaining('Absen masuk hari ini belum tercatat'), findsOneWidget);
      await tester.tap(find.text('Mulai hari kerja'));
      await settle(tester);
      expect(backend.requests.any((r) => r.path.endsWith('/start')), isFalse);
    });

    testWidgets('absen masuk tercatat hari jadwal: Mulai hari kerja mengirim permintaan', (tester) async {
      backend.routes['/work-plans/daily/a'] = (_) => planDetail('APPROVED');
      routeReport(exists: false);
      backend.routes['/attendance'] = (_) => {
        'items': [
          {'work_date': '2026-10-21', 'check_in_at': '2026-10-21T01:00:00Z'},
        ],
        'total': 1,
      };
      backend.routes['/start'] = (_) => planDetail('ONGOING');
      await show(tester, const DailyPlanScreen(dailyPlanId: 'a'));

      expect(find.textContaining('Absen masuk hari ini belum tercatat'), findsNothing);
      await tester.tap(find.text('Mulai hari kerja'));
      await settle(tester);
      expect(backend.requests.any((r) => r.path.endsWith('/start')), isTrue);
      expect(find.text('Hari kerja dimulai.'), findsOneWidget);
    });

    testWidgets('CHECKIN_REQUIRED dari server tampil dalam bahasa Indonesia', (tester) async {
      backend.routes['/work-plans/daily/a'] = (_) => planDetail('APPROVED');
      routeReport(exists: false);
      backend.routes['/attendance'] = (_) => {
        'items': [
          {'work_date': '2026-10-21', 'check_in_at': '2026-10-21T01:00:00Z'},
        ],
        'total': 1,
      };
      backend.routes['/start'] = (o) => throw httpError(o, 409, {'error': {'code': 'CHECKIN_REQUIRED', 'message': 'check-in required'}});
      await show(tester, const DailyPlanScreen(dailyPlanId: 'a'));

      await tester.tap(find.text('Mulai hari kerja'));
      await settle(tester);
      expect(
        find.text('Absen masuk hari ini belum tercatat. Lakukan absen masuk dulu di menu Absensi, lalu mulai hari kerja.'),
        findsOneWidget,
      );
      expect(find.text('check-in required'), findsNothing);
    });

    testWidgets('item menunggu pindah hari menahan tombol Selesaikan hari kerja', (tester) async {
      backend.routes['/work-plans/daily/a'] = (_) => planDetail('ONGOING', items: [planItem('PENDING_ROLLOVER')]);
      routeReport();
      backend.routes['/complete'] = (_) => planDetail('COMPLETED');
      await show(tester, const DailyPlanScreen(dailyPlanId: 'a'));

      expect(find.textContaining('menunggu keputusan PM untuk pindah hari'), findsOneWidget);
      await tester.tap(find.text('Selesaikan hari kerja'));
      await settle(tester);
      expect(find.text('Selesaikan hari kerja?'), findsNothing);
      expect(backend.requests.any((r) => r.path.endsWith('/complete')), isFalse);
    });

    testWidgets('ROLLOVER_PENDING dari server tampil sebagai pesan yang jelas', (tester) async {
      backend.routes['/work-plans/daily/a'] = (_) => planDetail('ONGOING');
      routeReport();
      backend.routes['/complete'] = (o) =>
          throw httpError(o, 409, {'error': {'code': 'ROLLOVER_PENDING', 'message': 'rollover pending'}});
      await show(tester, const DailyPlanScreen(dailyPlanId: 'a'));

      await tester.tap(find.text('Selesaikan hari kerja'));
      await settle(tester);
      await tester.tap(find.text('Selesaikan'));
      await settle(tester);
      expect(find.textContaining('Hari kerja belum bisa ditutup sebelum keputusan itu keluar'), findsOneWidget);
      expect(find.text('rollover pending'), findsNothing);
    });

    testWidgets('PM tanpa nomor HP: keterangan netral, bukan kalimat galat', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: VmsTheme.light,
          home: const Scaffold(body: ContactRow(label: 'PM', name: 'Budi')),
        ),
      );
      expect(find.textContaining('nomor HP belum tercatat'), findsOneWidget);
      expect(find.textContaining('belum ada nomor HP'), findsNothing);
    });

    // Item progres: dibuka dari layar jadwal, seperti di aplikasi.
    Map<String, dynamic> itemRow({String status = 'IN_PROGRESS', num saved = 4}) => {
      'item_id': 'i1',
      'title': 'Tiang A',
      'work_type_id': 'wt1',
      'work_type_name': 'Galian',
      'task_phase': 'INSTALLATION',
      'target_qty': 10,
      'completed_qty': saved,
      'status': status,
      'realization_photos_json': <Object>[],
      'notes': null,
    };

    Future<void> openItem(WidgetTester tester, {num saved = 4}) async {
      backend.routes['/work-plans/items/i1'] = (_) => itemRow(saved: saved);
      backend.routes['/by-work-type/wt1'] = (_) => <Object>[];
      await show(
        tester,
        Scaffold(
          body: Builder(
            builder: (ctx) => TextButton(
              onPressed: () => Navigator.of(ctx).push(
                MaterialPageRoute(
                  builder: (_) => const ItemProgressScreen(itemId: 'i1', dayStatus: 'ONGOING', isLeader: true),
                ),
              ),
              child: const Text('buka item'),
            ),
          ),
        ),
      );
      await tester.tap(find.text('buka item'));
      await settle(tester);
    }

    Future<void> tapPlus(WidgetTester tester, int times) async {
      for (var i = 0; i < times; i++) {
        await tester.tap(find.byIcon(Icons.add_rounded));
        await tester.pump();
      }
    }

    testWidgets('draf belum disimpan tidak mengubah status menjadi Selesai', (tester) async {
      await openItem(tester);
      expect(find.text('Selesai'), findsNothing);

      await tapPlus(tester, 6); // 4 tersimpan -> 10 (target), tetapi belum disimpan
      expect(find.textContaining('Belum disimpan'), findsOneWidget);
      expect(find.text('Selesai'), findsNothing);
    });

    testWidgets('setelah Simpan sukses: toast Tersimpan lalu kembali ke jadwal', (tester) async {
      backend.routes['/progress'] = (_) => <String, dynamic>{};
      await openItem(tester);

      await tapPlus(tester, 6);
      await tester.tap(find.text('Simpan hasil kerja'));
      await settle(tester);
      expect(find.text('Tersimpan'), findsOneWidget);
      expect(find.text('Kerjakan pekerjaan'), findsNothing);
      expect(find.text('buka item'), findsOneWidget);
    });

    testWidgets('galat simpan tampil di atas tombol, bukan sebagai toast yang menutupinya', (tester) async {
      backend.routes['/progress'] = (o) =>
          throw httpError(o, 422, {'error': {'code': 'BAD_QTY', 'message': 'Galat uji simpan'}});
      await openItem(tester);

      await tapPlus(tester, 6);
      await tester.tap(find.text('Simpan hasil kerja'));
      await settle(tester);
      expect(find.text('Galat uji simpan'), findsOneWidget);
      expect(find.byType(SnackBar), findsNothing);
      expect(find.text('Simpan hasil kerja'), findsOneWidget);
      expect(find.text('Kerjakan pekerjaan'), findsOneWidget);
    });
  });
}
