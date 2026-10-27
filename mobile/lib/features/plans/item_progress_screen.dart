import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart' show isNetworkFailure;
import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../data/sync_engine.dart' show OfflineOp;
import '../../shared/ui/vms_ui.dart';
import 'daily_plan_screen.dart' show phaseLabel, qtyText;
import 'photo_slots.dart' show PhotoOrigin, pickReportPhoto;

/// Alasan hasil kerja belum boleh disimpan, atau null bila valid. Jumlah tidak boleh melebihi target; menandai
/// selesai (jumlah = target) mewajibkan semua foto wajib terisi.
String? progressProblem({
  required num qty,
  required num target,
  required int mandatorySlots,
  required int filledMandatory,
}) {
  if (target > 0 && qty > target) {
    return 'Jumlah melebihi target (${qtyText(target)}). Periksa kembali.';
  }
  if (target > 0 && qty >= target && filledMandatory < mandatorySlots) {
    return 'Foto wajib belum lengkap ($filledMandatory/$mandatorySlots). Lengkapi sebelum menandai selesai.';
  }
  return null;
}

/// Unggah dengan percobaan ulang untuk gangguan jaringan (maks. 3 kali, jeda 2 dan 4 detik). Galat dari server
/// (4xx/5xx) tidak diulang karena hasilnya akan sama.
Future<T> retryUpload<T>(Future<T> Function() action, {Duration step = const Duration(seconds: 2)}) async {
  for (var attempt = 1; ; attempt++) {
    try {
      return await action();
    } on DioException catch (e) {
      if (!isNetworkFailure(e) || attempt >= 3) rethrow;
      await Future<void>.delayed(step * attempt);
    }
  }
}

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
      widget.dayStatus == 'ONGOING' && const {'TODO', 'IN_PROGRESS', 'DONE'}.contains(_item?['status']);

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
            for (final p in photoRefsOf(item['realization_photos_json']))
              _Photo(fileId: p.fileId, requirementId: p.requirementId),
          ]);
        _error = null;
      });
    } catch (e) {
      if (mounted) setState(() => _error = apiErrorMessage(e));
    }
  }

  void _snack(String text, {bool error = false}) => showVmsToast(context, text, error: error);

  Future<void> _add(String? requirementId, String label, PhotoOrigin origin) async {
    final picked = await pickReportPhoto(context: context, slot: label, origin: origin, onError: _snack);
    if (picked == null || !mounted) return;
    setState(() => _photos.add(_Photo(path: picked.path, requirementId: requirementId)));
  }

  Future<void> _save() async {
    final qty = num.tryParse(_qty.text.replaceAll(',', '.'));
    if (qty == null || qty < 0) return _snack('Isi jumlah yang sudah selesai dengan angka.');
    final problem = progressProblem(
      qty: qty,
      target: num.tryParse('${_item?['target_qty'] ?? 0}') ?? 0,
      mandatorySlots: _slots.where((s) => s['is_mandatory'] == true).length,
      filledMandatory: _slots
          .where((s) => s['is_mandatory'] == true)
          .where((s) => _photos.any((p) => p.requirementId == s['image_requirement_id']))
          .length,
    );
    if (problem != null) return _snack(problem, error: true);
    setState(() => _busy = true);
    try {
      final engine = ref.read(syncEngineProvider);
      final api = engine.api;
      final notes = _notes.text.trim().isEmpty ? null : _notes.text.trim();
      try {
        // Foto yang sudah terunggah tidak diunggah ulang bila simpan diulang setelah gagal di tengah jalan.
        for (final p in _photos.where((p) => p.fileId == null)) {
          p.fileId = await retryUpload(() => api.uploadFile(File(p.path!)));
        }
        await api.updateProgress(
          widget.itemId,
          completedQty: qty,
          photos: [
            for (final p in _photos) {'file_id': p.fileId, 'requirement_id': p.requirementId},
          ],
          notes: notes,
        );
        _snack('Hasil kerja tersimpan.');
        await _load();
      } on DioException catch (e) {
        if (!isNetworkFailure(e)) rethrow;
        // Tidak ada koneksi: simpan di antrean HP (foto ikut), dikirim otomatis saat online.
        final local = _photos.where((p) => p.fileId == null).toList();
        await engine.submit(
          OfflineOp.planItemProgress,
          {
            'item_id': widget.itemId,
            'completed_qty': qty,
            'notes': notes,
            'photos': [
              for (final p in _photos.where((p) => p.fileId != null))
                {'file_id': p.fileId, 'requirement_id': p.requirementId},
            ],
            'new_photo_requirements': [for (final p in local) p.requirementId],
          },
          localFiles: [for (final p in local) p.path!],
        );
        _snack('Tidak ada koneksi. Hasil kerja disimpan di HP dan dikirim otomatis saat online.');
      }
    } catch (e) {
      _snack(apiErrorMessage(e), error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _rollover() async {
    final reason = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Minta pindah ke hari lain'),
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
      await ref
          .read(syncEngineProvider)
          .api
          .requestRollover(
            widget.itemId,
            reason: reason.text.trim(),
            completedQty: num.tryParse(_qty.text.replaceAll(',', '.')) ?? 0,
          );
      _snack('Permintaan pindah hari terkirim; menunggu keputusan PM.');
      await _load();
    } catch (e) {
      _snack(apiErrorMessage(e), error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _bump(num delta) {
    final now = num.tryParse(_qty.text.replaceAll(',', '.')) ?? 0;
    final next = (now + delta) < 0 ? 0 : now + delta;
    setState(() => _qty.text = qtyText(next));
  }

  @override
  Widget build(BuildContext context) {
    final item = _item;
    final theme = Theme.of(context);
    if (item == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Kerjakan pekerjaan')),
        body: Center(
          child: _error == null
              ? const CircularProgressIndicator()
              : Padding(
                  padding: const EdgeInsets.all(16),
                  child: NoticeBanner(icon: Icons.error_outline, text: _error!),
                ),
        ),
      );
    }
    final phase = phaseAccent['${item['task_phase']}'] ?? Accent.slate;
    final target = num.tryParse('${item['target_qty'] ?? 0}') ?? 0;
    final qty = num.tryParse(_qty.text.replaceAll(',', '.')) ?? 0;
    final pct = target <= 0 ? 0.0 : (qty / target).clamp(0, 1).toDouble();
    final state = item['status'] == 'DONE' || (target > 0 && qty >= target)
        ? 'DONE'
        : qty > 0
        ? 'PARTIAL'
        : 'TODO';
    final stateAccent = statusStyle(state).accent;
    final overTarget = target > 0 && qty > target;
    final barColor = overTarget ? theme.colorScheme.error : stateAccent.strong;
    final mandatory = _slots.where((s) => s['is_mandatory'] == true).toList();
    final filled = mandatory.where((s) => _photos.any((p) => p.requirementId == s['image_requirement_id'])).length;
    final waiting = item['depends_on_title'] != null && item['depends_on_done'] != true;

    return Scaffold(
      appBar: AppBar(title: const Text('Kerjakan pekerjaan')),
      bottomNavigationBar: _editable
          ? SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
                child: PrimaryAction(
                  label: 'Simpan hasil kerja',
                  icon: Icons.check_circle_rounded,
                  busy: _busy,
                  onTap: _save,
                ),
              ),
            )
          : null,
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
        children: [
          // Kepala: jenis pekerjaan berwarna + judul + status
          Container(
            decoration: BoxDecoration(
              color: phase.soft,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: phase.strong.withValues(alpha: 0.25)),
            ),
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(color: phase.strong, borderRadius: BorderRadius.circular(99)),
                      child: Text(
                        phaseLabel['${item['task_phase']}'] ?? '${item['task_phase']}',
                        style: theme.textTheme.labelSmall?.copyWith(color: Colors.white, fontWeight: FontWeight.w700),
                      ),
                    ),
                    const Spacer(),
                    StatusPill(state),
                  ],
                ),
                const SizedBox(height: 10),
                Text('${item['title']}', style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)),
                const SizedBox(height: 4),
                Text('${item['work_type_name']}', style: theme.textTheme.bodyMedium?.copyWith(color: phase.strong)),
                if (item['location_name'] != null) ...[
                  const SizedBox(height: 8),
                  InfoRow(icon: Icons.place_outlined, text: '${item['location_name']}'),
                ],
                if (item['order_title'] != null) ...[
                  const SizedBox(height: 4),
                  InfoRow(icon: Icons.assignment_outlined, text: '${item['order_title']}'),
                ],
              ],
            ),
          ),
          if (item['depends_on_title'] != null) ...[
            const SizedBox(height: 10),
            _Banner(
              accent: waiting ? Accent.rose : Accent.emerald,
              icon: waiting ? Icons.hourglass_top_rounded : Icons.check_circle_rounded,
              text:
                  '${waiting ? 'Tunggu dulu sampai selesai' : 'Sudah selesai'}: ${item['depends_on_title']}'
                  '${item['depends_on_team_name'] != null ? ' · ${item['depends_on_team_name']}' : ''}',
            ),
          ],
          if (item['delay_reason'] != null) ...[
            const SizedBox(height: 10),
            _Banner(
              accent: Accent.amber,
              icon: Icons.update_rounded,
              text: 'Alasan pindah hari: ${item['delay_reason']}',
            ),
          ],
          if (!_editable) ...[
            const SizedBox(height: 10),
            _Banner(
              accent: Accent.slate,
              icon: Icons.lock_clock_rounded,
              text: switch (widget.dayStatus) {
                'ONGOING' => 'Pekerjaan ini sudah dipindah ke hari lain — tidak bisa diubah.',
                'COMPLETED' => 'Hari kerja ini sudah ditutup — hasil kerja tersimpan dan tidak bisa diubah.',
                _ => 'Hasil kerja bisa diisi setelah ketua tim menekan "Mulai hari kerja".',
              },
            ),
          ],

          // Langkah 1 — foto
          _Step(
            number: 1,
            title: 'Ambil foto',
            done: mandatory.isEmpty || filled == mandatory.length,
            trailing: mandatory.isEmpty ? null : '$filled dari ${mandatory.length} foto wajib',
          ),
          for (final slot in [
            ..._slots,
            if (_editable || _photos.any((p) => p.requirementId == null))
              {'image_requirement_id': null, 'name': 'Foto lain (boleh kosong)', 'is_mandatory': false},
          ])
            _slotCard(slot),

          // Langkah 2 — jumlah
          _Step(number: 2, title: 'Berapa yang sudah selesai?', done: qty > 0),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: theme.colorScheme.surface,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: stateAccent.strong.withValues(alpha: 0.25)),
            ),
            child: Column(
              children: [
                Row(
                  children: [
                    IconButton.filledTonal(
                      onPressed: _editable ? () => _bump(-1) : null,
                      icon: const Icon(Icons.remove_rounded),
                    ),
                    Expanded(
                      child: TextField(
                        controller: _qty,
                        enabled: _editable,
                        textAlign: TextAlign.center,
                        onChanged: (_) => setState(() {}),
                        style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800),
                        keyboardType: const TextInputType.numberWithOptions(decimal: true),
                        decoration: InputDecoration(border: InputBorder.none, suffixText: 'dari ${qtyText(target)}'),
                      ),
                    ),
                    IconButton.filledTonal(
                      onPressed: _editable ? () => _bump(1) : null,
                      icon: const Icon(Icons.add_rounded),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                TweenAnimationBuilder<double>(
                  tween: Tween(begin: 0, end: pct),
                  duration: const Duration(milliseconds: 500),
                  curve: Curves.easeOutCubic,
                  builder: (_, v, _) => ClipRRect(
                    borderRadius: BorderRadius.circular(99),
                    child: LinearProgressIndicator(
                      value: v,
                      minHeight: 8,
                      color: barColor,
                      backgroundColor: overTarget ? theme.colorScheme.errorContainer : stateAccent.soft,
                    ),
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  overTarget
                      ? 'Melebihi target (${qtyText(target)})'
                      : '${statusStyle(state).label} · ${(pct * 100).round()}%',
                  style: theme.textTheme.bodySmall?.copyWith(color: barColor, fontWeight: FontWeight.w700),
                ),
              ],
            ),
          ),

          // Langkah 3 — catatan
          const _Step(number: 3, title: 'Catatan (boleh kosong)', done: false, optional: true),
          TextField(
            controller: _notes,
            enabled: _editable,
            maxLines: 3,
            decoration: const InputDecoration(hintText: 'Contoh: kabel kurang 5 m, lanjut besok'),
          ),
          if (_editable && widget.isLeader && item['status'] != 'DONE') ...[
            const SizedBox(height: 16),
            TextButton.icon(
              onPressed: _busy ? null : _rollover,
              icon: const Icon(Icons.update_rounded),
              label: const Text('Tidak selesai hari ini? Minta pindah hari'),
            ),
          ],
        ],
      ),
    );
  }

  Widget _slotCard(Map<String, dynamic> slot) {
    final reqId = slot['image_requirement_id'] as String?;
    final mine = _photos.where((p) => p.requirementId == reqId).toList();
    final mandatory = slot['is_mandatory'] == true;
    final ok = mine.isNotEmpty;
    final accent = ok ? Accent.emerald : (mandatory ? Accent.rose : Accent.slate);
    final theme = Theme.of(context);
    return AnimatedContainer(
      duration: const Duration(milliseconds: 250),
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border(left: BorderSide(color: accent.strong, width: 4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(ok ? Icons.check_circle_rounded : Icons.photo_camera_outlined, size: 20, color: accent.strong),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  '${slot['name']}',
                  style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
                ),
              ),
              if (mandatory && !ok)
                Text(
                  'Wajib',
                  style: theme.textTheme.labelSmall?.copyWith(color: accent.strong, fontWeight: FontWeight.w700),
                ),
            ],
          ),
          if (slot['description'] != null)
            Padding(
              padding: const EdgeInsets.only(top: 4, left: 28),
              child: Text('${slot['description']}', style: theme.textTheme.bodySmall),
            ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final p in mine) _thumb(p),
              if (_editable) ...[
                _AddTile(
                  icon: Icons.photo_camera_rounded,
                  label: 'Kamera',
                  onTap: () => _add(reqId, '${slot['name']}', PhotoOrigin.camera),
                ),
                _AddTile(
                  icon: Icons.photo_library_rounded,
                  label: 'Galeri',
                  onTap: () => _add(reqId, '${slot['name']}', PhotoOrigin.phoneGallery),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }

  Widget _thumb(_Photo p) => Stack(
    children: [
      Container(
        width: 76,
        height: 76,
        decoration: BoxDecoration(borderRadius: BorderRadius.circular(12), color: Colors.black12),
        clipBehavior: Clip.antiAlias,
        child: p.path != null
            ? Image.file(File(p.path!), fit: BoxFit.cover)
            : FutureBuilder<String>(
                future: ref.read(syncEngineProvider).api.fileUrl(p.fileId!, variant: 'thumb'),
                builder: (_, s) => s.hasData
                    ? Image.network(
                        s.data!,
                        fit: BoxFit.cover,
                        errorBuilder: (_, _, _) => const Icon(Icons.cloud_done_rounded),
                      )
                    : const Center(
                        child: SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
                      ),
              ),
      ),
      if (_editable)
        Positioned(
          right: 2,
          top: 2,
          child: InkWell(
            onTap: () => setState(() => _photos.remove(p)),
            child: const CircleAvatar(
              radius: 11,
              backgroundColor: Colors.black54,
              child: Icon(Icons.close_rounded, size: 14, color: Colors.white),
            ),
          ),
        ),
    ],
  );
}

/// Judul langkah bernomor: lingkaran hijau ✓ bila selesai.
class _Step extends StatelessWidget {
  const _Step({required this.number, required this.title, required this.done, this.trailing, this.optional = false});
  final int number;
  final String title;
  final bool done;
  final String? trailing;
  final bool optional;

  @override
  Widget build(BuildContext context) {
    final a = done ? Accent.emerald : (optional ? Accent.slate : Accent.blue);
    final text = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.fromLTRB(0, 22, 0, 10),
      child: Row(
        children: [
          AnimatedContainer(
            duration: const Duration(milliseconds: 250),
            width: 28,
            height: 28,
            alignment: Alignment.center,
            decoration: BoxDecoration(color: a.strong, shape: BoxShape.circle),
            child: done
                ? const Icon(Icons.check_rounded, size: 18, color: Colors.white)
                : Text(
                    '$number',
                    style: text.labelLarge?.copyWith(color: Colors.white, fontWeight: FontWeight.w800),
                  ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(title, style: text.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
          ),
          if (trailing != null)
            Text(
              trailing!,
              style: text.bodySmall?.copyWith(color: a.strong, fontWeight: FontWeight.w600),
            ),
        ],
      ),
    );
  }
}

class _Banner extends StatelessWidget {
  const _Banner({required this.accent, required this.icon, required this.text});
  final Accent accent;
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(color: accent.soft, borderRadius: BorderRadius.circular(14)),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: accent.strong, size: 20),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            text,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: accent.strong, fontWeight: FontWeight.w600),
          ),
        ),
      ],
    ),
  );
}

class _AddTile extends StatelessWidget {
  const _AddTile({required this.icon, required this.label, required this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
    color: Accent.blue.soft,
    borderRadius: BorderRadius.circular(12),
    child: InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: onTap,
      child: SizedBox(
        width: 76,
        height: 76,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: Accent.blue.strong),
            const SizedBox(height: 4),
            Text(label, style: Theme.of(context).textTheme.labelSmall?.copyWith(color: Accent.blue.strong)),
          ],
        ),
      ),
    ),
  );
}

/// Foto bukti tersimpan sebagai objek `{file_id, requirement_id}` (baru) atau string id berkas (lama);
/// keduanya dibaca agar semua foto di server tampil dan data rusak tidak membuat layar error.
List<({String fileId, String? requirementId})> photoRefsOf(Object? raw) {
  if (raw is! List) return const [];
  final refs = <({String fileId, String? requirementId})>[];
  for (final e in raw) {
    if (e is String && e.isNotEmpty) {
      refs.add((fileId: e, requirementId: null));
    } else if (e is Map && e['file_id'] is String && (e['file_id'] as String).isNotEmpty) {
      refs.add((fileId: e['file_id'] as String, requirementId: e['requirement_id'] as String?));
    }
  }
  return refs;
}
