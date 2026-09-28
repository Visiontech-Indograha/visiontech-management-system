import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/providers.dart';
import '../features/auth/auth_controller.dart';
import 'sync_status_banner.dart';
import 'ui/floating_nav.dart';

/// Kerangka halaman utama dengan bottom navigation bar, dipakai oleh
/// StatefulShellRoute di router.dart supaya tiap tab punya riwayat navigasi
/// sendiri (indexed stack), bukan saling menimpa.
///
/// Juga tempat menawarkan aktivasi login sidik jari (plan Keputusan 7) tepat
/// SATU KALI setelah login password baru berhasil -- baru mount di sini
/// (bukan di LoginScreen) supaya tidak berebut dengan navigasi go_router
/// yang mengganti halaman begitu status auth berubah jadi AuthAuthenticated.
class HomeShell extends ConsumerStatefulWidget {
  const HomeShell({super.key, required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  @override
  ConsumerState<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends ConsumerState<HomeShell>
    with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    WidgetsBinding.instance.addPostFrameCallback((_) => _maybeOfferBiometric());
    // Lencana lonceng dihitung dari cache lokal supaya tidak menembak server
    // tiap kali digambar. Konsekuensinya: tepat setelah login cache-nya masih
    // kosong, dan lonceng tampak polos walau ada notifikasi menunggu. Satu
    // pengambilan saat aplikasi dibuka menutup celah itu.
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  /// Sejak kapan aplikasi ditinggalkan ke latar belakang.
  DateTime? _pausedAt;

  /// Ditinggalkan lebih lama dari ini baru dianggap perlu dikunci ulang.
  /// Perpindahan sekejap (menerima notifikasi, membuka kalkulator sebentar,
  /// atau prompt sistem milik aplikasi ini sendiri) tidak seharusnya memaksa
  /// teknisi memindai sidik jari berulang kali di tengah pekerjaan lapangan.
  static const _relockAfter = Duration(seconds: 20);

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused ||
        state == AppLifecycleState.hidden) {
      _pausedAt = DateTime.now();
      return;
    }
    if (state != AppLifecycleState.resumed) return;

    // Kunci ulang saat aplikasi kembali dari latar belakang. Tanpa ini gerbang
    // sidik jari hanya berlaku saat aplikasi dibuka dari kondisi mati total --
    // HP yang cuma di-minimize lalu berpindah tangan langsung menampilkan isi.
    final pausedAt = _pausedAt;
    _pausedAt = null;
    if (pausedAt == null ||
        DateTime.now().difference(pausedAt) < _relockAfter) {
      return;
    }
    ref.read(authControllerProvider.notifier).relockIfBiometricEnabled();
  }

  Future<void> _maybeOfferBiometric() async {
    if (!ref.read(authControllerProvider.notifier).consumeJustLoggedIn()) {
      return;
    }

    final tokenStorage = ref.read(tokenStorageProvider);
    if (await tokenStorage.readBiometricEnabled() != null) {
      return; // sudah pernah diputuskan
    }
    if (!await ref.read(biometricAuthProvider).isDeviceSupported()) return;
    if (!mounted) return;

    final enable = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Aktifkan Login Sidik Jari?'),
        content: const Text(
          'Buka aplikasi berikutnya cukup dengan sidik jari, tanpa perlu mengetik email & password lagi. '
          'Bisa diubah kapan saja lewat menu Profil.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Nanti Saja'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Aktifkan'),
          ),
        ],
      ),
    );
    if (enable != true) {
      await tokenStorage.saveBiometricEnabled(false);
      return;
    }

    // WAJIB verifikasi sensornya dulu, sama seperti toggle di layar Profil.
    // Menyalakan flag tanpa bukti sensor benar-benar bekerja bisa mengunci
    // user di layar sidik jari yang tidak pernah bisa dilewati.
    final verified = await ref
        .read(biometricAuthProvider)
        .authenticate('Verifikasi sidik jari untuk mengaktifkan login cepat');
    await tokenStorage.saveBiometricEnabled(verified);
    if (!verified && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Sidik jari belum terverifikasi. Login sidik jari belum diaktifkan.',
          ),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Column(
        children: [
          // Di atas bilah navigasi, bukan di puncak layar: tidak menumpuk di status bar
          // dan tidak menggeser AppBar tiap layar.
          Expanded(child: widget.navigationShell),
          const SyncStatusBanner(),
        ],
      ),
      bottomNavigationBar: FloatingNavBar(
        currentIndex: widget.navigationShell.currentIndex,
        onTap: (index) => widget.navigationShell.goBranch(
          index,
          initialLocation: index == widget.navigationShell.currentIndex,
        ),
        items: const [
          FloatingNavItem(
            icon: Icons.fingerprint_rounded,
            activeIcon: Icons.fingerprint_rounded,
            label: 'Absensi',
          ),
          FloatingNavItem(
            icon: Icons.assignment_outlined,
            activeIcon: Icons.assignment_rounded,
            label: 'Surat Kerja',
          ),
          FloatingNavItem(
            icon: Icons.person_outline_rounded,
            activeIcon: Icons.person_rounded,
            label: 'Profil',
          ),
        ],
      ),
    );
  }
}
