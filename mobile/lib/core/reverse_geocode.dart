import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:geocoding/geocoding.dart';

/// Alamat (reverse-geocoding) untuk watermark foto. Memakai geocoder platform
/// (Android Geocoder / CLGeocoder iOS) lewat paket `geocoding`.
///
/// Aturan: tidak pernah melempar galat dan tidak pernah memblokir pengambilan
/// foto. Gagal, offline, atau lewat [addressLookupTimeout] → null, lalu
/// watermark cukup memakai koordinat + nama lokasi tugas.
typedef AddressLookup = Future<List<Placemark>> Function(double lat, double lng);

/// Batas tunggu geocoder. Pendek supaya kamera tidak terasa macet.
const addressLookupTimeout = Duration(seconds: 3);

/// Celah uji: bila diisi, geocoder platform tidak dipanggil.
@visibleForTesting
AddressLookup? addressLookupOverride;

/// Hanya hasil berhasil yang disimpan; galat tidak, supaya dicoba lagi berikutnya.
final Map<String, String> _cache = {};

/// Kunci cache: koordinat dibulatkan 4 desimal (± 11 m) supaya GPS yang
/// bergeser sedikit tidak memicu permintaan geocoder baru.
@visibleForTesting
String addressCacheKey(double lat, double lng) =>
    '${lat.toStringAsFixed(4)},${lng.toStringAsFixed(4)}';

/// Susun satu baris alamat ringkas: jalan, kelurahan, kota, provinsi (tanpa duplikat).
@visibleForTesting
String? formatAddress(Placemark p) {
  final street = [
    p.thoroughfare,
    p.subThoroughfare,
  ].where((s) => s != null && s.trim().isNotEmpty).join(' ');
  final parts = <String>[];
  for (final raw in [
    street.isNotEmpty ? street : p.street,
    p.subLocality,
    p.locality,
    p.administrativeArea,
  ]) {
    final s = raw?.trim() ?? '';
    if (s.isNotEmpty && !parts.contains(s)) parts.add(s);
  }
  if (parts.isEmpty) return null;
  final text = parts.join(', ');
  return text.length > 140 ? '${text.substring(0, 137)}...' : text;
}

Future<List<Placemark>> _platformLookup(double lat, double lng) =>
    Geocoding(locale: const Locale('id', 'ID')).placemarkFromCoordinates(lat, lng);

/// Alamat untuk koordinat ini, atau null bila tidak tersedia. Hasil (berhasil)
/// di-cache per koordinat yang dibulatkan; galat tidak di-cache supaya dicoba lagi.
Future<String?> reverseGeocodeCached(double lat, double lng) async {
  final key = addressCacheKey(lat, lng);
  final cached = _cache[key];
  if (cached != null) return cached;

  final lookup = addressLookupOverride ?? _platformLookup;
  try {
    final list = await lookup(lat, lng).timeout(addressLookupTimeout);
    final text = list.isEmpty ? null : formatAddress(list.first);
    if (text != null) _cache[key] = text;
    return text;
  } catch (_) {
    return null;
  }
}

/// Kosongkan cache (uji).
@visibleForTesting
void resetAddressCache() => _cache.clear();
