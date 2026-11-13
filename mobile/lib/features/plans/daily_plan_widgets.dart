import 'package:flutter/material.dart';

import '../../shared/ui/vms_ui.dart';
import 'daily_plan_format.dart';
import 'item_progress_screen.dart' show photoRefsOf;
import 'item_state.dart';

class DailyPlanItemCard extends StatelessWidget {
  const DailyPlanItemCard({super.key, required this.item, required this.dayStatus, required this.onTap});

  final Map<String, dynamic> item;
  final String dayStatus;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final phase = phaseAccent['${item['task_phase']}'] ?? Accent.slate;
    final done = num.tryParse('${item['completed_qty'] ?? 0}') ?? 0;
    final target = num.tryParse('${item['target_qty'] ?? 0}') ?? 0;
    final pct = target <= 0 ? 0.0 : (done / target).clamp(0, 1).toDouble();
    final state = itemDisplayState(
      raw: '${item['status']}',
      done: done,
      target: target,
      photoCount: photoRefsOf(item['realization_photos_json']).length,
      dayStatus: dayStatus,
    );
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

class DailyPlanTile extends StatelessWidget {
  const DailyPlanTile({super.key, required this.icon, required this.title, required this.subtitle, required this.onTap});

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => SurfaceCard(
    padding: EdgeInsets.zero,
    // ListTile butuh Material sendiri: tanpanya latar kartu (DecoratedBox) menutupi efek tekan.
    child: Material(
      color: Colors.transparent,
      child: ListTile(
        leading: Icon(icon),
        title: Text(title),
        subtitle: Text(subtitle),
        trailing: const Icon(Icons.chevron_right_rounded),
        onTap: onTap,
      ),
    ),
  );
}
