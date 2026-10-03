import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../data/sync_engine.dart';
import '../auth/auth_controller.dart';
import '../auth/auth_state.dart';
import '../../core/theme/theme.dart';
import '../../shared/ui/vms_ui.dart';
import '../notifications/notifications_screen.dart';
import 'plan_day_screen.dart';
import 'sk_viewer_screen.dart';
import 'weekly_report_screen.dart';

final _date = DateFormat('d MMM yyyy', 'id_ID');

String employeeIdOf(WidgetRef ref) {
  final auth = ref.read(authControllerProvider);
  return auth is AuthAuthenticated ? auth.user.employeeId : '';
}

/// Daftar SK yang terlihat oleh pengguna (V-07). Tersimpan untuk dibaca saat luring.
class WorkPlansScreen extends ConsumerStatefulWidget {
  const WorkPlansScreen({super.key});

  @override
  ConsumerState<WorkPlansScreen> createState() => _WorkPlansScreenState();
}

class _WorkPlansScreenState extends ConsumerState<WorkPlansScreen> {
  List<Map<String, dynamic>> _plans = [];
  DateTime? _cachedAt;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final engine = ref.read(syncEngineProvider);
    try {
      final res = await engine.fetchList('work_plans', engine.api.workPlans);
      if (!mounted) return;
      final never = SyncEngine.neverCached(res.cachedAt);
      setState(() {
        _plans = res.items.where((p) => p['status'] != 'DRAFT').toList();
        // Luring & belum pernah termuat → jangan tampil "Belum ada SK" (menyesatkan).
        _cachedAt = never ? null : res.cachedAt;
        _error = never ? SyncEngine.offlineNoDataMessage : null;
      });
    } catch (e) {
      if (mounted) setState(() => _error = apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final running = _plans.where((p) => p['status'] == 'IN_PROGRESS').length;
    return Scaffold(
      appBar: VmsTopBar(
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            NotificationBell(onReturn: _load),
            const SizedBox(width: 8),
            HeaderAction(
              icon: Icons.refresh_rounded,
              tooltip: 'Muat ulang',
              onTap: _load,
            ),
          ],
        ),
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        edgeOffset: 120,
        child: ListView(
          padding: safeListPadding(context),
          children: [
            HeroHeader(
              eyebrow: 'Surat Kerja',
              title: 'SK Anda',
              subtitle: _loading
                  ? 'Memuat…'
                  : '${_plans.length} SK · $running sedang berjalan',
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (_cachedAt != null)
                    const NoticeBanner(
                      icon: Icons.cloud_off_rounded,
                      text: 'Luring — menampilkan data tersimpan.',
                    ),
                  if (_error != null)
                    NoticeBanner(
                      icon: Icons.error_outline_rounded,
                      text: _error!,
                      accent: Accent.rose,
                    ),
                  if (_loading)
                    const Padding(
                      padding: EdgeInsets.all(24),
                      child: Center(child: CircularProgressIndicator()),
                    ),
                  if (!_loading && _plans.isEmpty && _error == null)
                    const EmptyState(
                      icon: Icons.assignment_rounded,
                      title: 'Belum ada SK untuk Anda',
                      message: 'SK yang diterbitkan PM untuk Anda akan tampil di sini.',
                    ),
                  for (final (i, p) in _plans.indexed)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: FadeSlideIn(
                        index: i,
                        child: SurfaceCard(
                          // Kartu sorotan emas untuk SK berjalan teratas (gaya rujukan).
                          highlight: i == 0 && p['status'] == 'IN_PROGRESS',
                          onTap: () async {
                            await Navigator.of(context).push(
                              MaterialPageRoute(
                                builder: (_) => PlanDetailScreen(plan: p),
                              ),
                            );
                            await _load();
                          },
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Expanded(
                                    child: Text(
                                      '${p['title']}',
                                      style: VmsTextStyles.subheading.copyWith(
                                        fontWeight: FontWeight.w700,
                                        color:
                                            i == 0 &&
                                                p['status'] == 'IN_PROGRESS'
                                            ? Colors.white
                                            : VmsColors.neutral900,
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  StatusPill(p['status'] as String?),
                                ],
                              ),
                              const SizedBox(height: 10),
                              InfoRow(
                                icon: Icons.tag_rounded,
                                text: '${p['number'] ?? 'Belum bernomor'}',
                              ),
                              const SizedBox(height: 4),
                              InfoRow(
                                icon: Icons.place_rounded,
                                text: '${p['location_text']}',
                              ),
                              const SizedBox(height: 4),
                              InfoRow(
                                icon: Icons.date_range_rounded,
                                text:
                                    '${_date.format(DateTime.parse(p['period_start'] as String))} – '
                                    '${_date.format(DateTime.parse(p['period_end'] as String))}',
                              ),
                            ],
                          ),
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

/// Detail SK: hari kerja (laporan harian & tugas), lapor insiden, lapor lembur.
class PlanDetailScreen extends ConsumerStatefulWidget {
  const PlanDetailScreen({super.key, required this.plan});
  final Map<String, dynamic> plan;

  @override
  ConsumerState<PlanDetailScreen> createState() => _PlanDetailScreenState();
}

class _PlanDetailScreenState extends ConsumerState<PlanDetailScreen> {
  List<Map<String, dynamic>> _days = [];
  late Map<String, dynamic> _plan;
  bool _loading = true;
  bool _accepting = false;
  bool _amending = false;
  Map<String, dynamic>? _detail;
  List<Map<String, dynamic>> _weeks = [];
  String? _error;

  String get _planId => _plan['id'] as String;
  bool get _running => _plan['status'] == 'IN_PROGRESS';

  @override
  void initState() {
    super.initState();
    _plan = Map<String, dynamic>.from(widget.plan);
    _load();
  }

  Future<void> _acceptPlan() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Terima surat kerja ini?'),
        content: const Text(
          'Penerimaan akan dicatat dan ditandatangani secara digital. Pastikan rincian SK sudah benar.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Batal'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Terima'),
          ),
        ],
      ),
    );
    if (confirmed != true || _accepting) return;
    setState(() => _accepting = true);
    try {
      final accepted = await ref
          .read(syncEngineProvider)
          .api
          .acceptPlan(_planId, rowVersion: _plan['row_version'] as int);
      if (!mounted) return;
      setState(() => _plan = accepted);
      _snack('SK berhasil diterima dan ditandatangani.');
      await _load();
    } catch (e) {
      if (mounted) _snack(apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _accepting = false);
    }
  }

  Future<void> _requestAmendment() async {
    final reason = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Ajukan adendum'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'SK akan dikembalikan ke PM untuk direvisi. Tuliskan apa yang perlu diubah.',
            ),
            const SizedBox(height: 12),
            TextField(
              controller: reason,
              autofocus: true,
              maxLines: 4,
              textCapitalization: TextCapitalization.sentences,
              decoration: const InputDecoration(
                labelText: 'Alasan adendum',
                hintText: 'mis. Meminta penambahan hari kerja',
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Batal'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Kirim ke PM'),
          ),
        ],
      ),
    );
    if (ok != true || _amending) return;
    if (reason.text.trim().isEmpty) {
      return _snack('Alasan adendum wajib diisi.');
    }
    setState(() => _amending = true);
    try {
      final updated = await ref
          .read(syncEngineProvider)
          .api
          .requestAmendment(
            _planId,
            rowVersion: _plan['row_version'] as int,
            reason: reason.text.trim(),
          );
      if (!mounted) return;
      setState(() => _plan = updated);
      _snack('Adendum dikirim ke PM.');
    } catch (e) {
      if (mounted) _snack(apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _amending = false);
    }
  }

  Future<void> _load() async {
    final engine = ref.read(syncEngineProvider);
    // Header & isi SK dimuat ulang saat daring (status bisa berubah: terbit -> diterima -> berjalan).
    try {
      final fresh = await engine.api.workPlan(_planId);
      final detail = await engine.api.planDetail(_planId);
      final weeks = await engine.api.weeklyReports(_planId);
      if (mounted) {
        setState(() {
          _plan = fresh;
          _detail = detail;
          _weeks = weeks;
        });
      }
    } catch (_) {
      // Luring: tetap tampilkan data dari daftar yang tersimpan.
    }
    try {
      final res = await engine.fetchList(
        'days:$_planId',
        () => engine.api.planDays(_planId),
      );
      if (!mounted) return;
      setState(() {
        _days = res.items;
        if (SyncEngine.neverCached(res.cachedAt)) {
          _error = SyncEngine.offlineNoDataMessage;
        }
      });
    } catch (e) {
      if (mounted) setState(() => _error = apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _snack(String m) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));

  Future<void> _send(
    String op,
    Map<String, dynamic> payload, {
    List<String> files = const [],
  }) async {
    try {
      final sent = await ref
          .read(syncEngineProvider)
          .submit(op, payload, localFiles: files);
      _snack(
        sent
            ? 'Terkirim.'
            : 'Tersimpan di HP, dikirim otomatis saat ada sinyal.',
      );
    } on SyncRejectedException catch (e) {
      _snack(e.message);
    } catch (e) {
      _snack(apiErrorMessage(e));
    }
  }

  Future<void> _overtime() async {
    final hours = TextEditingController();
    final reason = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Lapor lembur'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: hours,
              autofocus: true,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              // Enter di keyboard pindah ke kolom Alasan (temuan uji HP R-17).
              textInputAction: TextInputAction.next,
              decoration: const InputDecoration(
                labelText: 'Jumlah jam',
                prefixIcon: Icon(Icons.schedule_rounded),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: reason,
              maxLines: 3,
              textCapitalization: TextCapitalization.sentences,
              decoration: const InputDecoration(labelText: 'Alasan'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Batal'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Kirim'),
          ),
        ],
      ),
    );
    final h = double.tryParse(hours.text.replaceAll(',', '.'));
    if (ok != true) return;
    if (h == null || h <= 0 || reason.text.trim().isEmpty) {
      return _snack('Isi jam dan alasan lembur.');
    }
    await _send(OfflineOp.overtimeReport, {
      'work_plan_id': _planId,
      'hours': h,
      'reason': reason.text.trim(),
    });
  }

  Future<void> _incident() async {
    final result = await Navigator.of(context).push<Map<String, dynamic>>(
      MaterialPageRoute(
        fullscreenDialog: true,
        builder: (_) => const IncidentFormScreen(),
      ),
    );
    if (result == null) return;
    final files = List<String>.from(result.remove('files') as List);
    await _send(OfflineOp.incidentReport, {
      ...result,
      'work_plan_id': _planId,
      'evidence_file_ids': <String>[],
    }, files: files);
  }

  @override
  Widget build(BuildContext context) {
    final p = _plan;
    final isLeader = p['leader_employee_id'] == employeeIdOf(ref);
    return Scaffold(
      appBar: VmsTopBar(onBack: () => Navigator.of(context).maybePop()),
      body: RefreshIndicator(
        onRefresh: _load,
        edgeOffset: 140,
        child: ListView(
          padding: safeListPadding(context),
          children: [
            HeroHeader(
              eyebrow: '${p['number'] ?? 'Surat Kerja'}',
              title: '${p['title']}',
              subtitle: '${p['location_text']}',
              bottom: Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  StatusPill(p['status'] as String?),
                  if (isLeader)
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 5,
                      ),
                      decoration: BoxDecoration(
                        color: VmsColors.gold,
                        borderRadius: BorderRadius.circular(99),
                      ),
                      child: Text(
                        'Anda ketua',
                        style: VmsTextStyles.caption.copyWith(
                          color: VmsColors.brand900,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (p['description'] != null)
                    FadeSlideIn(
                      child: SurfaceCard(
                        highlight: true,
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const IconTile(
                              icon: Icons.notes_rounded,
                              accent: Accent.violet,
                              size: 40,
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                '${p['description']}',
                                style: VmsTextStyles.bodySm.copyWith(
                                  color: Colors.white,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  if (_detail != null) _summary(_detail!),
                  if (p['status'] != 'DRAFT') ...[
                    const SizedBox(height: 10),
                    OutlinedButton.icon(
                      key: const Key('review-plan-button'),
                      onPressed: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => SkViewerScreen(
                            planId: _planId,
                            title: '${p['number'] ?? p['title']}',
                          ),
                        ),
                      ),
                      icon: const Icon(Icons.description_outlined),
                      label: const Text('Tinjau SK'),
                    ),
                  ],
                  if (p['status'] == 'APPEALED')
                    Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: NoticeBanner(
                        icon: Icons.edit_note_rounded,
                        text:
                            'Adendum diminta${p['appeal_reason'] != null ? ': ${p['appeal_reason']}' : ''}. Menunggu PM merevisi dan menerbitkan ulang SK.',
                        accent: Accent.amber,
                      ),
                    ),
                  if (p['status'] == 'ACCEPTED')
                    Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: NoticeBanner(
                        icon: Icons.event_available_rounded,
                        text:
                            'SK diterima. Status otomatis menjadi Berjalan pada ${_date.format(DateTime.parse(p['period_start'] as String))}.',
                        accent: Accent.emerald,
                      ),
                    ),
                  if (isLeader && p['status'] == 'PUBLISHED') ...[
                    const SectionTitle('Penerimaan SK'),
                    NoticeBanner(
                      icon: Icons.verified_user_outlined,
                      text: 'Tinjau SK lebih dulu. Terima SK = menandatangani secara digital (perlu internet). Bila ada yang perlu diubah, ajukan adendum ke PM.',
                      accent: Accent.amber,
                    ),
                    const SizedBox(height: 10),
                    OutlinedButton.icon(
                      key: const Key('amend-plan-button'),
                      onPressed: _amending || _accepting
                          ? null
                          : _requestAmendment,
                      icon: const Icon(Icons.edit_note_rounded),
                      label: Text(_amending ? 'Mengirim...' : 'Ajukan adendum'),
                    ),
                    const SizedBox(height: 8),
                    FilledButton.icon(
                      key: const Key('accept-plan-button'),
                      onPressed: _accepting ? null : _acceptPlan,
                      icon: _accepting
                          ? const SizedBox.square(
                              dimension: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.check_circle_outline_rounded),
                      label: Text(_accepting ? 'Menerima...' : 'Terima SK'),
                    ),
                  ],
                  if (_running) ...[
                    const SectionTitle('Aksi cepat'),
                    Row(
                      children: [
                        Expanded(
                          child: FadeSlideIn(
                            index: 1,
                            child: ActionTile(
                              icon: Icons.warning_amber_rounded,
                              label: 'Lapor insiden',
                              accent: Accent.rose,
                              onTap: _incident,
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: FadeSlideIn(
                            index: 2,
                            child: ActionTile(
                              icon: Icons.schedule_rounded,
                              label: 'Lapor lembur',
                              accent: Accent.amber,
                              onTap: _overtime,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                  const SectionTitle('Hari kerja'),
                  if (_error != null)
                    NoticeBanner(
                      icon: Icons.error_outline_rounded,
                      text: _error!,
                      accent: Accent.rose,
                    ),
                  if (_loading)
                    const Padding(
                      padding: EdgeInsets.all(24),
                      child: Center(child: CircularProgressIndicator()),
                    ),
                  if (!_loading && _days.isEmpty && _error == null)
                    const EmptyState(
                      icon: Icons.event_note_rounded,
                      title: 'Belum ada rincian hari',
                    ),
                  for (final (i, d) in _days.indexed) _dayCard(d, i, isLeader),
                  if (_weeks.isNotEmpty) ...[
                    const SectionTitle('Laporan mingguan'),
                    for (final w in _weeks)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: SurfaceCard(
                          padding: const EdgeInsets.all(14),
                          onTap: () async {
                            await Navigator.of(context).push(
                              MaterialPageRoute(
                                builder: (_) => WeeklyReportScreen(
                                  planId: _planId,
                                  week: w,
                                  days: _days,
                                  canEdit: isLeader && _running,
                                ),
                              ),
                            );
                            await _load();
                          },
                          child: Row(
                            children: [
                              const IconTile(
                                icon: Icons.view_week_rounded,
                                accent: Accent.violet,
                                size: 40,
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Text(
                                  '${w['name']}',
                                  style: VmsTextStyles.bodySm.copyWith(
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                              ),
                              StatusPill(
                                w['status'] == 'SUBMITTED' &&
                                        w['resubmitted'] == true
                                    ? 'RESUBMITTED'
                                    : w['status'] as String?,
                              ),
                            ],
                          ),
                        ),
                      ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Ringkasan isi SK alur v2: periode, kategori & tipe, tim, alat & kendaraan, detail per hari.
  Widget _summary(Map<String, dynamic> detail) {
    final plan = Map<String, dynamic>.from(detail['plan'] as Map);
    final team = (detail['team'] as List).cast<Map>();
    final assets = (detail['assets'] as List).cast<Map>();
    final days = (detail['days'] as List).cast<Map>();
    String date(Object? v) => _date.format(DateTime.parse('$v'));
    Widget line(IconData icon, String text) => Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: InfoRow(icon: icon, text: text),
    );
    return SurfaceCard(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          line(
            Icons.date_range_rounded,
            '${date(plan['period_start'])} – ${date(plan['period_end'])}',
          ),
          if (plan['category_label'] != null)
            line(
              Icons.category_outlined,
              '${plan['category_label']} · ${plan['unit_name'] ?? '-'}',
            ),
          if (plan['pm_name'] != null)
            line(Icons.badge_outlined, 'PM: ${plan['pm_name']}'),
          for (final m in team)
            line(
              m['role_in_plan'] == 'LEADER'
                  ? Icons.star_rounded
                  : Icons.person_outline_rounded,
              '${m['full_name']} — ${m['position']} (${m['role_in_plan'] == 'LEADER' ? 'Ketua tim' : 'Anggota'})',
            ),
          for (final a in assets)
            line(
              a['kind'] == 'VEHICLE'
                  ? Icons.directions_car_outlined
                  : Icons.handyman_outlined,
              '${a['name']} · ${a['code']}${a['driver_name'] != null ? ' — driver ${a['driver_name']}' : ''}',
            ),
          const Divider(height: 20),
          for (final (i, d) in days.indexed) ...[
            Text(
              'Hari ${i + 1} · ${date(d['work_date'])}',
              style: VmsTextStyles.bodySm.copyWith(fontWeight: FontWeight.w700),
            ),
            for (final t in (d['tasks'] as List).cast<Map>())
              Padding(
                padding: const EdgeInsets.only(left: 8, top: 2),
                child: Text(
                  '• ${t['title']} — ${t['description']}',
                  style: VmsTextStyles.caption,
                ),
              ),
            const SizedBox(height: 6),
          ],
        ],
      ),
    );
  }

  Widget _dayCard(Map<String, dynamic> d, int i, bool isLeader) {
    final date = DateTime.parse(d['work_date'] as String);
    final tasks = d['tasks'] as List;
    final done = tasks.where((t) => t['is_done'] == true).length;
    final progress = tasks.isEmpty ? 0.0 : done / tasks.length;
    final rep = d['report'] as Map?;
    final report = rep?['status'] == 'SUBMITTED' && rep?['resubmitted'] == true
        ? 'RESUBMITTED'
        : rep?['status'] as String?;
    final accent = statusStyle(report).accent;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: FadeSlideIn(
        index: i + 3,
        child: SurfaceCard(
          padding: const EdgeInsets.all(14),
          onTap: () async {
            await Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => PlanDayScreen(
                  planId: _planId,
                  day: d,
                  canEdit: isLeader && _running,
                  isLeader: isLeader,
                  running: _running,
                ),
              ),
            );
            await _load();
          },
          child: Row(
            children: [
              Container(
                width: 52,
                padding: const EdgeInsets.symmetric(vertical: 8),
                decoration: BoxDecoration(
                  color: accent.soft,
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Column(
                  children: [
                    Text(
                      DateFormat('d').format(date),
                      style: VmsTextStyles.title.copyWith(
                        color: accent.strong,
                        fontWeight: FontWeight.w800,
                        height: 1.1,
                      ),
                    ),
                    Text(
                      DateFormat('MMM', 'id_ID').format(date),
                      style: VmsTextStyles.caption.copyWith(
                        color: accent.strong,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${d['title']}',
                      style: VmsTextStyles.bodySm.copyWith(
                        fontWeight: FontWeight.w700,
                        color: VmsColors.neutral900,
                      ),
                    ),
                    const SizedBox(height: 8),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(99),
                      child: LinearProgressIndicator(
                        value: progress,
                        minHeight: 6,
                        color: progress == 1
                            ? Accent.emerald.strong
                            : Accent.blue.strong,
                        backgroundColor: VmsColors.neutral100,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        Text(
                          '$done/${tasks.length} tugas',
                          style: VmsTextStyles.caption,
                        ),
                        const Spacer(),
                        StatusPill(report),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 4),
              const Icon(
                Icons.chevron_right_rounded,
                color: VmsColors.neutral400,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
