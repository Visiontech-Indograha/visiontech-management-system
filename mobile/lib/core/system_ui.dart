import 'package:flutter/services.dart';

const _channel = MethodChannel('vms/system_ui');

/// R-14: sembunyikan lagi bilah navigasi HP (usap dari tepi bawah memunculkannya sementara).
/// Dipanggil setelah layar yang mengubah mode sistem (kamera) ditutup, karena
/// `SystemChrome.setEnabledSystemUIMode` menimpa pengaturan dari MainActivity.
Future<void> hideSystemNavigation() async {
  try {
    await _channel.invokeMethod<void>('hideNavigation');
  } on MissingPluginException {
    // Uji widget / platform non-Android: tidak ada kanal native — abaikan.
  } on PlatformException {
    // Tidak kritis bagi pengguna.
  }
}
