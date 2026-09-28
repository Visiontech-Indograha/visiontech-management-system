import 'package:flutter/material.dart';

/// Kerangka di atas Navigator, dipakai `ShadApp.router` di main.dart (dan uji widget).
///
/// - `ScaffoldMessenger`: `ShadApp` membangun `WidgetsApp`, bukan `MaterialApp`, jadi tidak ada
///   ScaffoldMessenger bawaan — tanpa ini setiap `showSnackBar` (mis. "Absen masuk tercatat.",
///   pesan galat) melempar "No ScaffoldMessenger widget found" dan tidak pernah tampil (temuan R-18).
/// - Safe zone global (R-14): jangan pernah menggambar di bawah notch/lekuk layar kiri-kanan
///   (mis. saat lanskap). Atas/bawah ditangani per layar (header, navbar, safeListPadding).
Widget vmsAppFrame(BuildContext context, Widget? child) => ScaffoldMessenger(
  child: SafeArea(
    top: false,
    bottom: false,
    child: child ?? const SizedBox.shrink(),
  ),
);
