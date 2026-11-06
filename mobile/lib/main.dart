import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import 'core/connectivity_sync.dart';
import 'core/location_helper.dart';
import 'core/theme/theme.dart';
import 'features/hse/k3_campaign_gate.dart';
import 'features/update/update_ui.dart';
import 'shared/app_frame.dart';
import 'shared/router.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Plus Jakarta Sans dibundel di assets/google_fonts/ — pembukaan pertama tanpa internet tetap
  // memakai huruf yang benar; tidak ada unduhan huruf saat berjalan.
  GoogleFonts.config.allowRuntimeFetching = false;
  LicenseRegistry.addLicense(() async* {
    final license = await rootBundle.loadString('assets/google_fonts/OFL.txt');
    yield LicenseEntryWithLineBreaks(['Plus Jakarta Sans'], license);
  });
  await initializeDateFormatting('id_ID');
  runApp(const ProviderScope(child: VmsMobileApp()));
}

class VmsMobileApp extends ConsumerWidget {
  const VmsMobileApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);

    // GPS dihangatkan sejak aplikasi dibuka agar absen & foto berlokasi tidak menunggu lama.
    return LocationWarmerScope(
      child: ConnectivitySyncWatcher(
        // shadcn_ui (R-14) + tema Material VMS untuk layar yang belum dimigrasi. Mode gelap di luar MVP (K-23).
        child: ShadApp.router(
          title: 'Visiontech',
          theme: VmsShadTheme.light,
          darkTheme: VmsShadTheme.light,
          themeMode: ThemeMode.light,
          materialThemeBuilder: (context, _) => VmsTheme.light,
          routerConfig: router,
          // Bahasa Indonesia: pemilih tanggal, penghitung karakter, dan teks bawaan Material tidak berbahasa Inggris.
          locale: const Locale('id', 'ID'),
          supportedLocales: const [Locale('id', 'ID')],
          localizationsDelegates: const [
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          // ScaffoldMessenger (SnackBar) + safe zone kiri/kanan — lihat shared/app_frame.dart.
          // Gerbang pembaruan wajib (docs/32) di atas Navigator: berlaku juga untuk layar login.
          builder: (context, child) => vmsAppFrame(
            context,
            AppUpdateGate(
              // Popup K3 wajib baca: tampil di atas semua layar (termasuk login); hanya saat sudah login.
              child: K3CampaignGate(child: child ?? const SizedBox.shrink()),
            ),
          ),
        ),
      ),
    );
  }
}
