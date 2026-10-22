import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/theme/theme.dart';
import 'ui/vms_ui.dart' show splashMarkAsset;

/// Ditampilkan sebentar saat AuthController masih memeriksa sesi tersimpan
/// (token di secure storage) sebelum memutuskan arah navigasi awal.
///
/// R-14: identik dengan layar pembuka native (latar navy + tanda "V + swirl" 288 dp di tengah,
/// lihat android/.../launch_background.xml & values-v31) sehingga peralihan native → Flutter
/// tidak melompat. Di bawah tanda: logo putih + bilah muat emas.
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

/// Animasi pembuka: tanda "V" (sama dengan layar native) mengecil & naik, lalu logo asli
/// Visiontech Indograha muncul memudar dari bawah, diikuti bilah muat emas.
class _SplashScreenState extends State<SplashScreen> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 1100))
    ..forward();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // Logo sama persis dengan layar native (tanpa lompatan), lalu naik sedikit & bilah muat emas muncul.
    final lift = CurvedAnimation(
      parent: _c,
      curve: const Interval(0.1, 0.6, curve: Curves.easeOutCubic),
    );
    final bar = CurvedAnimation(
      parent: _c,
      curve: const Interval(0.5, 1, curve: Curves.easeOut),
    );
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light.copyWith(statusBarColor: Colors.transparent),
      child: Scaffold(
        backgroundColor: VmsColors.brand700,
        body: AnimatedBuilder(
          animation: _c,
          builder: (context, _) => Stack(
            alignment: Alignment.center,
            children: [
              Transform.translate(
                offset: Offset(0, -28 * lift.value),
                child: Image.asset(splashMarkAsset, width: 288, height: 288, semanticLabel: 'Visiontech Indograha'),
              ),
              Align(
                alignment: const Alignment(0, 0.18),
                child: Opacity(
                  opacity: bar.value,
                  child: Transform.translate(
                    offset: Offset(0, 12 * (1 - bar.value)),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(99),
                      child: SizedBox(
                        width: 120,
                        child: LinearProgressIndicator(
                          minHeight: 4,
                          color: VmsColors.gold,
                          backgroundColor: Colors.white.withValues(alpha: 0.15),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
