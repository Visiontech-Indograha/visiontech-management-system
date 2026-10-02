import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import 'package:vms_mobile/core/theme/theme.dart';
import 'package:vms_mobile/features/auth/auth_controller.dart';
import 'package:vms_mobile/features/auth/auth_state.dart';
import 'package:vms_mobile/features/auth/login_screen.dart';

/// R-21: cooldown login terlihat di HP. (Kartu peran kantor dihapus — R-33: akun kantor ditolak login HP.)

class _Locked extends AuthController {
  @override
  AuthState build() => AuthUnauthenticated(
    error: 'Terlalu banyak kegagalan login. Coba lagi dalam 5 menit.',
    lockedUntil: DateTime.now().add(const Duration(minutes: 5)),
  );
}

class _Wrong extends AuthController {
  @override
  AuthState build() => const AuthUnauthenticated(
    error: 'Email atau kata sandi salah. Sisa 3 percobaan.',
  );
}

Widget _app(AuthController Function() auth, Widget home) => ProviderScope(
  overrides: [authControllerProvider.overrideWith(auth)],
  child: ShadApp(
    theme: VmsShadTheme.light,
    materialThemeBuilder: (context, _) => VmsTheme.light,
    home: Scaffold(body: home),
  ),
);

void main() {
  testWidgets('login terkunci: hitung mundur & tombol Masuk mati', (
    tester,
  ) async {
    await tester.pumpWidget(_app(_Locked.new, const LoginScreen()));
    await tester.pump(const Duration(seconds: 1));

    expect(find.byKey(const Key('login-locked')), findsOneWidget);
    final button = tester.widget<ShadButton>(find.byType(ShadButton).last);
    expect(button.onPressed, isNull);
    expect(find.textContaining('Tunggu 0'), findsOneWidget);

    await tester.pumpWidget(const SizedBox()); // hentikan detak hitung mundur
  });

  testWidgets('salah sandi: pesan server (sisa percobaan) tampil', (
    tester,
  ) async {
    await tester.pumpWidget(_app(_Wrong.new, const LoginScreen()));
    await tester.pump(const Duration(seconds: 1));

    expect(
      find.text('Email atau kata sandi salah. Sisa 3 percobaan.'),
      findsOneWidget,
    );
    expect(find.byKey(const Key('login-locked')), findsNothing);
  });
}
