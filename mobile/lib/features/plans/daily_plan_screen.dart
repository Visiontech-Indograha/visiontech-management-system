import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/api_client.dart';
import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../data/sync_engine.dart';
import '../../shared/ui/vms_ui.dart';
import '../auth/auth_controller.dart';
import '../auth/auth_state.dart';
import 'bast_sign_screen.dart';
import 'item_progress_screen.dart';
import 'survey_screen.dart';

const phaseLabel = {
  'SURVEY': 'Survei',
  'PREPARATION': 'Persiapan',
  'INSTALLATION': 'Instalasi',
  'REPLACEMENT': 'Replacement',
  'MAINTENANCE': 'Maintenance',
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

/// Koreksi yang masih berjalan dari riwayat koreksi satu jadwal (terbaru dulu); null bila tidak ada.
Map<String, dynamic>? openCorrectionOf(List<Map<String, dynamic>> corrections) {
  for (final c in corrections) {
    if (const {'REQUESTED', 'REVISING', 'IN_REVIEW'}.contains(c['status'])) return c;
  }
  return null;
}

String correctionStateTitle(String status) => switch (status) {
  'REQUESTED' => 'Koreksi menunggu keputusan PM',
  'REVISING' => 'PM meminta revisi laporan',
  'IN_REVIEW' => 'Revisi menunggu pemeriksaan PM',
  _ => status,
};

String correctionStateSubtitle(Map<String, dynamic> correction) {
  final note = (correction['review_note'] as String?)?.trim();
  return switch (correction['status']) {
    'REVISING' => note == null || note.isEmpty
        ? 'Perbarui laporan dan hasil kerja, lalu kirim revisi'
        : 'Catatan PM: $note',
    'REQUESTED' => 'Alasan: ${correction['reason']}',
    _ => 'Anda akan diberi tahu setelah PM memutuskan',
  };
}

class _DailyPlanScreenState extends ConsumerState<DailyPlanScreen> {
  Map<String, dynamic>? _plan;
  Map<String, dynamic>? _dailyReport;
  String? _error;
  bool _busy = false;
  bool _reportPending = false;
  List<Map<String, dynamic>> _corrections = const [];

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
      final engine = ref.read(syncEngineProvider);
      final plan = await engine.fetchMap(
        'daily_plan_${widget.dailyPlanId}',
        () => engine.api.dailyPlan(widget.dailyPlanId),
      );
      var report = _dailyReport;
      try {
        report = await engine.api.dailyReport(widget.dailyPlanId);
        await engine.cachePut('daily_report_${widget.dailyPlanId}', report);
        _reportPending = false;
      } on DioException catch (e) {
        if (e.response?.statusCode == 404) {
          report = null;
          _reportPending = false;
        } else if (!isNetworkFailure(e)) {
          rethrow;
        } else {
          final cached = await engine.cacheGet('daily_report_${widget.dailyPlanId}');
          if (cached.data is Map) report = Map<String, dynamic>.from(cached.data as Map);
        }
      }
      var corrections = _corrections;
      if (plan['leader_employee_id'] == _me) {
        try {
          corrections = await engine.api.planCorrections(widget.dailyPlanId);
        } on DioException {
          // riwayat koreksi hanya tambahan; layar tetap tampil tanpanya
        }
      }
      if (mounted) {
        setState(() => (_plan = plan, _dailyReport = report, _corrections = corrections, _error = null));
      }
    } catch (e) {
      if (mounted) setState(() => _error = apiErrorMessage(e));
    }
  }

  void _snack(String text, {bool error = false}) => showVmsToast(context, text, error: error);

  /// Koreksi yang masih berjalan (diminta, direvisi, atau menunggu pemeriksaan PM); null bila tidak ada.
  Map<String, dynamic>? get _openCorrection =>
      openCorrectionOf(_corrections);

  Future<void> _requestCorrection() async {
    final reason = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Ajukan koreksi laporan'),
        content: TextField(
          controller: reason,
          maxLines: 3,
          decoration: const InputDecoration(labelText: 'Apa yang perlu diperbaiki? (min. 5 karakter)'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Batal')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Kirim ke PM')),
        ],
      ),
    );
    final text = reason.text.trim();
    disposeAfterDialog([reason]);
    if (ok != true) return;
    if (text.length < 5) return _snack('Tulis alasan koreksi minimal 5 karakter.', error: true);
    await _run(
      () => ref.read(syncEngineProvider).api.requestCorrection(widget.dailyPlanId, text),
      'Permintaan koreksi dikirim ke PM.',
    );
  }

  /// Waktu kirim laporan untuk manusia (waktu HP), bukan string ISO mentah dari server.
  String _sentAt(dynamic iso) {
    final at = iso is String ? DateTime.tryParse(iso)?.toLocal() : null;
    return at == null ? '-' : DateFormat('d MMM yyyy, HH:mm', 'id_ID').format(at);
  }

  Future<void> _dailyReportForm() async {
    final summary = TextEditingController(text: _dailyReport?['summary'] as String? ?? '');
    final obstacles = TextEditingController(text: _dailyReport?['obstacles'] as String? ?? '');
    final report = await showDialog<Map<String, String>>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Laporan harian'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: summary,
              minLines: 2,
              maxLines: 4,
              decoration: const InputDecoration(labelText: 'Ringkasan hasil kerja *'),
            ),
            TextField(
              controller: obstacles,
              minLines: 1,
              maxLines: 3,
              decoration: const InputDecoration(labelText: 'Kendala (opsional)'),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Batal')),
          FilledButton(
            onPressed: () {
              final text = summary.text.trim();
              if (text.length < 3) {
                _snack('Ringkasan minimal 3 karakter.', error: true);
                return;
              }
              Navigator.pop(ctx, {'summary': text, 'obstacles': obstacles.text.trim()});
            },
            child: const Text('Kirim laporan'),
          ),
        ],
      ),
    );
    disposeAfterDialog([summary, obstacles]);
    if (report == null || !mounted) return;

    setState(() => _busy = true);
    try {
      final applied = await ref.read(syncEngineProvider).submit(
        OfflineOp.dailyReportSubmit,
        {
          'daily_plan_id': widget.dailyPlanId,
          'summary': report['summary'],
          'obstacles': report['obstacles'],
          'photos_json': const <String>[],
        },
      );
      if (applied) {
        _reportPending = false;
        _snack('Laporan harian tersimpan.');
        await _load();
      } else {
        setState(() => _reportPending = true);
        _snack('Laporan disimpan dan menunggu koneksi untuk dikirim.');
      }
    } catch (e) {
      _snack(apiErrorMessage(e), error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _run(Future<void> Function() action, String done) async {
    setState(() => _busy = true);
    try {
      await action();
      _snack(done);
      await _load();
    } catch (e) {
      _snack(apiErrorMessage(e), error: true);
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
            TextField(
              controller: reason,
              decoration: const InputDecoration(labelText: 'Alasan'),
            ),
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
      () => ref
          .read(syncEngineProvider)
          .api
          .requestOvertime(dayId: widget.dailyPlanId, hours: h, reason: reason.text.trim()),
      'Pengajuan lembur terkirim ke PM.',
    );
  }

  /// Tugas survei (fase SURVEY, menempel pada order) dibuka di layar survei berformat baku (docs/37).
  static bool isSurveyTask(Map<String, dynamic> item) =>
      item['task_phase'] == 'SURVEY' && item['depends_on_item_id'] == null && item['completion_id'] != null;

  /// Titik survei buatan ketua tim (anak tugas survei) dikelola di layar survei, tidak di daftar jadwal.
  static bool isSurveyPoint(Map<String, dynamic> item) =>
      item['task_phase'] == 'SURVEY' && item['depends_on_item_id'] != null;

  Future<void> _openItem(Map<String, dynamic> item) async {
    if (isSurveyTask(item)) {
      await Navigator.of(context).push(MaterialPageRoute(builder: (_) => SurveyScreen(taskId: '${item['item_id']}')));
      await _load();
      return;
    }
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => ItemProgressScreen(
          itemId: item['item_id'] as String,
          dayStatus: '${_plan!['status']}',
          isLeader: _isLeader,
        ),
      ),
    );
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
                  : Padding(
                      padding: const EdgeInsets.all(16),
                      child: NoticeBanner(icon: Icons.error_outline, text: _error!),
                    ),
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
                        InfoRow(
                          icon: Icons.place_outlined,
                          text: plan['site_lat'] == null ||
                                  plan['site_lng'] == null ||
                                  plan['attendance_radius_m'] == null
                              ? 'Lokasi belum ditentukan · presensi belum tersedia'
                              : '${plan['site_name'] ?? 'Site'} (radius absen ${plan['attendance_radius_m']} m)',
                        ),
                        const SizedBox(height: 4),
                        InfoRow(
                          icon: Icons.schedule_rounded,
                          text:
                              'Jam kerja ${'${plan['clock_in_time']}'.substring(0, 5)}–${'${plan['clock_out_time']}'.substring(0, 5)}',
                        ),
                        const SizedBox(height: 4),
                        InfoRow(
                          icon: Icons.groups_2_outlined,
                          text: '${plan['team_name']} · ketua ${plan['leader_name']}',
                        ),
                        if (plan['pm_name'] != null) ...[
                          const SizedBox(height: 4),
                          ContactRow(label: 'PM', name: '${plan['pm_name']}', phone: plan['pm_phone'] as String?),
                        ],
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
                  if (_isLeader && plan['status'] == 'COMPLETED' && _openCorrection == null) ...[
                    const SizedBox(height: 12),
                    _Tile(
                      icon: Icons.edit_note_rounded,
                      title: 'Ajukan koreksi laporan',
                      subtitle: 'Perbaikan laporan harus disetujui PM',
                      onTap: _busy ? null : _requestCorrection,
                    ),
                  ],
                  if (_isLeader && _openCorrection != null) ...[
                    const SizedBox(height: 12),
                    _Tile(
                      icon: Icons.rule_rounded,
                      title: correctionStateTitle(_openCorrection!['status'] as String),
                      subtitle: correctionStateSubtitle(_openCorrection!),
                      onTap: null,
                    ),
                    if (_openCorrection!['status'] == 'REVISING') ...[
                      const SizedBox(height: 12),
                      PrimaryAction(
                        label: 'Kirim revisi ke PM',
                        icon: Icons.send_rounded,
                        busy: _busy,
                        onTap: _dailyReport == null
                            ? null
                            : () => _run(
                                () => ref.read(syncEngineProvider).api.submitCorrection(
                                  _openCorrection!['correction_id'] as String,
                                ),
                                'Revisi dikirim ke PM.',
                              ),
                      ),
                    ],
                  ],
                  if (_isLeader && plan['status'] == 'ONGOING') ...[
                    const SizedBox(height: 12),
                    _Tile(
                      icon: _dailyReport == null ? Icons.assignment_outlined : Icons.assignment_turned_in_outlined,
                      title: _dailyReport == null ? 'Kirim laporan harian' : 'Perbarui laporan harian',
                      subtitle: _reportPending
                          ? 'Menunggu koneksi untuk dikirim'
                          : _dailyReport == null
                              ? 'Wajib sebelum hari kerja ditutup atau absen pulang'
                              : 'Terkirim · ${_sentAt(_dailyReport!['submitted_at'])}',
                      onTap: _busy ? null : _dailyReportForm,
                    ),
                    const SizedBox(height: 12),
                    if (_openCorrection == null)
                    PrimaryAction(
                      label: _dailyReport == null ? 'Kirim laporan untuk menutup hari' : 'Selesaikan hari kerja',
                      icon: Icons.task_alt_rounded,
                      busy: _busy,
                      onTap: _dailyReport == null || _reportPending ? null : () => _run(
                        () => ref.read(syncEngineProvider).api.completeDay(widget.dailyPlanId),
                        'Hari kerja ditutup.',
                      ),
                    ),
                  ],
                  const SectionTitle('Daftar pekerjaan hari ini'),
                  for (final item in (plan['items'] as List? ?? const []).cast<Map>().where(
                    (i) => !isSurveyPoint(Map<String, dynamic>.from(i)),
                  ))
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
      const SectionTitle('Serah terima pekerjaan'),
      for (final id in ids)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: FutureBuilder<Map<String, dynamic>>(
            future: ref.read(syncEngineProvider).api.workCompletion(id),
            builder: (context, snap) {
              final o = snap.data;
              final (title, subtitle) = o == null
                  ? ('Serah terima pekerjaan', 'Memuat status…')
                  : o['pm_signed_at'] != null
                  ? ('Sudah disetujui PM', '${o['project_title']} · pekerjaan selesai')
                  : o['leader_signed_at'] != null
                  ? ('Menunggu persetujuan PM', '${o['project_title']} · bisa tanda tangan ulang')
                  : ('Tanda tangan serah terima', '${o['project_title']} · ringkasan, foto hasil kerja, tanda tangan');
              return _Tile(
                icon: o?['pm_signed_at'] != null ? Icons.verified_rounded : Icons.draw_rounded,
                title: title,
                subtitle: subtitle,
                onTap: () async {
                  await Navigator.of(context).push(MaterialPageRoute(builder: (_) => BastSignScreen(completionId: id)));
                  await _load();
                },
              );
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
    final text = Theme.of(context).textTheme;
    final phase = phaseAccent['${item['task_phase']}'] ?? Accent.slate;
    final done = num.tryParse('${item['completed_qty'] ?? 0}') ?? 0;
    final target = num.tryParse('${item['target_qty'] ?? 0}') ?? 0;
    final pct = target <= 0 ? 0.0 : (done / target).clamp(0, 1).toDouble();
    final raw = '${item['status']}';
    final state = raw == 'DONE'
        ? 'DONE'
        : (done > 0 && raw != 'SHIFTED_DAY' && raw != 'PENDING_ROLLOVER' ? 'PARTIAL' : raw);
    final accent = statusStyle(state).accent;
    return Material(
      color: Theme.of(context).colorScheme.surface,
      borderRadius: BorderRadius.circular(16),
      clipBehavior: Clip.antiAlias,
      elevation: 0.5,
      child: InkWell(
        onTap: onTap,
        child: Container(
          decoration: BoxDecoration(
            border: Border(left: BorderSide(color: phase.strong, width: 5)),
          ),
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(color: phase.soft, borderRadius: BorderRadius.circular(99)),
                    child: Text(
                      phaseLabel['${item['task_phase']}'] ?? '${item['task_phase']}',
                      style: text.labelSmall?.copyWith(color: phase.strong, fontWeight: FontWeight.w700),
                    ),
                  ),
                  const Spacer(),
                  StatusPill(state),
                ],
              ),
              const SizedBox(height: 8),
              Text('${item['title']}', style: text.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
              if (item['location_name'] != null) ...[
                const SizedBox(height: 4),
                InfoRow(icon: Icons.place_outlined, text: '${item['location_name']}'),
              ],
              const SizedBox(height: 10),
              ClipRRect(
                borderRadius: BorderRadius.circular(99),
                child: LinearProgressIndicator(
                  value: pct,
                  minHeight: 6,
                  color: accent.strong,
                  backgroundColor: accent.soft,
                ),
              ),
              const SizedBox(height: 4),
              Row(
                children: [
                  Expanded(
                    child: Text(
                      '${qtyText(item['completed_qty'])} dari ${qtyText(item['target_qty'])} selesai',
                      style: text.bodySmall?.copyWith(color: accent.strong, fontWeight: FontWeight.w600),
                    ),
                  ),
                  Icon(Icons.chevron_right_rounded, color: accent.strong),
                ],
              ),
            ],
          ),
        ),
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
