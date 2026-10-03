import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/error_message.dart';
import '../../core/local_storage.dart';
import '../../core/photo_capture.dart';
import '../../core/providers.dart';
import '../../core/theme/theme.dart';
import '../../shared/ui/vms_ui.dart';

final _date = DateFormat('d MMM yyyy', 'id_ID');

/// Laporan akhir (alur SK v2 PR3, flowchart SK2-F): ketua menyusun dari laporan harian & mingguan yang
/// disetujui, boleh diedit, lalu mengajukan penutupan. Alat & kendaraan wajib sudah dikembalikan.
class FinalReportScreen extends ConsumerStatefulWidget {
  const FinalReportScreen({
    super.key,
    required this.plan,
    required this.days,
    required this.weeks,
    this.existing,
  });
  final Map<String, dynamic> plan;
  final List<Map<String, dynamic>> days;
  final List<Map<String, dynamic>> weeks;
  final Map<String, dynamic>? existing;

  @override
  ConsumerState<FinalReportScreen> createState() => _FinalReportScreenState();
}

class _FinalReportScreenState extends ConsumerState<FinalReportScreen> {
  late final _body = TextEditingController(
    text: widget.existing?['body'] as String? ?? '',
  );
  late final _obstacle = TextEditingController(
    text: widget.existing?['obstacle'] as String? ?? '',
  );
  final List<String> _photos = [];
  bool _busy = false;

  void _snack(String m) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));

  void _compile() {
    final lines = <String>[];
    final obstacles = <String>[];
    for (final w in widget.weeks) {
      if ('${w['body']}'.trim().isNotEmpty) {
        lines.add('${w['name']}: ${w['body']}');
      }
    }
    if (lines.isEmpty) {
      for (final d in widget.days) {
        final r = d['report'] as Map?;
        if (r == null) continue;
        lines.add(
          '${_date.format(DateTime.parse('${d['work_date']}'))} — ${r['body']}',
        );
      }
    }
    for (final d in widget.days) {
      final o = '${(d['report'] as Map?)?['obstacle'] ?? ''}'.trim();
      if (o.isNotEmpty && o.toLowerCase() != 'tidak ada') {
        obstacles.add(
          '${_date.format(DateTime.parse('${d['work_date']}'))}: $o',
        );
      }
    }
    _body.text = lines.join('\n');
    _obstacle.text = obstacles.isEmpty ? 'Tidak ada' : obstacles.join('\n');
    _snack(
      'Disusun dari laporan yang sudah disetujui PM. Periksa sebelum dikirim.',
    );
  }

  Future<void> _addPhoto() async {
    final (file, err) = await captureWatermarkedPhoto(
      context: context,
      label: 'Foto hasil akhir',
      kind: LocalFileKind.dailyReport,
      hint: 'Foto hasil pekerjaan selesai',
    );
    if (file != null) {
      setState(() => _photos.add(file.path));
    } else if (err != null) {
      _snack(err);
    }
  }

  Future<void> _submit() async {
    if (_body.text.trim().isEmpty || _obstacle.text.trim().isEmpty) {
      return _snack('Laporan keseluruhan dan ringkasan kendala wajib diisi.');
    }
    setState(() => _busy = true);
    final api = ref.read(syncEngineProvider).api;
    try {
      final ids = <String>[];
      for (final p in _photos) {
        ids.add(await api.uploadFile(File(p)));
      }
      final fresh = await api.workPlan(widget.plan['id'] as String);
      await api.requestCompletion(
        widget.plan['id'] as String,
        rowVersion: fresh['row_version'] as int,
        body: _body.text.trim(),
        obstacle: _obstacle.text.trim(),
        evidenceFileIds: ids,
      );
      if (!mounted) return;
      _snack('Laporan akhir dikirim. Status: Pengajuan penutupan.');
      Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted) _snack(apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final note = widget.existing?['review_note'];
    return Scaffold(
      appBar: VmsTopBar(onBack: () => Navigator.of(context).maybePop()),
      body: ListView(
        padding: safeListPadding(context),
        children: [
          HeroHeader(
            eyebrow: 'Laporan akhir',
            title: '${widget.plan['title']}',
            subtitle: '${widget.plan['number'] ?? ''}',
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (note != null)
                  NoticeBanner(
                    icon: Icons.rate_review_rounded,
                    text: 'Perlu perbaikan — catatan PM: $note',
                    accent: Accent.rose,
                  ),
                const NoticeBanner(
                  icon: Icons.inventory_2_outlined,
                  text: 'Pastikan semua alat & kendaraan sudah dikembalikan sebelum mengajukan penutupan.',
                  accent: Accent.amber,
                ),
                OutlinedButton.icon(
                  key: const Key('compile-final'),
                  onPressed: _compile,
                  icon: const Icon(Icons.merge_type_rounded),
                  label: const Text('Susun dari laporan harian & mingguan'),
                ),
                const SizedBox(height: 12),
                SurfaceCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      TextField(
                        controller: _body,
                        maxLines: 8,
                        decoration: const InputDecoration(
                          labelText: 'Laporan keseluruhan',
                          alignLabelWithHint: true,
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _obstacle,
                        maxLines: 3,
                        decoration: const InputDecoration(
                          labelText: 'Ringkasan kendala keseluruhan',
                          alignLabelWithHint: true,
                        ),
                      ),
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              '${_photos.length} foto baru',
                              style: VmsTextStyles.bodySm,
                            ),
                          ),
                          TextButton.icon(
                            onPressed: _addPhoto,
                            icon: const Icon(Icons.add_a_photo_rounded),
                            label: const Text('Foto'),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                PrimaryAction(
                  label: 'Ajukan penutupan',
                  icon: Icons.flag_rounded,
                  busy: _busy,
                  onTap: _submit,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
