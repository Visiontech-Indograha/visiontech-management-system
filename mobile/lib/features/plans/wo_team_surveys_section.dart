import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../shared/ui/vms_ui.dart';

const woSurveyStatusLabel = {
  'DRAFT': 'Sedang diisi',
  'SUBMITTED': 'Menunggu PM',
  'APPROVED': 'Disetujui PM',
};

String woSurveyDate(Object? v) {
  final d = DateTime.tryParse('${v ?? ''}');
  return d == null ? '-' : DateFormat('d MMMM yyyy', 'id_ID').format(d);
}

/// Satu kartu survei work order milik tim.
class WoSurveyCard extends StatelessWidget {
  const WoSurveyCard({super.key, required this.survey, this.onTap});

  final Map<String, dynamic> survey;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final s = survey;
    final lokasi = [s['client_name'], s['site_name']]
        .where((e) => e != null && '$e'.isNotEmpty)
        .join(' · ');
    return SurfaceCard(
      onTap: onTap,
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 48),
        child: Row(
          children: [
            const Icon(Icons.fact_check_outlined),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${s['wo_number']} · ${s['title']}',
                      style: Theme.of(context).textTheme.titleSmall),
                  if (lokasi.isNotEmpty)
                    Text(lokasi, style: Theme.of(context).textTheme.bodySmall),
                  Text(
                    '${woSurveyDate(s['survey_date'])} · ${s['filled_points'] ?? 0} titik terisi',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
            StatusPill('${s['survey_status']}',
                label: woSurveyStatusLabel['${s['survey_status']}']),
          ],
        ),
      ),
    );
  }
}

/// Bagian "Survei dari work order": dibaca lewat cache sehingga tetap tampil tanpa sinyal.
class WoTeamSurveysSection extends ConsumerStatefulWidget {
  const WoTeamSurveysSection({super.key});

  @override
  ConsumerState<WoTeamSurveysSection> createState() => _WoTeamSurveysSectionState();
}

class _WoTeamSurveysSectionState extends ConsumerState<WoTeamSurveysSection> {
  List<Map<String, dynamic>>? _items;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _error = null);
    try {
      final engine = ref.read(syncEngineProvider);
      final items = (await engine.fetchList('wo_team_surveys', () => engine.api.teamSurveys())).items;
      if (mounted) setState(() => _items = items);
    } catch (e) {
      if (mounted) setState(() => _error = apiErrorMessage(e));
    }
  }

  void _open(Map<String, dynamic> s) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (_) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              WoSurveyCard(survey: s),
              const SizedBox(height: 12),
              Text('Tim: ${s['surveyor_team_name'] ?? '-'}'),
              const SizedBox(height: 4),
              const Text(
                'Pengisian titik survei dari HP untuk work order belum tersedia. '
                'Hubungi PM bila perlu bantuan.',
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final items = _items;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SectionTitle('Survei dari work order'),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Column(
              children: [
                Text(_error!, textAlign: TextAlign.center),
                TextButton(onPressed: _load, child: const Text('Coba lagi')),
              ],
            ),
          )
        else if (items == null)
          const Padding(
            padding: EdgeInsets.all(16),
            child: Center(child: CircularProgressIndicator()),
          )
        else if (items.isEmpty)
          const EmptyState(
            icon: Icons.fact_check_outlined,
            title: 'Belum ada survei untuk tim Anda',
          )
        else
          for (final s in items)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: WoSurveyCard(survey: s, onTap: () => _open(s)),
            ),
      ],
    );
  }
}
