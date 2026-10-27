import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../core/theme/theme.dart';
import '../../shared/ui/vms_ui.dart';
import '../auth/auth_controller.dart';
import '../auth/auth_state.dart';
import '../face/face_flow.dart';
import '../sync/sync_queue_screen.dart';
import '../update/update_ui.dart';

const _roleLabel = {
  'ADMIN': 'Admin',
  'HR': 'HR',
  'PM': 'Project Manager',
  'FINANCE': 'Finance',
  'ASSET': 'Petugas aset',
  'OPS': 'Operasional',
  'LEADER': 'Ketua tim',
  'MEMBER': 'Karyawan lapangan',
};

/// Profil, tombol Sinkronisasi Manual, dan Logout.
class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  bool _isSyncing = false;
  String? _syncResultMessage;
  int _pendingPhotoCount = 0;
  int _pendingOperationCount = 0;
  int _deadLetterCount = 0;
  bool _biometricSupported = false;
  bool _biometricEnabled = false;
  bool _faceLoading = false;
  bool _isEnrolling = false;
  Map<String, dynamic>? _faceStatus;
  String? _faceError;
  Future<String>? _photoUrl;

  @override
  void initState() {
    super.initState();
    _loadSyncInfo();
    _loadBiometricState();
    _loadFaceState();
    _loadPhotoUrl();
  }

  /// URL bertanda tangan foto profil (berlaku 5 menit). Berkas dilayani API
  /// hanya setelah otorisasi, jadi URL harus diambil lewat `fileUrl`, bukan
  /// dipasang langsung sebagai path.
  void _loadPhotoUrl() {
    final authState = ref.read(authControllerProvider);
    final user = authState is AuthAuthenticated
        ? authState.user
        : (authState is AuthLocked ? authState.user : null);
    final id = user?.photoFileId;
    if (id == null || id.isEmpty) {
      _photoUrl = null;
      return;
    }
    _photoUrl = ref.read(syncEngineProvider).api.fileUrl(id);
  }

  /// Avatar bulat: foto profil bila ada, selain itu inisial nama (perilaku lama).
  Widget _avatar(String name, double size, {TextStyle? textStyle}) {
    final initials = name.isEmpty ? '?' : name.substring(0, 1).toUpperCase();
    final fallback = Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: const BoxDecoration(
        color: VmsColors.gold,
        shape: BoxShape.circle,
      ),
      child: Text(
        initials,
        style: (textStyle ?? VmsTextStyles.title).copyWith(
          color: VmsColors.brand900,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
    if (_photoUrl == null) return fallback;
    return FutureBuilder<String>(
      future: _photoUrl,
      builder: (context, snap) {
        final url = snap.data;
        if (url == null || url.isEmpty) return fallback;
        return ClipOval(
          child: Image.network(
            url,
            width: size,
            height: size,
            fit: BoxFit.cover,
            errorBuilder: (_, _, _) => fallback,
            loadingBuilder: (_, child, progress) =>
                progress == null ? child : fallback,
          ),
        );
      },
    );
  }

  Future<void> _loadFaceState() async {
    setState(() => _faceLoading = true);
    try {
      final res = await ref.read(syncEngineProvider).api.faceStatus();
      if (mounted) {
        setState(() {
          _faceStatus = res;
          _faceError = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _faceError = apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _faceLoading = false);
    }
  }

  Future<void> _enrollFaceFlow() async {
    if (!mounted) return;
    setState(() => _isEnrolling = true);
    try {
      final out = await runFaceEnrollment(context, ref);
      if (!mounted) return;
      if (out.message != null) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(out.message!)));
      }
      if (out.ok) await _loadFaceState();
    } finally {
      if (mounted) setState(() => _isEnrolling = false);
    }
  }

  Future<void> _loadBiometricState() async {
    final supported = await ref.read(biometricAuthProvider).isDeviceSupported();
    final enabled = await ref.read(tokenStorageProvider).readBiometricEnabled();
    if (mounted) {
      setState(() {
        _biometricSupported = supported;
        _biometricEnabled = enabled ?? false;
      });
    }
  }

  /// Mengaktifkan WAJIB verifikasi sidik jari dulu (bukti sensor benar
  /// bekerja di perangkat ini) -- menonaktifkan tidak perlu verifikasi apa
  /// pun. Lihat plan Keputusan 7: toggle manual di Profil, selain tawaran
  /// otomatis sekali setelah login pertama (lihat home_shell.dart).
  Future<void> _toggleBiometric(bool value) async {
    if (value) {
      final ok = await ref
          .read(biometricAuthProvider)
          .authenticate('Verifikasi sidik jari untuk mengaktifkan fitur ini');
      if (!ok) return;
    } else {
      // Mematikan gerbang keamanan layak dikonfirmasi. Sebelumnya sekali geser
      // langsung nonaktif tanpa pertanyaan apa pun -- mudah tersenggol.
      final yakin = await _konfirmasi(
        judul: 'Matikan Login Sidik Jari?',
        isi:
            'Setelah ini, membuka aplikasi tidak lagi meminta sidik jari. '
            'Siapa pun yang memegang HP ini bisa langsung melihat isinya.',
        tombol: 'Matikan',
      );
      if (!yakin) return;
    }
    await ref.read(tokenStorageProvider).saveBiometricEnabled(value);
    if (mounted) setState(() => _biometricEnabled = value);
  }

  Future<bool> _konfirmasi({
    required String judul,
    required String isi,
    required String tombol,
  }) async {
    final hasil = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(judul),
        content: Text(isi),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Batal'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: Text(tombol),
          ),
        ],
      ),
    );
    return hasil ?? false;
  }

  /// Ringkasan isi antrian: data tulis tertunda, foto tertunda, dan yang sudah
  /// berhenti dicoba. Sebelumnya layar ini hanya menghitung FOTO, sehingga
  /// cek-in/cuti/laporan yang tertahan di antrian sama sekali tidak terlihat.
  Future<void> _loadSyncInfo() async {
    final engine = ref.read(syncEngineProvider);
    final photos = await engine.pendingPhotoCount();
    final operations = await engine.pendingOperationCount();
    final stuck = await engine.deadLetterCount();
    if (mounted) {
      setState(() {
        _pendingPhotoCount = photos;
        _pendingOperationCount = operations;
        _deadLetterCount = stuck;
      });
    }
  }

  Future<void> _syncNow() async {
    setState(() {
      _isSyncing = true;
      _syncResultMessage = null;
    });
    try {
      final summary = await ref.read(syncEngineProvider).syncAll();
      ref.read(syncTickProvider.notifier).bump();
      await _loadSyncInfo();
      setState(() {
        _syncResultMessage = summary.hasErrors
            ? 'Sync selesai dengan sebagian gagal:\n${[...summary.pushErrors, ...summary.pullErrors].join('\n')}'
            : 'Sinkronisasi berhasil.';
      });
    } catch (e) {
      setState(() => _syncResultMessage = 'Sinkronisasi gagal: $e');
    } finally {
      if (mounted) setState(() => _isSyncing = false);
    }
  }

  Widget _stat(String label, int value, Accent accent, IconData icon) =>
      Expanded(
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: accent.soft,
            borderRadius: BorderRadius.circular(14),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, size: 18, color: accent.strong),
              const SizedBox(height: 6),
              Text(
                '$value',
                style: VmsTextStyles.title.copyWith(
                  color: accent.strong,
                  fontWeight: FontWeight.w800,
                  height: 1.1,
                ),
              ),
              Text(
                label,
                style: VmsTextStyles.caption.copyWith(color: accent.strong),
              ),
            ],
          ),
        ),
      );

  Future<void> _logout() async {
    // Logout membersihkan SELURUH data lokal termasuk antrian yang belum terkirim -- pertanyaannya
    // menyebutkan itu secara eksplisit supaya teknisi tidak kehilangan pekerjaan tanpa sadar.
    final tertunda =
        await ref.read(syncEngineProvider).pendingOperationCount() +
        await ref.read(syncEngineProvider).pendingPhotoCount();
    if (!mounted) return;
    final yakin = await _konfirmasi(
      judul: 'Keluar dari akun?',
      isi: tertunda > 0
          ? 'Masih ada $tertunda data yang BELUM terkirim ke server. '
                'Keluar sekarang akan menghapusnya dari HP ini. '
                'Sambungkan ke internet dan sinkronkan dulu bila datanya masih dibutuhkan.'
          : 'Anda perlu memasukkan email & password lagi untuk masuk.',
      tombol: 'Keluar',
    );
    if (!yakin) return;
    await ref.read(authControllerProvider.notifier).logout();
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authControllerProvider);
    final user = authState is AuthAuthenticated ? authState.user : null;
    final name = user?.displayName ?? '-';

    return Scaffold(
      appBar: VmsTopBar(trailing: _avatar(name, 44)),
      body: ListView(
        padding: safeListPadding(context),
        children: [
          HeroHeader(
            eyebrow: 'Profil',
            title: name,
            subtitle: user?.username,
            trailing: _avatar(name, 64),
            bottom: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                color: VmsColors.brand50,
                borderRadius: BorderRadius.circular(99),
              ),
              child: Text(
                _roleLabel[user?.role.wireValue] ?? user?.role.wireValue ?? '-',
                style: VmsTextStyles.caption.copyWith(
                  color: VmsColors.brand700,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SectionTitle('Sinkronisasi data'),
                FadeSlideIn(
                  child: SurfaceCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Row(
                          children: [
                            _stat(
                              'Data tertunda',
                              _pendingOperationCount,
                              Accent.blue,
                              Icons.cloud_upload_rounded,
                            ),
                            const SizedBox(width: 8),
                            _stat(
                              'Foto tertunda',
                              _pendingPhotoCount,
                              Accent.teal,
                              Icons.photo_rounded,
                            ),
                            const SizedBox(width: 8),
                            _stat(
                              'Perlu tindakan',
                              _deadLetterCount,
                              _deadLetterCount > 0 ? Accent.rose : Accent.slate,
                              Icons.report_rounded,
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Text(
                          'Data yang dibuat saat tanpa sinyal terkirim otomatis saat online. '
                          'Berkasnya tersimpan rapi di folder Visiontech pada HP.',
                          style: VmsTextStyles.bodySm.copyWith(
                            color: VmsColors.neutral500,
                          ),
                        ),
                        if (_syncResultMessage != null) ...[
                          const SizedBox(height: 12),
                          NoticeBanner(
                            icon: Icons.sync_rounded,
                            text: _syncResultMessage!,
                            accent:
                                _syncResultMessage!.startsWith(
                                  'Sinkronisasi berhasil',
                                )
                                ? Accent.emerald
                                : Accent.amber,
                          ),
                        ],
                        const SizedBox(height: 12),
                        PrimaryAction(
                          label: 'Sinkronkan sekarang',
                          icon: Icons.sync_rounded,
                          busy: _isSyncing,
                          onTap: _syncNow,
                        ),
                        const SizedBox(height: 8),
                        OutlinedButton.icon(
                          onPressed: () async {
                            await Navigator.of(context).push(
                              MaterialPageRoute(
                                builder: (_) => const SyncQueueScreen(),
                              ),
                            );
                            await _loadSyncInfo();
                          },
                          icon: const Icon(Icons.list_alt_rounded),
                          label: const Text('Lihat antrean sinkronisasi'),
                        ),
                      ],
                    ),
                  ),
                ),
                const SectionTitle('Layanan Karyawan'),
                for (final (route, icon, label) in const [
                  (
                    '/recap',
                    Icons.event_available_rounded,
                    'Rekap Absen & Uang Makan',
                  ),
                  ('/leaves', Icons.beach_access_rounded, 'Cuti & Izin'),
                  ('/assets', Icons.directions_car_rounded, 'Kendaraan & Alat'),
                  ('/overtime', Icons.more_time_rounded, 'Riwayat Lembur'),
                  ('/mess', Icons.home_work_rounded, 'Mess'),
                  ('/documents', Icons.badge_rounded, 'Dokumen Saya'),
                ])
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: FadeSlideIn(
                      index: 1,
                      child: SurfaceCard(
                        onTap: () => context.push(route),
                        child: Row(
                          children: [
                            IconTile(icon: icon, accent: Accent.teal, size: 40),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                label,
                                style: VmsTextStyles.bodySm.copyWith(
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                            const Icon(Icons.chevron_right_rounded),
                          ],
                        ),
                      ),
                    ),
                  ),
                const SectionTitle('Biometrik Wajah (Face API)'),
                FadeSlideIn(
                  index: 1,
                  child: SurfaceCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Row(
                          children: [
                            const IconTile(
                              icon: Icons.face_rounded,
                              accent: Accent.teal,
                              size: 40,
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'Pengenalan Wajah',
                                    style: VmsTextStyles.bodySm.copyWith(
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                  Text(
                                    _faceLoading
                                        ? 'Memeriksa status...'
                                        : (_faceStatus?['enrolled'] == true
                                              ? 'Wajah Terdaftar (Aktif)'
                                              : 'Belum Terdaftar'),
                                    style: VmsTextStyles.caption.copyWith(
                                      color: _faceStatus?['enrolled'] == true
                                          ? Accent.emerald.strong
                                          : VmsColors.neutral500,
                                      fontWeight:
                                          _faceStatus?['enrolled'] == true
                                          ? FontWeight.w600
                                          : FontWeight.normal,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            IconButton(
                              icon: const Icon(Icons.refresh_rounded, size: 20),
                              onPressed: _faceLoading ? null : _loadFaceState,
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Text(
                          'Pencocokan biometrik wajah dilakukan di server secara aman untuk memverifikasi absensi masuk dan pulang.',
                          style: VmsTextStyles.bodySm.copyWith(
                            color: VmsColors.neutral500,
                          ),
                        ),
                        if (_faceError != null) ...[
                          const SizedBox(height: 10),
                          NoticeBanner(
                            icon: Icons.info_outline_rounded,
                            text: _faceError!,
                          ),
                        ],
                        const SizedBox(height: 12),
                        if (_faceStatus?['enrolled'] == true)
                          Text(
                            'Perlu daftar ulang (ganti wajah/HP)? Minta HR mengatur ulang pendaftaran wajah Anda.',
                            style: VmsTextStyles.caption.copyWith(
                              color: VmsColors.neutral500,
                            ),
                          )
                        else if (_faceStatus?['required'] == true)
                          PrimaryAction(
                            label: 'Daftarkan Wajah (4 Foto)',
                            icon: Icons.camera_alt_rounded,
                            busy: _isEnrolling,
                            onTap: _isEnrolling || _faceLoading
                                ? null
                                : _enrollFaceFlow,
                          ),
                      ],
                    ),
                  ),
                ),
                if (_biometricSupported) ...[
                  const SectionTitle('Keamanan'),
                  FadeSlideIn(
                    index: 1,
                    child: SurfaceCard(
                      padding: const EdgeInsets.fromLTRB(14, 8, 8, 8),
                      child: Row(
                        children: [
                          const IconTile(
                            icon: Icons.fingerprint_rounded,
                            accent: Accent.violet,
                            size: 40,
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Login sidik jari',
                                  style: VmsTextStyles.bodySm.copyWith(
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                                Text(
                                  'Buka aplikasi cukup dengan sidik jari',
                                  style: VmsTextStyles.caption,
                                ),
                              ],
                            ),
                          ),
                          Switch(
                            value: _biometricEnabled,
                            onChanged: _toggleBiometric,
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
                const SectionTitle('Tentang aplikasi'),
                const FadeSlideIn(index: 2, child: AboutAppCard()),
                const SizedBox(height: 20),
                FadeSlideIn(
                  index: 3,
                  child: SurfaceCard(
                    onTap: _logout,
                    padding: const EdgeInsets.all(14),
                    child: Row(
                      children: [
                        const IconTile(
                          icon: Icons.logout_rounded,
                          accent: Accent.rose,
                          size: 40,
                        ),
                        const SizedBox(width: 12),
                        Text(
                          'Keluar',
                          style: VmsTextStyles.bodySm.copyWith(
                            fontWeight: FontWeight.w700,
                            color: Accent.rose.strong,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
