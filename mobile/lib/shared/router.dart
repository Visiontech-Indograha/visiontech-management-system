import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/attendance/attendance_screen.dart';
import '../features/auth/auth_controller.dart';
import '../features/auth/auth_state.dart';
import '../features/auth/biometric_lock_screen.dart';
import '../features/auth/login_screen.dart';
import '../features/gallery/photo_gallery_screen.dart';
import '../features/plans/daily_plans_screen.dart';
import '../features/profile/profile_screen.dart';
import 'home_shell.dart';
import 'splash_screen.dart';

/// Menjembatani AuthState (riverpod) ke GoRouter -- go_router butuh
/// Listenable biasa (bukan langsung provider) untuk memicu re-evaluasi
/// redirect setiap kali status auth berubah.
class _RouterRefreshNotifier extends ChangeNotifier {
  _RouterRefreshNotifier(Ref ref) {
    ref.listen<AuthState>(authControllerProvider, (previous, next) {
      if (previous.runtimeType != next.runtimeType) notifyListeners();
    });
  }
}

final routerProvider = Provider<GoRouter>((ref) {
  final refreshNotifier = _RouterRefreshNotifier(ref);
  ref.onDispose(refreshNotifier.dispose);

  return GoRouter(
    initialLocation: '/splash',
    refreshListenable: refreshNotifier,
    redirect: (context, state) {
      final authState = ref.read(authControllerProvider);
      final isLoginRoute = state.matchedLocation == '/login';
      final isSplashRoute = state.matchedLocation == '/splash';
      final isBiometricLockRoute = state.matchedLocation == '/biometric-lock';

      if (authState is AuthInitial || authState is AuthLoading) {
        return isSplashRoute ? null : '/splash';
      }
      // Sesi sudah sah tapi masih terkunci di balik sidik jari lokal (plan
      // Keputusan 7) -- tahan di layar unlock sampai berhasil, TIDAK boleh
      // tembus ke konten aplikasi lewat rute manapun.
      if (authState is AuthLocked) {
        return isBiometricLockRoute ? null : '/biometric-lock';
      }
      if (authState is AuthAuthenticated) {
        return (isLoginRoute || isSplashRoute || isBiometricLockRoute)
            ? '/'
            : null;
      }
      // AuthUnauthenticated
      return isLoginRoute ? null : '/login';
    },
    routes: [
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
      GoRoute(
        path: '/splash',
        builder: (context, state) => const SplashScreen(),
      ),
      GoRoute(
        path: '/biometric-lock',
        builder: (context, state) => const BiometricLockScreen(),
      ),
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) =>
            HomeShell(navigationShell: navigationShell),
        branches: [
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/',
                builder: (context, state) => const AttendanceScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/plans',
                builder: (context, state) => const DailyPlansScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/gallery',
                builder: (context, state) =>
                    const PhotoGalleryScreen(asTab: true),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/profile',
                builder: (context, state) => const ProfileScreen(),
              ),
            ],
          ),
        ],
      ),
    ],
  );
});
