import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../shared/ui/vms_ui.dart';
import 'daily_plan_screen.dart' show phaseLabel, qtyText;
import 'photo_slots.dart' show PhotoOrigin, pickReportPhoto;

/// Satu foto realisasi: berkas server (`fileId`) atau berkas lokal yang belum diunggah (`path`).
class _Photo {
  _Photo({this.fileId, this.path, this.requirementId});

  String? fileId;
  final String? path;
  final String? requirementId;
}

/// Progres satu titik (Milestone 6): jumlah realisasi + foto per syarat foto jenis pekerjaan. Server menolak DONE
/// bila foto wajib belum lengkap atau prasyarat belum selesai. Ketua tim bisa meminta item digeser ke hari lain.
class ItemProgressScreen extends ConsumerStatefulWidget {
  const ItemProgressScreen({super.key, required this.itemId, required this.dayStatus, required this.isLeader});

  final String itemId;
  final String dayStatus;
  final bool isLeader;

  @override
  ConsumerState<ItemProgressScreen> createState() => _ItemProgressScreenState();
}

class _ItemProgressScreenState extends ConsumerState<ItemProgressScreen> {
  Map<String, dynamic>? _item;
  List<Map<String, dynamic>> _slots = const [];
  final List<_Photo> _photos = [];
  final _qty = TextEditingController();
  final _notes = TextEditingController();
  String? _error;
  bool _busy = false;

  bool get _editable =>
      widget.dayStatus == 'ONGOING' &&
      const {'TODO', 'IN_PROGRESS', 'DONE'}.contains(_item?['status']);

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _qty.dispose();
    _notes.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final api = ref.read(syncEngineProvider).api;
      final item = await api.planItem(widget.itemId);
      final slots = await api.imageRequirements('${item['work_type_id']}');
      if (!mounted) return;
      setState(() {
        _item = item;
        _slots = slots;
        _qty.text = qtyText(item['completed_qty']);
        _notes.text = '${item['notes'] ?? ''}';
        _photos
          ..clear()
          ..addAll([
            for (final p in (item['realization_photos_json'] as List? ?? const []).cast<Map>())
              _Photo(fileId: '${p['file_id']}', requirementId: p['requirement_id'] as String?),
          ]);
        _error = null;
      });
    } catch (e) {
      if (mounted) setState(() => _error = apiErrorMessage(e));
    }
  }

  void _snack(String text) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));

  Future<void> _add(String? requirementId, String label, PhotoOrigin origin) async {
    final picked = await pickReportPhoto(context: context, slot: label, origin: origin, onError: _snack);
    if (picked == null || !mounted) return;
    setState(() => _photos.add(_Photo(path: picked.path, requirementId: requirementId)));
  }

  Future<void> _save() async {
    final qty = num.tryParse(_qty.text.replaceAll(',', '.'));
    if (qty == null || qty < 0) return _snack('Isi jumlah realisasi dengan angka.');
    setState(() => _busy = true);
    try {
      final api = ref.read(syncEngineProvider).api;
      for (final p in _photos.where((p) => p.fileId == null)) {
        p.fileId = await api.uploadFile(File(p.path!));
      }
      await api.updateProgress(
        widget.itemId,
        completedQty: qty,
        photos: [for (final p in _photos) {'file_id': p.fileId, 'requirement_id': p.requirementId}],
        notes: _notes.text.trim().isEmpty ? null : _notes.text.trim(),
      );
      _snack('Progres tersimpan.');
      await _load();
    } catch (e) {
      _snack(apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _rollover() async {
    final reason = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Minta geser ke hari lain'),
        content: TextField(
          controller: reason,
          maxLines: 3,
          decoration: const InputDecoration(labelText: 'Alasan (hujan, izin kerja, material, ...)'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Batal')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Kirim ke PM')),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      await ref.read(syncEngineProvider).api.requestRollover(
            widget.itemId,
            reason: reason.text.trim(),
            completedQty: num.tryParse(_qty.text.replaceAll(',', '.')) ?? 0,
          );
      _snack('Permintaan geser terkirim; menunggu keputusan PM.');
      await _load();
    } catch (e) {
      _snack(apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final item = _item;
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Progres titik')),
      body: item == null
          ? Center(
              child: _error == null
                  ? const CircularProgressIndicator()
                  : Padding(padding: const EdgeInsets.all(16), child: NoticeBanner(icon: Icons.error_outline, text: _error!)),
            )
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
              children: [
                SurfaceCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(child: Text('${item['title']}', style: theme.textTheme.titleMedium)),
                          StatusPill('${item['status']}'),
                        ],
                      ),
                      const SizedBox(height: 8),
                      InfoRow(
                        icon: Icons.category_outlined,
                        text: '${phaseLabel[item['task_phase']] ?? item['task_phase']} · ${item['work_type_name']}',
                      ),
                      if (item['order_title'] != null) ...[
                        const SizedBox(height: 4),
                        InfoRow(icon: Icons.assignment_outlined, text: 'Order: ${item['order_title']}'),
                      ],
                      if (item['depends_on_title'] != null) ...[
                        const SizedBox(height: 4),
                        InfoRow(icon: Icons.link_rounded, text: 'Prasyarat: ${item['depends_on_title']}'),
                      ],
                      if (item['location_name'] != null) ...[
                        const SizedBox(height: 4),
                        InfoRow(icon: Icons.place_outlined, text: '${item['location_name']}'),
                      ],
                      if (item['delay_reason'] != null) ...[
                        const SizedBox(height: 8),
                        NoticeBanner(icon: Icons.update_rounded, text: 'Alasan geser: ${item['delay_reason']}'),
                      ],
                    ],
                  ),
                ),
                if (!_editable)
                  Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: NoticeBanner(
                      icon: Icons.lock_clock_rounded,
                      text: widget.dayStatus == 'ONGOING'
                          ? 'Titik ini sedang/sudah digeser — tidak bisa diubah.'
                          : 'Progres bisa diisi setelah ketua tim memulai hari kerja.',
                    ),
                  ),
                const SectionTitle('Realisasi'),
                TextField(
                  controller: _qty,
                  enabled: _editable,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: InputDecoration(labelText: 'Jumlah selesai (target ${qtyText(item['target_qty'])})'),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: _notes,
                  enabled: _editable,
                  maxLines: 3,
                  decoration: const InputDecoration(labelText: 'Catatan / remark titik'),
                ),
                const SectionTitle('Foto'),
                for (final slot in [..._slots, {'image_requirement_id': null, 'name': 'Foto lain', 'is_mandatory': false}])
                  _slotCard(slot),
                const SizedBox(height: 16),
                if (_editable)
                  PrimaryAction(label: 'Simpan progres', icon: Icons.save_rounded, busy: _busy, onTap: _save),
                if (_editable && widget.isLeader && item['status'] != 'DONE') ...[
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                    onPressed: _busy ? null : _rollover,
                    icon: const Icon(Icons.update_rounded),
                    label: const Text('Minta geser ke hari lain'),
                  ),
                ],
              ],
            ),
    );
  }

  Widget _slotCard(Map<String, dynamic> slot) {
    final reqId = slot['image_requirement_id'] as String?;
    final mine = _photos.where((p) => p.requirementId == reqId).toList();
    final missing = slot['is_mandatory'] == true && mine.isEmpty;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: SurfaceCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    '${slot['name']}${slot['is_mandatory'] == true ? ' *' : ''}',
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                ),
                if (missing) Text('Wajib', style: TextStyle(color: Accent.rose.strong, fontSize: 12)),
              ],
            ),
            if (slot['description'] != null) Text('${slot['description']}', style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final p in mine)
                  Stack(
                    children: [
                      Container(
                        width: 72,
                        height: 72,
                        decoration: BoxDecoration(borderRadius: BorderRadius.circular(8), color: Colors.black12),
                        clipBehavior: Clip.antiAlias,
                        child: p.path != null
                            ? Image.file(File(p.path!), fit: BoxFit.cover)
                            : const Icon(Icons.cloud_done_rounded),
                      ),
                      if (_editable)
                        Positioned(
                          right: 0,
                          top: 0,
                          child: InkWell(
                            onTap: () => setState(() => _photos.remove(p)),
                            child: const Icon(Icons.cancel_rounded, size: 20),
                          ),
                        ),
                    ],
                  ),
                if (_editable) ...[
                  IconButton.filledTonal(
                    tooltip: 'Kamera',
                    onPressed: () => _add(reqId, '${slot['name']}', PhotoOrigin.camera),
                    icon: const Icon(Icons.photo_camera_rounded),
                  ),
                  IconButton.filledTonal(
                    tooltip: 'Galeri',
                    onPressed: () => _add(reqId, '${slot['name']}', PhotoOrigin.phoneGallery),
                    icon: const Icon(Icons.photo_library_rounded),
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }
}
