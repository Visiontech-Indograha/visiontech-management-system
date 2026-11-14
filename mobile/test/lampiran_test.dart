import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/core/providers.dart';
import 'package:vms_mobile/data/app_database.dart';
import 'package:vms_mobile/data/sync_engine.dart';
import 'package:vms_mobile/features/attachments/attachments_sheet.dart';
import 'package:vms_mobile/features/records/my_records_screens.dart';

import 'support/fake_backend.dart';

Map<String, dynamic> _item(String id, {bool mine = true}) => {
  'file_id': id,
  'file_name': 'bukti-$id.pdf',
  'mime_type': 'application/pdf',
  'byte_size': 2048,
  'mine': mine,
  'created_at': '2026-11-03T01:00:00Z',
};

DioException galat409(String code) => DioException(
  requestOptions: RequestOptions(path: '/x'),
  response: Response(
    requestOptions: RequestOptions(path: '/x'),
    statusCode: 409,
    data: {'error': {'code': code, 'message': 'x'}},
  ),
);

void main() {
  test('terkunci menurut status pengajuan', () {
    expect(LampiranJenis.lembur.terkunci('PENDING_PM'), isFalse);
    expect(LampiranJenis.lembur.terkunci('APPROVED'), isTrue);
    expect(LampiranJenis.mess.terkunci('REQUESTED'), isFalse);
    expect(LampiranJenis.mess.terkunci('CANCELLED'), isTrue);
  });

  test('aturan tambah dan hapus', () {
    expect(bisaTambahLampiran(4, terkunci: false), isTrue);
    expect(bisaTambahLampiran(maxLampiran, terkunci: false), isFalse);
    expect(bisaTambahLampiran(0, terkunci: true), isFalse);
    expect(bisaHapusLampiran(_item('a'), terkunci: false), isTrue);
    expect(bisaHapusLampiran(_item('a', mine: false), terkunci: false), isFalse);
    expect(bisaHapusLampiran(_item('a'), terkunci: true), isFalse);
  });

  test('pesan galat 409 awam', () {
    expect(pesanLampiran(galat409('LAMPIRAN_PENUH')), contains('5 berkas'));
    expect(pesanLampiran(galat409('LAMPIRAN_TERKUNCI')), contains('tidak bisa diubah'));
    expect(ukuranLampiran(2048), '2 KB');
  });

  group('lembar lampiran', () {
    late AppDatabase db;
    late FakeBackend backend;
    late SyncEngine engine;
    late List<Map<String, dynamic>> data;
    late Directory dir;

    setUp(() {
      db = memoryDb();
      backend = FakeBackend();
      engine = engineWith(db, backend);
      data = [_item('f1'), _item('f2', mine: false)];
      dir = Directory.systemTemp.createTempSync('lampiran-uji');
      backend.routes['/overtime/ot1/attachments'] = (o) {
        if (o.method == 'POST') data.add(_item((o.data as Map)['file_id'] as String));
        return data;
      };
      backend.routes['/files/upload'] = (_) => {'file_id': 'f9', 'message': 'ok'};
      backend.routes['/overtime/ot1/attachments/f1'] = (_) {
        data.removeWhere((e) => e['file_id'] == 'f1');
        return data;
      };
    });

    tearDown(() async {
      documentPickOverride = null;
      if (dir.existsSync()) dir.deleteSync(recursive: true);
      await db.close();
    });

    Future<void> settle(WidgetTester t) async {
      for (var i = 0; i < 15; i++) {
        await t.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 50)));
        await t.pump(const Duration(milliseconds: 50));
      }
    }

    Future<void> show(WidgetTester t, String status) async {
      await t.runAsync(() async {
        await t.pumpWidget(
          ProviderScope(
            overrides: [syncEngineProvider.overrideWithValue(engine)],
            child: MaterialApp(
              home: Scaffold(body: LampiranSheet(jenis: LampiranJenis.lembur, id: 'ot1', status: status)),
            ),
          ),
        );
      });
      await settle(t);
    }

    testWidgets('daftar tampil; hapus hanya untuk milik sendiri; tambah dan hapus berjalan', (t) async {
      await show(t, 'PENDING_PM');
      expect(find.text('bukti-f1.pdf'), findsOneWidget);
      expect(find.byKey(const Key('lampiran-hapus-f1')), findsOneWidget);
      expect(find.byKey(const Key('lampiran-hapus-f2')), findsNothing);

      final f = File('${dir.path}/baru.pdf')..writeAsBytesSync([1, 2, 3]);
      documentPickOverride = (_) async => (path: f.path, name: 'baru.pdf');
      await t.tap(find.byKey(const Key('lampiran-berkas')));
      await settle(t);
      expect(find.text('bukti-f9.pdf'), findsOneWidget);

      await t.tap(find.byKey(const Key('lampiran-hapus-f1')));
      await t.pumpAndSettle();
      await t.tap(find.text('Hapus'));
      await settle(t);
      expect(find.text('bukti-f1.pdf'), findsNothing);
    });

    testWidgets('terkunci: tombol tambah dan hapus tersembunyi', (t) async {
      await show(t, 'APPROVED');
      expect(find.byKey(const Key('lampiran-terkunci')), findsOneWidget);
      expect(find.byKey(const Key('lampiran-berkas')), findsNothing);
      expect(find.byKey(const Key('lampiran-hapus-f1')), findsNothing);
    });

    testWidgets('kosong: pesan ramah', (t) async {
      data.clear();
      await show(t, 'PENDING_PM');
      expect(find.byKey(const Key('lampiran-kosong')), findsOneWidget);
    });

    testWidgets('galat server: pesan dan tombol coba lagi', (t) async {
      backend.routes.remove('/overtime/ot1/attachments');
      backend.routes['/overtime/ot1/attachments'] = (_) => throw galat409('LAMPIRAN_PENUH');
      await show(t, 'PENDING_PM');
      expect(find.text('Coba lagi'), findsOneWidget);
    });
  });
}
