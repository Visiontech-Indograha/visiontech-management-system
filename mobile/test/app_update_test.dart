import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/core/app_update_channel.dart';
import 'package:vms_mobile/features/update/app_update_controller.dart';
import 'package:vms_mobile/features/update/app_update_service.dart';
import 'package:vms_mobile/features/update/update_ui.dart';

/// Pembaruan aplikasi (docs/32): gerbang wajib, pita opsional, tunda, galat tidak mengunci, pesan "sudah diperbarui".
class FakeUpdateService implements AppUpdateService {
  FakeUpdateService({this.build = 5, this.info, this.error});

  final int build;
  UpdateInfo? info;
  Exception? error;
  int checks = 0;

  @override
  Future<InstalledApp> installed() async => InstalledApp(
    versionName: '1.1.0',
    versionCode: build,
    abis: const ['arm64-v8a'],
    sdk: 36,
    model: 'Uji',
  );

  @override
  Future<UpdateInfo> check(InstalledApp app) async {
    checks++;
    if (error != null) throw error!;
    return info ??
        UpdateInfo(status: UpdateStatus.upToDate, currentBuild: build);
  }

  @override
  Future<void> cleanup(int installedBuild) async {}

  @override
  Future<bool> canInstall() async => true;

  @override
  Future<void> openInstallSettings() async {}

  @override
  Future<void> install(File apk) async {}

  @override
  Future<File> download(
    ReleaseDownload d, {
    void Function(double progress)? onProgress,
    CancelToken? cancelToken,
  }) async => File('uji.apk');
}

class FakePrefs implements UpdatePrefs {
  FakePrefs([Map<String, dynamic>? data]) : data = data ?? {};
  final Map<String, dynamic> data;

  @override
  Future<Map<String, dynamic>> read() async => Map.of(data);

  @override
  Future<void> write(Map<String, dynamic> d) async => data
    ..clear()
    ..addAll(d);
}

UpdateInfo release(UpdateStatus status) => UpdateInfo(
  status: status,
  currentBuild: 5,
  latestBuild: 6,
  latestVersion: '1.2.0',
  notes: const ['Perbaikan absensi'],
  download: const ReleaseDownload(
    abi: 'arm64-v8a',
    url: '/api/v1/app/android/files/vms-1.2.0-6-arm64-v8a.apk',
    sha256: 'aa',
    size: 25 * 1024 * 1024,
  ),
);

Widget host(FakeUpdateService service, FakePrefs prefs) => ProviderScope(
  overrides: [
    appUpdateEnabledProvider.overrideWithValue(true),
    appUpdateServiceProvider.overrideWithValue(service),
    updatePrefsProvider.overrideWithValue(prefs),
  ],
  child: MaterialApp(
    builder: (context, child) => AppUpdateGate(child: child!),
    home: const Scaffold(
      body: Text('ISI-APLIKASI'),
      bottomNavigationBar: UpdateAvailableBanner(),
    ),
  ),
);

void main() {
  testWidgets(
    'pembaruan wajib menutup aplikasi dengan layar "Pembaruan wajib"',
    (tester) async {
      await tester.pumpWidget(
        host(
          FakeUpdateService(info: release(UpdateStatus.required)),
          FakePrefs(),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('ISI-APLIKASI'), findsNothing);
      expect(find.text('Pembaruan wajib'), findsOneWidget);
      expect(find.textContaining('1.2.0 (build 6)'), findsWidgets);
      expect(find.text('Perbarui sekarang'), findsOneWidget);
    },
  );

  testWidgets(
    'pembaruan opsional: aplikasi terbuka + pita; "Nanti" menyembunyikan pita',
    (tester) async {
      final prefs = FakePrefs();
      await tester.pumpWidget(
        host(FakeUpdateService(info: release(UpdateStatus.optional)), prefs),
      );
      await tester.pumpAndSettle();

      expect(find.text('ISI-APLIKASI'), findsOneWidget);
      expect(find.byKey(const Key('pita-pembaruan')), findsOneWidget);

      await tester.tap(find.byKey(const Key('pita-pembaruan')));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Nanti'));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('pita-pembaruan')), findsNothing);
      expect(prefs.data['snoozed_build'], 6);
    },
  );

  testWidgets('galat jaringan saat memeriksa tidak pernah mengunci aplikasi', (
    tester,
  ) async {
    await tester.pumpWidget(
      host(FakeUpdateService(error: Exception('tanpa sinyal')), FakePrefs()),
    );
    await tester.pumpAndSettle();

    expect(find.text('ISI-APLIKASI'), findsOneWidget);
    expect(find.text('Pembaruan wajib'), findsNothing);
  });

  testWidgets(
    'setelah diperbarui (build tercatat lebih rendah) tampil pesan sekali',
    (tester) async {
      final prefs = FakePrefs({'last_build': 4});
      await tester.pumpWidget(host(FakeUpdateService(), prefs));
      await tester.pumpAndSettle();

      expect(
        find.text('Aplikasi sudah diperbarui ke versi 1.1.0 (build 5).'),
        findsOneWidget,
      );
      expect(prefs.data['last_build'], 5);
    },
  );
  testWidgets(
    'AboutAppCard menampilkan tombol periksa pembaruan jika appUpdateEnabled aktif',
    (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            appUpdateEnabledProvider.overrideWithValue(true),
            appUpdateServiceProvider.overrideWithValue(FakeUpdateService()),
          ],
          child: const MaterialApp(
            home: Scaffold(body: AboutAppCard()),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Versi aplikasi'), findsOneWidget);
      expect(find.text('Periksa pembaruan'), findsOneWidget);
    },
  );

  testWidgets(
    'AboutAppCard menyembunyikan tombol periksa pembaruan jika appUpdateEnabled mati (play store)',
    (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            appUpdateEnabledProvider.overrideWithValue(false),
            appUpdateServiceProvider.overrideWithValue(FakeUpdateService()),
          ],
          child: const MaterialApp(
            home: Scaffold(body: AboutAppCard()),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Versi aplikasi'), findsOneWidget);
      expect(find.text('Periksa pembaruan'), findsNothing);
    },
  );
}
