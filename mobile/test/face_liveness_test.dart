import 'dart:math';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:vms_mobile/core/face/liveness.dart';
import 'package:vms_mobile/core/face/nv21.dart';
import 'package:vms_mobile/features/face/face_flow.dart';

/// Bingkai NV21 abu-abu 64x48 dengan blok terang 16x12 di KIRI-ATAS; `stride` > lebar mensimulasikan padding baris.
FrameData frame({int rotation = 0, int stride = 0}) {
  const w = 64;
  const h = 48;
  final s = stride > 0 ? stride : w;
  final bytes = Uint8List(s * h * 3 ~/ 2)..fillRange(0, s * h, 40);
  for (var y = 0; y < 12; y++) {
    for (var x = 0; x < 16; x++) {
      bytes[y * s + x] = 240;
    }
  }
  for (var i = s * h; i < bytes.length; i++) {
    bytes[i] = 128; // chroma netral → abu-abu
  }
  return FrameData(
    bytes: bytes,
    width: w,
    height: h,
    rowStride: stride,
    rotation: rotation,
  );
}

int luma(img.Image im, int x, int y) => img.getLuminance(im.getPixel(x, y)).round();

void main() {
  group('tantangan liveness', () {
    test('memilih dua tantangan berbeda yang dikenal server', () {
      final known = livenessChallenges.map((c) => c.id).toSet();
      for (var i = 0; i < 100; i++) {
        final picked = pickLivenessChallenges(Random(i));
        expect(picked, hasLength(livenessChallengeCount));
        expect(picked.map((c) => c.id).toSet(), hasLength(picked.length));
        expect(known.containsAll(picked.map((c) => c.id)), isTrue);
      }
    });

    test('semua tantangan bisa terpilih (urutan tak bisa ditebak)', () {
      final seen = <String>{};
      for (var i = 0; i < 200; i++) {
        seen.addAll(pickLivenessChallenges(Random(i)).map((c) => c.id));
      }
      expect(seen, livenessChallenges.map((c) => c.id).toSet());
    });

    test('depan tidak pernah menjadi tantangan; id sama dengan face-service', () {
      expect(
        livenessChallenges.map((c) => c.id),
        unorderedEquals(['kiri', 'kanan', 'atas', 'buka_mulut', 'kedip']),
      );
    });

    test('lolos hanya bila jumlah bukti cukup', () {
      expect(
        livenessPayload(challenges: ['kedip', 'kiri'], proofs: ['a'])['passed'],
        isFalse,
      );
      final ok = livenessPayload(
        challenges: ['kedip', 'kiri'],
        proofs: ['a', 'b'],
      );
      expect(ok['passed'], isTrue);
      expect(ok['proofs'], ['a', 'b']);
      expect(livenessPayload(challenges: [], proofs: [])['passed'], isFalse);
    });

    test('petunjuk server dibersihkan dari awalan teknis', () {
      expect(
        friendlyChallengeHint('Tantangan Gagal: Mulut kurang terbuka!'),
        'Mulut kurang terbuka!',
      );
      expect(friendlyChallengeHint('Tidak ada wajah.'), 'Tidak ada wajah.');
    });
  });

  group('NV21 → JPEG', () {
    test('ukuran mengikuti step dan putaran', () {
      final upright = img.decodeJpg(nv21ToJpeg(frame()))!;
      expect((upright.width, upright.height), (32, 24));
      final rotated = img.decodeJpg(nv21ToJpeg(frame(rotation: 270)))!;
      expect((rotated.width, rotated.height), (24, 32));
    });

    test('putaran searah jarum jam: kiri-atas → kanan-atas (90) dan kiri-bawah (270)', () {
      final r90 = img.decodeJpg(nv21ToJpeg(frame(rotation: 90)))!;
      expect(luma(r90, r90.width - 3, 3), greaterThan(150)); // blok terang di kanan-atas
      expect(luma(r90, 3, r90.height - 3), lessThan(90));
      final r270 = img.decodeJpg(nv21ToJpeg(frame(rotation: 270)))!;
      expect(luma(r270, 3, r270.height - 3), greaterThan(150)); // blok terang di kiri-bawah
      expect(luma(r270, r270.width - 3, 3), lessThan(90));
    });

    test('padding baris (stride > lebar) tidak menggeser gambar', () {
      final padded = img.decodeJpg(nv21ToJpeg(frame(rotation: 90, stride: 80)))!;
      expect(luma(padded, padded.width - 3, 3), greaterThan(150));
    });
  });

  testWidgets('dialog persetujuan menampilkan teks server dan butuh centang', (
    tester,
  ) async {
    bool? answer;
    await tester.pumpWidget(
      MaterialApp(
        home: Builder(
          builder: (ctx) => TextButton(
            onPressed: () async => answer = await showFaceConsentDialog(
              ctx,
              text: 'Saya menyetujui pemakaian data wajah.',
              version: '2026-10-05',
            ),
            child: const Text('buka'),
          ),
        ),
      ),
    );
    await tester.tap(find.text('buka'));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('face-policy-text')), findsOneWidget);
    expect(find.textContaining('v2026-10-05'), findsOneWidget);
    FilledButton okButton() => tester.widget(find.byKey(const Key('face-consent-ok')));
    expect(okButton().onPressed, isNull); // belum dicentang → tidak bisa setuju

    await tester.tap(find.byKey(const Key('face-consent-check')));
    await tester.pump();
    expect(okButton().onPressed, isNotNull);
    await tester.tap(find.byKey(const Key('face-consent-ok')));
    await tester.pumpAndSettle();
    expect(answer, isTrue);
  });
}
