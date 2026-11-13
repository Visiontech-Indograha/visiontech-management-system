import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../shared/ui/vms_network_image.dart';
import '../../shared/ui/vms_ui.dart';

class SurveyStep extends StatelessWidget {
  const SurveyStep({super.key, required this.done, required this.text});
  final bool done;
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 2),
    child: Row(
      children: [
        Icon(
          done ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded,
          size: 18,
          color: done ? Colors.green : Colors.grey,
        ),
        const SizedBox(width: 8),
        Expanded(child: Text(text)),
      ],
    ),
  );
}

class SurveyPointCard extends StatelessWidget {
  const SurveyPointCard({super.key,
    required this.point,
    required this.editable,
    required this.busy,
    required this.onOpen,
    required this.onDelete,
  });

  final Map<String, dynamic> point;
  final bool editable;
  final bool busy;
  final VoidCallback onOpen;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final photos = (point['photos'] as List? ?? const []).cast<Map>();
    final lines = (point['lines'] as List? ?? const []).cast<Map>();
    final materials = lines.where((l) => l['category'] == 'MATERIAL').length;
    final needs = lines.where((l) => l['category'] == 'KEBUTUHAN').map((l) => '${l['name']}').toList();
    final remarks = (point['remarks'] as List? ?? const []).cast<Object>();
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: SurfaceCard(
        onTap: onOpen,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.place_rounded, size: 20),
                const SizedBox(width: 6),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('${point['name']}', style: Theme.of(context).textTheme.titleSmall),
                      Text(
                        '${point['point_type_name'] ?? ''} · '
                        '${point['point_status'] == 'EXISTING' ? 'Sudah terpasang' : 'Usulan baru'}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
                if (editable)
                  IconButton(
                    tooltip: 'Hapus titik',
                    onPressed: busy ? null : onDelete,
                    icon: const Icon(Icons.delete_outline),
                  )
                else
                  const Icon(Icons.chevron_right_rounded),
              ],
            ),
            const SizedBox(height: 6),
            if (photos.isEmpty)
              Text('Tidak ada foto', style: Theme.of(context).textTheme.bodySmall)
            else
              SizedBox(
              height: 64,
              child: ListView(
                scrollDirection: Axis.horizontal,
                children: [
                  for (final ph in photos)
                    Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: SurveyThumb(fileId: '${ph['file_id']}', label: ph['slot'] as String?, size: 64),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              runSpacing: 4,
              children: [
                SurveyChip(icon: Icons.photo_outlined, text: '${photos.length} foto'),
                SurveyChip(icon: Icons.inventory_2_outlined, text: '$materials material'),
                for (final n in needs) SurveyChip(icon: Icons.construction_rounded, text: n),
              ],
            ),
            if (remarks.isNotEmpty) ...[
              const SizedBox(height: 6),
              for (final r in remarks.take(3)) Text('• $r', style: Theme.of(context).textTheme.bodySmall),
            ],
          ],
        ),
      ),
    );
  }
}

class SurveyChip extends StatelessWidget {
  const SurveyChip({super.key, required this.icon, required this.text});
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
    decoration: BoxDecoration(color: Colors.black.withValues(alpha: 0.05), borderRadius: BorderRadius.circular(20)),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14),
        const SizedBox(width: 4),
        Text(text, style: const TextStyle(fontSize: 12)),
      ],
    ),
  );
}

/// Tanggal API (yyyy-MM-dd) → "21 Oktober 2026".
String surveyTgl(Object? v) {
  final d = DateTime.tryParse('${v ?? ''}');
  return d == null ? '-' : DateFormat('d MMMM yyyy', 'id_ID').format(d);
}

/// Pratinjau kecil foto berkas server (`fileId`, varian thumb).
class SurveyThumb extends ConsumerWidget {
  const SurveyThumb({super.key, required this.fileId, this.label, this.size = 72});
  final String fileId;
  final String? label;
  final double size;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final Widget image = VmsNetworkImage(fileId: fileId);
    return Stack(
      children: [
        Container(
          width: size,
          height: size,
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(8), color: Colors.black12),
          clipBehavior: Clip.antiAlias,
          child: image,
        ),
        if (label != null)
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: Container(
              color: Colors.black54,
              padding: const EdgeInsets.symmetric(horizontal: 3, vertical: 1),
              child: Text(
                label!,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: Colors.white, fontSize: 9),
              ),
            ),
          ),
      ],
    );
  }
}
