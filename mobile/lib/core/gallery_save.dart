import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

const _channel = MethodChannel('vms/gallery');

/// Galat operasi galeri HP dengan pesan bahasa Indonesia sederhana untuk pengguna.
class GallerySaveException implements Exception {
  final String message;
  const GallerySaveException(this.message);

  @override
  String toString() => message;
}

/// Salin foto laporan ke galeri HP, album "Visiontech" (T10). HANYA untuk foto laporan harian dari kamera aplikasi;
/// jangan dipakai untuk swafoto absen (privat).
/// Hapus salinan foto di album "Visiontech" galeri HP (T10).
Future<void> deleteFromPhoneGallery(String path) async {
  if (kIsWeb || !Platform.isAndroid) return;
  try {
    await _channel.invokeMethod<void>('deleteImage', {'path': path});
  } on PlatformException catch (e) {
    throw GallerySaveException('Foto gagal dihapus dari galeri HP: ${e.message ?? "Terjadi kesalahan."}');
  } catch (e) {
    throw const GallerySaveException('Foto gagal dihapus dari galeri HP.');
  }
}

Future<void> saveToPhoneGallery(String path) async {
  if (kIsWeb || !Platform.isAndroid) return;
  try {
    await _channel.invokeMethod<void>('saveImage', {'path': path});
  } on PlatformException catch (e) {
    throw GallerySaveException('Foto gagal disimpan ke galeri HP: ${e.message ?? "Terjadi kesalahan."}');
  } catch (e) {
    throw const GallerySaveException('Foto gagal disimpan ke galeri HP.');
  }
}
