import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:vms_mobile/shared/router.dart';

void main() {
  testWidgets('rute tak dikenal menampilkan halaman Indonesia dan tombol ke Beranda berfungsi', (tester) async {
    final router = GoRouter(
      initialLocation: '/ngawur',
      routes: [GoRoute(path: '/', builder: (_, _) => const Scaffold(body: Text('BERANDA')))],
      errorBuilder: vmsNotFoundScreen,
    );
    await tester.pumpWidget(MaterialApp.router(routerConfig: router));
    await tester.pumpAndSettle();
    expect(find.text('Halaman tidak ditemukan'), findsOneWidget);

    await tester.tap(find.text('Ke Beranda'));
    await tester.pumpAndSettle();
    expect(find.text('BERANDA'), findsOneWidget);
  });
}
