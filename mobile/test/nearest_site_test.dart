import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/features/attendance/nearest_site.dart';

void main() {
  final sites = [
    {'id': 'jauh', 'location': {'lat': -6.2, 'lng': 106.8}},
    {'id': 'dekat', 'location': {'lat': 3.5952, 'lng': 98.6722}},
    {'id': 'tanpa-koordinat'},
  ];

  test('memilih lokasi terdekat dari titik pengguna', () {
    expect(nearestSiteId(sites, 3.5950, 98.6720), 'dekat');
    expect(nearestSiteId(sites, -6.2001, 106.8001), 'jauh');
  });

  test('daftar kosong atau tanpa koordinat → null', () {
    expect(nearestSiteId([], 1, 1), isNull);
    expect(nearestSiteId([{'id': 'x'}], 1, 1), isNull);
  });
}
