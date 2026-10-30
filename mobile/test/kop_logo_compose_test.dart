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
  test('logo tim dan Visiontech tampil berdampingan di kotak standar', () {
    final vms = _solidPng(400, 100, img.ColorRgba8(255, 255, 255, 255));
    final team = _solidPng(900, 300, img.ColorRgba8(20, 60, 160, 255));

    final out = img.decodePng(composeKopLogos([vms, team]))!;

    expect(out.width, watermarkLogoBoxWidth.toInt());
    expect(out.height, watermarkLogoBoxHeight.toInt());
    expect(out.getPixel(4, 15).a, greaterThan(0), reason: 'logo Visiontech di sisi kiri');
    expect(out.getPixel(out.width - 5, 15).a, greaterThan(0), reason: 'logo tim di sisi kanan');
  });

  test('tanpa logo tim, hanya logo Visiontech (tidak digabung)', () {
    final vms = _solidPng(400, 100, img.ColorRgba8(255, 255, 255, 255));
    final out = img.decodePng(composeKopLogos([vms]))!;
    expect(out.getPixel(out.width - 5, 15).a, 0, reason: 'sisi kanan kosong bila hanya satu logo');
  });
}
