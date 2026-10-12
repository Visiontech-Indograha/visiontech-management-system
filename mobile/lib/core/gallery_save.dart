import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

const _channel = MethodChannel('vms/gallery');

/// Salin foto laporan ke galeri HP, album "Visiontech" (T10). HANYA untuk foto laporan harian dari kamera aplikasi;
/// jangan dipakai untuk swafoto absen (privat). Galat tidak pernah menggagalkan laporan: hanya dicatat.
/// Hapus salinan foto di album "Visiontech" galeri HP (T10). Galat tidak pernah melempar.
Future<void> deleteFromPhoneGallery(String path) async {
  if (kIsWeb || !Platform.isAndroid) return;
  try {
    await _channel.invokeMethod<void>('deleteImage', {'path': path});
  } catch (e) {
    debugPrint('Gagal menghapus dari galeri HP: $e');
  }
}

Future<void> saveToPhoneGallery(String path) async {
  if (kIsWeb || !Platform.isAndroid) return;
  try {
    await _channel.invokeMethod<void>('saveImage', {'path': path});
  } catch (e) {
    debugPrint('Gagal menyimpan ke galeri HP: $e');
  }
}
