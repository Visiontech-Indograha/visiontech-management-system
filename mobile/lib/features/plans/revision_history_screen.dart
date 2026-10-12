import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../core/theme/theme.dart';
import '../../shared/ui/vms_ui.dart';

final _stamp = DateFormat('d MMM yyyy, HH.mm', 'id_ID');
final _day = DateFormat('d MMM yyyy', 'id_ID');

/// Riwayat revisi rencana kerja (T6): siapa, kapan, alasan, dan sebelum → sesudah. Sama dengan tampilan web.
class RevisionHistoryScreen extends ConsumerStatefulWidget {
  const RevisionHistoryScreen({super.key, required this.planId});
  final String planId;

  @override
  ConsumerState<RevisionHistoryScreen> createState() => _RevisionHistoryScreenState();
}

class _RevisionHistoryScreenState extends ConsumerState<RevisionHistoryScreen> {
  List<Map<String, dynamic>> _items = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final items = await ref.read(syncEngineProvider).api.planRevisions(widget.planId);
      if (mounted) setState(() => _items = items);
    } catch (e) {
      if (mounted) setState(() => _error = apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String _value(Object? v) {
    if (v == null || '$v'.isEmpty) return '-';
    if (v is bool) return v ? 'Ya' : 'Tidak';
    final s = '$v';
    if (RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch(s)) return _day.format(DateTime.parse(s));
    return s;
  }

  String _list(Object? v, {bool dates = false}) => (v as List? ?? [])
      .map((e) => dates ? _day.format(DateTime.parse('$e')) : '$e')
      .join(', ');

  Widget _line(Map d) {
    final label = '${d['label']}';
    if (d['added'] != null || d['removed'] != null) {
      final dates = d['field'] == 'days';
      final parts = <String>[
        if ((d['added'] as List? ?? []).isNotEmpty) '+ ${_list(d['added'], dates: dates)}',
        if ((d['removed'] as List? ?? []).isNotEmpty) '− ${_list(d['removed'], dates: dates)}',
        if ((d['changed'] as List? ?? []).isNotEmpty) 'diubah: ${_list(d['changed'], dates: true)}',
      ];
      return Text('$label: ${parts.join('  ')}', style: VmsTextStyles.body);
    }
    return Text('$label: ${_value(d['before'])} → ${_value(d['after'])}', style: VmsTextStyles.body);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: VmsTopBar(
      onBack: () => Navigator.of(context).maybePop(),
      trailing: HeaderAction(icon: Icons.refresh_rounded, tooltip: 'Muat ulang', onTap: _load),
    ),
    body: _loading
        ? const Center(child: CircularProgressIndicator())
        : _error != null
        ? Center(child: Padding(padding: const EdgeInsets.all(24), child: Text(_error!)))
        : _items.isEmpty
        ? const EmptyState(
            icon: Icons.history_rounded,
            title: 'Belum ada revisi',
            message: 'Rencana kerja ini belum pernah direvisi PM.',
          )
        : ListView(
            padding: const EdgeInsets.all(16),
            children: [
              const SectionTitle('Riwayat revisi'),
              for (final r in _items)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: SurfaceCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Revisi ke-${((r['revision'] as num).toInt() - 1).clamp(1, 9999)} · ${r['revised_by_name'] ?? '-'}',
                          style: VmsTextStyles.subheading.copyWith(fontWeight: FontWeight.w700),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          _stamp.format(DateTime.parse('${r['created_at']}').toLocal()),
                          style: VmsTextStyles.caption,
                        ),
                        const SizedBox(height: 8),
                        Text('Alasan: ${r['reason']}', style: VmsTextStyles.body),
                        const SizedBox(height: 8),
                        for (final d in (r['diff'] as List).cast<Map>())
                          Padding(padding: const EdgeInsets.only(bottom: 4), child: _line(d)),
                      ],
                    ),
                  ),
                ),
            ],
          ),
  );
}
