import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import 'vms_colors.dart';

/// Tema shadcn_ui dengan palet Visiontech (navy + emas, R-12/R-14) — sama dengan web.
abstract final class VmsShadTheme {
  static ShadThemeData get light => ShadThemeData(
    brightness: Brightness.light,
    radius: const BorderRadius.all(Radius.circular(14)),
    // Komponen shadcn memakai Plus Jakarta Sans juga (sama dengan VmsTextStyles).
    // Blockquote bawaan shadcn miring, padahal varian Italic tidak dibundel (unduhan huruf mati) —
    // tanpa ini aplikasi mencoba memuat PlusJakartaSans-Italic tiap kali dibuka dan mencatat galat.
    textTheme: ShadTextTheme.fromGoogleFont(
      GoogleFonts.plusJakartaSans,
      textTheme: ShadTextTheme(
        blockquote: ShadTextTheme().blockquote.copyWith(
          fontStyle: FontStyle.normal,
        ),
      ),
    ),
    colorScheme: const ShadColorScheme(
      background: VmsColors.neutral50,
      foreground: VmsColors.neutral800,
      card: VmsColors.neutral0,
      cardForeground: VmsColors.neutral800,
      popover: VmsColors.neutral0,
      popoverForeground: VmsColors.neutral800,
      primary: VmsColors.brand700,
      primaryForeground: VmsColors.neutral0,
      secondary: VmsColors.neutral100,
      secondaryForeground: VmsColors.neutral800,
      muted: VmsColors.neutral100,
      mutedForeground: VmsColors.neutral500,
      accent: VmsColors.brand50,
      accentForeground: VmsColors.brand700,
      destructive: VmsColors.dangerSolid,
      destructiveForeground: VmsColors.neutral0,
      border: VmsColors.neutral200,
      input: VmsColors.neutral300,
      ring: VmsColors.brand500,
      selection: VmsColors.brand100,
    ),
  );
}
