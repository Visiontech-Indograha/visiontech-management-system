import 'dart:math' as math;

import 'package:flutter/material.dart';

/// Info jarak posisi HP ke SATU lokasi target -- dipakai
/// [confirmProceedIfOutsideGeofence] untuk menyusun pesan dialog. [isWithin]
/// true berarti tidak perlu dialog sama sekali.
class GeofenceProximity {
  const GeofenceProximity({
    required this.isWithin,
    required this.label,
    required this.distanceMeters,
    required this.radiusMeters,
  });

  final bool isWithin;
  final String label;
  final double distanceMeters;
  final double radiusMeters;
}

double haversineMeters(double lat1, double lon1, double lat2, double lon2) {
  const earthRadius = 6371000.0;
  final dLat = _deg2rad(lat2 - lat1);
  final dLon = _deg2rad(lon2 - lon1);
  final a =
      math.sin(dLat / 2) * math.sin(dLat / 2) +
      math.cos(_deg2rad(lat1)) *
          math.cos(_deg2rad(lat2)) *
          math.sin(dLon / 2) *
          math.sin(dLon / 2);
  final c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a));
  return earthRadius * c;
}

double _deg2rad(double deg) => deg * (math.pi / 180);

/// Cek jarak posisi HP ke SATU target spesifik (mis. site_latitude/longitude
/// milik penugasan yang sedang aktif) -- dipakai saat konteksnya sudah tahu
/// pasti lokasi mana yang jadi acuan (bukan "situs manapun").
GeofenceProximity checkTargetProximity({
  required double latitude,
  required double longitude,
  required double targetLatitude,
  required double targetLongitude,
  required double radiusMeters,
  required String label,
}) {
  final distance = haversineMeters(
    latitude,
    longitude,
    targetLatitude,
    targetLongitude,
  );
  return GeofenceProximity(
    isWithin: distance <= radiusMeters,
    label: label,
    distanceMeters: distance,
    radiusMeters: radiusMeters,
  );
}

/// Tampilkan dialog konfirmasi "di luar lokasi yang ditentukan, tetap
/// lanjutkan?" BILA [proximity] menyatakan di luar radius (plan M7 Keputusan
/// 17). Kalau [proximity] null (cache/data belum tersedia) atau sudah di
/// dalam radius, langsung return `true` tanpa dialog -- prinsip yang sama
/// dengan Keputusan 13: jangan menuduh "di luar lokasi" tanpa data
/// pembanding, dan validasi resmi (PostGIS geodesic) tetap selalu di server.
///
/// Return `true` bila boleh lanjut kirim data, `false` bila user memilih
/// Batal (pemanggil WAJIB menghentikan proses sepenuhnya, tidak ada data
/// terkirim/terqueue).
Future<bool> confirmProceedIfOutsideGeofence(
  BuildContext context,
  GeofenceProximity? proximity,
) async {
  if (proximity == null || proximity.isWithin) return true;

  final proceed = await showDialog<bool>(
    context: context,
    barrierDismissible: false,
    builder: (ctx) => AlertDialog(
      title: const Text('Di Luar Lokasi yang Ditentukan'),
      content: Text(
        'Anda terdeteksi sekitar ${proximity.distanceMeters.round()} meter dari ${proximity.label} '
        '(radius diizinkan ${proximity.radiusMeters.round()} m).\n\n'
        'Data tetap akan tersimpan & ditinjau HR/PM bila dilanjutkan. Tetap lanjutkan?',
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(ctx).pop(false),
          child: const Text('Batal'),
        ),
        FilledButton(
          onPressed: () => Navigator.of(ctx).pop(true),
          child: const Text('Tetap Lanjutkan'),
        ),
      ],
    ),
  );
  return proceed ?? false;
}
