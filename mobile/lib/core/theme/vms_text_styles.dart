import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'vms_colors.dart';

/// Skala tipografi VMS.
/// Sumber: docs/design/tokens.json §font.scale
/// Font: Plus Jakarta Sans (paket: google_fonts)
/// Jangan buat TextStyle di luar file ini.
abstract final class VmsTextStyles {
  // Setiap gaya membawa keluarga huruf Plus Jakarta Sans (google_fonts) — tanpa ini teks yang
  // memakai VmsTextStyles langsung jatuh ke Roboto (temuan R-14). Judul dipertegas (w700/w800).
  static TextStyle _j(TextStyle s) => GoogleFonts.plusJakartaSans(textStyle: s);

  static final TextStyle display = _j(
    const TextStyle(
      fontSize: 30,
      height: 36 / 30,
      fontWeight: FontWeight.w800,
      letterSpacing: -0.02 * 30,
      color: VmsColors.neutral900,
    ),
  );

  static final TextStyle titleLg = _j(
    const TextStyle(
      fontSize: 24,
      height: 32 / 24,
      fontWeight: FontWeight.w800,
      letterSpacing: -0.015 * 24,
      color: VmsColors.neutral900,
    ),
  );

  static final TextStyle title = _j(
    const TextStyle(
      fontSize: 20,
      height: 28 / 20,
      fontWeight: FontWeight.w700,
      letterSpacing: -0.01 * 20,
      color: VmsColors.neutral900,
    ),
  );

  static final TextStyle heading = _j(
    const TextStyle(
      fontSize: 18,
      height: 26 / 18,
      fontWeight: FontWeight.w700,
      letterSpacing: -0.005 * 18,
      color: VmsColors.neutral900,
    ),
  );

  static final TextStyle subheading = _j(
    const TextStyle(
      fontSize: 16,
      height: 24 / 16,
      fontWeight: FontWeight.w600,
      color: VmsColors.neutral800,
    ),
  );

  static final TextStyle body = _j(
    const TextStyle(
      fontSize: 16,
      height: 24 / 16,
      fontWeight: FontWeight.w400,
      color: VmsColors.neutral800,
    ),
  );

  static final TextStyle bodySm = _j(
    const TextStyle(
      fontSize: 14,
      height: 20 / 14,
      fontWeight: FontWeight.w400,
      color: VmsColors.neutral800,
    ),
  );

  static final TextStyle caption = _j(
    const TextStyle(
      fontSize: 12,
      height: 16 / 12,
      fontWeight: FontWeight.w500,
      letterSpacing: 0.01 * 12,
      color: VmsColors.neutral500,
    ),
  );

  /// OVERLINE: hanya dipakai untuk label tabel/section.
  /// Tampil huruf besar secara otomatis via textCapitalization atau toUpperCase().
  static final TextStyle overline = _j(
    const TextStyle(
      fontSize: 12,
      height: 16 / 12,
      fontWeight: FontWeight.w600,
      letterSpacing: 0.06 * 12,
      color: VmsColors.neutral500,
    ),
  );
}
