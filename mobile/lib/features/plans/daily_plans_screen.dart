import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../core/team_logo.dart';
import '../../data/sync_engine.dart';
import '../../shared/ui/vms_ui.dart';
import '../notifications/notifications_screen.dart' show NotificationBell;
import 'daily_plan_format.dart' show phaseLabel;
import 'daily_plan_screen.dart' show DailyPlanScreen;
import 'survey_screen.dart' show MySurveysSection, openReportFile;
import 'wo_team_surveys_section.dart';

String isoDate(DateTime d) => DateFormat('yyyy-MM-dd').format(d);

DateTime mondayOf(DateTime d) {
  final day = DateTime(d.year, d.month, d.day);
  return day.subtract(Duration(days: day.weekday - 1));
}

/// Jadwal harian tim saya per minggu (Senin–Minggu) — dilengkapi kartu sorotan "Hari Ini",
/// pencarian cepat lokasi/tim, dan filter status & jenis pekerjaan.
class DailyPlansScreen extends ConsumerStatefulWidget {
  const DailyPlansScreen({super.key});

  @override
  ConsumerState<DailyPlansScreen> createState() => _DailyPlansScreenState();
}

class _DailyPlansScreenState extends ConsumerState<DailyPlansScreen> {
  DateTime _monday = mondayOf(DateTime.now());
  List<Map<String, dynamic>> _plans = const [];
  String? _only; // filter jenis pekerjaan; null = semua
  String _statusFilter = 'ALL'; // ALL, TODAY, ONGOING, OUT_OF_TOWN, DONE
  String _searchQ = '';
  final _searchCtrl = TextEditingController();
  bool _loading = true;
  String? _error;
  DateTime? _cachedAt;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  int _loadSeq = 0;
  int _refreshes = 0;

  Future<void> _load() async {
    final seq = ++_loadSeq; // respons minggu lama tidak boleh menimpa minggu yang sedang dilihat
    setState(() => _loading = true);
    try {
      final engine = ref.read(syncEngineProvider);
      final start = isoDate(_monday), end = isoDate(_monday.add(const Duration(days: 6)));
      final res = await engine.fetchList('daily_$start', () => engine.api.dailyPlans(start: start, end: end));
      final plans = res.items;
      if (mounted && seq == _loadSeq) setState(() => (_plans = plans, _error = null, _cachedAt = SyncEngine.neverCached(res.cachedAt) ? null : res.cachedAt));
      if (seq == _loadSeq) unawaited(engine.prefetchPlanDetails(plans));
    } catch (e) {
      if (mounted && seq == _loadSeq) setState(() => _error = apiErrorMessage(e));
    } finally {
      if (mounted && seq == _loadSeq) setState(() => _loading = false);
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
    ref.listen(syncTickProvider, (_, _) => _load());
    final fmt = DateFormat('d MMM', 'id_ID');
    final today = isoDate(DateTime.now());
    final thisWeek = _monday == mondayOf(DateTime.now());
    final needle = _searchQ.trim().toLowerCase();

    final shown = _plans.where((p) {
      if (_only != null && !(p['phases'] as List? ?? const []).contains(_only)) return false;
      final st = workState(p, today);
      if (_statusFilter == 'TODAY' && p['work_date'] != today) return false;
      if (_statusFilter == 'ONGOING' && st != 'ONGOING') return false;
      if (_statusFilter == 'OUT_OF_TOWN' && p['is_out_of_town'] != true) return false;
      if (_statusFilter == 'DONE' && st != 'DONE' && st != 'COMPLETED') return false;
      if (needle.isNotEmpty) {
        final hay = '${jadwalTitle(p)} ${p['team_name'] ?? ''} ${p['leader_name'] ?? ''}'.toLowerCase();
        if (!hay.contains(needle)) return false;
      }
      return true;
    }).toList();

    final hasFilter = _only != null || _statusFilter != 'ALL' || needle.isNotEmpty;
    final todayPlan = _plans.where((p) => p['work_date'] == today).firstOrNull;

    return Scaffold(
      appBar: const VmsTopBar(trailing: NotificationBell()),
      body: RefreshIndicator(
        onRefresh: () {
          setState(() => _refreshes++);
          return _load();
        },
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
            // Kolom cari cepat lokasi / nama tim
            TextField(
              controller: _searchCtrl,
              onChanged: (v) => setState(() => _searchQ = v),
              textInputAction: TextInputAction.search,
              decoration: InputDecoration(
                hintText: 'Cari lokasi atau nama tim...',
                prefixIcon: const Icon(Icons.search_rounded),
                suffixIcon: _searchQ.isEmpty
                    ? null
                    : IconButton(
                        tooltip: 'Bersihkan pencarian',
                        icon: const Icon(Icons.close_rounded),
                        onPressed: () {
                          _searchCtrl.clear();
                          setState(() => _searchQ = '');
                        },
                      ),
                isDense: true,
                filled: true,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
              ),
            ),
            const SizedBox(height: 8),
            // Baris chip status cepat
            Text(
              'Geser ke kanan untuk melihat filter lainnya.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 4),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.only(right: 16),
              child: Row(
                children: [
                  for (final (key, label) in const [
                    ('ALL', 'Semua status'),
                    ('TODAY', 'Hari ini'),
                    ('ONGOING', 'Sedang berjalan'),
                    ('OUT_OF_TOWN', 'Luar kota'),
                    ('DONE', 'Sudah selesai'),
                  ])
                    Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: ChoiceChip(
                        label: Text(label),
                        selected: _statusFilter == key,
                        showCheckmark: false,
                        onSelected: (_) => setState(() => _statusFilter = _statusFilter == key && key != 'ALL' ? 'ALL' : key),
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 6),
            // Pisahkan jenis pekerjaan, tiap jenis punya warna sendiri.
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.only(right: 16),
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
            if (hasFilter)
              Align(
                alignment: Alignment.centerRight,
                child: TextButton.icon(
                  onPressed: () {
                    _searchCtrl.clear();
                    setState(() {
                      _only = null;
                      _statusFilter = 'ALL';
                      _searchQ = '';
                    });
                  },
                  icon: const Icon(Icons.restart_alt_rounded, size: 16),
                  label: const Text('Atur ulang filter'),
                ),
              ),
            if (hasFilter && _plans.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Text(
                  'Menampilkan ${shown.length} dari ${_plans.length} jadwal',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
            if (!hasFilter && todayPlan != null)
              Padding(
                padding: const EdgeInsets.only(top: 4, bottom: 4),
                child: FilledButton.icon(
                  key: const Key('today-spotlight'),
                  style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
                  onPressed: () => _open(todayPlan),
                  icon: const Icon(Icons.play_arrow_rounded),
                  label: Text(
                    workState(todayPlan, today) == 'DONE' ? 'Lihat jadwal hari ini' : 'Buka / lanjutkan jadwal hari ini',
                  ),
                ),
              ),
            const SizedBox(height: 8),
            if (_cachedAt != null && _error == null)
              NoticeBanner(
                icon: Icons.cloud_off_rounded,
                text: 'Offline — data terakhir ${DateFormat('d MMM HH:mm', 'id_ID').format(_cachedAt!)}; status bisa belum terbaru',
              ),
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
                message: hasFilter ? 'Coba atur ulang pencarian atau filter status di atas.' : 'Jadwal muncul setelah disetujui atasan.',
              )
            else
              for (final (n, p) in shown.indexed)
                _AppearIn(
                  key: ValueKey(p['daily_plan_id']),
                  index: n,
                  child: _PlanCard(plan: p, today: today, onTap: () => _open(p)),
                ),
            const SizedBox(height: 12),
            WoTeamSurveysSection(key: ValueKey('wo-$_monday'), reloadToken: _refreshes),
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
                                jadwalTitle(plan),
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: text.titleSmall?.copyWith(fontWeight: FontWeight.w700),
                              ),
                            ),
                            const SizedBox(width: 8),
                            plan['kind'] == 'STANDBY'
                                ? const StatusPill('SUBMITTED', label: 'Siaga')
                                : StatusPill(state),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            TeamLogoAvatar(
                              key: const Key('team-card-logo'),
                              teamId: '${plan['team_id']}',
                              size: 22,
                            ),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                '${plan['team_name']} · ketua ${plan['leader_name']}',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: text.bodySmall,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Wrap(
                          spacing: 6,
                          runSpacing: 6,
                          children: [
                            if (plan['is_out_of_town'] == true) const StatusPill('ONGOING', label: 'Luar kota'),
                            for (final ph in (plan['phases'] as List? ?? const [])) _PhaseTag(phase: '$ph'),
                          ],
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
