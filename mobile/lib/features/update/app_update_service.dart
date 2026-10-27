import 'dart:io';

import 'package:dio/dio.dart';

import '../../core/app_update_channel.dart';
import '../../core/constants.dart';
import '../../data/vms_api.dart';

enum UpdateStatus { upToDate, optional, required }

/// Berkas APK yang cocok untuk HP ini (dari `GET /app/android/update`).
class ReleaseDownload {
  const ReleaseDownload({
    required this.abi,
    required this.url,
    required this.sha256,
    required this.size,
  });

  factory ReleaseDownload.fromJson(Map<String, dynamic> j) => ReleaseDownload(
    abi: j['abi'] as String,
    url: j['url'] as String,
    sha256: ((j['sha256'] as String?) ?? '').toLowerCase(),
    size: (j['size'] as num).toInt(),
  );

  final String abi;

  /// Jalur relatif ke API (mis. `/api/v1/app/android/files/vms-1.1.0-2-arm64-v8a.apk`).
  final String url;
  final String sha256;
  final int size;

  String get fileName => url.split('/').last;

  String get sizeLabel => '${(size / (1024 * 1024)).toStringAsFixed(1)} MB';
}

class UpdateInfo {
  const UpdateInfo({
    required this.status,
    required this.currentBuild,
    this.latestBuild,
    this.latestVersion,
    this.notes = const [],
    this.download,
  });

  factory UpdateInfo.fromJson(Map<String, dynamic> j) => UpdateInfo(
    status: switch (j['status']) {
      'REQUIRED' => UpdateStatus.required,
      'OPTIONAL' => UpdateStatus.optional,
      _ => UpdateStatus.upToDate,
    },
    currentBuild: (j['current_build'] as num).toInt(),
    latestBuild: (j['latest_build'] as num?)?.toInt(),
    latestVersion: j['latest_version'] as String?,
    notes: [for (final n in (j['notes'] as List?) ?? const []) '$n'],
    download: j['download'] == null
        ? null
        : ReleaseDownload.fromJson(
            Map<String, dynamic>.from(j['download'] as Map),
          ),
  );

  final UpdateStatus status;
  final int currentBuild;
  final int? latestBuild;
  final String? latestVersion;
  final List<String> notes;
  final ReleaseDownload? download;

  bool get hasUpdate => status != UpdateStatus.upToDate && download != null;

  /// Mis. `1.2.0 (build 5)` — nomor build ikut ditampilkan agar rilis bernama sama tetap bisa dibedakan.
  String get latestLabel =>
      '${latestVersion ?? '-'} (build ${latestBuild ?? '-'})';
}

/// Unduhan tidak cocok dengan manifest (rusak/terpotong/dipalsukan) — berkas sudah dihapus.
class UpdateVerificationException implements Exception {
  const UpdateVerificationException(this.message);
  final String message;
  @override
  String toString() => message;
}

/// Memeriksa versi di portal dan mengunduh APK terverifikasi (docs/32). Tidak menyentuh UI.
class AppUpdateService {
  AppUpdateService({
    required VmsApi api,
    AppUpdateChannel channel = const AppUpdateChannel(),
    Dio? downloader,
    String? baseUrl,
  }) : _api = api, // ignore: prefer_initializing_formals
       _channel = channel, // ignore: prefer_initializing_formals
       _baseUrl = baseUrl ?? ApiConfig.baseUrl,
       _downloader =
           downloader ??
           Dio(
             BaseOptions(
               connectTimeout: ApiConfig.connectTimeout,
               // Batas jeda antar-potongan data, bukan total: APK ±30 MB di sinyal lapangan tetap boleh lambat.
               receiveTimeout: const Duration(seconds: 60),
             ),
           );

  final VmsApi _api;
  final AppUpdateChannel _channel;
  final Dio _downloader;
  final String _baseUrl;

  Future<InstalledApp> installed() => _channel.info();

  Future<UpdateInfo> check(InstalledApp app) async => UpdateInfo.fromJson(
    await _api.appUpdate(build: app.versionCode, abis: app.abis),
  );

  /// APK terverifikasi di folder unduhan. Berkas yang sudah ada dan cocok dipakai ulang (mis. proses aplikasi
  /// dimulai ulang setelah izin pasang diberikan), selain itu diunduh ke `.part` lalu diganti nama.
  Future<File> download(
    ReleaseDownload d, {
    void Function(double progress)? onProgress,
    CancelToken? cancelToken,
  }) async {
    if (!d.url.startsWith('/')) {
      throw const UpdateVerificationException(
        'Alamat unduhan tidak sah. Hubungi Tim IT.',
      );
    }
    final dir = Directory(await _channel.updatesDir());
    final target = File('${dir.path}${Platform.pathSeparator}${d.fileName}');
    if (await _matches(target, d)) return target;

    final part = File('${target.path}.part');
    await _downloader.download(
      '$_baseUrl${d.url}',
      part.path,
      cancelToken: cancelToken,
      onReceiveProgress: (received, total) {
        final all = total > 0 ? total : d.size;
        if (all > 0) onProgress?.call((received / all).clamp(0, 1).toDouble());
      },
    );
    if (!await _matches(part, d)) {
      await _deleteQuietly(part);
      throw const UpdateVerificationException(
        'Berkas pembaruan rusak atau tidak lengkap. Coba unduh lagi.',
      );
    }
    if (await target.exists()) await target.delete();
    return part.rename(target.path);
  }

  Future<bool> canInstall() => _channel.canInstall();

  Future<void> openInstallSettings() => _channel.openInstallSettings();

  Future<void> install(File apk) => _channel.install(apk.path);

  /// Hapus APK/unduhan setengah jadi yang sudah tidak diperlukan (build ≤ yang terpasang).
  Future<void> cleanup(int installedBuild) async {
    try {
      final dir = Directory(await _channel.updatesDir());
      await for (final f in dir.list()) {
        if (f is! File) continue;
        final m = RegExp(r'-(\d+)-[^-]+\.apk(\.part)?$').firstMatch(f.path);
        final build = int.tryParse(m?.group(1) ?? '');
        if (build == null || build <= installedBuild) await _deleteQuietly(f);
      }
    } catch (_) {
      // Pembersihan bersifat oportunistik; kegagalan tidak boleh mengganggu pembukaan aplikasi.
    }
  }

  Future<bool> _matches(File f, ReleaseDownload d) async {
    if (!await f.exists() || await f.length() != d.size) return false;
    if (d.sha256.isEmpty) return false;
    return (await _channel.sha256(f.path)).toLowerCase() == d.sha256;
  }

  Future<void> _deleteQuietly(File f) async {
    try {
      await f.delete();
    } catch (_) {}
  }
}
