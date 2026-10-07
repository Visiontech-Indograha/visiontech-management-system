import 'package:flutter/services.dart';

/// Aplikasi yang terpasang di HP ini (dibaca dari Android, bukan dari konstanta build).
class InstalledApp {
  const InstalledApp({
    required this.versionName,
    required this.versionCode,
    required this.abis,
    required this.sdk,
    required this.model,
  });

  factory InstalledApp.fromMap(Map<Object?, Object?> m) => InstalledApp(
    versionName: m['version_name'] as String? ?? '',
    versionCode: (m['version_code'] as num?)?.toInt() ?? 0,
    abis: [for (final a in (m['abis'] as List?) ?? const []) '$a'],
    sdk: (m['sdk'] as num?)?.toInt() ?? 0,
    model: m['model'] as String? ?? '',
  );

  final String versionName;

  /// versionCode Android = nomor build di pubspec (`1.1.0+2` → 2), dipakai membandingkan versi.
  final int versionCode;

  /// Build.SUPPORTED_ABIS, urutan prioritas HP (mis. arm64-v8a, armeabi-v7a).
  final List<String> abis;
  final int sdk;
  final String model;

  String get label => '$versionName (build $versionCode)';

  /// User-Agent API: versi aplikasi ikut tercatat di sesi (daftar perangkat halaman Akun).
  String get userAgent =>
      'VisiontechVMS/$versionName (build $versionCode; Android SDK $sdk; $model)';
}

/// Kanal native `vms/app_update` (android/.../AppUpdate.kt) — docs/32.
class AppUpdateChannel {
  const AppUpdateChannel();

  static const _channel = MethodChannel('vms/app_update');

  Future<InstalledApp> info() async => InstalledApp.fromMap(
    (await _channel.invokeMapMethod<Object?, Object?>('info'))!,
  );

  /// Folder unduhan yang boleh dibagikan ke installer (`cache/updates`, lihat res/xml/update_paths.xml).
  Future<String> updatesDir() async =>
      (await _channel.invokeMethod<String>('updatesDir'))!;

  /// Izin "Instal aplikasi tak dikenal" untuk aplikasi ini (Android 8+).
  Future<bool> canInstall() async =>
      await _channel.invokeMethod<bool>('canInstall') ?? false;

  Future<void> openInstallSettings() =>
      _channel.invokeMethod<void>('openInstallSettings');

  Future<void> install(String path) =>
      _channel.invokeMethod<void>('install', {'path': path});

  Future<String> sha256(String path) async =>
      (await _channel.invokeMethod<String>('sha256', {'path': path}))!;
}

/// User-Agent dihitung sekali per proses; null bila kanal tidak tersedia (uji, platform lain).
Future<String?>? _userAgent;

Future<String?> appUserAgent() => _userAgent ??= () async {
  try {
    return (await const AppUpdateChannel().info()).userAgent;
  } catch (_) {
    return null;
  }
}();
