import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/providers.dart';
import '../features/sync/sync_queue_screen.dart';

/// Pita status tipis di atas seluruh layar: sedang online/offline, berapa data
/// yang belum terkirim, dan apakah ada yang butuh keputusan user.
///
/// Sebelumnya status ini HANYA ada di layar Profil, dan yang dihitung pun cuma
/// jumlah FOTO tertunda -- cek-in/cuti/laporan yang tertahan di antrian sama
/// sekali tidak terlihat. Teknisi tidak punya cara tahu datanya belum sampai
/// kecuali sengaja membuka Profil.
class SyncStatusBanner extends ConsumerStatefulWidget {
  const SyncStatusBanner({super.key});

  @override
  ConsumerState<SyncStatusBanner> createState() => _SyncStatusBannerState();
}

class _SyncStatusBannerState extends ConsumerState<SyncStatusBanner> {
  bool _offline = false;
  int _pendingOps = 0;
  int _pendingPhotos = 0;
  int _deadLetters = 0;
  StreamSubscription<List<ConnectivityResult>>? _connSub;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _connSub = Connectivity().onConnectivityChanged.listen((results) {
      final offline = results.every((r) => r == ConnectivityResult.none);
      if (mounted) setState(() => _offline = offline);
    });
    _muat();
    // Antrian berubah dari banyak layar (absensi, cuti, logbook, laporan);
    // menyegarkan berkala jauh lebih sederhana daripada menyambungkan callback
    // dari setiap titik yang menulis ke antrian.
    _refreshTimer = Timer.periodic(const Duration(seconds: 10), (_) => _muat());
  }

  @override
  void dispose() {
    _connSub?.cancel();
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _muat() async {
    final engine = ref.read(syncEngineProvider);
    final ops = await engine.pendingOperationCount();
    final photos = await engine.pendingPhotoCount();
    final stuck = await engine.deadLetterCount();
    final results = await Connectivity().checkConnectivity();
    if (!mounted) return;
    setState(() {
      _pendingOps = ops;
      _pendingPhotos = photos;
      _deadLetters = stuck;
      _offline = results.every((r) => r == ConnectivityResult.none);
    });
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final tertunda = _pendingOps + _pendingPhotos;

    // Tidak ada yang perlu dikhawatirkan: online, antrian kosong. Jangan
    // memakan ruang layar untuk memberitahu bahwa semuanya normal.
    if (!_offline && tertunda == 0 && _deadLetters == 0) {
      return const SizedBox.shrink();
    }

    final (
      Color latar,
      Color teks,
      IconData ikon,
      String pesan,
    ) = switch (null) {
      _ when _deadLetters > 0 => (
        scheme.errorContainer,
        scheme.onErrorContainer,
        Icons.report_problem_outlined,
        '$_deadLetters item gagal terkirim — butuh keputusan Anda',
      ),
      _ when _offline => (
        scheme.tertiaryContainer,
        scheme.onTertiaryContainer,
        Icons.cloud_off,
        tertunda > 0
            ? 'Offline — $tertunda data menunggu, akan dikirim otomatis'
            : 'Offline — data yang Anda buat tersimpan di HP dulu',
      ),
      _ => (
        scheme.secondaryContainer,
        scheme.onSecondaryContainer,
        Icons.cloud_upload_outlined,
        '$tertunda data menunggu dikirim',
      ),
    };

    return Material(
      color: latar,
      child: InkWell(
        onTap: () async {
          await Navigator.of(context)
              .push(MaterialPageRoute(builder: (_) => const SyncQueueScreen()));
          await _muat();
        },
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            children: [
              Icon(ikon, size: 18, color: teks),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  pesan,
                  style: TextStyle(fontSize: 12.5, color: teks),
                ),
              ),
              Icon(Icons.chevron_right, size: 18, color: teks),
            ],
          ),
        ),
      ),
    );
  }
}
