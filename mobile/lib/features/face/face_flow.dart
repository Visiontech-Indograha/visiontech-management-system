import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/error_message.dart';
import '../../core/providers.dart';
import 'face_capture_screen.dart';

/// Hasil pengambilan gambar wajah untuk satu absen.
class FaceProbeOutcome {
  const FaceProbeOutcome({
    this.probeId,
    this.cancelled = false,
    this.error,
    this.stopReason,
  });

  /// Id gambar wajah sementara di server; null bila tidak ada (dibatalkan, jaringan putus, atau galat).
  final String? probeId;

  /// Pengguna menutup kamera: absen DIBATALKAN (bukan dilanjutkan tanpa wajah).
  final bool cancelled;

  /// Galat dari server yang harus ditampilkan dan membuat absen tidak dilanjutkan (mis. wajah tidak terdeteksi).
  final String? error;

  /// `offline` bila jaringan putus saat mengunggah/memeriksa: absen lanjut lewat jalur luring.
  final String? stopReason;
}

/// Buka kamera wajah (dua tantangan acak), lalu unggah gambar wajah akhir sebagai probe. Gambar mentah di HP dihapus
/// segera setelah diunggah; ia bukan foto absensi dan tidak disimpan di riwayat.
Future<FaceProbeOutcome> captureFaceProbe(
  BuildContext context,
  WidgetRef ref,
) async {
  final result = await Navigator.of(context).push<FaceCaptureResult>(
    MaterialPageRoute(
      fullscreenDialog: true,
      builder: (_) => const FaceCaptureScreen(mode: FaceCaptureMode.attendance),
    ),
  );
  if (result == null || result.photos.isEmpty) {
    return const FaceProbeOutcome(cancelled: true);
  }
  try {
    final id = await ref
        .read(syncEngineProvider)
        .api
        .createFaceProbe(result.photos.first, liveness: result.liveness);
    return FaceProbeOutcome(probeId: id, stopReason: result.stopReason);
  } on DioException catch (e) {
    if (isNetworkFailure(e)) return const FaceProbeOutcome(stopReason: 'offline');
    return FaceProbeOutcome(error: apiErrorMessage(e));
  } finally {
    await _deleteAll(result.photos);
  }
}

Future<void> _deleteAll(List<File> files) async {
  for (final f in files) {
    try {
      await f.delete();
    } on FileSystemException {
      // Berkas sementara; tidak kritis.
    }
  }
}

/// Teks persetujuan biometrik MILIK SERVER (`/face/policy`): pengguna harus melihat kalimat yang benar-benar
/// disetujui. Mengembalikan true bila disetujui.
Future<bool> showFaceConsentDialog(
  BuildContext context, {
  required String text,
  required String version,
}) async {
  var agreed = false;
  final ok = await showDialog<bool>(
    context: context,
    builder: (ctx) => StatefulBuilder(
      builder: (ctx, setLocal) => AlertDialog(
        title: const Text('Persetujuan data wajah'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(text, key: const Key('face-policy-text')),
              const SizedBox(height: 12),
              CheckboxListTile(
                key: const Key('face-consent-check'),
                contentPadding: EdgeInsets.zero,
                controlAffinity: ListTileControlAffinity.leading,
                value: agreed,
                onChanged: (v) => setLocal(() => agreed = v ?? false),
                title: Text('Saya sudah membaca dan menyetujui (v$version)'),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Batal'),
          ),
          FilledButton(
            key: const Key('face-consent-ok'),
            onPressed: agreed ? () => Navigator.of(ctx).pop(true) : null,
            child: const Text('Setuju'),
          ),
        ],
      ),
    ),
  );
  return ok ?? false;
}
