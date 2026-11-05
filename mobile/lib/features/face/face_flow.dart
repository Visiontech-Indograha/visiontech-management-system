import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/error_message.dart';
import '../../core/providers.dart';
import 'face_capture_screen.dart';

/// Hasil satu putaran pendaftaran wajah: `message` untuk ditampilkan ke pengguna; `cancelled` = kamera ditutup.
class FaceEnrollOutcome {
  const FaceEnrollOutcome({required this.ok, this.message, this.cancelled = false});

  final bool ok;
  final String? message;
  final bool cancelled;
}

/// Layar konfirmasi sebelum memotret: pastikan hanya wajah pemilik akun yang ada di depan kamera.
/// Tombol dibuat besar agar mudah ditekan di lapangan. Return `false` bila dibatalkan.
Future<bool> confirmFaceEnrollStart(BuildContext context) async {
  final ok = await showDialog<bool>(
    context: context,
    barrierDismissible: false,
    builder: (ctx) => AlertDialog(
      icon: const Icon(Icons.face_retouching_natural_rounded, size: 40),
      title: const Text(
        'Pastikan hanya wajah Anda di depan kamera',
        textAlign: TextAlign.center,
      ),
      content: const Text(
        'Tidak ada orang lain di sekitar kamera. Setelah ini, kamera akan memotret '
        'beberapa sudut wajah Anda.',
        textAlign: TextAlign.center,
      ),
      actionsAlignment: MainAxisAlignment.center,
      actionsOverflowDirection: VerticalDirection.down,
      actions: [
        SizedBox(
          width: double.infinity,
          height: 52,
          child: FilledButton.icon(
            key: const Key('face-confirm-start'),
            onPressed: () => Navigator.of(ctx).pop(true),
            icon: const Icon(Icons.camera_alt_rounded),
            label: const Text('Ya, mulai foto', style: TextStyle(fontSize: 16)),
          ),
        ),
        SizedBox(
          width: double.infinity,
          height: 52,
          child: OutlinedButton(
            key: const Key('face-confirm-cancel'),
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Batal', style: TextStyle(fontSize: 16)),
          ),
        ),
      ],
    ),
  );
  return ok ?? false;
}

/// Wajah V2 (Milestone 7): kamera mengambil beberapa pose lalu diunggah ke /face/enroll; server menolak bila bukan
/// satu wajah, kurang jelas, bukan orang yang sama, atau wajah karyawan lain. Saat absen, swafoto biasa dicocokkan
/// server — tidak ada langkah wajah terpisah. Gambar mentah selalu dihapus dari HP.
Future<FaceEnrollOutcome> runFaceEnrollment(BuildContext context, WidgetRef ref) async {
  if (!await confirmFaceEnrollStart(context)) {
    return const FaceEnrollOutcome(ok: false, cancelled: true);
  }
  if (!context.mounted) return const FaceEnrollOutcome(ok: false, cancelled: true);
  final result = await Navigator.of(context).push<FaceCaptureResult>(
    MaterialPageRoute(fullscreenDialog: true, builder: (_) => const FaceCaptureScreen()),
  );
  if (result == null || result.photos.isEmpty) {
    return const FaceEnrollOutcome(ok: false, cancelled: true);
  }
  try {
    final res = await ref.read(syncEngineProvider).api.enrollFace(result.photos);
    return FaceEnrollOutcome(
      ok: true,
      message: 'Wajah berhasil didaftarkan (${res['images_used'] ?? result.photos.length} foto).',
    );
  } on DioException catch (e) {
    return FaceEnrollOutcome(ok: false, message: apiErrorMessage(e));
  } finally {
    for (final f in result.photos) {
      try {
        await f.delete();
      } on FileSystemException {
        // Berkas sementara; tidak kritis.
      }
    }
  }
}
