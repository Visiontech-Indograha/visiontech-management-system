import 'package:flutter/material.dart';

const _isBeta = bool.fromEnvironment('VMS_BETA');
const _isDev = bool.fromEnvironment('VMS_DEVELOPMENT');

/// Ungu tua: teks putih di atasnya kontras sekitar 10:1 (WCAG AA >= 4,5:1); beda dari pita BETA (merah).
const vmsDevBannerColor = Color(0xFF5B2A86);

/// Kerangka di atas Navigator, dipakai `ShadApp.router` di main.dart (dan uji widget).
///
/// - `ScaffoldMessenger`: `ShadApp` membangun `WidgetsApp`, bukan `MaterialApp`, jadi tidak ada
///   ScaffoldMessenger bawaan — tanpa ini setiap `showSnackBar` (mis. "Absen masuk tercatat.",
///   pesan galat) melempar "No ScaffoldMessenger widget found" dan tidak pernah tampil (temuan R-18).
/// - Safe zone global (R-14): jangan pernah menggambar di bawah notch/lekuk layar kiri-kanan
///   (mis. saat lanskap). Atas/bawah ditangani per layar (header, navbar, safeListPadding).
/// - Pita lingkungan hanya dari --dart-define (build produksi tidak memuatnya). Bila BETA dan DEV
///   aktif bersamaan, DEV menang. `beta`/`dev` bisa disuntik untuk uji.
Widget vmsAppFrame(
  BuildContext context,
  Widget? child, {
  bool beta = _isBeta,
  bool dev = _isDev,
}) {
  final body = SafeArea(
    top: false,
    bottom: false,
    child: child ?? const SizedBox.shrink(),
  );
  return ScaffoldMessenger(
    child: dev
        ? Banner(
            message: 'DEV · uji lokal',
            location: BannerLocation.topEnd,
            color: vmsDevBannerColor,
            child: body,
          )
        : beta
        ? Banner(
            message: 'BETA · uji lokal',
            location: BannerLocation.topEnd,
            child: body,
          )
        : body,
  );
}
