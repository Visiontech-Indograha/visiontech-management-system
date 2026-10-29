import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/core/photo_capture.dart';

/// Dua ketukan cepat pada slot foto hanya boleh membuka kamera sekali: setiap jepretan menghasilkan
/// satu file, dan ketukan kedua tidak menimpa atau menghilangkan foto yang sedang diambil.
void main() {
  late int calls;
  late Completer<(File?, String?)> pending;

  setUp(() {
    calls = 0;
    pending = Completer<(File?, String?)>();
    photoCaptureOverride = (_) {
      calls++;
      return pending.future;
    };
  });

  tearDown(() {
    photoCaptureOverride = null;
  });

  testWidgets('ketukan ganda pada slot foto hanya membuka kamera sekali', (tester) async {
    final saved = <List<File?>>[];
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: GuidedPhotoCapture(
          slots: const [PhotoSlotConfig(label: 'Foto lokasi', hint: 'Arahkan ke lokasi')],
          onChanged: saved.add,
        ),
      ),
    ));

    final slot = find.byType(InkWell).first;
    // Dua ketukan tanpa pump di antaranya: tombol belum sempat berubah keadaan.
    await tester.tap(slot);
    await tester.tap(slot);
    await tester.pump();

    expect(calls, 1, reason: 'ketukan kedua tidak boleh membuka kamera kedua');

    final dir = Directory.systemTemp.createTempSync('vms-jepretan');
    final file = File('${dir.path}/foto.jpg')..writeAsBytesSync([1, 2, 3]);
    await tester.runAsync(() async {
      pending.complete((file, null));
      await Future<void>.delayed(const Duration(milliseconds: 10));
    });
    await tester.pump();
    await tester.pump();

    expect(saved, hasLength(1));
    expect(saved.single.single?.path, file.path);
    dir.deleteSync(recursive: true);
  });
}
