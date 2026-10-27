import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/app_update_channel.dart';
import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../data/vms_api.dart';
import 'app_update_service.dart';

/// Pembaruan mandiri aktif untuk APK yang disebar di luar Google Play (portal dan rilis/beta).
/// Build untuk Google Play (`--dart-define=UPDATE_CHANNEL=play`, kebijakan Play melarang
/// pembaruan di luar Play) tidak memeriksa apa pun.
const _updateChannel = String.fromEnvironment(
  'UPDATE_CHANNEL',
  defaultValue: 'portal',
);
const _checkInDebug = bool.fromEnvironment('UPDATE_CHECK_IN_DEBUG');
const _isBeta = bool.fromEnvironment('VMS_BETA');

final appUpdateEnabledProvider = Provider<bool>(
  (ref) =>
      _updateChannel != 'play' &&
      (kReleaseMode || _checkInDebug || _isBeta || _updateChannel == 'beta') &&
      !kIsWeb &&
      Platform.isAndroid,
);

final appUpdateServiceProvider = Provider<AppUpdateService>(
  (ref) => AppUpdateService(api: VmsApi(ref.watch(apiClientProvider))),
);

/// Penyimpanan kecil pilihan pengguna: tunda pembaruan & build terakhir yang pernah dibuka.
class UpdatePrefs {
  const UpdatePrefs();

  Future<File> _file() async {
    final dir = await getApplicationSupportDirectory();
    return File('${dir.path}${Platform.pathSeparator}pembaruan.json');
  }

  Future<Map<String, dynamic>> read() async {
    try {
      final f = await _file();
      if (!await f.exists()) return {};
      return Map<String, dynamic>.from(
        jsonDecode(await f.readAsString()) as Map,
      );
    } catch (_) {
      return {};
    }
  }

  Future<void> write(Map<String, dynamic> data) async {
    try {
      await (await _file()).writeAsString(jsonEncode(data));
    } catch (_) {}
  }
}

final updatePrefsProvider = Provider<UpdatePrefs>((ref) => const UpdatePrefs());

enum UpdatePhase { idle, downloading, needsPermission, installing, failed }

@immutable
class AppUpdateState {
  const AppUpdateState({
    this.installed,
    this.info,
    this.phase = UpdatePhase.idle,
    this.progress = 0,
    this.error,
    this.snoozedBuild,
    this.justUpdatedTo,
  });

  final InstalledApp? installed;
  final UpdateInfo? info;
  final UpdatePhase phase;
  final double progress;
  final String? error;

  /// Build yang ditunda pengguna ("Nanti") — pita tidak muncul untuk build itu sampai masa tunda habis.
  final int? snoozedBuild;

  /// Diisi sekali setelah aplikasi berhasil diperbarui, untuk pesan "Aplikasi diperbarui ke …".
  final String? justUpdatedTo;

  bool get isRequired =>
      info?.status == UpdateStatus.required && info!.hasUpdate;

  bool get isOptional =>
      info?.status == UpdateStatus.optional && info!.hasUpdate;

  bool get showBanner =>
      isOptional &&
      (snoozedBuild != info!.latestBuild || phase != UpdatePhase.idle);

  bool get busy =>
      phase == UpdatePhase.downloading || phase == UpdatePhase.installing;

  AppUpdateState copyWith({
    InstalledApp? installed,
    UpdateInfo? info,
    UpdatePhase? phase,
    double? progress,
    String? error,
    bool clearError = false,
    int? snoozedBuild,
    bool clearSnooze = false,
    String? justUpdatedTo,
    bool clearJustUpdated = false,
  }) => AppUpdateState(
    installed: installed ?? this.installed,
    info: info ?? this.info,
    phase: phase ?? this.phase,
    progress: progress ?? this.progress,
    error: clearError ? null : (error ?? this.error),
    snoozedBuild: clearSnooze ? null : (snoozedBuild ?? this.snoozedBuild),
    justUpdatedTo: clearJustUpdated
        ? null
        : (justUpdatedTo ?? this.justUpdatedTo),
  );
}

/// Alur pembaruan aplikasi (docs/32): periksa → (opsional: pita, bisa ditunda) / (wajib: layar penuh) →
/// unduh + verifikasi → izin pasang → installer Android. Galat apa pun tidak pernah mengunci aplikasi:
/// status wajib hanya berasal dari jawaban server yang berhasil.
class AppUpdateController extends Notifier<AppUpdateState> {
  static const checkEvery = Duration(minutes: 30);
  static const snoozeFor = Duration(hours: 24);

  DateTime? _lastCheck;
  File? _apk;
  CancelToken? _cancel;

  AppUpdateService get _service => ref.read(appUpdateServiceProvider);
  UpdatePrefs get _prefs => ref.read(updatePrefsProvider);

  @override
  AppUpdateState build() => const AppUpdateState();

  /// Dipanggil saat aplikasi dibuka & kembali aktif. `force` = tombol "Periksa pembaruan".
  Future<UpdateInfo?> check({bool force = false}) async {
    if (!ref.read(appUpdateEnabledProvider)) return null;
    if (state.busy) return state.info;
    final now = DateTime.now();
    if (!force &&
        _lastCheck != null &&
        now.difference(_lastCheck!) < checkEvery) {
      return state.info;
    }
    _lastCheck = now;
    try {
      final app = state.installed ?? await _service.installed();
      if (state.installed == null) await _firstRun(app);
      final info = await _service.check(app);
      state = state.copyWith(installed: app, info: info, clearError: true);
      return info;
    } catch (_) {
      // Offline / server tak terjangkau: biarkan apa adanya, coba lagi nanti.
      _lastCheck = null;
      return state.info;
    }
  }

  Future<void> _firstRun(InstalledApp app) async {
    final prefs = await _prefs.read();
    final lastBuild = (prefs['last_build'] as num?)?.toInt();
    final snoozedBuild = (prefs['snoozed_build'] as num?)?.toInt();
    final until = DateTime.tryParse('${prefs['snoozed_until']}');
    final snoozeActive = until != null && DateTime.now().isBefore(until);
    state = state.copyWith(
      installed: app,
      snoozedBuild: snoozeActive ? snoozedBuild : null,
      justUpdatedTo: lastBuild != null && lastBuild < app.versionCode
          ? app.label
          : null,
    );
    if (lastBuild != app.versionCode) {
      await _prefs.write({...prefs, 'last_build': app.versionCode});
    }
    unawaited(_service.cleanup(app.versionCode));
  }

  /// Versi terpasang untuk ditampilkan (Profil), juga saat pemeriksaan otomatis mati (build debug).
  Future<void> loadInstalled() async {
    if (state.installed != null) return;
    try {
      state = state.copyWith(installed: await _service.installed());
    } catch (_) {}
  }

  void consumeJustUpdated() => state = state.copyWith(clearJustUpdated: true);

  /// "Nanti": pita disembunyikan 24 jam untuk build ini (pembaruan wajib tidak bisa ditunda).
  Future<void> snooze() async {
    final build = state.info?.latestBuild;
    if (build == null || state.isRequired) return;
    state = state.copyWith(snoozedBuild: build);
    final prefs = await _prefs.read();
    await _prefs.write({
      ...prefs,
      'snoozed_build': build,
      'snoozed_until': DateTime.now().add(snoozeFor).toIso8601String(),
    });
  }

  /// Unduh (atau pakai ulang unduhan terverifikasi) lalu buka installer.
  Future<void> startUpdate() async {
    final download = state.info?.download;
    if (download == null || state.busy) return;
    _cancel = CancelToken();
    state = state.copyWith(
      phase: UpdatePhase.downloading,
      progress: 0,
      clearError: true,
    );
    try {
      _apk = await _service.download(
        download,
        cancelToken: _cancel,
        onProgress: (p) => state = state.copyWith(progress: p),
      );
      state = state.copyWith(progress: 1);
      await _install();
    } on DioException catch (e) {
      if (CancelToken.isCancel(e)) {
        state = state.copyWith(phase: UpdatePhase.idle, progress: 0);
        return;
      }
      _fail(apiErrorMessage(e));
    } on UpdateVerificationException catch (e) {
      _fail(e.message);
    } catch (_) {
      _fail('Pembaruan gagal diunduh. Periksa sinyal lalu coba lagi.');
    }
  }

  void cancelDownload() => _cancel?.cancel();

  /// Dipanggil saat aplikasi kembali aktif: bila izin pasang baru saja diberikan, lanjutkan ke installer.
  Future<void> resumeAfterPermission() async {
    if (state.phase != UpdatePhase.needsPermission || _apk == null) return;
    if (await _service.canInstall()) await _install();
  }

  Future<void> _install() async {
    final apk = _apk;
    if (apk == null) return;
    if (!await _service.canInstall()) {
      state = state.copyWith(phase: UpdatePhase.needsPermission);
      await _service.openInstallSettings();
      return;
    }
    state = state.copyWith(phase: UpdatePhase.installing);
    try {
      await _service.install(apk);
      // Installer Android kini di depan; bila dibatalkan, tombol "Pasang" tetap tersedia.
      state = state.copyWith(phase: UpdatePhase.idle);
    } catch (_) {
      _fail('Installer Android tidak bisa dibuka. Coba lagi.');
    }
  }

  void _fail(String message) =>
      state = state.copyWith(phase: UpdatePhase.failed, error: message);

  /// Tombol utama: "Pasang" bila APK sudah siap, selain itu mulai unduh.
  Future<void> primaryAction() async {
    if (_apk != null && await _apk!.exists()) {
      state = state.copyWith(clearError: true);
      await _install();
    } else {
      await startUpdate();
    }
  }

  bool get hasDownloaded => _apk != null;
}

final appUpdateControllerProvider =
    NotifierProvider<AppUpdateController, AppUpdateState>(
      AppUpdateController.new,
    );
