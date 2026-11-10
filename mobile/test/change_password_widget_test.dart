import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:vms_mobile/features/auth/auth_controller.dart';
import 'package:vms_mobile/features/auth/auth_state.dart';
import 'package:vms_mobile/features/auth/change_password_screen.dart';
import 'package:vms_mobile/shared/router.dart';

const _user = AuthUser(
  id: 'u1',
  username: 'a@contoh.test',
  role: UserRole.member,
  employeeId: 'e1',
  mustChangePassword: true,
);

class _Must extends AuthController {
  bool loggedOut = false;
  String? nextError;
  String? lastNext;

  @override
  AuthState build() => const AuthAuthenticated(_user);

  @override
  Future<String?> changePassword({required String current, required String next}) async {
    lastNext = next;
    if (nextError != null) return nextError;
    state = AuthAuthenticated(_user.withMustChange(false));
    return null;
  }

  @override
  Future<void> logout() async {
    loggedOut = true;
  }
}

void main() {
  testWidgets('router mengunci ke Ganti sandi dan Keluar tetap bisa', (tester) async {
    final fake = _Must();
    final container = ProviderContainer(overrides: [authControllerProvider.overrideWith(() => fake)]);
    addTearDown(container.dispose);
    final router = container.read(routerProvider);
    await tester.pumpWidget(
      UncontrolledProviderScope(container: container, child: MaterialApp.router(routerConfig: router)),
    );
    await tester.pumpAndSettle();
    expect(find.text('Simpan sandi baru'), findsOneWidget);

    router.go('/leaves');
    await tester.pumpAndSettle();
    expect(find.text('Simpan sandi baru'), findsOneWidget);
    router.go('/profile');
    await tester.pumpAndSettle();
    expect(find.text('Simpan sandi baru'), findsOneWidget);

    await tester.ensureVisible(find.text('Keluar'));
    await tester.tap(find.text('Keluar'));
    expect(fake.loggedOut, isTrue);
  });

  Future<_Must> pumpScreen(WidgetTester tester) async {
    final fake = _Must();
    final router = GoRouter(
      initialLocation: '/ganti-sandi',
      routes: [
        GoRoute(path: '/', builder: (_, _) => const Scaffold(body: Text('Beranda'))),
        GoRoute(path: '/ganti-sandi', builder: (_, _) => const ChangePasswordScreen()),
      ],
    );
    await tester.pumpWidget(
      ProviderScope(
        overrides: [authControllerProvider.overrideWith(() => fake)],
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();
    return fake;
  }

  Future<void> isi(WidgetTester tester, String lama, String baru, String ulang) async {
    final f = find.byType(TextField);
    await tester.enterText(f.at(0), lama);
    await tester.enterText(f.at(1), baru);
    await tester.enterText(f.at(2), ulang);
    await tester.ensureVisible(find.text('Simpan sandi baru'));
    await tester.tap(find.text('Simpan sandi baru'));
    await tester.pumpAndSettle();
  }

  testWidgets('validasi menolak sandi lemah dan tidak memanggil server', (tester) async {
    final fake = await pumpScreen(tester);
    await isi(tester, 'lama1234', 'pendek', 'pendek');
    expect(find.text('Sandi baru minimal 8 karakter.'), findsOneWidget);
    await isi(tester, 'lama1234', 'abcdefgh', 'abcdefgh');
    expect(find.text('Sandi baru harus berisi huruf dan angka.'), findsOneWidget);
    expect(fake.lastNext, isNull);
  });

  testWidgets('sukses membersihkan tanda wajib-ganti dan menutup layar', (tester) async {
    final fake = await pumpScreen(tester);
    await isi(tester, 'lama1234', 'baru12345', 'baru12345');
    expect(fake.lastNext, 'baru12345');
    expect((fake.state as AuthAuthenticated).user.mustChangePassword, isFalse);
    expect(find.text('Beranda'), findsOneWidget);
  });
}
