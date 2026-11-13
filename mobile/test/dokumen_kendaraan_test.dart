import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:vms_mobile/core/providers.dart';
import 'package:vms_mobile/data/sync_engine.dart';
import 'package:vms_mobile/data/vms_api.dart';
import 'package:vms_mobile/features/dokumen/dokumen_kendaraan.dart';
import 'package:vms_mobile/features/notifications/notifications_screen.dart';

final _hari = DateTime(2026, 11, 13);

Map<String, dynamic> _dok(String tipe, String exp) => {
  'doc_type_name': tipe,
  'vehicle_name': 'Hilux',
  'number_plate': 'BM 1 AB',
  'expired_on': exp,
};

class _Api implements VmsApi {
  _Api(this.items, {this.gagal = false});
  final List<Map<String, dynamic>> items;
  final bool gagal;
  @override
  Future<List<Map<String, dynamic>>> vehicleDocumentsMine() async {
    if (gagal) {
      throw DioException(
        requestOptions: RequestOptions(path: '/x'),
        type: DioExceptionType.badResponse,
        response: Response(requestOptions: RequestOptions(path: '/x'), statusCode: 500),
      );
    }
    return items;
  }

  @override
  dynamic noSuchMethod(Invocation i) => super.noSuchMethod(i);
}

class _Sync implements SyncEngine {
  _Sync(this.a);
  final _Api a;
  @override
  VmsApi get api => a;
  @override
  Future<({List<Map<String, dynamic>> items, DateTime? cachedAt})> fetchList(
    String key,
    Future<List<Map<String, dynamic>>> Function() fetch,
  ) async => (items: await fetch(), cachedAt: null);
  @override
  dynamic noSuchMethod(Invocation i) => super.noSuchMethod(i);
}

Future<void> _pump(WidgetTester t, _Api api, Widget home) async {
  await t.pumpWidget(ProviderScope(
    overrides: [syncEngineProvider.overrideWithValue(_Sync(api))],
    child: MaterialApp(home: Scaffold(body: home)),
  ));
  await t.pumpAndSettle();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() => initializeDateFormatting('id_ID'));

  test('label dan status berlaku', () {
    final s = dokumenSisaHari('2026-12-13', _hari);
    expect(s, 30);
    expect(dokumenLabelBerlaku('2026-12-13', s), 'Berlaku sampai 13 Des 2026 (30 hari lagi)');
    expect(dokumenStatus(31), DokumenStatus.aman);
    expect(dokumenStatus(30), DokumenStatus.segera);
    expect(dokumenStatus(-1), DokumenStatus.lewat);
    expect(dokumenLabelBerlaku('2026-11-10', -3), contains('Sudah lewat 3 hari'));
  });

  test('notifikasi dokumen menuju layar dokumen', () {
    expect(notificationRoute('document_expiry'), '/dokumen-kendaraan');
  });

  testWidgets('banner Beranda muncul bila <= 30 hari', (t) async {
    await _pump(t, _Api([_dok('SIM A', '2026-11-20'), _dok('STNK', '2027-06-01')]),
        DokumenPengingatBanner(hariIni: _hari));
    expect(find.textContaining('SIM A BM 1 AB habis dalam 7 hari'), findsOneWidget);
  });

  testWidgets('banner tersembunyi bila semua aman', (t) async {
    await _pump(t, _Api([_dok('STNK', '2027-06-01')]), DokumenPengingatBanner(hariIni: _hari));
    expect(find.byType(InkWell), findsNothing);
  });

  testWidgets('layar: daftar, kosong, galat', (t) async {
    await _pump(t, _Api([_dok('STNK', '2026-12-13')]), DokumenSayaScreen(hariIni: _hari));
    expect(find.text('Berlaku sampai 13 Des 2026 (30 hari lagi)'), findsOneWidget);
    expect(find.text('Segera habis'), findsOneWidget);

    await _pump(t, _Api([]), DokumenSayaScreen(hariIni: _hari));
    expect(find.text('Belum ada dokumen'), findsOneWidget);

    await _pump(t, _Api([], gagal: true), DokumenSayaScreen(hariIni: _hari));
    expect(find.text('Coba lagi'), findsOneWidget);
  });
}
