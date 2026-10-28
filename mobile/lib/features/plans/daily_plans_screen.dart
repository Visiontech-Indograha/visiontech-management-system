import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/error_message.dart';

import '../../core/providers.dart';
import '../../shared/ui/vms_ui.dart';
import '../notifications/notifications_screen.dart' show NotificationBell;
import 'daily_plan_screen.dart' show DailyPlanScreen, phaseLabel;
import 'survey_screen.dart' show MySurveysSection, openReportFile;

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
  String? _only; // filter jenis pekerjaan; null = semua
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
      final engine = ref.read(syncEngineProvider);
      final start = isoDate(_monday), end = isoDate(_monday.add(const Duration(days: 6)));
      final plans = (await engine.fetchList('daily_$start', () => engine.api.dailyPlans(start: start, end: end))).items;
      if (mounted) setState(() => (_plans = plans, _error = null));
      unawaited(engine.prefetchPlanDetails(plans));
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

  bool _exporting = false;

  /// Laporan mingguan tim (.pptx) untuk minggu yang sedang dilihat.
  Future<void> _weekSlides() async {
    final teamId = _plans.isEmpty ? null : '${_plans.first['team_id']}';
    if (teamId == null) return;
    setState(() => _exporting = true);
    try {
      final start = isoDate(_monday);
      final bytes = await ref.read(syncEngineProvider).api.teamWeekSlides(teamId, start);
      final msg = await openReportFile(bytes, 'Laporan-mingguan-$start.pptx');
      if (msg != null && mounted) showVmsToast(context, msg, error: true);
    } catch (e) {
      if (mounted) showVmsToast(context, apiErrorMessage(e), error: true);
    } finally {
      if (mounted) setState(() => _exporting = false);
    }
  }

  Future<void> _open(Map<String, dynamic> plan) async {
    await Navigator.of(context)
        .push(MaterialPageRoute(builder: (_) => DailyPlanScreen(dailyPlanId: plan['daily_plan_id'] as String)));
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    // Peristiwa realtime (jadwal disetujui / item digeser) → muat ulang.
    ref.listen(liveEventTickProvider, (_, _) => _load());
    final fmt = DateFormat('d MMM', 'id_ID');
    final today = isoDate(DateTime.now());
    final thisWeek = _monday == mondayOf(DateTime.now());
    final shown = _plans.where((p) => _only == null || (p['phases'] as List? ?? const []).contains(_only)).toList();
    return Scaffold(
      appBar: const VmsTopBar(trailing: NotificationBell()),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 120),
          children: [
            // Survei tim (sedang diisi / menunggu PM / disetujui) — tetap bisa dibuka setelah dikirim.
            MySurveysSection(key: ValueKey(_monday)),
            const SectionTitle('Jadwal kerja'),
            // Navigasi minggu dalam satu baris.
            Container(
              decoration: BoxDecoration(color: Accent.blue.soft, borderRadius: BorderRadius.circular(14)),
              child: Row(
                children: [
                  IconButton(
                    key: const Key('week-prev'),
                    icon: const Icon(Icons.chevron_left_rounded),
                    onPressed: () => _shift(-7),
                  ),
                  Expanded(
                    child: GestureDetector(
                      onTap: thisWeek ? null : () => _shift(0),
                      child: Column(
                        children: [
                          Text(
                            '${fmt.format(_monday)} – ${fmt.format(_monday.add(const Duration(days: 6)))}',
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
                          ),
                          Text(
                            thisWeek ? 'Minggu ini' : 'Ketuk untuk kembali ke minggu ini',
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Accent.blue.strong),
                          ),
                        ],
                      ),
                    ),
                  ),
                  IconButton(
                    key: const Key('week-next'),
                    icon: const Icon(Icons.chevron_right_rounded),
                    onPressed: () => _shift(7),
                  ),
                ],
              ),
            ),
            if (_plans.isNotEmpty) ...[
              const SizedBox(height: 8),
              OutlinedButton.icon(
                onPressed: _exporting ? null : _weekSlides,
                icon: _exporting
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.slideshow_rounded),
                label: Text(_exporting ? 'Menyiapkan laporan…' : 'Laporan minggu ini (.pptx)'),
              ),
            ],
            const SizedBox(height: 10),
            // Pisahkan jenis pekerjaan, tiap jenis punya warna sendiri.
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  for (final (key, label) in [(null, 'Semua'), ...phaseLabel.entries.map((e) => (e.key, e.value))])
                    Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: ChoiceChip(
                        avatar: key == null
                            ? null
                            : CircleAvatar(radius: 5, backgroundColor: (phaseAccent[key] ?? Accent.slate).strong),
                        label: Text(label),
                        selected: _only == key,
                        showCheckmark: false,
                        selectedColor: (phaseAccent[key] ?? Accent.blue).soft,
                        labelStyle: TextStyle(
                          fontWeight: _only == key ? FontWeight.w700 : FontWeight.w500,
                          color: _only == key ? (phaseAccent[key] ?? Accent.blue).strong : null,
                        ),
                        onSelected: (_) => setState(() => _only = key),
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            if (_loading && _plans.isEmpty)
              const Padding(
                padding: EdgeInsets.all(32),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_error != null)
              NoticeBanner(icon: Icons.wifi_off_rounded, text: _error!)
            else if (shown.isEmpty)
              EmptyState(
                icon: Icons.event_busy_rounded,
                title: _only == null ? 'Tidak ada jadwal minggu ini' : 'Tidak ada ${phaseLabel[_only]} minggu ini',
                message: 'Jadwal muncul setelah disetujui PM.',
              )
            else
              for (final (n, p) in shown.indexed)
                _AppearIn(
                  key: ValueKey(p['daily_plan_id']),
                  index: n,
                  child: _PlanCard(plan: p, today: today, onTap: () => _open(p)),
                ),
          ],
        ),
      ),
    );
  }
}

/// Muncul memudar + naik sedikit, berurutan per kartu.
class _AppearIn extends StatelessWidget {
  const _AppearIn({super.key, required this.index, required this.child});
  final int index;
  final Widget child;

  @override
  Widget build(BuildContext context) => TweenAnimationBuilder<double>(
    tween: Tween(begin: 0, end: 1),
    duration: Duration(milliseconds: 280 + 60 * index.clamp(0, 6)),
    curve: Curves.easeOutCubic,
    builder: (_, v, c) => Opacity(
      opacity: v,
      child: Transform.translate(offset: Offset(0, 16 * (1 - v)), child: c),
    ),
    child: child,
  );
}

/// Kartu satu hari: blok tanggal berwarna status di kiri (biru berjalan, merah terlambat,
/// hijau selesai, kuning selesai sebagian, abu belum mulai), isi di kanan.
class _PlanCard extends StatelessWidget {
  const _PlanCard({required this.plan, required this.today, required this.onTap});
  final Map<String, dynamic> plan;
  final String today;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final date = DateTime.parse(plan['work_date'] as String);
    final state = workState(plan, today);
    final accent = statusStyle(state).accent;
    final done = (plan['done_count'] as num?)?.toInt() ?? 0;
    final total = (plan['item_count'] as num?)?.toInt() ?? 0;
    final pct = workPercent(plan) / 100;
    final isToday = plan['work_date'] == today;
    final text = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Material(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(18),
        elevation: isToday ? 3 : 0.5,
        shadowColor: accent.strong.withValues(alpha: 0.25),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Container(
                  width: 68,
                  color: accent.soft,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        DateFormat('EEE', 'id_ID').format(date).toUpperCase(),
                        style: text.labelSmall?.copyWith(color: accent.strong, fontWeight: FontWeight.w700),
                      ),
                      Text(
                        '${date.day}',
                        style: text.headlineSmall?.copyWith(color: accent.strong, fontWeight: FontWeight.w800),
                      ),
                      Text(
                        DateFormat('MMM', 'id_ID').format(date),
                        style: text.labelSmall?.copyWith(color: accent.strong),
                      ),
                      if (isToday) ...[
                        const SizedBox(height: 4),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(color: accent.strong, borderRadius: BorderRadius.circular(99)),
                          child: Text('Hari ini', style: text.labelSmall?.copyWith(color: Colors.white, fontSize: 9)),
                        ),
                      ],
                    ],
                  ),
                ),
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(
                              child: Text(
                                '${plan['site_name']}',
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: text.titleSmall?.copyWith(fontWeight: FontWeight.w700),
                              ),
                            ),
                            const SizedBox(width: 8),
                            StatusPill(state),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${plan['team_name']} · ketua ${plan['leader_name']}',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: text.bodySmall,
                        ),
                        const SizedBox(height: 8),
                        Wrap(
                          spacing: 6,
                          runSpacing: 6,
                          children: [for (final ph in (plan['phases'] as List? ?? const [])) _PhaseTag(phase: '$ph')],
                        ),
                        const SizedBox(height: 10),
                        TweenAnimationBuilder<double>(
                          tween: Tween(begin: 0, end: pct),
                          duration: const Duration(milliseconds: 700),
                          curve: Curves.easeOutCubic,
                          builder: (_, v, _) => ClipRRect(
                            borderRadius: BorderRadius.circular(99),
                            child: LinearProgressIndicator(
                              value: v,
                              minHeight: 6,
                              color: accent.strong,
                              backgroundColor: accent.soft,
                            ),
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '$done dari $total pekerjaan selesai · ${(pct * 100).round()}%',
                          style: text.bodySmall?.copyWith(color: accent.strong, fontWeight: FontWeight.w600),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _PhaseTag extends StatelessWidget {
  const _PhaseTag({required this.phase});
  final String phase;

  @override
  Widget build(BuildContext context) {
    final a = phaseAccent[phase] ?? Accent.slate;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: a.soft,
        borderRadius: BorderRadius.circular(99),
        border: Border.all(color: a.strong.withValues(alpha: 0.3)),
      ),
      child: Text(
        phaseLabel[phase] ?? phase,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(color: a.strong, fontWeight: FontWeight.w700),
      ),
    );
  }
}
