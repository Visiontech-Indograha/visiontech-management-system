// ignore_for_file: constant_identifier_names

import 'package:flutter/material.dart';

/// Palet warna VMS — sumber tunggal.
/// Jangan definisikan warna di tempat lain. Semua warna berasal dari sini.
/// Aturan lengkap: docs/18-SISTEM-DESAIN-UI.md · Token: docs/design/tokens.json
abstract final class VmsColors {
  // ── Brand ──────────────────────────────────────────────────────────────────
  static const Color brand50 = Color(0xFFEEF0FA);
  static const Color brand100 = Color(0xFFDDE1F3);
  static const Color brand200 = Color(0xFFBCC3E6);
  static const Color brand300 = Color(0xFF8F99D1);
  static const Color brand400 = Color(0xFF5F6BB6);
  static const Color brand500 = Color(0xFF3D4A9C);
  static const Color brand600 = Color(0xFF2E3A86);
  static const Color brand700 = Color(0xFF232C6F); // primary
  static const Color brand800 = Color(0xFF1B2359);
  static const Color brand900 = Color(0xFF141A43);

  /// Aksen emas logo Visiontech — dekoratif (penanda aktif), bukan untuk teks (R-12/R-14).
  static const Color gold = Color(0xFFF0C000);

  // ── Neutral ────────────────────────────────────────────────────────────────
  static const Color neutral0 = Color(0xFFFFFFFF);
  static const Color neutral25 = Color(0xFFF9FAFB);
  static const Color neutral50 = Color(0xFFF4F5F8); // background
  static const Color neutral100 = Color(0xFFECEEF3); // muted / secondary
  static const Color neutral200 = Color(0xFFE2E5EC); // border
  static const Color neutral300 = Color(0xFFCBD0DA); // border hover
  static const Color neutral400 = Color(0xFF8A91A0); // input border
  static const Color neutral500 = Color(0xFF5E6573); // muted foreground
  static const Color neutral600 = Color(0xFF4A505D); // icon / label
  static const Color neutral700 = Color(0xFF363B46);
  static const Color neutral800 = Color(0xFF252A36); // foreground
  static const Color neutral900 = Color(0xFF161A24); // heading

  // ── Status ─────────────────────────────────────────────────────────────────
  // success
  static const Color successFg = Color(0xFF1E6B43);
  static const Color successBg = Color(0xFFE8F3EC);
  static const Color successBorder = Color(0xFFB9DCC6);
  static const Color successSolid = Color(0xFF23804F);

  // warning
  static const Color warningFg = Color(0xFF8A5A12);
  static const Color warningBg = Color(0xFFFCF1DD);
  static const Color warningBorder = Color(0xFFEFD29F);
  static const Color warningSolid = Color(0xFFC7892A);

  // danger
  static const Color dangerFg = Color(0xFFA33A2C);
  static const Color dangerBg = Color(0xFFFBECEA);
  static const Color dangerBorder = Color(0xFFF0C2BA);
  static const Color dangerSolid = Color(0xFFB93C2D);

  // info
  static const Color infoFg = Color(0xFF2F5F8A);
  static const Color infoBg = Color(0xFFE8F0F8);
  static const Color infoBorder = Color(0xFFBCD2E8);
  static const Color infoSolid = Color(0xFF3569A0);

  // neutral-status
  static const Color neutralStatusFg = Color(0xFF4A505D);
  static const Color neutralStatusBg = Color(0xFFECEEF3);
  static const Color neutralStatusBorder = Color(0xFFE2E5EC);
  static const Color neutralStatusSolid = Color(0xFF5E6573);
}
