import 'dart:typed_data';

import 'package:image/image.dart' as img;

/// Bingkai kamera mentah (NV21) yang akan dikirim ke isolate untuk diubah menjadi JPEG.
class FrameData {
  const FrameData({
    required this.bytes,
    required this.width,
    required this.height,
    required this.rowStride,
    required this.rotation,
  });

  final Uint8List bytes;
  final int width;
  final int height;

  /// Panjang satu baris dalam bita (bisa lebih besar dari `width` bila ada padding); 0 = sama dengan `width`.
  final int rowStride;

  /// Putaran searah jarum jam (derajat) agar tegak: `sensorOrientation` kamera depan (umumnya 270).
  final int rotation;
}

/// NV21 → JPEG tegak. `step` mengambil tiap-n piksel (2 = setengah resolusi) agar murah di HP; wajah untuk
/// pemeriksaan tantangan tetap cukup besar. Bukan untuk gambar akhir (itu `takePicture`, resolusi penuh).
Uint8List nv21ToJpeg(FrameData f, {int step = 2, int quality = 80}) {
  final stride = f.rowStride > 0 ? f.rowStride : f.width;
  final outW = f.width ~/ step;
  final outH = f.height ~/ step;
  final image = img.Image(width: outW, height: outH);
  final uvStart = stride * f.height;
  final bytes = f.bytes;
  for (var j = 0; j < outH; j++) {
    final y = j * step;
    for (var i = 0; i < outW; i++) {
      final x = i * step;
      final luma = bytes[y * stride + x];
      final uv = uvStart + (y >> 1) * stride + (x & ~1);
      var v = 0;
      var u = 0;
      if (uv + 1 < bytes.length) {
        v = bytes[uv] - 128;
        u = bytes[uv + 1] - 128;
      }
      image.setPixelRgb(
        i,
        j,
        (luma + 1.402 * v).round().clamp(0, 255),
        (luma - 0.344136 * u - 0.714136 * v).round().clamp(0, 255),
        (luma + 1.772 * u).round().clamp(0, 255),
      );
    }
  }
  final upright = f.rotation % 360 == 0
      ? image
      : img.copyRotate(image, angle: f.rotation);
  return Uint8List.fromList(img.encodeJpg(upright, quality: quality));
}

/// Dipakai `compute`: fungsi tingkat atas agar bisa berjalan di isolate.
Uint8List encodeFrame(FrameData f) => nv21ToJpeg(f);
