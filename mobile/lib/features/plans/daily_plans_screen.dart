import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/error_message.dart';

import '../../core/providers.dart';
import '../../shared/ui/vms_ui.dart';
import 'daily_plan_screen.dart';

String isoDate(DateTime d) => DateFormat('yyyy-MM-dd').format(d);

DateTime mondayOf(DateTime d) {
  final day = DateTime(d.year, d.month, d.day);
  return day.subtract(Duration(days: day.weekday - 1));
}

/// Jadwal harian tim saya per minggu (Senin–Minggu) — pengganti daftar SK (Milestone 5, daily-first).
class DailyPlansScreen extends ConsumerStatefulWidget {
  const DailyPlansScreen({super.key});

  @override
  ConsumerState<DailyPlansScreen> createState() => _DailyPlansScreenState();
}

class _DailyPlansScreenState extends ConsumerState<DailyPlansScreen> {
  DateTime _monday = mondayOf(DateTime.now());
  List<Map<String, dynamic>> _plans = const [];
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
      final plans = await ref.read(syncEngineProvider).api.dailyPlans(
            start: isoDate(_monday),
            end: isoDate(_monday.add(const Duration(days: 6))),
          );
      if (mounted) setState(() => (_plans = plans, _error = null));
    } catch (e) {
      if (mounted) setState(() => _error = apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _shift(int days) {
    setState(() => _monday = days == 0 ? mondayOf(DateTime.now()) : _monday.add(Duration(days: days)));
    _load();
  }

  Future<void> _open(Map<String, dynamic> plan) async {
    await Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => DailyPlanScreen(dailyPlanId: plan['daily_plan_id'] as String)),
    );
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    // Peristiwa realtime (jadwal disetujui / item digeser) → muat ulang.
    ref.listen(liveEventTickProvider, (_, _) => _load());
    final fmt = DateFormat('d MMM', 'id_ID');
    final today = isoDate(DateTime.now());
    return Scaffold(
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 120),
          children: [
            SectionTitle(
              'Jadwal kerja',
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  IconButton(
                    key: const Key('week-prev'),
                    icon: const Icon(Icons.chevron_left_rounded),
                    onPressed: () => _shift(-7),
                  ),
                  TextButton(onPressed: () => _shift(0), child: const Text('Minggu ini')),
                  IconButton(
                    key: const Key('week-next'),
                    icon: const Icon(Icons.chevron_right_rounded),
                    onPressed: () => _shift(7),
                  ),
                ],
              ),
            ),
            Text(
              '${fmt.format(_monday)} – ${fmt.format(_monday.add(const Duration(days: 6)))}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 12),
            if (_loading && _plans.isEmpty)
              const Padding(padding: EdgeInsets.all(32), child: Center(child: CircularProgressIndicator()))
            else if (_error != null)
              NoticeBanner(icon: Icons.wifi_off_rounded, text: _error!)
            else if (_plans.isEmpty)
              const EmptyState(
                icon: Icons.event_busy_rounded,
                title: 'Tidak ada jadwal minggu ini',
                message: 'Jadwal muncul setelah disetujui PM.',
              )
            else
              for (final p in _plans)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: SurfaceCard(
                    highlight: p['work_date'] == today,
                    onTap: () => _open(p),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                DateFormat('EEEE, d MMMM', 'id_ID').format(DateTime.parse(p['work_date'] as String)),
                                style: Theme.of(context).textTheme.titleSmall,
                              ),
                            ),
                            StatusPill(p['status'] as String?),
                          ],
                        ),
                        const SizedBox(height: 8),
                        InfoRow(icon: Icons.place_outlined, text: '${p['site_name']}'),
                        const SizedBox(height: 4),
                        InfoRow(icon: Icons.groups_2_outlined, text: '${p['team_name']} · ketua ${p['leader_name']}'),
                        const SizedBox(height: 4),
                        InfoRow(
                          icon: Icons.checklist_rounded,
                          text: '${p['done_count']} dari ${p['item_count']} titik selesai',
                        ),
                      ],
                    ),
                  ),
                ),
          ],
        ),
      ),
    );
  }
}
