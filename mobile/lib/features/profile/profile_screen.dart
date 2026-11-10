import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../core/theme/theme.dart';
import '../../shared/ui/vms_network_image.dart';
import '../../shared/ui/vms_ui.dart';
import '../auth/auth_controller.dart';
import '../auth/auth_state.dart';
import '../face/face_flow.dart';
import '../notifications/notifications_screen.dart' show NotificationBell;
import '../sync/sync_queue_screen.dart';
import '../update/update_ui.dart';
import 'sessions_screen.dart';

const _roleLabel = {
  'ADMIN': 'Admin',
  'HR': 'HR',
  'PM': 'Atasan',
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
  bool _photoChanged = false;
  bool _photoBusy = false;
  String? _photoId;

  @override
  void initState() {
    super.initState();
    _loadSyncInfo();
    _loadBiometricState();
    _loadFaceState();
  }

  /// Id berkas foto profil yang tampil: hasil ganti foto di layar ini, selain itu dari `/auth/me`.
  String? _currentPhotoId() {
    if (_photoChanged) return _photoId;
    final authState = ref.read(authControllerProvider);
    final user = authState is AuthAuthenticated
        ? authState.user
        : (authState is AuthLocked ? authState.user : null);
    return user?.photoFileId;
  }

  /// Avatar bulat: foto profil bila ada, selain itu inisial nama.
  Widget _avatar(String name, double size, {bool editable = false}) {
    final avatar = VmsAvatar(name: name, fileId: _currentPhotoId(), radius: size / 2);
    return editable
        ? InkWell(customBorder: const CircleBorder(), onTap: _changePhoto, child: avatar)
        : avatar;
  }

  Future<void> _changePhoto() async {
    if (_photoBusy) return;
    final choice = await showModalBottomSheet<String>(
      context: context,
      builder: (_) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.photo_camera_outlined),
              title: const Text('Ambil foto'),
              onTap: () => Navigator.pop(context, 'camera'),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library_outlined),
              title: const Text('Pilih dari galeri'),
              onTap: () => Navigator.pop(context, 'gallery'),
            ),
            if (_currentPhotoId() != null)
              ListTile(
                leading: const Icon(Icons.delete_outline),
                title: const Text('Hapus foto'),
                onTap: () => Navigator.pop(context, 'remove'),
              ),
          ],
        ),
      ),
    );
    if (choice == null || !mounted) return;
    setState(() => _photoBusy = true);
    try {
      final api = ref.read(syncEngineProvider).api;
      String? fileId;
      if (choice != 'remove') {
        final picked = await ImagePicker().pickImage(
          source: choice == 'camera' ? ImageSource.camera : ImageSource.gallery,
          preferredCameraDevice: CameraDevice.front,
          maxWidth: 1024,
          imageQuality: 85,
        );
        if (picked == null) return;
        fileId = await api.uploadFile(File(picked.path));
      }
      await api.setMyPhoto(fileId);
      if (!mounted) return;
      setState(() {
        _photoChanged = true;
        _photoId = fileId;
      });
      showVmsToast(context, fileId == null ? 'Foto profil dihapus.' : 'Foto profil diperbarui.');
    } catch (e) {
      if (mounted) showVmsToast(context, apiErrorMessage(e), error: true);
    } finally {
      if (mounted) setState(() => _photoBusy = false);
    }
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

  /// Hapus pendaftaran wajah sendiri (mis. ganti HP/wajah) setelah konfirmasi.
  Future<void> _hapusWajahSaya() async {
    final yakin = await _konfirmasi(
      judul: 'Hapus pendaftaran wajah Anda?',
      isi:
          'Hapus wajah hanya bisa dilakukan sekali sehari. '
          'Setelah dihapus, absensi memakai pengenalan wajah tidak aktif sampai Anda mendaftarkan wajah lagi. '
          'Tindakan ini dicatat di log aktivitas.',
      tombol: 'Ya, hapus',
    );
    if (!yakin || !mounted) return;
    setState(() => _isEnrolling = true);
    try {
      await ref.read(syncEngineProvider).api.deleteOwnFaceEnrollment();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Pendaftaran wajah Anda sudah dihapus.')),
      );
      await _loadFaceState();
    } catch (e) {
      if (mounted) {
        // Server membalas 429 bila wajah sudah dihapus hari ini.
        final batasHarian = e is DioException && e.response?.statusCode == 429;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            duration: const Duration(seconds: 6),
            content: Text(
              batasHarian
                  ? 'Wajah hanya bisa dihapus sekali sehari. Coba lagi besok, atau minta bantuan HR.'
                  : apiErrorMessage(e),
            ),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isEnrolling = false);
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
      final galat = await ref
          .read(authControllerProvider.notifier)
          .enableDeviceCredential();
      if (galat != null) {
        if (mounted) {
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(SnackBar(content: Text(galat)));
        }
        return;
      }
    } else {
      // Mematikan gerbang keamanan layak dikonfirmasi. Sebelumnya sekali geser
      // langsung nonaktif tanpa pertanyaan apa pun -- mudah tersenggol.
      final yakin = await _konfirmasi(
        judul: 'Matikan login sidik jari?',
        isi:
            'Setelah ini, membuka aplikasi tidak lagi meminta sidik jari. '
            'Siapa pun yang memegang HP ini bisa langsung melihat isinya.',
        tombol: 'Matikan',
      );
      if (!yakin) return;
      await ref.read(tokenStorageProvider).clearDeviceCredential();
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
      final summary = await ref.read(syncEngineProvider).syncAll(manual: true);
      ref.read(syncTickProvider.notifier).bump();
      await _loadSyncInfo();
      setState(() {
        _syncResultMessage = summary.hasErrors
            ? 'Sync selesai dengan sebagian gagal:\n${[...summary.pushErrors, ...summary.pullErrors].join('\n')}'
            : 'Data berhasil dikirim.';
      });
    } catch (e) {
      setState(() => _syncResultMessage = 'Data belum terkirim: $e');
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
        await ref.read(syncEngineProvider).pendingPhotoCount() +
        await ref.read(syncEngineProvider).deadLetterCount();
    if (!mounted) return;
    final yakin = await _konfirmasi(
      judul: 'Keluar dari akun?',
      isi: tertunda > 0
          ? 'Masih ada $tertunda data yang BELUM terkirim ke server. '
                'Keluar sekarang akan menghapusnya dari HP ini. '
                'Sambungkan ke internet dan sinkronkan dulu bila datanya masih dibutuhkan.'
          : 'Anda perlu memasukkan email dan sandi lagi untuk masuk.',
      tombol: 'Keluar',
    );
    if (!yakin) return;
    await ref.read(authControllerProvider.notifier).logout();
  }

  static const _services = <(String, IconData, String, Accent)>[
    ('/recap', Icons.event_available_rounded, 'Rekap absen dan uang makan', Accent.teal),
    ('/leaves', Icons.beach_access_rounded, 'Cuti dan Izin', Accent.blue),
    ('/assets', Icons.directions_car_rounded, 'Kendaraan dan Alat', Accent.amber),
    ('/overtime', Icons.more_time_rounded, 'Riwayat lembur', Accent.indigo),
    ('/mess', Icons.home_work_rounded, 'Mess karyawan', Accent.violet),
    ('/documents', Icons.badge_rounded, 'Dokumen saya', Accent.emerald),
  ];

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authControllerProvider);
    final user = authState is AuthAuthenticated ? authState.user : null;
    final name = user?.displayName ?? '-';

    return Scaffold(
      appBar: VmsTopBar(
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [const NotificationBell(), const SizedBox(width: 8), _avatar(name, 44, editable: true)],
        ),
      ),
      body: ListView(
        padding: safeListPadding(context),
        children: [
          HeroHeader(
            eyebrow: 'Profil',
            title: name,
            subtitle: user?.username,
            trailing: _avatar(name, 64, editable: true),
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
                const SectionTitle('Layanan karyawan'),
                // Grid 2 kolom ringkas agar pengguna tidak perlu menggulir panjang.
                GridView.count(
                  crossAxisCount: 2,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  mainAxisSpacing: 8,
                  crossAxisSpacing: 8,
                  childAspectRatio: 1.55,
                  children: [
                    for (final (route, icon, label, accent) in _services)
                      SurfaceCard(
                        onTap: () => context.push(route),
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Row(
                              children: [
                                IconTile(icon: icon, accent: accent, size: 36),
                                const Spacer(),
                                const Icon(Icons.chevron_right_rounded, size: 18, color: VmsColors.neutral400),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text(
                              label,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: VmsTextStyles.bodySm.copyWith(
                                fontWeight: FontWeight.w700,
                                height: 1.2,
                              ),
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
                const SectionTitle('Kirim ulang data'),
                FadeSlideIn(
                  child: SurfaceCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Row(
                          children: [
                            _stat(
                              'Menunggu terkirim',
                              _pendingOperationCount,
                              Accent.blue,
                              Icons.cloud_upload_rounded,
                            ),
                            const SizedBox(width: 8),
                            _stat(
                              'Foto menunggu',
                              _pendingPhotoCount,
                              Accent.teal,
                              Icons.photo_rounded,
                            ),
                            const SizedBox(width: 8),
                            _stat(
                              'Perlu dicek',
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
                                  'Data berhasil dikirim',
                                )
                                ? Accent.emerald
                                : Accent.amber,
                          ),
                        ],
                        const SizedBox(height: 12),
                        PrimaryAction(
                          label: 'Kirim ulang sekarang',
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
                          label: const Text('Lihat data menunggu terkirim'),
                        ),
                      ],
                    ),
                  ),
                ),
                const SectionTitle('Pengenalan wajah'),
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
                                    'Pengenalan wajah',
                                    style: VmsTextStyles.bodySm.copyWith(
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                  Text(
                                    _faceLoading
                                        ? 'Memeriksa status...'
                                        : (_faceStatus?['enrolled'] == true
                                              ? 'Wajah terdaftar (aktif)'
                                              : 'Belum terdaftar'),
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
                          'Pencocokan wajah dilakukan di server secara aman untuk memverifikasi absensi masuk dan pulang.',
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
                          OutlinedButton.icon(
                            key: const Key('profil-hapus-wajah'),
                            style: OutlinedButton.styleFrom(
                              foregroundColor: Accent.rose.strong,
                              minimumSize: const Size.fromHeight(48),
                            ),
                            onPressed: _isEnrolling || _faceLoading
                                ? null
                                : _hapusWajahSaya,
                            icon: const Icon(Icons.delete_outline_rounded),
                            label: const Text('Hapus pendaftaran wajah saya'),
                          )
                        else if (_faceStatus?['required'] == true)
                          PrimaryAction(
                            label: 'Daftarkan wajah Anda',
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
                SurfaceCard(
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const SessionsScreen()),
                  ),
                  padding: const EdgeInsets.all(14),
                  child: Row(
                    children: [
                      const IconTile(icon: Icons.devices_rounded, accent: Accent.blue, size: 40),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Perangkat yang masuk', style: VmsTextStyles.subheading),
                            Text('Lihat dan keluarkan perangkat lain', style: VmsTextStyles.caption),
                          ],
                        ),
                      ),
                      const Icon(Icons.chevron_right_rounded, color: VmsColors.neutral400),
                    ],
                  ),
                ),
                const SizedBox(height: 8),
                SurfaceCard(
                  onTap: () => context.push('/ganti-sandi'),
                  padding: const EdgeInsets.all(14),
                  child: Row(
                    children: [
                      const IconTile(icon: Icons.lock_reset_rounded, accent: Accent.blue, size: 40),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Ganti sandi', style: VmsTextStyles.subheading),
                            Text('Ubah sandi akun Anda', style: VmsTextStyles.caption),
                          ],
                        ),
                      ),
                      const Icon(Icons.chevron_right_rounded, color: VmsColors.neutral400),
                    ],
                  ),
                ),
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
