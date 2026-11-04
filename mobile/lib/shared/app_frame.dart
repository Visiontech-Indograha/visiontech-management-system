import 'package:flutter/material.dart';

const _isBeta = bool.fromEnvironment('VMS_BETA');

/// Kerangka di atas Navigator, dipakai `ShadApp.router` di main.dart (dan uji widget).
///
/// - `ScaffoldMessenger`: `ShadApp` membangun `WidgetsApp`, bukan `MaterialApp`, jadi tidak ada
///   ScaffoldMessenger bawaan — tanpa ini setiap `showSnackBar` (mis. "Absen masuk tercatat.",
///   pesan galat) melempar "No ScaffoldMessenger widget found" dan tidak pernah tampil (temuan R-18).
/// - Safe zone global (R-14): jangan pernah menggambar di bawah notch/lekuk layar kiri-kanan
///   (mis. saat lanskap). Atas/bawah ditangani per layar (header, navbar, safeListPadding).
Widget vmsAppFrame(BuildContext context, Widget? child) {
  final body = SafeArea(
    top: false,
    bottom: false,
    child: child ?? const SizedBox.shrink(),
  );
  return ScaffoldMessenger(
    // APK beta uji lokal (build beta lokal): pita agar tidak tertukar dengan aplikasi prod.
    child: _isBeta
        ? Banner(
            message: 'BETA · uji lokal',
            location: BannerLocation.topEnd,
            child: body,
          )
        : body,
  );
}
