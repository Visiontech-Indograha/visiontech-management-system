import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

import 'vms_colors.dart';
import 'vms_page_transitions.dart';
import 'vms_sizes.dart';
import 'vms_text_styles.dart';

/// Tema utama VMS Mobile.
///
/// Cara pakai di main.dart:
/// ```dart
/// MaterialApp.router(
///   theme: VmsTheme.light,
///   darkTheme: VmsTheme.light,   // dark mode di luar cakupan MVP
///   themeMode: ThemeMode.light,
///   ...
/// )
/// ```
///
/// Aturan desain: docs/18-SISTEM-DESAIN-UI.md
/// Token: docs/design/tokens.json
abstract final class VmsTheme {
  static ThemeData get light {
    final base = ThemeData(useMaterial3: true, brightness: Brightness.light);

    final textTheme = GoogleFonts.plusJakartaSansTextTheme(base.textTheme)
        .copyWith(
          displayLarge: VmsTextStyles.display.copyWith(fontSize: 30),
          displayMedium: VmsTextStyles.titleLg,
          displaySmall: VmsTextStyles.title,
          headlineLarge: VmsTextStyles.heading,
          headlineMedium: VmsTextStyles.subheading,
          headlineSmall: VmsTextStyles.subheading,
          titleLarge: VmsTextStyles.subheading,
          titleMedium: VmsTextStyles.bodySm.copyWith(
            fontWeight: FontWeight.w600,
          ),
          titleSmall: VmsTextStyles.caption.copyWith(
            fontWeight: FontWeight.w600,
          ),
          bodyLarge: VmsTextStyles.body,
          bodyMedium: VmsTextStyles.bodySm,
          bodySmall: VmsTextStyles.caption,
          labelLarge: VmsTextStyles.bodySm.copyWith(
            fontWeight: FontWeight.w600,
          ),
          labelMedium: VmsTextStyles.caption.copyWith(
            fontWeight: FontWeight.w600,
          ),
          labelSmall: VmsTextStyles.overline,
        );

    return base.copyWith(
      colorScheme: _colorScheme,
      textTheme: textTheme,
      pageTransitionsTheme: const PageTransitionsTheme(
        builders: {
          TargetPlatform.android: VmsPageTransitionsBuilder(),
          TargetPlatform.iOS: VmsPageTransitionsBuilder(),
        },
      ),
      scaffoldBackgroundColor: const Color(0xFFF4F5F8),

      // ── AppBar ──────────────────────────────────────────────────────────────
      appBarTheme: AppBarTheme(
        backgroundColor: VmsColors.neutral0,
        foregroundColor: VmsColors.neutral900,
        elevation: VmsSizes.elevation0,
        scrolledUnderElevation: VmsSizes.elevation1,
        shadowColor: const Color(0x0F161A24),
        titleTextStyle: VmsTextStyles.subheading.copyWith(
          fontFamily: GoogleFonts.plusJakartaSans().fontFamily,
        ),
        systemOverlayStyle: const SystemUiOverlayStyle(
          statusBarColor: Colors.transparent,
          statusBarIconBrightness: Brightness.dark,
          statusBarBrightness: Brightness.light,
        ),
        surfaceTintColor: Colors.transparent,
      ),

      // ── Card ────────────────────────────────────────────────────────────────
      cardTheme: CardThemeData(
        color: VmsColors.neutral0,
        elevation: VmsSizes.elevation0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(VmsSizes.radiusLg),
          side: const BorderSide(color: VmsColors.neutral200),
        ),
        margin: EdgeInsets.zero,
      ),

      // ── ElevatedButton ──────────────────────────────────────────────────────
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: VmsColors.brand700,
          foregroundColor: VmsColors.neutral0,
          disabledBackgroundColor: VmsColors.neutral100,
          disabledForegroundColor: VmsColors.neutral400,
          elevation: VmsSizes.elevation0,
          minimumSize: const Size(double.infinity, VmsSizes.control),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(VmsSizes.radiusLg),
          ),
          textStyle: VmsTextStyles.bodySm.copyWith(fontWeight: FontWeight.w600),
          padding: const EdgeInsets.symmetric(horizontal: VmsSizes.s16),
        ),
      ),

      // ── OutlinedButton ──────────────────────────────────────────────────────
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: VmsColors.brand700,
          disabledForegroundColor: VmsColors.neutral400,
          minimumSize: const Size(double.infinity, VmsSizes.control),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(VmsSizes.radiusLg),
          ),
          side: const BorderSide(color: VmsColors.neutral200),
          textStyle: VmsTextStyles.bodySm.copyWith(fontWeight: FontWeight.w600),
          padding: const EdgeInsets.symmetric(horizontal: VmsSizes.s16),
        ),
      ),

      // ── TextButton ──────────────────────────────────────────────────────────
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: VmsColors.brand700,
          minimumSize: const Size(0, VmsSizes.control),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(VmsSizes.radiusLg),
          ),
          textStyle: VmsTextStyles.bodySm.copyWith(fontWeight: FontWeight.w600),
          padding: const EdgeInsets.symmetric(horizontal: VmsSizes.s12),
        ),
      ),

      // ── InputDecoration ─────────────────────────────────────────────────────
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0xFFF7F8FB),
        prefixIconColor: VmsColors.neutral500,
        suffixIconColor: VmsColors.neutral500,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: VmsSizes.s16,
          vertical: VmsSizes.s16,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(VmsSizes.radiusLg),
          borderSide: const BorderSide(color: VmsColors.neutral200),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(VmsSizes.radiusLg),
          borderSide: const BorderSide(color: VmsColors.neutral200),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(VmsSizes.radiusLg),
          borderSide: const BorderSide(color: VmsColors.brand500, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(VmsSizes.radiusLg),
          borderSide: const BorderSide(color: VmsColors.dangerSolid),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(VmsSizes.radiusLg),
          borderSide: const BorderSide(color: VmsColors.dangerSolid, width: 2),
        ),
        labelStyle: VmsTextStyles.bodySm.copyWith(color: VmsColors.neutral600),
        hintStyle: VmsTextStyles.body.copyWith(color: VmsColors.neutral400),
        errorStyle: VmsTextStyles.caption.copyWith(color: VmsColors.dangerFg),
        constraints: const BoxConstraints(minHeight: VmsSizes.control),
      ),

      // ── BottomNavigationBar ─────────────────────────────────────────────────
      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: VmsColors.neutral0,
        selectedItemColor: VmsColors.brand700,
        unselectedItemColor: VmsColors.neutral500,
        elevation: VmsSizes.elevation2,
        type: BottomNavigationBarType.fixed,
        selectedLabelStyle: VmsTextStyles.caption.copyWith(
          fontWeight: FontWeight.w600,
          color: VmsColors.brand700,
        ),
        unselectedLabelStyle: VmsTextStyles.caption,
      ),

      // ── NavigationBar (bawah) — pil lembut + ikon/label navy (R-14) ─────────
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: VmsColors.neutral0,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        height: 68,
        indicatorColor: VmsColors.brand50,
        indicatorShape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
        ),
        iconTheme: WidgetStateProperty.resolveWith(
          (s) => IconThemeData(
            color: s.contains(WidgetState.selected)
                ? VmsColors.brand700
                : VmsColors.neutral500,
            size: 24,
          ),
        ),
        labelTextStyle: WidgetStateProperty.resolveWith(
          (s) => VmsTextStyles.caption.copyWith(
            fontWeight: s.contains(WidgetState.selected)
                ? FontWeight.w700
                : FontWeight.w500,
            color: s.contains(WidgetState.selected)
                ? VmsColors.brand700
                : VmsColors.neutral500,
          ),
        ),
      ),

      // ── Divider ─────────────────────────────────────────────────────────────
      // ── FilledButton / menu dropdown / popup (R-14) ─────────────────────────
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: VmsColors.brand700,
          foregroundColor: VmsColors.neutral0,
          minimumSize: const Size(64, VmsSizes.control),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(VmsSizes.radiusLg),
          ),
          textStyle: VmsTextStyles.bodySm.copyWith(fontWeight: FontWeight.w700),
          padding: const EdgeInsets.symmetric(horizontal: 20),
        ),
      ),
      dropdownMenuTheme: DropdownMenuThemeData(
        menuStyle: MenuStyle(
          backgroundColor: const WidgetStatePropertyAll(VmsColors.neutral0),
          surfaceTintColor: const WidgetStatePropertyAll(Colors.transparent),
          elevation: const WidgetStatePropertyAll(8),
          shadowColor: const WidgetStatePropertyAll(Color(0x33161A24)),
          shape: WidgetStatePropertyAll(
            RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          ),
        ),
      ),
      popupMenuTheme: PopupMenuThemeData(
        color: VmsColors.neutral0,
        surfaceTintColor: Colors.transparent,
        elevation: 8,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        textStyle: VmsTextStyles.body,
      ),

      dividerTheme: const DividerThemeData(
        color: VmsColors.neutral200,
        thickness: 1,
        space: 1,
      ),

      // ── ListTile ────────────────────────────────────────────────────────────
      listTileTheme: ListTileThemeData(
        minLeadingWidth: VmsSizes.s0,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: VmsSizes.s16,
          vertical: VmsSizes.s8,
        ),
        titleTextStyle: VmsTextStyles.body,
        subtitleTextStyle: VmsTextStyles.bodySm.copyWith(
          color: VmsColors.neutral500,
        ),
        iconColor: VmsColors.neutral600,
        tileColor: VmsColors.neutral0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(VmsSizes.radiusMd),
        ),
      ),

      // ── Chip ────────────────────────────────────────────────────────────────
      chipTheme: ChipThemeData(
        backgroundColor: VmsColors.neutral100,
        labelStyle: VmsTextStyles.caption.copyWith(color: VmsColors.neutral700),
        side: BorderSide.none,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(VmsSizes.radiusFull),
        ),
        padding: const EdgeInsets.symmetric(
          horizontal: VmsSizes.s8,
          vertical: VmsSizes.s2,
        ),
      ),

      // ── Dialog ──────────────────────────────────────────────────────────────
      dialogTheme: DialogThemeData(
        backgroundColor: VmsColors.neutral0,
        surfaceTintColor: Colors.transparent,
        elevation: VmsSizes.elevation3,
        insetPadding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 24.0),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(VmsSizes.radiusXl),
        ),
        titleTextStyle: VmsTextStyles.heading.copyWith(
          fontWeight: FontWeight.w800,
        ),
        contentTextStyle: VmsTextStyles.body.copyWith(
          color: VmsColors.neutral600,
        ),
        actionsPadding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
      ),

      // ── BottomSheet ─────────────────────────────────────────────────────────
      bottomSheetTheme: const BottomSheetThemeData(
        backgroundColor: VmsColors.neutral0,
        surfaceTintColor: Colors.transparent,
        elevation: VmsSizes.elevation2,
        modalBarrierColor: Color(0x66000000),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(
            top: Radius.circular(VmsSizes.radiusXl),
          ),
        ),
        showDragHandle: true,
        dragHandleColor: VmsColors.neutral300,
        clipBehavior: Clip.antiAliasWithSaveLayer,
      ),

      // ── SnackBar ─────────────────────────────────────────────────────────────
      snackBarTheme: SnackBarThemeData(
        backgroundColor: VmsColors.neutral900,
        contentTextStyle: VmsTextStyles.bodySm.copyWith(
          color: VmsColors.neutral0,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(VmsSizes.radiusLg),
        ),
        behavior: SnackBarBehavior.floating,
        insetPadding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
        elevation: VmsSizes.elevation2,
      ),

      // ── Switch ──────────────────────────────────────────────────────────────
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) return VmsColors.neutral0;
          return VmsColors.neutral400;
        }),
        trackColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) return VmsColors.brand700;
          return VmsColors.neutral200;
        }),
        trackOutlineColor: WidgetStateProperty.all(Colors.transparent),
      ),

      // ── ProgressIndicator ───────────────────────────────────────────────────
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: VmsColors.brand700,
        linearTrackColor: VmsColors.neutral100,
        circularTrackColor: VmsColors.brand50,
      ),

      // ── TabBar ──────────────────────────────────────────────────────────────
      tabBarTheme: TabBarThemeData(
        labelColor: VmsColors.brand700,
        unselectedLabelColor: VmsColors.neutral500,
        labelStyle: VmsTextStyles.bodySm.copyWith(fontWeight: FontWeight.w600),
        unselectedLabelStyle: VmsTextStyles.bodySm,
        indicator: const UnderlineTabIndicator(
          borderSide: BorderSide(color: VmsColors.brand700, width: 2),
        ),
        indicatorSize: TabBarIndicatorSize.tab,
        dividerColor: VmsColors.neutral200,
        overlayColor: WidgetStateProperty.all(VmsColors.brand50),
      ),

      // ── Badge ───────────────────────────────────────────────────────────────
      badgeTheme: BadgeThemeData(
        backgroundColor: VmsColors.dangerSolid,
        textColor: VmsColors.neutral0,
        smallSize: VmsSizes.s8,
        largeSize: VmsSizes.s20,
        textStyle: VmsTextStyles.caption.copyWith(color: VmsColors.neutral0),
      ),
    );
  }

  // ── ColorScheme ─────────────────────────────────────────────────────────────
  static const ColorScheme _colorScheme = ColorScheme(
    brightness: Brightness.light,

    primary: VmsColors.brand700,
    onPrimary: VmsColors.neutral0,
    primaryContainer: VmsColors.brand100,
    onPrimaryContainer: VmsColors.brand900,

    secondary: VmsColors.neutral100,
    onSecondary: VmsColors.neutral800,
    secondaryContainer: VmsColors.brand50,
    onSecondaryContainer: VmsColors.brand700,

    tertiary: VmsColors.infoSolid,
    onTertiary: VmsColors.neutral0,
    tertiaryContainer: VmsColors.infoBg,
    onTertiaryContainer: VmsColors.infoFg,

    error: VmsColors.dangerSolid,
    onError: VmsColors.neutral0,
    errorContainer: VmsColors.dangerBg,
    onErrorContainer: VmsColors.dangerFg,

    surface: VmsColors.neutral0,
    onSurface: VmsColors.neutral800,
    surfaceContainerHighest: VmsColors.neutral100,
    onSurfaceVariant: VmsColors.neutral600,
    surfaceTint: Colors.transparent,

    outline: VmsColors.neutral200,
    outlineVariant: VmsColors.neutral300,
    shadow: Color(0x19161A24),
    scrim: Color(0x7A161A24),

    inverseSurface: VmsColors.neutral800,
    onInverseSurface: VmsColors.neutral0,
    inversePrimary: VmsColors.brand300,
  );
}
