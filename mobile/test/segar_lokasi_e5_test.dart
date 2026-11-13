import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:geolocator_platform_interface/geolocator_platform_interface.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:vms_mobile/core/providers.dart';
import 'package:vms_mobile/data/app_database.dart';
import 'package:vms_mobile/data/sync_engine.dart';
import 'package:vms_mobile/features/plans/wo_survey_form_screen.dart';
import 'package:vms_mobile/features/plans/wo_team_surveys_section.dart';
import 'package:vms_mobile/shared/ui/vms_ui.dart';

import 'support/fake_backend.dart';

Map<String, dynamic> _s(String wo) => {
  'work_order_id': wo,
  'wo_number': wo,
  'title': 'Pasang CCTV',
  'survey_date': '2026-11-13',
  'survey_status': 'DRAFT',
  'filled_points': 0,
};

class _MockGps extends GeolocatorPlatform {
  @override
  Future<bool> isLocationServiceEnabled() async => true;
  @override
  Future<LocationPermission> checkPermission() async => LocationPermission.whileInUse;
  @override
  Future<LocationPermission> requestPermission() async => LocationPermission.whileInUse;
  @override
  Future<Position> getCurrentPosition({LocationSettings? locationSettings}) async => Position(
    latitude: -6.2, longitude: 106.8, timestamp: DateTime(2026, 11, 13, 8), accuracy: 8,
    altitude: 0, altitudeAccuracy: 0, heading: 0, headingAccuracy: 0, speed: 0, speedAccuracy: 0,
    isMocked: true,
  );
}

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

  Future<ProviderContainer> pump(WidgetTester t, Widget home) async {
    late ProviderContainer c;
    await t.runAsync(() async {
      await t.pumpWidget(ProviderScope(
        overrides: [syncEngineProvider.overrideWithValue(engine)],
        child: Builder(builder: (ctx) {
          c = ProviderScope.containerOf(ctx);
          return MaterialApp(home: home);
        }),
      ));
      await Future<void>.delayed(const Duration(milliseconds: 100));
    });
    await t.pump(const Duration(milliseconds: 100));
    return c;
  }

  testWidgets('E5-1: survei baru dari PM tampil saat ada sinyal sinkron, tanpa mulai ulang', (t) async {
    backend.routes['/work-orders/team-surveys'] = (_) => <Map<String, dynamic>>[];
    final c = await pump(t, const Scaffold(body: SingleChildScrollView(child: WoTeamSurveysSection())));
    expect(find.text('Belum ada survei untuk tim Anda'), findsOneWidget);

    backend.routes['/work-orders/team-surveys'] = (_) => [_s('WO-009')];
    await t.runAsync(() async {
      c.read(syncTickProvider.notifier).bump();
      await Future<void>.delayed(const Duration(milliseconds: 200));
    });
    await t.pump(const Duration(milliseconds: 100));
    expect(find.text('WO-009 · Pasang CCTV'), findsOneWidget);
  });

  testWidgets('E5-1: tarik-segarkan (reloadToken naik) memuat ulang daftar survei', (t) async {
    backend.routes['/work-orders/team-surveys'] = (_) => <Map<String, dynamic>>[];
    Widget host(int n) => MaterialApp(
      home: Scaffold(body: SingleChildScrollView(child: WoTeamSurveysSection(reloadToken: n))),
    );
    await t.runAsync(() async {
      await t.pumpWidget(ProviderScope(overrides: [syncEngineProvider.overrideWithValue(engine)], child: host(0)));
      await Future<void>.delayed(const Duration(milliseconds: 100));
    });
    await t.pump(const Duration(milliseconds: 100));
    backend.routes['/work-orders/team-surveys'] = (_) => [_s('WO-010')];
    await t.runAsync(() async {
      await t.pumpWidget(ProviderScope(overrides: [syncEngineProvider.overrideWithValue(engine)], child: host(1)));
      await Future<void>.delayed(const Duration(milliseconds: 200));
    });
    await t.pump(const Duration(milliseconds: 100));
    expect(find.text('WO-010 · Pasang CCTV'), findsOneWidget);
  });

  testWidgets('E5-7: titik survei menolak lokasi palsu seperti absen', (t) async {
    GeolocatorPlatform.instance = _MockGps();
    addTearDown(() => GeolocatorPlatform.instance = _MockGps());
    await pump(t, WoSurveyFormScreen(survey: _s('WO-001')));
    await t.tap(find.text('Tambah titik'));
    await t.pump();
    await t.ensureVisible(find.text('Pakai lokasi saya sekarang'));
    await t.pump(const Duration(seconds: 1));
    await t.tap(find.text('Pakai lokasi saya sekarang'));
    await t.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 100)));
    await t.pump(const Duration(milliseconds: 100));
    expect(find.text('Lokasi palsu terdeteksi. Matikan aplikasi pemalsu lokasi.'), findsOneWidget);
    expect(find.text('Pakai lokasi saya sekarang'), findsOneWidget);
  });

  testWidgets('status Perlu ditinjau berbahasa Indonesia', (t) async {
    await t.pumpWidget(const MaterialApp(home: Scaffold(body: StatusPill('NEEDS_REVIEW'))));
    expect(find.text('Perlu ditinjau'), findsOneWidget);
  });
}
