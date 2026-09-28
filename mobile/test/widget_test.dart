import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import 'package:vms_mobile/core/theme/theme.dart';
import 'package:vms_mobile/features/auth/login_screen.dart';

/// LoginScreen memakai komponen shadcn_ui (R-12/R-14) → perlu ShadApp seperti di main.dart.
Widget _app() => ProviderScope(
  child: ShadApp(
    theme: VmsShadTheme.light,
    materialThemeBuilder: (context, _) => VmsTheme.light,
    home: const LoginScreen(),
  ),
);

void main() {
  testWidgets('LoginScreen menampilkan validasi saat form kosong disubmit', (
    tester,
  ) async {
    await tester.pumpWidget(_app());
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.widgetWithText(ShadButton, 'Masuk'));
    await tester.tap(find.widgetWithText(ShadButton, 'Masuk'));
    await tester.pumpAndSettle();

    expect(find.text('Email wajib diisi'), findsOneWidget);
    expect(find.text('Password wajib diisi'), findsOneWidget);
  });

  testWidgets('LoginScreen bisa diisi email & password', (tester) async {
    await tester.pumpWidget(_app());
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(EditableText).first, 'admin@lokal.test');
    await tester.enterText(find.byType(EditableText).last, 'password123');
    await tester.pump();

    expect(find.text('admin@lokal.test'), findsOneWidget);
  });
}
