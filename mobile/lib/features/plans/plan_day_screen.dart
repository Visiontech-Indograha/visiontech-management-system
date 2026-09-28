import 'package:flutter/material.dart';

import '../../core/local_storage.dart';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/error_message.dart';
import '../../core/photo_capture.dart';
import '../../core/providers.dart';
import '../../data/sync_engine.dart';
import '../../core/theme/theme.dart';
import '../../shared/ui/vms_select_field.dart';
import '../../shared/ui/vms_ui.dart';

/// Satu hari kerja SK: checklist tugas + laporan harian (dok 05 §3.7). Ketua SK
/// mengisi & mengirim; semua aksi lewat antrean luring (idempoten per client_op_id).
class PlanDayScreen extends ConsumerStatefulWidget {
  const PlanDayScreen({
    super.key,
    required this.planId,
    required this.day,
    required this.canEdit,
  });
  final String planId;
  final Map<String, dynamic> day;
  final bool canEdit;

  @override
  ConsumerState<PlanDayScreen> createState() => _PlanDayScreenState();
}

class _PlanDayScreenState extends ConsumerState<PlanDayScreen> {
  late final List<Map<String, dynamic>> _tasks = (widget.day['tasks'] as List)
      .map((t) => Map<String, dynamic>.from(t as Map))
      .toList();
  late final Map<String, dynamic>? _report = widget.day['report'] == null
      ? null
      : Map<String, dynamic>.from(widget.day['report'] as Map);
  late final _body = TextEditingController(
    text: _report?['body'] as String? ?? '',
  );
  late final _obstacle = TextEditingController(
    text: _report?['obstacle'] as String? ?? '',
  );
  final List<String> _photos = [];
  bool _busy = false;

  String get _dayId => widget.day['id'] as String;
  String get _status => (_report?['status'] as String?) ?? 'DRAFT';
  bool get _editable =>
      widget.canEdit && (_status == 'DRAFT' || _status == 'CHANGES_REQUESTED');

  void _snack(String m) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));

  Future<bool> _send(
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
      return true;
    } on SyncRejectedException catch (e) {
      _snack(e.message);
    } catch (e) {
      _snack(apiErrorMessage(e));
    }
    return false;
  }

  Future<void> _toggle(Map<String, dynamic> task) async {
    setState(() => task['is_done'] = !(task['is_done'] == true));
    final ok = await _send(OfflineOp.taskToggle, {
      'plan_id': widget.planId,
      'day_id': _dayId,
      'task_id': task['id'],
    });
    if (!ok && mounted) {
      setState(() => task['is_done'] = !(task['is_done'] == true));
    }
  }

  Future<void> _addPhoto() async {
    final (file, err) = await captureWatermarkedPhoto(
      context: context,
      label: 'Foto bukti',
      kind: LocalFileKind.dailyReport,
      hint: 'Foto hasil pekerjaan hari ini',
    );
    if (file != null) {
      setState(() => _photos.add(file.path));
    } else if (err != null) {
      _snack(err);
    }
  }

  Future<void> _save({required bool submit}) async {
    if (_body.text.trim().isEmpty) {
      return _snack('Isi uraian pekerjaan hari ini.');
    }
    setState(() => _busy = true);
    final base = {'plan_id': widget.planId, 'day_id': _dayId};
    final saved = await _send(OfflineOp.dailyReportSave, {
      ...base,
      'body': _body.text.trim(),
      'obstacle': _obstacle.text.trim(),
      'evidence_file_ids': List<String>.from(
        (_report?['evidence_file_ids'] as List?) ?? const [],
      ),
    }, files: List.of(_photos));
    if (saved) _photos.clear();
    if (saved && submit) await _send(OfflineOp.dailyReportSubmit, base);
    if (mounted) {
      setState(() => _busy = false);
      if (saved && submit) Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final done = _tasks.where((t) => t['is_done'] == true).length;
    final saved = ((_report?['evidence_file_ids'] as List?) ?? const []).length;
    return Scaffold(
      appBar: VmsTopBar(onBack: () => Navigator.of(context).maybePop()),
      body: ListView(
        padding: safeListPadding(context),
        children: [
          HeroHeader(
            eyebrow: 'Hari kerja',
            title: '${widget.day['title']}',
            subtitle: '$done dari ${_tasks.length} tugas selesai',
            bottom: StatusPill(_status),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SectionTitle('Tugas'),
                if (_tasks.isEmpty)
                  const EmptyState(
                    icon: Icons.checklist_rounded,
                    title: 'Belum ada tugas untuk hari ini',
                  ),
                for (final (i, t) in _tasks.indexed)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: FadeSlideIn(
                      index: i,
                      child: SurfaceCard(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 10,
                        ),
                        onTap: widget.canEdit ? () => _toggle(t) : null,
                        child: Row(
                          children: [
                            AnimatedContainer(
                              duration: const Duration(milliseconds: 220),
                              width: 26,
                              height: 26,
                              decoration: BoxDecoration(
                                color: t['is_done'] == true
                                    ? Accent.emerald.strong
                                    : Colors.transparent,
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(
                                  color: t['is_done'] == true
                                      ? Accent.emerald.strong
                                      : VmsColors.neutral300,
                                  width: 2,
                                ),
                              ),
                              child: t['is_done'] == true
                                  ? const Icon(
                                      Icons.check_rounded,
                                      size: 18,
                                      color: Colors.white,
                                    )
                                  : null,
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                '${t['title']}',
                                style: VmsTextStyles.bodySm.copyWith(
                                  fontWeight: FontWeight.w600,
                                  color: t['is_done'] == true
                                      ? VmsColors.neutral500
                                      : VmsColors.neutral900,
                                  decoration: t['is_done'] == true
                                      ? TextDecoration.lineThrough
                                      : null,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                const SectionTitle('Laporan harian'),
                if (_report?['review_note'] != null)
                  NoticeBanner(
                    icon: Icons.rate_review_rounded,
                    text: 'Catatan PM: ${_report!['review_note']}',
                    accent: Accent.rose,
                  ),
                SurfaceCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      TextField(
                        controller: _body,
                        enabled: _editable,
                        maxLines: 5,
                        decoration: const InputDecoration(
                          labelText: 'Uraian pekerjaan',
                          alignLabelWithHint: true,
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _obstacle,
                        enabled: _editable,
                        maxLines: 3,
                        decoration: const InputDecoration(
                          labelText: 'Kendala (boleh kosong)',
                          alignLabelWithHint: true,
                        ),
                      ),
                      const SizedBox(height: 14),
                      Row(
                        children: [
                          const IconTile(
                            icon: Icons.photo_library_rounded,
                            accent: Accent.teal,
                            size: 40,
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              '$saved foto tersimpan${_photos.isEmpty ? '' : ' · ${_photos.length} baru'}',
                              style: VmsTextStyles.bodySm.copyWith(
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                          if (_editable)
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
                ] else if (!widget.canEdit)
                  const NoticeBanner(
                    icon: Icons.info_outline_rounded,
                    text:
                        'Hanya ketua SK yang mengisi laporan saat SK berjalan.',
                    accent: Accent.blue,
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Form insiden K3/aset (dok 05 §3.9). Mengembalikan data + path foto lokal.
class IncidentFormScreen extends StatefulWidget {
  const IncidentFormScreen({super.key});

  @override
  State<IncidentFormScreen> createState() => _IncidentFormScreenState();
}

class _IncidentFormScreenState extends State<IncidentFormScreen> {
  static const _categories = {
    'K3_RINGAN': 'K3 ringan',
    'K3_BERAT': 'K3 berat',
    'K3_LINGKUNGAN': 'K3 lingkungan',
    'K3_HAMPIR': 'Hampir celaka',
    'ASET': 'Kerusakan aset',
  };
  static const _severities = {
    'RENDAH': 'Rendah',
    'SEDANG': 'Sedang',
    'TINGGI': 'Tinggi',
    'KRITIS': 'Kritis',
  };

  String _category = 'K3_RINGAN';
  String _severity = 'RENDAH';
  final _description = TextEditingController();
  final List<String> _photos = [];

  Future<void> _addPhoto() async {
    final (file, err) = await captureWatermarkedPhoto(
      context: context,
      label: 'Foto insiden',
      hint: 'Foto lokasi kejadian',
      kind: LocalFileKind.incident,
    );
    if (file != null) setState(() => _photos.add(file.path));
    if (err != null && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(err)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: VmsTopBar(onBack: () => Navigator.of(context).maybePop()),
      body: ListView(
        padding: safeListPadding(context),
        children: [
          HeroHeader(
            eyebrow: 'K3 & aset',
            title: 'Lapor insiden',
            subtitle: 'Foto berwatermark GPS & waktu, tersimpan di HP bila tanpa sinyal.',
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                SurfaceCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      VmsSelectField<String>(
                        label: 'Kategori',
                        icon: Icons.category_rounded,
                        value: _category,
                        options: [
                          for (final e in _categories.entries)
                            VmsOption(e.key, e.value),
                        ],
                        onChanged: (v) => setState(() => _category = v),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        'Tingkat keparahan',
                        style: VmsTextStyles.caption.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          for (final e in _severities.entries)
                            Pressable(
                              onTap: () => setState(() => _severity = e.key),
                              child: AnimatedContainer(
                                duration: const Duration(milliseconds: 200),
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 14,
                                  vertical: 8,
                                ),
                                decoration: BoxDecoration(
                                  color: _severity == e.key
                                      ? _severityAccent(e.key).strong
                                      : _severityAccent(e.key).soft,
                                  borderRadius: BorderRadius.circular(99),
                                ),
                                child: Text(
                                  e.value,
                                  style: VmsTextStyles.bodySm.copyWith(
                                    fontWeight: FontWeight.w700,
                                    color: _severity == e.key
                                        ? Colors.white
                                        : _severityAccent(e.key).strong,
                                  ),
                                ),
                              ),
                            ),
                        ],
                      ),
                      const SizedBox(height: 14),
                      TextField(
                        controller: _description,
                        maxLines: 5,
                        decoration: const InputDecoration(
                          labelText: 'Kronologi',
                          alignLabelWithHint: true,
                        ),
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          const IconTile(
                            icon: Icons.photo_camera_rounded,
                            accent: Accent.rose,
                            size: 40,
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              '${_photos.length} foto bukti',
                              style: VmsTextStyles.bodySm.copyWith(
                                fontWeight: FontWeight.w600,
                              ),
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
                  label: 'Kirim laporan',
                  icon: Icons.send_rounded,
                  accent: Accent.rose,
                  onTap: () {
                    if (_description.text.trim().isEmpty) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Isi kronologi kejadian.'),
                        ),
                      );
                      return;
                    }
                    Navigator.of(context).pop(<String, dynamic>{
                      'category': _category,
                      'severity': _severity,
                      'description': _description.text.trim(),
                      'files': _photos,
                    });
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Accent _severityAccent(String key) => switch (key) {
    'RENDAH' => Accent.emerald,
    'SEDANG' => Accent.amber,
    'TINGGI' => Accent.rose,
    _ => Accent.violet,
  };
}
