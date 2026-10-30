import 'dart:io';

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
import 'package:vms_mobile/features/records/my_records_screens.dart';
import 'package:vms_mobile/shared/app_frame.dart';

import 'support/fake_backend.dart';

/// Dokumen pribadi: validasi berkas sama dengan API, ikon tipe berkas (bukan thumbnail kosong),
/// dan alur unggah (pilih jenis & berkas → progres → simpan → daftar menyegarkan).

class _SignedIn extends AuthController {
  @override
  AuthState build() => const AuthAuthenticated(
    AuthUser(
      id: 'u1',
      username: 'karyawan@contoh.test',
      role: UserRole.leader,
      employeeId: 'e1',
    ),
  );
}

Map<String, dynamic> _doc({
  required String id,
  required String type,
  String? fileId,
  String? mime,
  String? expiredAt,
}) => {
  'id': id,
  'employee_id': 'e1',
  'doc_type': type,
  'status': 'active',
  'active_at': '2026-01-01',
  'expired_at': expiredAt,
  'file_id': fileId,
  'file_mime': mime,
  'created_at': '2026-01-01T00:00:00Z',
};

void main() {
  late AppDatabase db;
  late FakeBackend backend;
  late SyncEngine engine;
  late List<Map<String, dynamic>> docs;
  late Directory dir;

  setUpAll(() => initializeDateFormatting('id_ID'));

  setUp(() {
    db = memoryDb();
    backend = FakeBackend();
    engine = engineWith(db, backend);
    docs = [_doc(id: 'd1', type: 'KTP', fileId: 'f-ktp', mime: 'application/pdf')];
    dir = Directory.systemTemp.createTempSync('dokumen-uji');
    backend.routes['/files/upload'] = (_) => {'file_id': 'f-baru', 'message': 'ok'};
    backend.routes['/employees/e1/documents'] = (o) {
      if (o.method == 'POST') {
        final body = Map<String, dynamic>.from(o.data as Map);
        docs.add(_doc(id: 'd2', type: body['doc_type'] as String, fileId: body['file_id'] as String,
            mime: 'application/pdf', expiredAt: body['expired_at'] as String?));
        return docs.last;
      }
      return {'items': docs, 'total': docs.length};
    };
  });

  tearDown(() async {
    documentPickOverride = null;
    if (dir.existsSync()) dir.deleteSync(recursive: true);
    await db.close();
  });

  Future<void> settle(WidgetTester tester) async {
    for (var i = 0; i < 30; i++) {
      await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 50)));
      await tester.pump(const Duration(milliseconds: 50));
      if (i >= 10 && find.byType(CircularProgressIndicator).evaluate().isEmpty) break;
    }
    await tester.pumpAndSettle();
  }

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
            builder: vmsAppFrame,
            home: screen,
          ),
        ),
      );
      await Future<void>.delayed(const Duration(milliseconds: 100));
    });
    await settle(tester);
  }

  File berkas(String name, int bytes) => File('${dir.path}/$name')..writeAsBytesSync(List.filled(bytes, 7));

  test('validasi berkas sama dengan API: jenis, ukuran, dan berkas kosong', () {
    expect(validateDocumentFile(name: 'ktp.PDF', bytes: 10), isNull);
    expect(validateDocumentFile(name: 'sim.docx', bytes: 10), isNull);
    expect(validateDocumentFile(name: 'foto.jpeg', bytes: 10), isNull);
    expect(validateDocumentFile(name: 'batas.png', bytes: documentUploadMaxBytes), isNull);
    expect(validateDocumentFile(name: 'skrip.exe', bytes: 10), contains('Jenis berkas tidak didukung'));
    expect(validateDocumentFile(name: 'tanpa_ekstensi', bytes: 10), contains('Jenis berkas tidak didukung'));
    expect(validateDocumentFile(name: 'besar.pdf', bytes: documentUploadMaxBytes + 1), contains('10 MB'));
    expect(validateDocumentFile(name: 'kosong.pdf', bytes: 0), contains('kosong'));
  });

  test('ikon dan label berkas menurut tipe MIME', () {
    expect(documentFileKind('application/pdf').label, 'PDF');
    expect(documentFileKind('application/vnd.openxmlformats-officedocument.wordprocessingml.document').label, 'DOCX');
    expect(documentFileKind('application/msword').label, 'DOC');
    expect(documentFileKind(null).label, 'Berkas');
  });

  testWidgets('dokumen PDF tampil sebagai ikon, tanpa meminta thumbnail yang tidak ada', (tester) async {
    await show(tester, const DocumentsScreen());
    expect(find.text('KTP'), findsWidgets);
    expect(find.text('PDF'), findsOneWidget);
    expect(find.byKey(const Key('dokumen-unggah')), findsOneWidget);
    expect(
      backend.requests.where((r) => r.queryParameters['variant'] == 'thumb'),
      isEmpty,
    );
  });

  testWidgets('unggah PDF: pilih jenis dan berkas, simpan, lalu daftar menyegarkan', (tester) async {
    documentPickOverride = (source) async {
      expect(source, DocumentPickSource.file);
      return (path: berkas('sim-a.pdf', 2048).path, name: 'sim-a.pdf');
    };
    await show(tester, const DocumentsScreen());
    expect(find.text('SIM A'), findsNothing);

    await tester.tap(find.byKey(const Key('dokumen-unggah')));
    await settle(tester);
    await tester.tap(find.byKey(const Key('dokumen-berkas-pilih')));
    await settle(tester);
    expect(find.byKey(const Key('dokumen-terpilih')), findsOneWidget);

    await tester.tap(find.text('Jenis dokumen'));
    await settle(tester);
    await tester.tap(find.text('SIM A').last);
    await settle(tester);

    await tester.tap(find.byKey(const Key('dokumen-simpan')));
    await settle(tester);

    final upload = backend.requests.where((r) => r.path.endsWith('/files/upload'));
    expect(upload, hasLength(1));
    final saved = backend.requests.where((r) => r.method == 'POST' && r.path.endsWith('/employees/e1/documents'));
    expect(saved, hasLength(1));
    expect(Map<String, dynamic>.from(saved.single.data as Map), {'doc_type': 'SIM_A', 'file_id': 'f-baru'});
    // Layar unggah tertutup dan daftar memuat ulang dokumen baru.
    expect(find.byKey(const Key('dokumen-simpan')), findsNothing);
    expect(find.text('SIM A'), findsOneWidget);
  });

  testWidgets('berkas tidak didukung ditolak di layar sebelum unggah, tombol simpan tetap nonaktif', (tester) async {
    documentPickOverride = (_) async => (path: berkas('skrip.exe', 10).path, name: 'skrip.exe');
    await show(tester, const DocumentUploadScreen());
    await tester.tap(find.byKey(const Key('dokumen-berkas-pilih')));
    await settle(tester);
    expect(find.textContaining('Jenis berkas tidak didukung'), findsOneWidget);
    expect(find.byKey(const Key('dokumen-terpilih')), findsNothing);
    expect(backend.requests.where((r) => r.path.endsWith('/files/upload')), isEmpty);
  });

  testWidgets('galat server tampil jelas dan layar tetap terbuka untuk dicoba lagi', (tester) async {
    backend.routes['/employees/e1/documents'] = (o) {
      throw httpError(o, 422, {'detail': 'Berkas belum diunggah atau sudah dihapus. Unggah ulang berkasnya.'});
    };
    documentPickOverride = (_) async => (path: berkas('ktp.png', 64).path, name: 'ktp.png');
    await show(tester, const DocumentUploadScreen());
    await tester.tap(find.byKey(const Key('dokumen-galeri')));
    await settle(tester);
    await tester.tap(find.text('Jenis dokumen'));
    await settle(tester);
    await tester.tap(find.text('KTP').last);
    await settle(tester);
    await tester.tap(find.byKey(const Key('dokumen-simpan')));
    await settle(tester);

    expect(find.byKey(const Key('dokumen-galat')), findsOneWidget);
    expect(find.text('Berkas belum diunggah atau sudah dihapus. Unggah ulang berkasnya.'), findsOneWidget);
    expect(find.byKey(const Key('dokumen-simpan')), findsOneWidget);
  });
}
