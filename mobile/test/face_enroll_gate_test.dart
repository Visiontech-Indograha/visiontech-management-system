import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart' show Override;
import 'package:flutter_test/flutter_test.dart';
import 'package:vms_mobile/features/face/face_enroll_gate.dart';

Widget host(Override override) => ProviderScope(
  overrides: [override],
  child: const MaterialApp(
    home: FaceEnrollGate(child: Scaffold(body: Text('ISI-APLIKASI'))),
  ),
);

void main() {
  testWidgets('wajib daftar: menu lain tertutup, tampil layar pendaftaran dan tombol keluar', (tester) async {
    await tester.pumpWidget(host(faceGateProvider.overrideWith((ref) async => true)));
    await tester.pumpAndSettle();

    expect(find.text('ISI-APLIKASI'), findsNothing);
    expect(find.text('Daftarkan wajah Anda'), findsOneWidget);
    expect(find.byKey(const Key('face-gate-start')), findsOneWidget);
    expect(find.text('Keluar'), findsOneWidget);
  });

  testWidgets('sudah terdaftar atau tidak diwajibkan: isi aplikasi tampil normal', (tester) async {
    await tester.pumpWidget(host(faceGateProvider.overrideWith((ref) async => false)));
    await tester.pumpAndSettle();

    expect(find.text('ISI-APLIKASI'), findsOneWidget);
    expect(find.text('Daftarkan wajah Anda'), findsNothing);
  });

  testWidgets('galat (mis. tanpa sinyal) tidak mengunci pekerja lapangan', (tester) async {
    await tester.pumpWidget(
      host(faceGateProvider.overrideWith((ref) async => throw Exception('tanpa sinyal'))),
    );
    await tester.pumpAndSettle();

    expect(find.text('ISI-APLIKASI'), findsOneWidget);
  });

  testWidgets('selama status dimuat: indikator, bukan isi aplikasi', (tester) async {
    await tester.pumpWidget(
      host(
        faceGateProvider.overrideWith((ref) async {
          await Future<void>.delayed(const Duration(seconds: 5));
          return false;
        }),
      ),
    );
    await tester.pump();

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    expect(find.text('ISI-APLIKASI'), findsNothing);
    await tester.pump(const Duration(seconds: 6)); // selesaikan timer agar uji bersih
  });
}
