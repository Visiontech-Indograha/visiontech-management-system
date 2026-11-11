import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:vms_mobile/core/providers.dart';
import 'package:vms_mobile/data/app_database.dart';
import 'package:vms_mobile/data/sync_engine.dart';
import 'package:vms_mobile/features/plans/wo_survey_draft.dart';
import 'package:vms_mobile/features/plans/wo_survey_form_screen.dart';
import 'package:vms_mobile/features/plans/wo_team_surveys_section.dart';

import 'support/fake_backend.dart';

const _survey = {
  'work_order_id': 'wo-1',
  'wo_number': 'WO-001',
  'title': 'Pasang CCTV',
  'survey_date': '2026-11-12',
  'survey_status': 'DRAFT',
  'filled_points': 0,
};

WoSurveyDraft _valid() => WoSurveyDraft(
  narrative: 'Aman',
  points: [WoSurveyPoint(name: ' Pintu depan ', workTypeId: 'wt-1', lat: -6.2, lng: 106.8)],
);

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

  group('validasi sama dengan API', () {
    test('wajib titik, nama, jenis pekerjaan', () {
      expect(WoSurveyDraft().validate(), 'Tambah minimal satu titik survei.');
      expect(WoSurveyDraft(points: [WoSurveyPoint(workTypeId: 'x')]).validate(), contains('isi nama titik'));
      expect(WoSurveyDraft(points: [WoSurveyPoint(name: 'A')]).validate(), contains('pilih jenis pekerjaan'));
      expect(_valid().validate(), isNull);
    });

    test('batas panjang nama titik 150', () {
      final d = WoSurveyDraft(points: [WoSurveyPoint(name: 'a' * 151, workTypeId: 'x')]);
      expect(d.validate(), contains('terlalu panjang'));
      d.points.first.name = 'a' * 150;
      expect(d.validate(), isNull);
    });

    test('muatan sesuai bentuk API', () {
      final p = _valid().toPayload('wo-1');
      final pt = ((p['survey'] as Map)['points'] as List).single as Map;
      expect(p['work_order_id'], 'wo-1');
      expect(pt['point_name'], 'Pintu depan');
      expect(pt['recommended_work_type_id'], 'wt-1');
      expect(pt['site_lat'], -6.2);
      expect(pt.containsKey('local_files'), isFalse);
    });
  });

  group('antrean WO_SURVEY_SUBMIT', () {
    test('luring: tetap di antrean, foto diunggah per titik saat online, op terkirim', () async {
      final foto = File('${Directory.systemTemp.path}/vms_uji_wo_survey.jpg')..writeAsBytesSync([1, 2, 3]);
      addTearDown(foto.deleteSync);
      final d = _valid()..points.first.photoPaths.add(foto.path);

      expect(await engine.submit(OfflineOp.woSurveySubmit, d.toPayload('wo-1')), isFalse);
      expect(await engine.pendingOperationCount(), 1);
      expect(await engine.pendingPhotoCount(), 1);
      expect(await engine.pendingWoSurveyIds(), {'wo-1'});

      backend.routes['/files/upload'] = (_) => {'file_id': 'f-1'};
      backend.answerSync((_) => 'APPLIED');
      await engine.syncAll();

      final op = backend.sentOps.single;
      expect(op['op_type'], 'WO_SURVEY_SUBMIT');
      final pt = (((op['payload'] as Map)['survey'] as Map)['points'] as List).single as Map;
      expect(pt['evidence_file_ids'], ['f-1']);
      expect(pt.containsKey('local_files'), isFalse);
      expect(await engine.pendingOperationCount(), 0);
    });

    test('ditolak server: menjadi dead-letter dan terlihat', () async {
      backend.answerSync((_) => 'REJECTED', errorMessage: 'Survei sudah dikirim.');
      await expectLater(
        engine.submit(OfflineOp.woSurveySubmit, _valid().toPayload('wo-1')),
        throwsA(isA<SyncRejectedException>()),
      );
      expect(await engine.deadLetterCount(), 1);
    });
  });

  group('layar', () {
    Future<void> pump(WidgetTester t, Widget home) async {
      await t.runAsync(() async {
        await t.pumpWidget(
          ProviderScope(
            overrides: [syncEngineProvider.overrideWithValue(engine)],
            child: MaterialApp(home: home),
          ),
        );
        await Future<void>.delayed(const Duration(milliseconds: 100));
      });
      await t.pump(const Duration(milliseconds: 100));
    }

    testWidgets('kirim tanpa titik menampilkan pesan awam, tidak ada yang diantrekan', (t) async {
      await pump(t, const WoSurveyFormScreen(survey: _survey));
      await t.tap(find.text('Kirim survei'));
      await t.pump();
      expect(find.text('Tambah minimal satu titik survei.'), findsOneWidget);
      await t.runAsync(() async => expect(await engine.pendingOperationCount(), 0));
    });

    testWidgets('tombol utama berukuran minimal 48 dp', (t) async {
      await pump(t, const WoSurveyFormScreen(survey: _survey));
      expect(t.getSize(find.ancestor(of: find.text('Tambah titik'), matching: find.byType(SizedBox)).first).height, greaterThanOrEqualTo(48));
      await t.tap(find.text('Tambah titik'));
      await t.pump();
      await t.scrollUntilVisible(find.text('Foto'), 200, scrollable: find.byType(Scrollable).first);
      expect(t.getSize(find.ancestor(of: find.text('Foto'), matching: find.byType(SizedBox)).first).height, greaterThanOrEqualTo(48));
    });

    testWidgets('survei yang sudah masuk antrean tidak tampil lagi sebagai menunggu', (t) async {
      backend.routes['/work-orders/team-surveys'] = (_) => [_survey];
      await t.runAsync(() => engine.submit(OfflineOp.woSurveySubmit, _valid().toPayload('wo-1')));
      await pump(t, const Scaffold(body: SingleChildScrollView(child: WoTeamSurveysSection())));
      expect(find.text('WO-001 · Pasang CCTV'), findsNothing);
      expect(find.text('Belum ada survei untuk tim Anda'), findsOneWidget);
    });
  });
}
