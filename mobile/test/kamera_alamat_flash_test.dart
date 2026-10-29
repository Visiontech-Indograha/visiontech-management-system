import 'dart:async';
import 'dart:typed_data';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:geocoding/geocoding.dart';
import 'package:geolocator_platform_interface/geolocator_platform_interface.dart';
import 'package:image/image.dart' as img;
import 'package:vms_mobile/core/photo_capture.dart';
import 'package:vms_mobile/core/reverse_geocode.dart';
import 'package:vms_mobile/core/watermark_camera_screen.dart';

/// Alamat watermark (reverse-geocoding dengan cache & galat), flash kamera, dan logo tim di panel.
/// Pola uji: GPS & geocoder palsu, tanpa plugin kamera (layar kamera tetap bisa dibuka).

class _FakeGps extends GeolocatorPlatform {
  _FakeGps(this.position);
  final Position position;

  @override
  Future<bool> isLocationServiceEnabled() async => true;
  @override
  Future<LocationPermission> checkPermission() async =>
      LocationPermission.whileInUse;
  @override
  Future<LocationPermission> requestPermission() async =>
      LocationPermission.whileInUse;
  @override
  Future<Position> getCurrentPosition({
    LocationSettings? locationSettings,
  }) async => position;
}

Position _pos(double lat, double lng) => Position(
  latitude: lat,
  longitude: lng,
  timestamp: DateTime(2026, 10, 29, 8),
  accuracy: 8,
  altitude: 0,
  altitudeAccuracy: 0,
  heading: 0,
  headingAccuracy: 0,
  speed: 0,
  speedAccuracy: 0,
);

Placemark _sudirman() => const Placemark(
  thoroughfare: 'Jl. Sudirman',
  subThoroughfare: '1',
  subLocality: 'Tanah Abang',
  locality: 'Jakarta Pusat',
  administrativeArea: 'DKI Jakarta',
);

Uint8List _png(int w, int h) =>
    Uint8List.fromList(img.encodePng(img.Image(width: w, height: h)));

void main() {
  setUp(resetAddressCache);
  tearDown(() {
    addressLookupOverride = null;
    GeolocatorPlatform.instance = _FakeGps(_pos(0, 0));
  });

  group('Alamat dari GPS', () {
    test('formatAddress menyusun jalan, kelurahan, kota, provinsi tanpa duplikat', () {
      expect(
        formatAddress(_sudirman()),
        'Jl. Sudirman 1, Tanah Abang, Jakarta Pusat, DKI Jakarta',
      );
      expect(formatAddress(const Placemark(locality: 'Jakarta Pusat', subLocality: 'Jakarta Pusat')), 'Jakarta Pusat');
      expect(formatAddress(const Placemark()), isNull);
    });

    test('koordinat yang berdekatan (dibulatkan 4 desimal) memakai satu permintaan geocoder', () async {
      var calls = 0;
      addressLookupOverride = (lat, lng) async {
        calls++;
        return [_sudirman()];
      };
      final a = await reverseGeocodeCached(1.23456, 101.0);
      final b = await reverseGeocodeCached(1.23457, 101.0);
      expect(a, 'Jl. Sudirman 1, Tanah Abang, Jakarta Pusat, DKI Jakarta');
      expect(b, a);
      expect(calls, 1);
    });

    test('galat geocoder → null dan tidak di-cache (dicoba lagi berikutnya)', () async {
      var calls = 0;
      addressLookupOverride = (lat, lng) async {
        calls++;
        if (calls == 1) throw StateError('tidak ada sinyal');
        return [_sudirman()];
      };
      expect(await reverseGeocodeCached(2, 102), isNull);
      expect(await reverseGeocodeCached(2, 102), isNotNull);
      expect(calls, 2);
    });

    test('geocoder tidak membalas dalam batas waktu → null, tanpa menahan pemanggil', () async {
      addressLookupOverride = (lat, lng) => Completer<List<Placemark>>().future;
      final start = DateTime.now();
      expect(await reverseGeocodeCached(3, 103), isNull);
      expect(DateTime.now().difference(start), lessThan(const Duration(seconds: 6)));
    });
  });

  group('Watermark', () {
    test('baris teks: alamat tampil di antara koordinat dan waktu; tanpa alamat tetap 3 baris', () {
      final ts = DateTime(2026, 10, 29, 8, 15);
      final dengan = watermarkTextLines(
        latitude: -6.2,
        longitude: 106.8,
        timestamp: ts,
        isMocked: false,
        locationCaption: 'Kantor Utama',
        address: 'Jl. Sudirman 1, Jakarta Pusat',
      );
      expect(dengan, [
        '-6.200000, 106.800000',
        'Jl. Sudirman 1, Jakarta Pusat',
        '29/10/2026 08:15',
        'Kantor Utama',
      ]);
      final tanpa = watermarkTextLines(
        latitude: -6.2,
        longitude: 106.8,
        timestamp: ts,
        isMocked: false,
      );
      expect(tanpa, ['-6.200000, 106.800000', '29/10/2026 08:15']);
    });

    testWidgets('panel kamera menampilkan alamat dari GPS (tanpa menunggu kamera)', (tester) async {
      GeolocatorPlatform.instance = _FakeGps(_pos(-6.2, 106.8));
      addressLookupOverride = (lat, lng) async => [_sudirman()];
      await tester.pumpWidget(
        const MaterialApp(
          home: WatermarkCameraScreen(title: 'Foto uji', hint: 'Panduan'),
        ),
      );
      await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 50)));
      await tester.pump();
      expect(find.byKey(const Key('watermark-address')), findsOneWidget);
      expect(
        find.text('Jl. Sudirman 1, Tanah Abang, Jakarta Pusat, DKI Jakarta'),
        findsOneWidget,
      );
    });

    testWidgets('alamat gagal → panel tetap tanpa baris alamat', (tester) async {
      GeolocatorPlatform.instance = _FakeGps(_pos(-6.2, 106.8));
      addressLookupOverride = (lat, lng) async => throw StateError('offline');
      await tester.pumpWidget(
        const MaterialApp(
          home: WatermarkCameraScreen(title: 'Foto uji', hint: 'Panduan'),
        ),
      );
      await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 50)));
      await tester.pump();
      expect(find.byKey(const Key('watermark-address')), findsNothing);
      expect(find.text('-6.200000, 106.800000'), findsOneWidget);
    });

    testWidgets('logo tim dipakai di panel; tanpa logo tim → logo default', (tester) async {
      GeolocatorPlatform.instance = _FakeGps(_pos(-6.2, 106.8));
      addressLookupOverride = (lat, lng) async => <Placemark>[];
      final logo = _png(100, 50);
      await tester.pumpWidget(
        MaterialApp(
          home: WatermarkCameraScreen(title: 'Foto uji', hint: 'Panduan', logo: logo),
        ),
      );
      await tester.pump();
      final teamImage = tester.widget<Image>(
        find.descendant(
          of: find.byKey(const Key('watermark-logo')),
          matching: find.byType(Image),
        ),
      );
      expect(teamImage.image, isA<MemoryImage>());
      expect((teamImage.image as MemoryImage).bytes, logo);
      expect(teamImage.fit, BoxFit.contain);

      await tester.pumpWidget(
        const MaterialApp(
          home: WatermarkCameraScreen(title: 'Foto uji', hint: 'Panduan'),
        ),
      );
      await tester.pump();
      final defaultImage = tester.widget<Image>(
        find.descendant(
          of: find.byKey(const Key('watermark-logo')),
          matching: find.byType(Image),
        ),
      );
      expect(defaultImage.image, isA<AssetImage>());
    });
  });

  group('Flash', () {
    test('kamera belakang punya flash; kamera depan (swafoto) tidak', () {
      expect(flashAvailableFor(CameraLensDirection.back), isTrue);
      expect(flashAvailableFor(CameraLensDirection.front), isFalse);
    });

    test('siklus tombol: mati ⇄ nyala', () {
      expect(nextFlashMode(FlashMode.off), FlashMode.always);
      expect(nextFlashMode(FlashMode.always), FlashMode.off);
    });

    testWidgets('tombol menampilkan status mati/nyala dan memanggil aksi saat ditekan', (tester) async {
      var taps = 0;
      Future<void> pumpMode(FlashMode mode) => tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: CameraFlashToggle(mode: mode, onPressed: () => taps++),
          ),
        ),
      );

      await pumpMode(FlashMode.off);
      expect(find.text('Flash mati'), findsOneWidget);
      expect(find.byIcon(Icons.flash_off), findsOneWidget);

      await tester.tap(find.byKey(const Key('camera-flash-toggle')));
      expect(taps, 1);

      await pumpMode(FlashMode.always);
      expect(find.text('Flash nyala'), findsOneWidget);
      expect(find.byIcon(Icons.flash_on), findsOneWidget);
    });
  });
}
