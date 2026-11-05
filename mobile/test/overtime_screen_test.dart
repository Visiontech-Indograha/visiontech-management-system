import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:vms_mobile/core/providers.dart';
import 'package:vms_mobile/data/sync_engine.dart';
import 'package:vms_mobile/data/vms_api.dart';
import 'package:vms_mobile/features/overtime/overtime_screen.dart';

Map<String, dynamic> _lembur({
  String id = 'ot1',
  String status = 'PENDING_PM',
  bool canReview = false,
  String nama = 'Budi Uji',
}) => {
  'id': id,
  'daily_plan_id': 'plan1',
  'employee_id': 'emp-$id',
  'employee_name': nama,
  'work_date': '2026-11-03',
  'hours': 2,
  'reason': 'Menyelesaikan pemasangan kabel',
  'status': status,
  'review_note': null,
  'can_review': canReview,
};

class _FakeApi implements VmsApi {
  List<Map<String, dynamic>> items = [];
  DioException? muatError;
  DioException? reviewError;
  final List<Map<String, dynamic>> reviews = [];

  @override
  Future<List<Map<String, dynamic>>> myOvertime() async {
    if (muatError != null) throw muatError!;
    return items;
  }

  @override
  Future<Map<String, dynamic>> reviewOvertime({
    required String id,
    required String decision,
    String? note,
  }) async {
    if (reviewError != null) throw reviewError!;
    reviews.add({'id': id, 'decision': decision, 'note': note});
    return {'id': id, 'status': decision, 'review_note': note};
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeSync implements SyncEngine {
  _FakeSync(this._fake);
  final _FakeApi _fake;

  @override
  VmsApi get api => _fake;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

DioException _offline() => DioException(
  requestOptions: RequestOptions(path: '/api/v1/overtime'),
  type: DioExceptionType.connectionError,
  error: 'tidak ada sinyal',
);

Future<void> _pump(WidgetTester tester, _FakeApi fake) async {
  final container = ProviderContainer(overrides: [
    syncEngineProvider.overrideWithValue(_FakeSync(fake)),
  ]);
  addTearDown(container.dispose);
  await tester.pumpWidget(UncontrolledProviderScope(
    container: container,
    child: const MaterialApp(home: OvertimeScreen()),
  ));
  await tester.pumpAndSettle();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() => initializeDateFormatting('id_ID'));

  test('label status lembur, termasuk status menunggu dari API (PENDING_PM)', () {
    expect(overtimeStatusLabel('PENDING_PM'), 'Menunggu persetujuan');
    expect(overtimeStatusLabel('PENDING'), 'Menunggu persetujuan');
    expect(overtimeStatusLabel('APPROVED'), 'Disetujui');
    expect(overtimeStatusLabel('REJECTED'), 'Ditolak');
    expect(overtimeStatusLabel('ASING'), 'Status belum diketahui');
  });

  testWidgets('kosong: tampil kalimat arahan tanpa daftar', (tester) async {
    await _pump(tester, _FakeApi());
    expect(find.text('Belum ada lembur'), findsOneWidget);
    expect(find.textContaining('Ajukan lembur dari tab Jadwal kerja'), findsOneWidget);
  });

  testWidgets('galat tanpa data: tampil pesan dan tombol Coba lagi', (tester) async {
    final fake = _FakeApi()
      ..muatError = DioException(
        requestOptions: RequestOptions(path: '/api/v1/overtime'),
        type: DioExceptionType.connectionError,
      );
    await _pump(tester, fake);
    expect(find.textContaining('Tidak ada koneksi ke server'), findsOneWidget);
    expect(find.text('Coba lagi'), findsOneWidget);
  });

  testWidgets('pengaju melihat status sendiri tanpa tombol persetujuan', (tester) async {
    final fake = _FakeApi()..items = [_lembur()];
    await _pump(tester, fake);
    expect(find.text('Menunggu persetujuan'), findsOneWidget);
    expect(find.text('Setujui'), findsNothing);
    expect(find.text('Tolak'), findsNothing);
  });

  testWidgets('atasan menyetujui pengajuan tim lewat dialog konfirmasi', (tester) async {
    final fake = _FakeApi()..items = [_lembur(canReview: true)];
    await _pump(tester, fake);

    await tester.tap(find.text('Setujui'));
    await tester.pumpAndSettle();
    final dialog = find.byType(AlertDialog);
    expect(dialog, findsOneWidget);
    await tester.enterText(find.descendant(of: dialog, matching: find.byType(TextField)), 'Sesuai rencana');
    await tester.tap(find.descendant(of: dialog, matching: find.text('Setujui')));
    await tester.pumpAndSettle();

    expect(fake.reviews, [
      {'id': 'ot1', 'decision': 'APPROVED', 'note': 'Sesuai rencana'},
    ]);
    expect(find.text('Disetujui'), findsOneWidget);
    expect(find.text('Setujui'), findsNothing);
  });

  testWidgets('tolak tanpa catatan mengirim REJECTED tanpa note', (tester) async {
    final fake = _FakeApi()..items = [_lembur(canReview: true)];
    await _pump(tester, fake);

    await tester.tap(find.text('Tolak'));
    await tester.pumpAndSettle();
    await tester.tap(find.descendant(of: find.byType(AlertDialog), matching: find.text('Tolak')));
    await tester.pumpAndSettle();

    expect(fake.reviews.single, {'id': 'ot1', 'decision': 'REJECTED', 'note': null});
    expect(find.text('Ditolak'), findsOneWidget);
  });

  testWidgets('batal di dialog tidak mengirim keputusan', (tester) async {
    final fake = _FakeApi()..items = [_lembur(canReview: true)];
    await _pump(tester, fake);

    await tester.tap(find.text('Setujui'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Batal'));
    await tester.pumpAndSettle();

    expect(fake.reviews, isEmpty);
    expect(find.text('Setujui'), findsOneWidget);
  });

  testWidgets('offline saat memutuskan: pesan jelas, daftar tetap tampil', (tester) async {
    final fake = _FakeApi()
      ..items = [_lembur(canReview: true)]
      ..reviewError = _offline();
    await _pump(tester, fake);

    await tester.tap(find.text('Setujui'));
    await tester.pumpAndSettle();
    await tester.tap(find.descendant(of: find.byType(AlertDialog), matching: find.text('Setujui')));
    await tester.pumpAndSettle();

    expect(
      find.textContaining('Persetujuan lembur hanya bisa dikirim saat HP terhubung ke internet'),
      findsOneWidget,
    );
    expect(find.text('Menunggu persetujuan'), findsOneWidget);
    expect(find.text('Setujui'), findsOneWidget);
  });
}
