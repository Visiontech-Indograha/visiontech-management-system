import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/theme/theme.dart';
import 'ui/vms_ui.dart' show logoWhiteAsset, splashMarkAsset;

/// Ditampilkan sebentar saat AuthController masih memeriksa sesi tersimpan
/// (token di secure storage) sebelum memutuskan arah navigasi awal.
///
/// R-14: identik dengan layar pembuka native (latar navy + tanda "V + swirl" 288 dp di tengah,
/// lihat android/.../launch_background.xml & values-v31) sehingga peralihan native → Flutter
/// tidak melompat. Di bawah tanda: logo putih + bilah muat emas.
class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light.copyWith(
        statusBarColor: Colors.transparent,
      ),
      child: Scaffold(
        backgroundColor: VmsColors.brand700,
        body: Stack(
          alignment: Alignment.center,
          children: [
            Image.asset(
              splashMarkAsset,
              width: 288,
              height: 288,
              semanticLabel: 'Visiontech',
            ),
            Align(
              alignment: const Alignment(0, 0.42),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Image.asset(logoWhiteAsset, height: 30),
                  const SizedBox(height: 20),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(99),
                    child: SizedBox(
                      width: 96,
                      child: LinearProgressIndicator(
                        minHeight: 4,
                        color: VmsColors.gold,
                        backgroundColor: Colors.white.withValues(alpha: 0.15),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
