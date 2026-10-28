import 'package:geolocator/geolocator.dart';

/// Id lokasi kerja terdekat dari titik ([lat], [lng]); null bila daftar kosong atau tak ada yang berkoordinat.
String? nearestSiteId(List<Map<String, dynamic>> sites, double lat, double lng) {
  String? best;
  var bestDistance = double.infinity;
  for (final s in sites) {
    final loc = s['location'];
    if (loc is! Map || loc['lat'] is! num || loc['lng'] is! num) continue;
    final d = Geolocator.distanceBetween(lat, lng, (loc['lat'] as num).toDouble(), (loc['lng'] as num).toDouble());
    if (d < bestDistance) {
      bestDistance = d;
      best = s['id'] as String;
    }
  }
  return best;
}
