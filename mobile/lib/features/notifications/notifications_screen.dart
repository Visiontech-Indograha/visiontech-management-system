import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../core/theme/theme.dart';
import '../../shared/ui/vms_ui.dart';
import '../plans/revision_history_screen.dart';
import '../plans/work_plans_screen.dart';

final _time = DateFormat('d MMM yyyy, HH.mm', 'id_ID');

/// Tombol lonceng dengan jumlah belum dibaca (alur SK v2). Diperiksa saat tampil dan tiap 60 detik.
class NotificationBell extends ConsumerStatefulWidget {
  const NotificationBell({super.key, this.onReturn});
  final VoidCallback? onReturn;

  @override
  ConsumerState<NotificationBell> createState() => _NotificationBellState();
}

class _NotificationBellState extends ConsumerState<NotificationBell> {
  int _unread = 0;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _refresh();
    _timer = Timer.periodic(const Duration(seconds: 60), (_) => _refresh());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _refresh() async {
    try {
      final res = await ref.read(syncEngineProvider).api.notifications();
      if (mounted) setState(() => _unread = res.unread);
    } catch (_) {
      // Luring: lencana tetap angka terakhir.
    }
  }

  @override
  Widget build(BuildContext context) => Stack(
    clipBehavior: Clip.none,
    children: [
      HeaderAction(
        key: const Key('notification-bell'),
        icon: Icons.notifications_none_rounded,
        tooltip: 'Notifikasi',
        onTap: () async {
          await Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => const NotificationsScreen()),
          );
          await _refresh();
          widget.onReturn?.call();
        },
      ),
      if (_unread > 0)
        Positioned(
          right: -2,
          top: -2,
          child: IgnorePointer(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: Accent.rose.strong,
                borderRadius: BorderRadius.circular(99),
              ),
              child: Text(
                _unread > 99 ? '99+' : '$_unread',
                style: VmsTextStyles.caption.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
          ),
        ),
    ],
  );
}

/// Daftar notifikasi; ketuk untuk menandai dibaca dan membuka SK terkait.
class NotificationsScreen extends ConsumerStatefulWidget {
  const NotificationsScreen({super.key});

  @override
  ConsumerState<NotificationsScreen> createState() =>
      _NotificationsScreenState();
}

class _NotificationsScreenState extends ConsumerState<NotificationsScreen> {
  List<Map<String, dynamic>> _items = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final res = await ref.read(syncEngineProvider).api.notifications();
      if (mounted) {
        setState(() {
          _items = res.items;
          _error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _open(Map<String, dynamic> n) async {
    final api = ref.read(syncEngineProvider).api;
    try {
      if (n['read_at'] == null) await api.readNotification(n['id'] as String);
      final planId = n['work_plan_id'] as String?;
      if (planId != null && n['kind'] == 'PLAN_REVISED') {
        if (!mounted) return;
        await Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => RevisionHistoryScreen(planId: planId)),
        );
      } else if (planId != null) {
        final plan = await api.workPlan(planId);
        if (!mounted) return;
        await Navigator.of(
          context,
        ).push(MaterialPageRoute(builder: (_) => PlanDetailScreen(plan: plan)));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(apiErrorMessage(e))));
      }
    }
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    final unread = _items.where((n) => n['read_at'] == null).length;
    return Scaffold(
      appBar: VmsTopBar(
        onBack: () => Navigator.of(context).maybePop(),
        trailing: unread > 0
            ? HeaderAction(
                icon: Icons.done_all_rounded,
                tooltip: 'Tandai semua dibaca',
                onTap: () async {
                  await ref.read(syncEngineProvider).api.readAllNotifications();
                  await _load();
                },
              )
            : null,
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        edgeOffset: 120,
        child: ListView(
          padding: safeListPadding(context),
          children: [
            HeroHeader(
              eyebrow: 'Kotak masuk',
              title: 'Notifikasi',
              subtitle: _loading ? 'Memuat…' : '$unread belum dibaca',
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (_error != null)
                    NoticeBanner(
                      icon: Icons.error_outline_rounded,
                      text: _error!,
                      accent: Accent.rose,
                    ),
                  if (_loading && _items.isEmpty)
                    const Padding(
                      padding: EdgeInsets.all(24),
                      child: Center(child: CircularProgressIndicator()),
                    ),
                  if (!_loading && _items.isEmpty && _error == null)
                    const EmptyState(
                      icon: Icons.notifications_off_outlined,
                      title: 'Belum ada notifikasi',
                    ),
                  for (final n in _items)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: SurfaceCard(
                        padding: const EdgeInsets.all(14),
                        onTap: () => _open(n),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Icon(
                              n['read_at'] == null
                                  ? Icons.circle
                                  : Icons.circle_outlined,
                              size: 10,
                              color: Accent.blue.strong,
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    '${n['title']}',
                                    style: VmsTextStyles.bodySm.copyWith(
                                      fontWeight: n['read_at'] == null
                                          ? FontWeight.w800
                                          : FontWeight.w500,
                                      color: VmsColors.neutral900,
                                    ),
                                  ),
                                  if ('${n['body']}'.isNotEmpty)
                                    Text(
                                      '${n['body']}',
                                      style: VmsTextStyles.caption,
                                    ),
                                  const SizedBox(height: 4),
                                  Text(
                                    _time.format(
                                      DateTime.parse('${n['created_at']}')
                                          .toLocal(),
                                    ),
                                    style: VmsTextStyles.caption,
                                  ),
                                ],
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
      ),
    );
  }
}
