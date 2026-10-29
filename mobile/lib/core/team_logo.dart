import 'dart:io';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:dio/dio.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:path_provider/path_provider.dart';

import '../data/vms_api.dart';
import 'api_client.dart';
import 'providers.dart';

/// Tim tempat pengguna bertugas (dari jadwal harian). Dipakai untuk logo tim
/// dan untuk menentukan apakah pengguna ketua tim (`leaderEmployeeId`).
class MyTeam {
  const MyTeam({
    required this.teamId,
    required this.teamName,
    required this.leaderEmployeeId,
  });

  final String teamId;
  final String teamName;
  final String? leaderEmployeeId;
}

String _isoDay(DateTime d) => DateFormat('yyyy-MM-dd').format(d);

/// Tim saya = tim pada jadwal harian terdekat (jadwal lapangan hanya memuat tim sendiri).
/// Lewat [SyncEngine.fetchList], jadi tetap ada saat luring (cache terakhir).
final myTeamProvider = FutureProvider<MyTeam?>((ref) async {
  final engine = ref.read(syncEngineProvider);
  final now = DateTime.now();
  final res = await engine.fetchList(
    'my_team_plans',
    () => engine.api.dailyPlans(
      start: _isoDay(now.subtract(const Duration(days: 7))),
      end: _isoDay(now.add(const Duration(days: 30))),
    ),
  );
  if (res.items.isEmpty) return null;
  final plan = res.items.first;
  final teamId = plan['team_id'];
  if (teamId == null) return null;
  return MyTeam(
    teamId: '$teamId',
    teamName: '${plan['team_name'] ?? 'Tim'}',
    leaderEmployeeId: plan['leader_employee_id'] as String?,
  );
});

/// Batas ukuran & dimensi logo (sama dengan validasi server).
const teamLogoMaxBytes = 2 * 1024 * 1024;
const teamLogoMinSide = 64;
const teamLogoMaxSide = 4000;

/// Pesan galat (Bahasa Indonesia) bila [bytes] tak layak jadi logo tim; null bila layak.
Future<String?> validateTeamLogo(Uint8List bytes) async {
  if (bytes.length > teamLogoMaxBytes) {
    return 'Ukuran gambar maksimal 2 MB.';
  }
  if (!_isPng(bytes) && !_isJpeg(bytes) && !_isWebP(bytes)) {
    return 'Format gambar harus PNG, JPEG, atau WebP.';
  }
  final size = await _imageSize(bytes);
  if (size == null) return 'Berkas tidak dapat dibaca sebagai gambar.';
  final (w, h) = size;
  if (w < teamLogoMinSide ||
      h < teamLogoMinSide ||
      w > teamLogoMaxSide ||
      h > teamLogoMaxSide) {
    return 'Ukuran gambar harus 64–4000 px per sisi (saat ini $w×$h px).';
  }
  return null;
}

bool _isPng(Uint8List b) =>
    b.length >= 8 &&
    b[0] == 0x89 &&
    b[1] == 0x50 &&
    b[2] == 0x4E &&
    b[3] == 0x47;

bool _isJpeg(Uint8List b) =>
    b.length >= 3 && b[0] == 0xFF && b[1] == 0xD8 && b[2] == 0xFF;

bool _isWebP(Uint8List b) =>
    b.length >= 12 &&
    String.fromCharCodes(b.sublist(0, 4)) == 'RIFF' &&
    String.fromCharCodes(b.sublist(8, 12)) == 'WEBP';

/// Lebar & tinggi tanpa men-decode penuh (cukup header).
Future<(int, int)?> _imageSize(Uint8List bytes) async {
  ui.ImmutableBuffer? buffer;
  ui.ImageDescriptor? desc;
  try {
    buffer = await ui.ImmutableBuffer.fromUint8List(bytes);
    desc = await ui.ImageDescriptor.encoded(buffer);
    return (desc.width, desc.height);
  } catch (_) {
    return null;
  } finally {
    desc?.dispose();
    buffer?.dispose();
  }
}

/// Logo tersimpan di perangkat. Satu berkas per tim: baris pertama = versi
/// (`logo_file_id` dari server), sisanya bytes gambar. Versi berbeda = cache usang.
class TeamLogoStore {
  TeamLogoStore({Future<Directory> Function()? dirFactory})
    : _dirFactory = dirFactory ?? _defaultDir;

  final Future<Directory> Function() _dirFactory;

  static Future<Directory> _defaultDir() async {
    final base = await getApplicationSupportDirectory();
    final dir = Directory('${base.path}${Platform.pathSeparator}team_logo');
    await dir.create(recursive: true);
    return dir;
  }

  Future<File> _file(String teamId) async {
    final dir = await _dirFactory();
    return File('${dir.path}${Platform.pathSeparator}$teamId.logo');
  }

  Future<({String version, Uint8List bytes})?> read(String teamId) async {
    try {
      final f = await _file(teamId);
      if (!await f.exists()) return null;
      final raw = await f.readAsBytes();
      final nl = raw.indexOf(0x0A);
      if (nl < 0) return null;
      return (
        version: String.fromCharCodes(raw.sublist(0, nl)),
        bytes: Uint8List.sublistView(raw, nl + 1),
      );
    } catch (_) {
      return null;
    }
  }

  Future<void> write(String teamId, String version, Uint8List bytes) async {
    final f = await _file(teamId);
    final out = BytesBuilder(copy: false)
      ..add(version.codeUnits)
      ..addByte(0x0A)
      ..add(bytes);
    await f.writeAsBytes(out.takeBytes(), flush: true);
  }

  Future<void> clear(String teamId) async {
    try {
      final f = await _file(teamId);
      if (await f.exists()) await f.delete();
    } catch (_) {
      // Berkas cache tak bisa dihapus: cukup diabaikan, sumbernya tetap server.
    }
  }
}

/// Logo tim dari server (GET /teams/{id}/logo) dengan cache perangkat.
/// Urutan: detail tim (versi logo) → cache bila versi sama → unduh bila berbeda.
/// Luring → cache terakhir. Tanpa cache & luring → null (pakai logo default).
class TeamLogoService {
  TeamLogoService({required this.api, required this.store});

  final VmsApi api;
  final TeamLogoStore store;

  Future<Uint8List?> resolve(String teamId) async {
    final stored = await store.read(teamId);
    Map<String, dynamic>? detail;
    try {
      detail = await api.teamDetail(teamId);
    } on DioException catch (e) {
      if (isNetworkFailure(e)) return stored?.bytes;
      // Anggota tanpa izin lihat tim tetap boleh melihat logo: ambil langsung.
    }
    if (detail != null) {
      final version = detail['logo_file_id'] as String?;
      if (version == null) {
        await store.clear(teamId);
        return null;
      }
      if (stored != null && stored.version == version) return stored.bytes;
      return _download(teamId, version, stored?.bytes);
    }
    return _download(teamId, '-', stored?.bytes);
  }

  Future<Uint8List?> _download(
    String teamId,
    String version,
    Uint8List? fallback,
  ) async {
    try {
      final bytes = await api.teamLogoBytes(teamId);
      if (bytes == null) {
        await store.clear(teamId);
        return null;
      }
      await store.write(teamId, version, bytes);
      return bytes;
    } on DioException catch (e) {
      if (isNetworkFailure(e)) return fallback;
      rethrow;
    }
  }

  /// Unggah logo baru (sudah lolos [validateTeamLogo]); bytes disimpan ke cache dengan versi baru.
  Future<void> upload(String teamId, Uint8List bytes, String filename) async {
    final res = await api.uploadTeamLogo(teamId, bytes, filename);
    await store.write(teamId, '${res['logo_file_id']}', bytes);
  }

  Future<void> remove(String teamId) async {
    await api.deleteTeamLogo(teamId);
    await store.clear(teamId);
  }
}

final teamLogoServiceProvider = Provider<TeamLogoService>(
  (ref) => TeamLogoService(
    api: ref.watch(syncEngineProvider).api,
    store: TeamLogoStore(),
  ),
);

/// Logo tim per [teamId]; null = belum ada logo (tampilkan logo default).
final teamLogoProvider = FutureProvider.family<Uint8List?, String>(
  (ref, teamId) => ref.watch(teamLogoServiceProvider).resolve(teamId),
);

/// Logo tim untuk watermark foto. Tidak pernah melempar & berbatas waktu singkat:
/// bila lambat/gagal → null, foto tetap memakai logo default.
Future<Uint8List?> teamLogoForWatermark(ProviderContainer container) async {
  try {
    final team = await container
        .read(myTeamProvider.future)
        .timeout(const Duration(seconds: 2));
    if (team == null) return null;
    return await container
        .read(teamLogoServiceProvider)
        .resolve(team.teamId)
        .timeout(const Duration(seconds: 2));
  } catch (_) {
    return null;
  }
}

/// Logo tim kecil (kartu tim). Tanpa logo tim → logo default Visiontech, dengan 'contain'.
class TeamLogoAvatar extends ConsumerWidget {
  const TeamLogoAvatar({super.key, required this.teamId, this.size = 32});

  final String teamId;
  final double size;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final logo = ref.watch(teamLogoProvider(teamId)).value;
    return SizedBox(
      width: size,
      height: size,
      child: logo != null
          ? Image.memory(logo, fit: BoxFit.contain)
          : Image.asset('assets/branding/logo_visiontech.png', fit: BoxFit.contain),
    );
  }
}
