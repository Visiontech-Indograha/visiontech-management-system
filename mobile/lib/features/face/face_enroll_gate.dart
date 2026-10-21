import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../auth/auth_controller.dart';
import 'face_flow.dart';

/// Status wajah akun ini. Galat (mis. tanpa sinyal) TIDAK memblokir: pekerja lapangan harus tetap bisa masuk saat
/// offline; gerbang hanya menutup bila server SECARA EKSPLISIT menyatakan wajib (`required`) dan belum terdaftar.
final faceGateProvider = FutureProvider.autoDispose<bool>((ref) async {
  try {
    final st = await ref.read(syncEngineProvider).api.faceStatus();
    return st['required'] == true && st['enrolled'] != true;
  } catch (_) {
    return false;
  }
});

/// Membungkus isi aplikasi: bila akun wajib mendaftarkan wajah dan belum, menu lain tidak bisa dibuka.
class FaceEnrollGate extends ConsumerWidget {
  const FaceEnrollGate({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final required = ref.watch(faceGateProvider);
    return required.when(
      data: (needs) => needs ? const _EnrollRequiredScreen() : child,
      loading: () =>
          const Scaffold(body: Center(child: CircularProgressIndicator())),
      error: (_, _) => child,
    );
  }
}

class _EnrollRequiredScreen extends ConsumerStatefulWidget {
  const _EnrollRequiredScreen();

  @override
  ConsumerState<_EnrollRequiredScreen> createState() =>
      _EnrollRequiredScreenState();
}

class _EnrollRequiredScreenState extends ConsumerState<_EnrollRequiredScreen> {
  bool _busy = false;

  Future<void> _start() async {
    setState(() => _busy = true);
    try {
      final out = await runFaceEnrollment(context, ref);
      if (!mounted) return;
      if (out.message != null) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(out.message!)));
      }
      if (out.ok) ref.invalidate(faceGateProvider);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(apiErrorMessage(e))));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.face_retouching_natural_rounded,
                size: 72,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(height: 16),
              Text(
                'Daftarkan wajah Anda',
                style: theme.textTheme.headlineSmall,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                'Absensi memakai pengenalan wajah. Pendaftaran wajib dilakukan sekali sebelum Anda dapat membuka menu '
                'lainnya. Siapkan tempat dengan cahaya cukup, lalu ikuti petunjuk pose di kamera.',
                textAlign: TextAlign.center,
                style: theme.textTheme.bodyMedium,
              ),
              const SizedBox(height: 24),
              FilledButton.icon(
                key: const Key('face-gate-start'),
                onPressed: _busy ? null : _start,
                icon: _busy
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.camera_alt_rounded),
                label: const Text('Mulai pendaftaran wajah'),
              ),
              TextButton(
                onPressed: _busy
                    ? null
                    : () => ref.read(authControllerProvider.notifier).logout(),
                child: const Text('Keluar'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
