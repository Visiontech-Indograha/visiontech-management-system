import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import 'auth_controller.dart';
import 'auth_state.dart';

/// Gerbang lokal saat sesi sudah sah (token direstore) tapi user pernah
/// mengaktifkan login sidik jari di Profil (plan Keputusan 7). Otomatis
/// memicu prompt sistem begitu layar ini terbuka; gagal/dibatalkan
/// menampilkan tombol coba lagi + opsi jatuh ke form password biasa.
class BiometricLockScreen extends ConsumerStatefulWidget {
  const BiometricLockScreen({super.key});

  @override
  ConsumerState<BiometricLockScreen> createState() =>
      _BiometricLockScreenState();
}

class _BiometricLockScreenState extends ConsumerState<BiometricLockScreen> {
  bool _isAuthenticating = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _authenticate());
  }

  Future<void> _authenticate() async {
    final authState = ref.read(authControllerProvider);
    if (authState is! AuthLocked) return;
    setState(() {
      _isAuthenticating = true;
      _error = null;
    });
    final success = await ref
        .read(biometricAuthProvider)
        .authenticate('Verifikasi sidik jari untuk membuka VMS Mobile');
    if (!mounted) return;
    if (success) {
      await ref
          .read(authControllerProvider.notifier)
          .unlockWithBiometrics(authState.user);
    } else {
      setState(() => _error = 'Verifikasi sidik jari gagal atau dibatalkan.');
    }
    if (mounted) setState(() => _isAuthenticating = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.fingerprint,
                  size: 72,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(height: 16),
                Text(
                  'Verifikasi Sidik Jari',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 8),
                Text(
                  'Sesi Anda masih aktif -- verifikasi sidik jari untuk melanjutkan.',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                if (_error != null) ...[
                  const SizedBox(height: 16),
                  Text(
                    _error!,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ],
                const SizedBox(height: 24),
                FilledButton.icon(
                  onPressed: _isAuthenticating ? null : _authenticate,
                  icon: _isAuthenticating
                      ? const SizedBox(
                          height: 16,
                          width: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.fingerprint),
                  label: const Text('Coba Lagi'),
                ),
                const SizedBox(height: 12),
                TextButton(
                  // switchToPasswordLogin, BUKAN logout(): logout menunggu
                  // panggilan ke server lebih dulu, sehingga jalan keluar
                  // darurat ini justru menggantung saat tidak ada sinyal.
                  onPressed: () => ref
                      .read(authControllerProvider.notifier)
                      .switchToPasswordLogin(),
                  child: const Text('Masuk dengan Password'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
