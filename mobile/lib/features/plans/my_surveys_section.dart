import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../shared/ui/vms_ui.dart';
import 'survey_screen.dart' show SurveyScreen, surveyStateLabel;
import 'survey_widgets.dart' show surveyTgl;

class MySurveysSection extends ConsumerStatefulWidget {
  const MySurveysSection({super.key});

  @override
  ConsumerState<MySurveysSection> createState() => _MySurveysSectionState();
}

class _MySurveysSectionState extends ConsumerState<MySurveysSection> {
  List<Map<String, dynamic>>? _items;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final engine = ref.read(syncEngineProvider);
      final items = (await engine.fetchList('surveys_mine', () => engine.api.surveys())).items;
      if (mounted) setState(() => _items = items);
    } catch (_) {
      if (mounted) setState(() => _items = const []);
    }
  }

  @override
  Widget build(BuildContext context) {
    final items = _items;
    if (items == null || items.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SectionTitle('Survei saya'),
        for (final s in items.take(6))
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: SurfaceCard(
              onTap: () async {
                await Navigator.of(context)
                    .push(MaterialPageRoute(builder: (_) => SurveyScreen(taskId: '${s['task_id']}')));
                await _load();
              },
              child: Row(
                children: [
                  Icon(s['format'] == 'ACS' ? Icons.door_front_door_outlined : Icons.videocam_outlined),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('${s['title']}', style: Theme.of(context).textTheme.titleSmall),
                        Text(
                          '${s['client_name']} · ${s['point_count']} titik · ${surveyTgl(s['work_date'])}',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                  StatusPill('${s['state']}', label: surveyStateLabel[s['state']]),
                ],
              ),
            ),
          ),
      ],
    );
  }
}
