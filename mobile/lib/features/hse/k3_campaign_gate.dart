import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/root_navigator.dart';
import '../auth/auth_controller.dart';
import '../auth/auth_state.dart';
import 'k3_campaign_controller.dart';
import 'k3_campaign_view.dart';

/// Membungkus isi aplikasi. Saat login, saat aplikasi kembali ke depan, dan saat online, memeriksa kampanye K3
/// wajib baca. Bila ada, tampil sebagai layar penuh di atas semua layar dengan rute yang tidak bisa ditutup
/// (tanpa tombol X, tombol back diblokir).
class K3CampaignGate extends ConsumerStatefulWidget {
  const K3CampaignGate({super.key, required this.child});

  final Widget child;

  @override
  ConsumerState<K3CampaignGate> createState() => _K3CampaignGateState();
}

class _K3CampaignGateState extends ConsumerState<K3CampaignGate> with WidgetsBindingObserver {
  Route<void>? _route;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    WidgetsBinding.instance.addPostFrameCallback((_) => _check());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  void _check() => unawaited(ref.read(k3CampaignProvider.notifier).check());

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed) return;
    final notifier = ref.read(k3CampaignProvider.notifier);
    // Konfirmasi yang gagal karena jaringan dicoba ulang saat kembali ke depan; pemeriksaan kampanye baru juga.
    if (ref.read(k3CampaignProvider).pendingReadSeconds != null) unawaited(notifier.retryPending());
    unawaited(notifier.check());
  }

  void _openRoute() {
    final nav = rootNavigatorKey.currentState;
    if (nav == null || _route != null) return;
    final route = PageRouteBuilder<void>(
      transitionDuration: Duration.zero,
      reverseTransitionDuration: Duration.zero,
      pageBuilder: (_, _, _) => const PopScope(
        canPop: false,
        child: _K3CampaignRoute(),
      ),
    );
    _route = route;
    nav.push(route).whenComplete(() {
      if (identical(_route, route)) _route = null;
    });
  }

  void _closeRoute() {
    final route = _route;
    if (route == null) return;
    _route = null;
    rootNavigatorKey.currentState?.removeRoute(route);
  }

  @override
  Widget build(BuildContext context) {
    ref.listen<AuthState>(authControllerProvider, (prev, next) {
      if (next is AuthAuthenticated && prev is! AuthAuthenticated) {
        _check();
      } else if (next is! AuthAuthenticated) {
        ref.read(k3CampaignProvider.notifier).reset();
      }
    });
    ref.listen<K3State>(k3CampaignProvider, (prev, next) {
      if (next.campaign != null) {
        if (_route == null) WidgetsBinding.instance.addPostFrameCallback((_) => _openRoute());
      } else {
        _closeRoute();
      }
    });
    return widget.child;
  }
}

/// Isi rute K3: layar penuh, latar sesuai tema, selalu mengikuti status terbaru di penyimpanan provider.
class _K3CampaignRoute extends ConsumerWidget {
  const _K3CampaignRoute();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(k3CampaignProvider);
    final campaign = state.campaign;
    if (campaign == null) return const SizedBox.shrink();
    return Scaffold(
      body: K3CampaignView(
        key: ValueKey(campaign.id),
        campaign: campaign,
        sending: state.sending,
        error: state.error,
        onConfirm: (seconds) => ref.read(k3CampaignProvider.notifier).confirm(seconds),
      ),
    );
  }
}
