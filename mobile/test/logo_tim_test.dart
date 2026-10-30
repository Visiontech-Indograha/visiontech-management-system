import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:vms_mobile/core/team_logo.dart';
import 'package:vms_mobile/features/auth/auth_controller.dart';
import 'package:vms_mobile/features/auth/auth_state.dart';
import 'package:vms_mobile/features/gallery/photo_gallery_screen.dart';
import 'package:vms_mobile/features/gallery/team_logo_screen.dart';

import 'support/fake_backend.dart';

/// Logo tim: validasi klien (format/ukuran/dimensi), cache perangkat, layanan
/// (unduh/unggah/hapus lewat FakeBackend), dan layar pengaturan untuk ketua vs anggota.

const _teamId = 't1';

class _SignedIn extends AuthController {
  _SignedIn(this.employeeId);
  final String employeeId;

  @override
  AuthState build() => AuthAuthenticated(
    AuthUser(
      id: 'u1',
      username: 'teknisi@contoh.test',
      role: UserRole.leader,
      employeeId: employeeId,
    ),
  );
}

Uint8List _png(int w, int h) =>
    Uint8List.fromList(img.encodePng(img.Image(width: w, height: h)));

Uint8List _bytesFromRoute(RequestOptions o) => _png(100, 64);

int _countRequests(FakeBackend b, String method, String suffix) => b.requests
    .where((r) => r.method == method && r.path.endsWith(suffix))
    .length;

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late Directory dir;
  late TeamLogoStore store;

  setUp(() {
    dir = Directory.systemTemp.createTempSync('logo-tim-test');
    store = TeamLogoStore(dirFactory: () async => dir);
  });

  tearDown(() {
    teamLogoPickOverride = null;
    if (dir.existsSync()) dir.deleteSync(recursive: true);
  });

  group('Validasi logo (klien)', () {
    test('format selain PNG/JPEG/WebP ditolak', () async {
      final gif = Uint8List.fromList('GIF89a........'.codeUnits);
      expect(await validateTeamLogo(gif), 'Format gambar harus PNG, JPEG, atau WebP.');
    });

    test('lebih dari 2 MB ditolak', () async {
      final big = Uint8List(teamLogoMaxBytes + 1)
        ..setAll(0, [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]);
      expect(await validateTeamLogo(big), 'Ukuran gambar maksimal 2 MB.');
    });

    test('sisi kurang dari 64 px ditolak dengan ukuran saat ini', () async {
      expect(
        await validateTeamLogo(_png(32, 32)),
        'Ukuran gambar harus 64–4000 px per sisi (saat ini 32×32 px).',
      );
    });

    test('sisi lebih dari 4000 px ditolak', () async {
      expect(
        await validateTeamLogo(_png(4001, 100)),
        'Ukuran gambar harus 64–4000 px per sisi (saat ini 4001×100 px).',
      );
    });

    test('persegi, lebar, dan JPEG yang valid diterima (rasio asli tidak diubah validasi)', () async {
      expect(await validateTeamLogo(_png(64, 64)), isNull);
      expect(await validateTeamLogo(_png(300, 80)), isNull);
      final jpg = Uint8List.fromList(img.encodeJpg(img.Image(width: 128, height: 128)));
      expect(await validateTeamLogo(jpg), isNull);
    });

    test('berkas ber-header WebP tetapi rusak → pesan tidak dapat dibaca', () async {
      final bogus = Uint8List(64)
        ..setAll(0, 'RIFF'.codeUnits)
        ..setAll(8, 'WEBP'.codeUnits);
      expect(await validateTeamLogo(bogus), 'Berkas tidak dapat dibaca sebagai gambar.');
    });
  });

  group('Penyimpanan logo di perangkat', () {
    test('tulis lalu baca: versi & bytes sama; hapus → kosong', () async {
      final bytes = _png(64, 64);
      await store.write(_teamId, 'L1', bytes);
      final read = await store.read(_teamId);
      expect(read?.version, 'L1');
      expect(read?.bytes, bytes);

      await store.clear(_teamId);
      expect(await store.read(_teamId), isNull);
    });
  });

  group('Layanan logo tim', () {
    test('unduh sekali lalu pakai cache selama versi (logo_file_id) belum berubah', () async {
      final backend = FakeBackend()
        ..routes['/teams/$_teamId'] = ((o) => ({'team_id': _teamId, 'logo_file_id': 'L1'}))
        ..routes['/teams/$_teamId/logo'] = _bytesFromRoute;
      final service = TeamLogoService(api: engineWith(memoryDb(), backend).api, store: store);

      final first = await service.resolve(_teamId);
      expect(first, isNotNull);
      final second = await service.resolve(_teamId);
      expect(second, first);
      expect(_countRequests(backend, 'GET', '/teams/$_teamId/logo'), 1);
    });

    test('versi logo berubah di server → unduh ulang', () async {
      var version = 'L1';
      final backend = FakeBackend()
        ..routes['/teams/$_teamId'] = ((o) => ({'team_id': _teamId, 'logo_file_id': version}))
        ..routes['/teams/$_teamId/logo'] = _bytesFromRoute;
      final service = TeamLogoService(api: engineWith(memoryDb(), backend).api, store: store);

      await service.resolve(_teamId);
      version = 'L2';
      await service.resolve(_teamId);
      expect(_countRequests(backend, 'GET', '/teams/$_teamId/logo'), 2);
      expect((await store.read(_teamId))?.version, 'L2');
    });

    test('tim tanpa logo → null dan cache lama dihapus', () async {
      await store.write(_teamId, 'L0', _png(64, 64));
      final backend = FakeBackend()
        ..routes['/teams/$_teamId'] = ((o) => ({'team_id': _teamId, 'logo_file_id': null}));
      final service = TeamLogoService(api: engineWith(memoryDb(), backend).api, store: store);

      expect(await service.resolve(_teamId), isNull);
      expect(await store.read(_teamId), isNull);
    });

    test('luring: tetap memakai cache terakhir', () async {
      final cached = _png(64, 64);
      await store.write(_teamId, 'L1', cached);
      final backend = FakeBackend(); // tanpa rute = sinyal putus
      final service = TeamLogoService(api: engineWith(memoryDb(), backend).api, store: store);

      expect(await service.resolve(_teamId), cached);
    });

    test('anggota tanpa izin lihat tim (403 pada detail) tetap mengambil logo langsung', () async {
      final backend = FakeBackend()
        ..routes['/teams/$_teamId'] = ((o) => throw httpError(o, 403, {'detail': 'x'}))
        ..routes['/teams/$_teamId/logo'] = _bytesFromRoute;
      final service = TeamLogoService(api: engineWith(memoryDb(), backend).api, store: store);

      expect(await service.resolve(_teamId), isNotNull);
    });

    test('unggah: PUT multipart lalu cache memakai logo_file_id baru', () async {
      final backend = FakeBackend()
        ..routes['/teams/$_teamId/logo'] = ((o) => ({
          'team_id': _teamId,
          'logo_file_id': 'L9',
          'logo_url': '/api/v1/teams/$_teamId/logo',
        }));
      final service = TeamLogoService(api: engineWith(memoryDb(), backend).api, store: store);
      final bytes = _png(100, 64);

      await service.upload(_teamId, bytes, 'logo.png');
      final put = backend.requests.singleWhere((r) => r.method == 'PUT');
      expect(put.data, isA<FormData>());
      expect((await store.read(_teamId))?.version, 'L9');
      expect((await store.read(_teamId))?.bytes, bytes);
    });

    test('hapus: DELETE lalu cache dikosongkan', () async {
      await store.write(_teamId, 'L1', _png(64, 64));
      final backend = FakeBackend()..routes['/teams/$_teamId/logo'] = (o) => null;
      final service = TeamLogoService(api: engineWith(memoryDb(), backend).api, store: store);

      await service.remove(_teamId);
      expect(_countRequests(backend, 'DELETE', '/teams/$_teamId/logo'), 1);
      expect(await store.read(_teamId), isNull);
    });
  });

  group('Pengaturan logo tim (layar)', () {
    // I/O nyata (berkas cache, Dio palsu, decode gambar) butuh waktu nyata; pumpAndSettle bisa
    // tak pernah selesai selama indikator muat berputar, jadi cukup pompa beberapa kali.
    Future<void> settle(WidgetTester tester) async {
      for (var i = 0; i < 20; i++) {
        await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 40)));
        await tester.pump(const Duration(milliseconds: 40));
      }
    }

    Future<FakeBackend> pumpTeamLogo(
      WidgetTester tester, {
      required String userEmployeeId,
      required FakeBackend backend,
      Widget? home,
    }) async {
      final service = TeamLogoService(
        api: engineWith(memoryDb(), backend).api,
        store: store,
      );
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider.overrideWith(() => _SignedIn(userEmployeeId)),
            myTeamProvider.overrideWith(
              (ref) async => const MyTeam(
                teamId: _teamId,
                teamName: 'MEP',
                leaderEmployeeId: 'e9',
              ),
            ),
            teamLogoServiceProvider.overrideWithValue(service),
          ],
          child: MaterialApp(home: home ?? const TeamLogoScreen()),
        ),
      );
      await settle(tester);
      return backend;
    }

    FakeBackend leaderBackend({String? logoFileId}) => FakeBackend()
      ..routes['/teams/$_teamId'] = ((o) => ({'team_id': _teamId, 'logo_file_id': logoFileId}));

    testWidgets('anggota hanya melihat: tidak ada tombol ganti/hapus', (tester) async {
      await pumpTeamLogo(tester, userEmployeeId: 'e1', backend: leaderBackend());
      expect(find.byKey(const Key('team-logo-readonly')), findsOneWidget);
      expect(find.byKey(const Key('team-logo-pick-gallery')), findsNothing);
      expect(find.byKey(const Key('team-logo-pick-camera')), findsNothing);
    });

    testWidgets('ketua: gambar terlalu kecil ditolak, tidak diunggah', (tester) async {
      final backend = leaderBackend();
      await pumpTeamLogo(tester, userEmployeeId: 'e9', backend: backend);
      teamLogoPickOverride = (_) async => ('kecil.png', _png(32, 32));

      await tester.tap(find.byKey(const Key('team-logo-pick-gallery')));
      await settle(tester);

      expect(
        find.text('Ukuran gambar harus 64–4000 px per sisi (saat ini 32×32 px).'),
        findsOneWidget,
      );
      expect(find.byKey(const Key('team-logo-save')), findsNothing);
      expect(_countRequests(backend, 'PUT', '/teams/$_teamId/logo'), 0);
    });

    testWidgets('ketua: pilih gambar valid → simpan → unggah dan pesan sukses', (tester) async {
      final backend = leaderBackend()
        ..routes['/teams/$_teamId/logo'] = ((o) => ({
          'team_id': _teamId,
          'logo_file_id': 'L2',
          'logo_url': '/x',
        }));
      await pumpTeamLogo(tester, userEmployeeId: 'e9', backend: backend);
      teamLogoPickOverride = (_) async => ('logo.png', _png(300, 80));

      await tester.tap(find.byKey(const Key('team-logo-pick-gallery')));
      await settle(tester);
      expect(find.byKey(const Key('team-logo-save')), findsOneWidget);

      await tester.tap(find.byKey(const Key('team-logo-save')));
      await settle(tester);

      expect(_countRequests(backend, 'PUT', '/teams/$_teamId/logo'), 1);
      expect(find.text('Logo tim disimpan.'), findsOneWidget);
    });

    testWidgets('ketua: 403 saat unggah → pesan hanya ketua yang boleh', (tester) async {
      final backend = leaderBackend()
        ..routes['/teams/$_teamId/logo'] = (o) => throw httpError(o, 403, {'detail': 'x'});
      await pumpTeamLogo(tester, userEmployeeId: 'e9', backend: backend);
      teamLogoPickOverride = (_) async => ('logo.png', _png(100, 64));

      await tester.tap(find.byKey(const Key('team-logo-pick-gallery')));
      await settle(tester);
      await tester.tap(find.byKey(const Key('team-logo-save')));
      await settle(tester);

      expect(find.text('Hanya ketua tim yang dapat mengganti logo'), findsOneWidget);
    });

    testWidgets('ketua: hapus logo → DELETE dan kembali ke default', (tester) async {
      final backend = leaderBackend(logoFileId: 'L1')
        ..routes['/teams/$_teamId/logo'] = (o) =>
            o.method == 'DELETE' ? null : _bytesFromRoute(o);
      await pumpTeamLogo(tester, userEmployeeId: 'e9', backend: backend);

      await tester.tap(find.byKey(const Key('team-logo-delete')));
      await settle(tester);
      await tester.tap(find.byKey(const Key('team-logo-delete-confirm')));
      await settle(tester);

      expect(_countRequests(backend, 'DELETE', '/teams/$_teamId/logo'), 1);
      expect(find.text('Logo tim dihapus.'), findsOneWidget);
    });

    testWidgets('galeri: tombol Logo tim membuka pengaturan logo', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider.overrideWith(() => _SignedIn('e1')),
            myTeamProvider.overrideWith((ref) async => null),
          ],
          child: const MaterialApp(home: PhotoGalleryScreen()),
        ),
      );
      await settle(tester);
      await tester.tap(find.byKey(const Key('gallery-team-logo')));
      await settle(tester);
      expect(find.byType(TeamLogoScreen), findsOneWidget);
      expect(
        find.text('Logo tim tersedia setelah Anda terdaftar di tim pada jadwal harian.'),
        findsOneWidget,
      );
    });
  });
}
