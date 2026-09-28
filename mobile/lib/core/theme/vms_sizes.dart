/// Token ukuran dan spasi VMS.
/// Sumber: docs/design/tokens.json §size, §space, §radius, §layout
abstract final class VmsSizes {
  // ── Spasi (8-pt grid) ──────────────────────────────────────────────────────
  static const double s0 = 0;
  static const double s2 = 2;
  static const double s4 = 4;
  static const double s8 = 8;
  static const double s12 = 12;
  static const double s16 = 16;
  static const double s20 = 20;
  static const double s24 = 24;
  static const double s32 = 32;
  static const double s40 = 40;
  static const double s48 = 48;
  static const double s64 = 64;

  // ── Radius ─────────────────────────────────────────────────────────────────
  static const double radiusSm = 4;
  static const double radiusMd = 10;
  static const double radiusLg = 14; // default kartu, tombol, input (R-14)
  static const double radiusXl = 24; // dialog, lembar bawah (R-14)
  static const double radiusFull = 9999;

  // ── Ukuran kontrol (touch-target 44 dp) ────────────────────────────────────
  static const double controlSm = 36;
  static const double control = 48; // tinggi tombol / sasaran sentuh (R-14)
  static const double controlLg = 52;

  // ── Ikon ───────────────────────────────────────────────────────────────────
  static const double iconSm = 16;
  static const double iconMd = 20;
  static const double iconLg = 24;

  // ── Avatar ─────────────────────────────────────────────────────────────────
  static const double avatarSm = 32;
  static const double avatarMd = 40;
  static const double avatarLg = 56;

  // ── Layout ─────────────────────────────────────────────────────────────────
  static const double gutter = 16; // padding horizontal layar
  static const double cardPadding = 16; // padding dalam kartu
  static const double listRowHeight = 64; // baris daftar standar
  static const double bottomNavHeight = 64;
  static const double headerHeight = 56;

  // ── Elevasi ─────────────────────────────────────────────────────────────────
  /// elevation 0 → flat (kartu, kontrol)
  /// elevation 1 → sedikit bayangan (dropdown)
  /// elevation 2 → melayang (bottom sheet, FAB)
  /// elevation 3 → dialog, modal
  static const double elevation0 = 0;
  static const double elevation1 = 1;
  static const double elevation2 = 2;
  static const double elevation3 = 3;
}
