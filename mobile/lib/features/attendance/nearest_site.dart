import 'package:geolocator/geolocator.dart';

double? _extractLat(Map<String, dynamic> s) {
  if (s['latitude'] is num) return (s['latitude'] as num).toDouble();
  if (s['site_lat'] is num) return (s['site_lat'] as num).toDouble();
  final loc = s['location'];
  if (loc is Map && loc['lat'] is num) return (loc['lat'] as num).toDouble();
  return null;
}

double? _extractLng(Map<String, dynamic> s) {
  if (s['longitude'] is num) return (s['longitude'] as num).toDouble();
  if (s['site_lng'] is num) return (s['site_lng'] as num).toDouble();
  final loc = s['location'];
  if (loc is Map && loc['lng'] is num) return (loc['lng'] as num).toDouble();
  return null;
}

/// Id lokasi kerja terdekat dari titik ([lat], [lng]); null bila daftar kosong atau tak ada yang berkoordinat.
/// Mendukung format kantor umum (`location: {lat, lng}`) maupun `client_sites` (`latitude`, `longitude`).
String? nearestSiteId(List<Map<String, dynamic>> sites, double lat, double lng) {
  String? best;
  var bestDistance = double.infinity;
  for (final s in sites) {
    final sLat = _extractLat(s);
    final sLng = _extractLng(s);
    if (sLat == null || sLng == null) continue;
    final d = Geolocator.distanceBetween(lat, lng, sLat, sLng);
    if (d < bestDistance) {
      bestDistance = d;
      best = (s['id'] ?? s['site_id']) as String?;
    }
  }
  return best;
}

/// Pilihan lokasi absen bawaan: terdekat (GPS) > lokasi absen terakhir > kantor sendiri > urutan pertama.
String? defaultSiteId(List<Map<String, dynamic>> sites, {String? near, String? last, String? ownOfficeId}) {
  bool has(String? id) => id != null && sites.any((s) => s['id'] == id);
  if (has(near)) return near;
  if (has(last)) return last;
  if (has(ownOfficeId)) return ownOfficeId;
  return sites.isEmpty ? null : sites.first['id'] as String?;
}

/// Kantor sendiri didahulukan di daftar lokasi (setelah lokasi tugas hari ini); sisanya tetap urutannya.
List<Map<String, dynamic>> ownOfficeFirst(List<Map<String, dynamic>> offices, String? ownOfficeId) {
  if (ownOfficeId == null) return offices;
  return [
    ...offices.where((s) => s['id'] == ownOfficeId),
    ...offices.where((s) => s['id'] != ownOfficeId),
  ];
}
