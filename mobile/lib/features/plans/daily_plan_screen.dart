import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../shared/ui/vms_ui.dart';
import '../auth/auth_controller.dart';
import '../auth/auth_state.dart';
import 'bast_sign_screen.dart';
import 'item_progress_screen.dart';

const phaseLabel = {
  'SURVEY': 'Survei',
  'PREPARATION': 'Persiapan',
  'INSTALLATION': 'Instalasi',
  'REPLACEMENT': 'Penggantian',
  'MAINTENANCE': 'Pemeliharaan',
};

String qtyText(Object? v) {
  final n = num.tryParse('$v') ?? 0;
  return n == n.roundToDouble() ? n.toStringAsFixed(0) : n.toString();
}

/// Detail satu jadwal harian: lokasi & jam, item per titik, aksi ketua (mulai/selesaikan hari, BAST), lembur.
class DailyPlanScreen extends ConsumerStatefulWidget {
  const DailyPlanScreen({super.key, required this.dailyPlanId});

  final String dailyPlanId;

  @override
  ConsumerState<DailyPlanScreen> createState() => _DailyPlanScreenState();
}

class _DailyPlanScreenState extends ConsumerState<DailyPlanScreen> {
  Map<String, dynamic>? _plan;
  String? _error;
  bool _busy = false;

  String get _me {
    final auth = ref.read(authControllerProvider);
    return auth is AuthAuthenticated ? auth.user.employeeId : '';
  }

  bool get _isLeader => _plan != null && _plan!['leader_employee_id'] == _me;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final plan = await ref.read(syncEngineProvider).api.dailyPlan(widget.dailyPlanId);
      if (mounted) setState(() => (_plan = plan, _error = null));
    } catch (e) {
      if (mounted) setState(() => _error = apiErrorMessage(e));
    }
  }

  void _snack(String text) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));

  Future<void> _run(Future<void> Function() action, String done) async {
    setState(() => _busy = true);
    try {
      await action();
      _snack(done);
      await _load();
    } catch (e) {
      _snack(apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _overtime() async {
    final hours = TextEditingController();
    final reason = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Ajukan lembur'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: hours,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(labelText: 'Jam lembur (maks. 12)'),
            ),
            TextField(controller: reason, decoration: const InputDecoration(labelText: 'Alasan')),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Batal')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Kirim')),
        ],
      ),
    );
    if (ok != true) return;
    final h = num.tryParse(hours.text.replaceAll(',', '.'));
    if (h == null) return _snack('Isi jam lembur dengan angka.');
    await _run(
      () => ref.read(syncEngineProvider).api.requestOvertime(
            dayId: widget.dailyPlanId,
            hours: h,
            reason: reason.text.trim(),
          ),
      'Pengajuan lembur terkirim ke PM.',
    );
  }

  Future<void> _openItem(Map<String, dynamic> item) async {
    await Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => ItemProgressScreen(
        itemId: item['item_id'] as String,
        dayStatus: '${_plan!['status']}',
        isLeader: _isLeader,
      ),
    ));
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    final plan = _plan;
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Jadwal harian')),
      body: plan == null
          ? Center(
              child: _error == null
                  ? const CircularProgressIndicator()
                  : Padding(padding: const EdgeInsets.all(16), child: NoticeBanner(icon: Icons.error_outline, text: _error!)),
            )
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
                children: [
                  SurfaceCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                DateFormat('EEEE, d MMMM yyyy', 'id_ID').format(DateTime.parse('${plan['work_date']}')),
                                style: theme.textTheme.titleMedium,
                              ),
                            ),
                            StatusPill('${plan['status']}'),
                          ],
                        ),
                        const SizedBox(height: 10),
                        InfoRow(icon: Icons.place_outlined, text: '${plan['site_name']} (radius absen ${plan['attendance_radius_m']} m)'),
                        const SizedBox(height: 4),
                        InfoRow(
                          icon: Icons.schedule_rounded,
                          text: 'Jam kerja ${'${plan['clock_in_time']}'.substring(0, 5)}–${'${plan['clock_out_time']}'.substring(0, 5)}',
                        ),
                        const SizedBox(height: 4),
                        InfoRow(icon: Icons.groups_2_outlined, text: '${plan['team_name']} · ketua ${plan['leader_name']}'),
                      ],
                    ),
                  ),
                  if (_isLeader && plan['status'] == 'APPROVED') ...[
                    const SizedBox(height: 12),
                    PrimaryAction(
                      label: 'Mulai hari kerja',
                      icon: Icons.play_arrow_rounded,
                      busy: _busy,
                      onTap: () => _run(
                        () => ref.read(syncEngineProvider).api.startDay(widget.dailyPlanId),
                        'Hari kerja dimulai.',
                      ),
                    ),
                  ],
                  if (_isLeader && plan['status'] == 'ONGOING') ...[
                    const SizedBox(height: 12),
                    PrimaryAction(
                      label: 'Selesaikan hari kerja',
                      icon: Icons.task_alt_rounded,
                      busy: _busy,
                      onTap: () => _run(
                        () => ref.read(syncEngineProvider).api.completeDay(widget.dailyPlanId),
                        'Hari kerja ditutup.',
                      ),
                    ),
                  ],
                  const SectionTitle('Pekerjaan per titik'),
                  for (final item in (plan['items'] as List? ?? const []).cast<Map>())
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: _ItemCard(
                        item: Map<String, dynamic>.from(item),
                        onTap: () => _openItem(Map<String, dynamic>.from(item)),
                      ),
                    ),
                  if ((plan['items'] as List? ?? const []).isEmpty)
                    const EmptyState(icon: Icons.inventory_2_outlined, title: 'Belum ada pekerjaan'),
                  ..._orders(plan),
                  if (plan['status'] == 'ONGOING') ...[
                    const SectionTitle('Lembur'),
                    _Tile(
                      icon: Icons.more_time_rounded,
                      title: 'Ajukan lembur',
                      subtitle: 'Diputus PM/OM divisi',
                      onTap: _busy ? null : _overtime,
                    ),
                  ],
                ],
              ),
            ),
    );
  }

  /// Order klien yang dikerjakan hari ini → ketua menandatangani BAST (Milestone 8).
  List<Widget> _orders(Map<String, dynamic> plan) {
    if (!_isLeader) return const [];
    final ids = {
      for (final i in (plan['items'] as List? ?? const []).cast<Map>())
        if (i['completion_id'] != null) '${i['completion_id']}',
    };
    if (ids.isEmpty) return const [];
    return [
      const SectionTitle('Berita acara (BAST)'),
      for (final id in ids)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: _Tile(
            icon: Icons.draw_rounded,
            title: 'Tandatangani BAST order',
            subtitle: 'Ringkasan, foto realisasi, tanda tangan ketua',
            onTap: () async {
              await Navigator.of(context).push(MaterialPageRoute(builder: (_) => BastSignScreen(completionId: id)));
              await _load();
            },
          ),
        ),
    ];
  }
}

class _ItemCard extends StatelessWidget {
  const _ItemCard({required this.item, required this.onTap});

  final Map<String, dynamic> item;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return SurfaceCard(
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text('${item['title']}', style: Theme.of(context).textTheme.titleSmall)),
              StatusPill('${item['status']}'),
            ],
          ),
          const SizedBox(height: 6),
          InfoRow(
            icon: Icons.category_outlined,
            text: '${phaseLabel[item['task_phase']] ?? item['task_phase']} · ${item['work_type_name'] ?? ''}',
          ),
          if (item['location_name'] != null) ...[
            const SizedBox(height: 4),
            InfoRow(icon: Icons.place_outlined, text: '${item['location_name']}'),
          ],
          const SizedBox(height: 4),
          InfoRow(
            icon: Icons.straighten_rounded,
            text: 'Realisasi ${qtyText(item['completed_qty'])} / ${qtyText(item['target_qty'])}',
          ),
        ],
      ),
    );
  }
}

class _Tile extends StatelessWidget {
  const _Tile({required this.icon, required this.title, required this.subtitle, required this.onTap});

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => SurfaceCard(
    padding: EdgeInsets.zero,
    child: ListTile(
      leading: Icon(icon),
      title: Text(title),
      subtitle: Text(subtitle),
      trailing: const Icon(Icons.chevron_right_rounded),
      onTap: onTap,
    ),
  );
}
