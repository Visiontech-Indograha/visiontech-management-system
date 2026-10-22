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

/// Wajah V2 (Milestone 7): kamera mengambil beberapa pose lalu diunggah ke /face/enroll; server menolak bila bukan
/// satu wajah, kurang jelas, bukan orang yang sama, atau wajah karyawan lain. Saat absen, swafoto biasa dicocokkan
/// server — tidak ada langkah wajah terpisah. Gambar mentah selalu dihapus dari HP.
Future<FaceEnrollOutcome> runFaceEnrollment(BuildContext context, WidgetRef ref) async {
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
