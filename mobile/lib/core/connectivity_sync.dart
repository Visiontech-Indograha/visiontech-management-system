import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../features/auth/auth_controller.dart';
import '../features/auth/auth_state.dart';
import 'providers.dart';

bool _hasConnection(List<ConnectivityResult> results) =>
    results.any((r) => r != ConnectivityResult.none);

/// Widget tak-tampak yang mengawasi status jaringan & siklus hidup app, lalu
/// otomatis memicu `SyncEngine.syncAll()` begitu:
/// (a) koneksi baru saja PULIH dari kondisi tanpa jaringan sama sekali, atau
/// (b) app kembali ke foreground (mis. user membuka app lagi setelah lama di
///     background) -- keduanya skenario "otomatis online lagi" yang diminta,
/// supaya user tidak perlu ingat buka Profil > Sinkronisasi Sekarang.
///
/// Tidak melakukan apa-apa selama belum login (AuthUnauthenticated/Initial) --
/// tidak ada gunanya memanggil endpoint yang butuh token.
class ConnectivitySyncWatcher extends ConsumerStatefulWidget {
  const ConnectivitySyncWatcher({required this.child, super.key});

  final Widget child;

  @override
  ConsumerState<ConnectivitySyncWatcher> createState() =>
      _ConnectivitySyncWatcherState();
}

class _ConnectivitySyncWatcherState
    extends ConsumerState<ConnectivitySyncWatcher>
    with WidgetsBindingObserver {
  StreamSubscription<List<ConnectivityResult>>? _subscription;
  Timer? _retryTimer;
  bool _wasConnected = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _subscription = Connectivity().onConnectivityChanged.listen((results) {
      final isConnected = _hasConnection(results);
      if (isConnected && !_wasConnected) {
        _trySync();
      }
      _wasConnected = isConnected;
    });
    // Cakup juga kasus cold-start: app baru dibuka, sudah online, dan ada
    // antrian tersisa dari sesi sebelumnya (bukan cuma transisi offline->online
    // yang terdeteksi listener di atas).
    _trySync();
    // (c) Jaringan tetap tersambung tetapi server tak terjangkau (sinyal lemah, server mati):
    // tidak ada peristiwa konektivitas, jadi antrean dicoba ulang berkala selama masih ada isinya.
    _retryTimer = Timer.periodic(const Duration(seconds: 60), (_) async {
      if (await ref.read(syncEngineProvider).pendingOperationCount() > 0) {
        _trySync();
      }
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _retryTimer?.cancel();
    _subscription?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _trySync();
    }
  }

  void _trySync() {
    if (ref.read(authControllerProvider) is! AuthAuthenticated) return;
    // Sengaja tidak di-await (fire-and-forget) -- ini sinkronisasi oportunistik
    // di latar belakang, UI tidak perlu menunggu ataupun menampilkan loading.
    // syncTickProvider dinaikkan setelahnya supaya layar manapun yang sedang
    // terbuka (Absensi/Cuti/Logbook menyimpan riwayat sebagai State lokal,
    // bukan lewat provider reaktif) tahu harus memuat ulang datanya.
    ref.read(syncEngineProvider).syncAll().then((_) {
      if (mounted) ref.read(syncTickProvider.notifier).bump();
    });
  }

  @override
  Widget build(BuildContext context) => widget.child;
}
