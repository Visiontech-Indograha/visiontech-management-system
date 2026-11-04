// Logo watermark: logo Visiontech selalu ada; logo tim (bila ada) digabung berdampingan dalam kotak standar.
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:vms_mobile/core/photo_capture.dart';
import 'package:vms_mobile/core/watermark_camera_screen.dart';

Uint8List _solidPng(int w, int h, img.ColorRgba8 color) {
  final im = img.Image(width: w, height: h, numChannels: 4);
  img.fill(im, color: color);
  return img.encodePng(im);
}

void main() {
  test('trimLogoMargins memangkas margin transparan dan latar putih', () {
    final a = img.Image(width: 100, height: 100, numChannels: 4);
    for (var y = 40; y < 60; y++) {
      for (var x = 10; x < 90; x++) {
        a.setPixelRgba(x, y, 200, 0, 0, 255);
      }
    }
    final ta = trimLogoMargins(a);
    expect((ta.width, ta.height), (80, 20));
    final b = img.Image(width: 100, height: 100, numChannels: 4)
      ..clear(img.ColorRgba8(255, 255, 255, 255));
    for (var y = 30; y < 70; y++) {
      for (var x = 30; x < 70; x++) {
        b.setPixelRgba(x, y, 0, 0, 200, 255);
      }
    }
    final tb = trimLogoMargins(b);
    expect((tb.width, tb.height), (40, 40));
    final empty = img.Image(width: 10, height: 10, numChannels: 4);
    expect(trimLogoMargins(empty).width, 10);
  });
  test('logo tim dan Visiontech tampil berdampingan di kotak standar', () {
    final vms = _solidPng(400, 100, img.ColorRgba8(255, 255, 255, 255));
    final team = _solidPng(900, 300, img.ColorRgba8(20, 60, 160, 255));

    final out = img.decodePng(composeKopLogos([vms, team]))!;

    expect(out.width, (watermarkLogoBoxWidth * watermarkLogoRenderScale).toInt());
    expect(out.height, (watermarkLogoBoxHeight * watermarkLogoRenderScale).toInt());
    expect(out.getPixel(12, out.height ~/ 2).a, greaterThan(0), reason: 'logo Visiontech di sisi kiri');
    expect(out.getPixel(out.width - 15, out.height ~/ 2).a, greaterThan(0), reason: 'logo tim di sisi kanan');
  });

  test('tanpa logo tim, hanya logo Visiontech (tidak digabung)', () {
    final vms = _solidPng(400, 100, img.ColorRgba8(255, 255, 255, 255));
    final out = img.decodePng(composeKopLogos([vms]))!;
    expect(out.getPixel(out.width - 15, out.height ~/ 2).a, 0, reason: 'sisi kanan kosong bila hanya satu logo');
  });
}
