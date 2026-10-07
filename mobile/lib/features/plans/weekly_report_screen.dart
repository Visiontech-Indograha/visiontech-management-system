import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../core/theme/theme.dart';
import '../../shared/ui/vms_ui.dart';
import 'sk_viewer_screen.dart';

final _date = DateFormat('d MMM yyyy', 'id_ID');

/// Laporan mingguan (alur SK v2, SK > 1 minggu): ketua menyusun dari laporan harian yang sudah disetujui
/// PM dalam minggu itu, boleh diedit, lalu dikirim; setelah disetujui dapat dibuka sebagai dokumen.
class WeeklyReportScreen extends ConsumerStatefulWidget {
  const WeeklyReportScreen({
    super.key,
    required this.planId,
    required this.week,
    required this.days,
    required this.canEdit,
  });
  final String planId;
  final Map<String, dynamic> week;
  final List<Map<String, dynamic>> days;
  final bool canEdit;

  @override
  ConsumerState<WeeklyReportScreen> createState() => _WeeklyReportScreenState();
}

class _WeeklyReportScreenState extends ConsumerState<WeeklyReportScreen> {
  late final _body = TextEditingController(text: '${widget.week['body']}');
  late final _obstacle = TextEditingController(
    text: '${widget.week['obstacle']}',
  );
  bool _busy = false;

  int get _no => widget.week['week'] as int;
  String get _status => widget.week['status'] as String;
  bool get _editable =>
      widget.canEdit &&
      widget.week['days_approved'] == true &&
      (_status == 'DRAFT' || _status == 'CHANGES_REQUESTED');

  void _snack(String m) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));

  List<Map<String, dynamic>> get _weekDays {
    final from = '${widget.week['starts_on']}';
    final to = '${widget.week['ends_on']}';
    return widget.days.where((d) {
      final w = '${d['work_date']}';
      return w.compareTo(from) >= 0 && w.compareTo(to) <= 0;
    }).toList();
  }

  void _compile() {
    final lines = <String>[];
    final obstacles = <String>[];
    for (final d in _weekDays) {
      final r = d['report'] as Map?;
      if (r == null) continue;
      final day = _date.format(DateTime.parse('${d['work_date']}'));
      lines.add('$day — ${r['body']}');
      final o = '${r['obstacle']}'.trim();
      if (o.isNotEmpty && o.toLowerCase() != 'tidak ada') {
        obstacles.add('$day: $o');
      }
    }
    _body.text = lines.join('\n');
    _obstacle.text = obstacles.isEmpty ? 'Tidak ada' : obstacles.join('\n');
    _snack(
      'Disusun dari ${lines.length} laporan harian. Periksa sebelum dikirim.',
    );
  }

  Future<void> _save({required bool submit}) async {
    if (_body.text.trim().length <= 10) {
      return _snack('Laporan mingguan wajib diisi (lebih dari 10 karakter).');
    }
    if (_obstacle.text.trim().isEmpty) {
      return _snack(
        'Ringkasan kendala wajib diisi (isi "Tidak ada" jika lancar).',
      );
    }
    setState(() => _busy = true);
    final api = ref.read(syncEngineProvider).api;
    try {
      await api.saveWeekly(
        widget.planId,
        _no,
        body: _body.text.trim(),
        obstacle: _obstacle.text.trim(),
      );
      if (submit) await api.submitWeekly(widget.planId, _no);
      if (!mounted) return;
      _snack(submit ? 'Laporan mingguan dikirim ke PM.' : 'Draf disimpan.');
      if (submit) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) _snack(apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final w = widget.week;
    final badge = _status == 'SUBMITTED' && w['resubmitted'] == true
        ? 'RESUBMITTED'
        : _status;
    return Scaffold(
      appBar: VmsTopBar(onBack: () => Navigator.of(context).maybePop()),
      body: ListView(
        padding: safeListPadding(context),
        children: [
          HeroHeader(
            eyebrow: 'Laporan mingguan',
            title: '${w['name']}',
            subtitle:
                '${_date.format(DateTime.parse('${w['starts_on']}'))} – ${_date.format(DateTime.parse('${w['ends_on']}'))}',
            bottom: StatusPill(badge),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (w['days_approved'] != true)
                  const NoticeBanner(
                    icon: Icons.hourglass_empty_rounded,
                    text: 'Semua laporan harian minggu ini harus disetujui PM sebelum laporan mingguan dibuat.',
                  ),
                if (w['review_note'] != null)
                  NoticeBanner(
                    icon: Icons.rate_review_rounded,
                    text: 'Catatan PM: ${w['review_note']}',
                    accent: Accent.rose,
                  ),
                if (_status == 'APPROVED')
                  OutlinedButton.icon(
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => SkViewerScreen(
                          planId: widget.planId,
                          title: '${w['name']}',
                          htmlPath:
                              '/work-plans/${widget.planId}/weekly/$_no/report/html',
                        ),
                      ),
                    ),
                    icon: const Icon(Icons.description_outlined),
                    label: const Text('Lihat laporan (disetujui PM)'),
                  ),
                if (_editable)
                  OutlinedButton.icon(
                    key: const Key('compile-weekly'),
                    onPressed: _compile,
                    icon: const Icon(Icons.merge_type_rounded),
                    label: const Text('Susun dari laporan harian'),
                  ),
                const SizedBox(height: 12),
                SurfaceCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      TextField(
                        controller: _body,
                        enabled: _editable,
                        maxLines: 8,
                        decoration: const InputDecoration(
                          labelText: 'Laporan mingguan',
                          alignLabelWithHint: true,
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _obstacle,
                        enabled: _editable,
                        maxLines: 3,
                        decoration: const InputDecoration(
                          labelText: 'Ringkasan kendala',
                          alignLabelWithHint: true,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                if (_editable) ...[
                  PrimaryAction(
                    label: 'Kirim ke PM',
                    icon: Icons.send_rounded,
                    busy: _busy,
                    onTap: () => _save(submit: true),
                  ),
                  const SizedBox(height: 10),
                  OutlinedButton.icon(
                    onPressed: _busy ? null : () => _save(submit: false),
                    icon: const Icon(Icons.save_rounded),
                    label: const Text('Simpan draf'),
                  ),
                ],
                if (!widget.canEdit)
                  Text(
                    'Laporan mingguan disusun ketua tim.',
                    style: VmsTextStyles.caption,
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
