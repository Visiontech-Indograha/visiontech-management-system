import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../core/theme/theme.dart';
import '../../shared/ui/vms_ui.dart';
import 'app_update_controller.dart';

/// Membungkus seluruh aplikasi (di atas Navigator, lihat main.dart): memeriksa pembaruan saat aplikasi dibuka &
/// kembali aktif, dan menutup aplikasi dengan layar "Pembaruan wajib" bila server mewajibkannya — juga di layar
/// login. Sinkronisasi antrean offline (ConnectivitySyncWatcher) tetap berjalan di belakangnya.
class AppUpdateGate extends ConsumerStatefulWidget {
  const AppUpdateGate({super.key, required this.child});

  final Widget child;

  @override
  ConsumerState<AppUpdateGate> createState() => _AppUpdateGateState();
}

class _AppUpdateGateState extends ConsumerState<AppUpdateGate>
    with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    WidgetsBinding.instance.addPostFrameCallback(
      (_) => unawaited(ref.read(appUpdateControllerProvider.notifier).check()),
    );
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed) return;
    final controller = ref.read(appUpdateControllerProvider.notifier);
    unawaited(controller.resumeAfterPermission());
    unawaited(controller.check());
  }

  @override
  Widget build(BuildContext context) {
    final required = ref.watch(
      appUpdateControllerProvider.select((s) => s.isRequired),
    );
    return required ? const UpdateRequiredScreen() : widget.child;
  }
}

/// Layar penuh saat versi terpasang sudah tidak didukung. Tidak ada jalan pintas ke menu lain.
class UpdateRequiredScreen extends ConsumerStatefulWidget {
  const UpdateRequiredScreen({super.key});

  @override
  ConsumerState<UpdateRequiredScreen> createState() =>
      _UpdateRequiredScreenState();
}

class _UpdateRequiredScreenState extends ConsumerState<UpdateRequiredScreen> {
  int _pending = 0;

  @override
  void initState() {
    super.initState();
    unawaited(_loadPending());
  }

  Future<void> _loadPending() async {
    try {
      final engine = ref.read(syncEngineProvider);
      final n =
          await engine.pendingOperationCount() +
          await engine.pendingPhotoCount();
      if (mounted) setState(() => _pending = n);
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(appUpdateControllerProvider);
    final info = state.info!;
    return Scaffold(
      backgroundColor: VmsColors.neutral25,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 32, 20, 24),
          children: [
            Center(child: Image.asset(logoAsset, height: 34)),
            const SizedBox(height: 28),
            const Center(
              child: IconTile(
                icon: Icons.system_update_rounded,
                accent: Accent.amber,
                size: 64,
              ),
            ),
            const SizedBox(height: 16),
            Text(
              'Pembaruan wajib',
              textAlign: TextAlign.center,
              style: VmsTextStyles.titleLg.copyWith(
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Versi aplikasi ini (${state.installed?.label ?? '-'}) sudah tidak didukung. '
              'Perbarui ke versi ${info.latestLabel} untuk melanjutkan.',
              textAlign: TextAlign.center,
              style: VmsTextStyles.body.copyWith(color: VmsColors.neutral600),
            ),
            const SizedBox(height: 20),
            UpdateDetails(state: state),
            if (_pending > 0)
              NoticeBanner(
                icon: Icons.cloud_upload_rounded,
                accent: Accent.blue,
                text:
                    '$_pending data belum terkirim tetap aman di HP dan terkirim otomatis setelah pembaruan.',
              ),
            const SizedBox(height: 4),
            const UpdateActionButton(),
          ],
        ),
      ),
    );
  }
}

/// Isi bersama layar wajib & lembar opsional: catatan rilis, ukuran, saran Wi-Fi, progres, galat.
class UpdateDetails extends StatefulWidget {
  const UpdateDetails({super.key, required this.state});

  final AppUpdateState state;

  @override
  State<UpdateDetails> createState() => _UpdateDetailsState();
}

class _UpdateDetailsState extends State<UpdateDetails> {
  bool _mobileData = false;

  @override
  void initState() {
    super.initState();
    unawaited(_checkNetwork());
  }

  Future<void> _checkNetwork() async {
    try {
      final r = await Connectivity().checkConnectivity();
      final mobile =
          r.contains(ConnectivityResult.mobile) &&
          !r.contains(ConnectivityResult.wifi);
      if (mounted) setState(() => _mobileData = mobile);
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.state;
    final info = s.info!;
    final download = info.download!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SurfaceCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Versi ${info.latestLabel} · ${download.sizeLabel}',
                style: VmsTextStyles.subheading.copyWith(
                  fontWeight: FontWeight.w700,
                ),
              ),
              if (info.notes.isNotEmpty) ...[
                const SizedBox(height: 8),
                for (final n in info.notes)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Text('• $n', style: VmsTextStyles.bodySm),
                  ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 12),
        if (_mobileData && s.phase == UpdatePhase.idle)
          NoticeBanner(
            icon: Icons.wifi_rounded,
            accent: Accent.slate,
            text:
                'Anda memakai data seluler. Unduhan ±${download.sizeLabel}; pakai Wi-Fi bila ada.',
          ),
        if (s.phase == UpdatePhase.downloading) ...[
          ClipRRect(
            borderRadius: BorderRadius.circular(99),
            child: LinearProgressIndicator(
              value: s.progress > 0 ? s.progress : null,
              minHeight: 8,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'Mengunduh… ${(s.progress * 100).round()}%',
            style: VmsTextStyles.caption,
          ),
          const SizedBox(height: 12),
        ],
        if (s.phase == UpdatePhase.needsPermission)
          const NoticeBanner(
            icon: Icons.security_rounded,
            text:
                'Izinkan "Instal aplikasi tak dikenal" untuk Visiontech, lalu kembali ke aplikasi ini. '
                'Izin ini hanya diminta sekali.',
          ),
        if (s.phase == UpdatePhase.failed && s.error != null)
          NoticeBanner(
            icon: Icons.error_outline_rounded,
            accent: Accent.rose,
            text: s.error!,
          ),
      ],
    );
  }
}

/// Tombol utama alur pembaruan; labelnya mengikuti tahap.
class UpdateActionButton extends ConsumerWidget {
  const UpdateActionButton({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = ref.watch(appUpdateControllerProvider);
    final controller = ref.read(appUpdateControllerProvider.notifier);
    final (label, icon) = switch (s.phase) {
      UpdatePhase.downloading => ('Mengunduh…', Icons.downloading_rounded),
      UpdatePhase.installing => (
        'Membuka installer…',
        Icons.install_mobile_rounded,
      ),
      UpdatePhase.needsPermission => (
        'Buka pengaturan izin',
        Icons.security_rounded,
      ),
      UpdatePhase.failed => ('Coba lagi', Icons.refresh_rounded),
      UpdatePhase.idle when controller.hasDownloaded => (
        'Pasang pembaruan',
        Icons.install_mobile_rounded,
      ),
      UpdatePhase.idle => ('Perbarui sekarang', Icons.system_update_rounded),
    };
    return PrimaryAction(
      label: label,
      icon: icon,
      busy: s.busy,
      onTap: () => unawaited(controller.primaryAction()),
    );
  }
}

/// Pita tipis di atas navigasi bawah (HomeShell) untuk pembaruan opsional yang belum ditunda.
class UpdateAvailableBanner extends ConsumerWidget {
  const UpdateAvailableBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = ref.watch(appUpdateControllerProvider);
    // Pesan sekali setelah pembaruan berhasil, ditampilkan saat menu utama sudah terlihat (bukan saat layar
    // pembuka — pesan yang dikirim di sana hilang ketika rute berganti; ditemukan saat uji emulator).
    if (s.justUpdatedTo != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        final label = ref.read(appUpdateControllerProvider).justUpdatedTo;
        if (label == null || !context.mounted) return;
        ref.read(appUpdateControllerProvider.notifier).consumeJustUpdated();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Aplikasi sudah diperbarui ke versi $label.')),
        );
      });
    }
    if (!s.showBanner) return const SizedBox.shrink();
    final downloading = s.phase == UpdatePhase.downloading;
    return Material(
      key: const Key('pita-pembaruan'),
      color: VmsColors.brand50,
      child: InkWell(
        onTap: () => unawaited(showUpdateSheet(context)),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          child: Row(
            children: [
              const Icon(
                Icons.system_update_rounded,
                size: 18,
                color: VmsColors.brand700,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  downloading
                      ? 'Mengunduh pembaruan… ${(s.progress * 100).round()}%'
                      : 'Versi baru ${s.info!.latestLabel} tersedia — ketuk untuk memperbarui',
                  style: VmsTextStyles.bodySm.copyWith(
                    color: VmsColors.brand700,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              const Icon(
                Icons.chevron_right,
                size: 18,
                color: VmsColors.brand700,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Lembar detail pembaruan opsional: catatan, ukuran, "Perbarui sekarang" atau "Nanti" (tunda 24 jam).
Future<void> showUpdateSheet(BuildContext context) =>
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (ctx) => Consumer(
        builder: (ctx, ref, _) {
          final s = ref.watch(appUpdateControllerProvider);
          if (s.info?.download == null) return const SizedBox.shrink();
          return SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'Pembaruan aplikasi',
                    style: VmsTextStyles.title.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Terpasang: ${s.installed?.label ?? '-'}',
                    style: VmsTextStyles.caption,
                  ),
                  const SizedBox(height: 16),
                  UpdateDetails(state: s),
                  const UpdateActionButton(),
                  if (!s.busy)
                    TextButton(
                      onPressed: () async {
                        await ref
                            .read(appUpdateControllerProvider.notifier)
                            .snooze();
                        if (ctx.mounted) Navigator.of(ctx).pop();
                      },
                      child: const Text('Nanti'),
                    ),
                ],
              ),
            ),
          );
        },
      ),
    );

/// Kartu "Tentang aplikasi" di Profil: versi terpasang + periksa pembaruan manual.
class AboutAppCard extends ConsumerStatefulWidget {
  const AboutAppCard({super.key});

  @override
  ConsumerState<AboutAppCard> createState() => _AboutAppCardState();
}

class _AboutAppCardState extends ConsumerState<AboutAppCard> {
  bool _checking = false;

  @override
  void initState() {
    super.initState();
    unawaited(ref.read(appUpdateControllerProvider.notifier).loadInstalled());
  }

  Future<void> _check() async {
    setState(() => _checking = true);
    final controller = ref.read(appUpdateControllerProvider.notifier);
    final info = await controller.check(force: true);
    if (!mounted) return;
    setState(() => _checking = false);
    if (info != null && info.hasUpdate) {
      await showUpdateSheet(context);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            info == null
                ? 'Belum bisa memeriksa pembaruan. Periksa sinyal lalu coba lagi.'
                : 'Aplikasi sudah versi terbaru.',
          ),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final enabled = ref.watch(appUpdateEnabledProvider);
    final s = ref.watch(appUpdateControllerProvider);
    return SurfaceCard(
      padding: const EdgeInsets.fromLTRB(14, 8, 8, 8),
      child: Row(
        children: [
          const IconTile(
            icon: Icons.info_outline_rounded,
            accent: Accent.slate,
            size: 40,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Versi aplikasi',
                  style: VmsTextStyles.bodySm.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                Text(s.installed?.label ?? '-', style: VmsTextStyles.caption),
              ],
            ),
          ),
          if (enabled)
            TextButton(
              onPressed: _checking ? null : _check,
              child: Text(_checking ? 'Memeriksa…' : 'Periksa pembaruan'),
            ),
        ],
      ),
    );
  }
}
