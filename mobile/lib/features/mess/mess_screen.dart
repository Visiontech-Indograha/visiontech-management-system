import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../core/theme/theme.dart';
import '../../data/pengajuan_idempotency.dart';
import '../../shared/ui/vms_list_filter.dart';
import '../../shared/ui/vms_ui.dart';
import '../attachments/attachments_sheet.dart';

final _date = DateFormat('d MMM yyyy', 'id_ID');

String _fmt(dynamic iso) => iso == null ? '-' : _date.format(DateTime.parse(iso as String));

String _iso(DateTime d) => DateFormat('yyyy-MM-dd').format(d);

/// Label status hunian/pengajuan mess untuk karyawan.
/// Mess di daftar `/mess/places` untuk `mess_id` hunian (kunci API: `mess_id`); null bila sudah tidak ada.
Map<String, dynamic>? findMessPlace(List<Map<String, dynamic>> places, String? messId) {
  if (messId == null) return null;
  return places.where((p) => p['mess_id'] == messId).firstOrNull;
}

String messStatusLabel(String status) => switch (status) {
  'REQUESTED' => 'Menunggu persetujuan',
  'APPROVED' => 'Disetujui',
  'REJECTED' => 'Ditolak',
  'CANCELLED' => 'Dibatalkan',
  _ => status,
};

/// Aksi yang tersedia bagi penghuni untuk sebuah hunian pada tanggal [today]: 'cancel', 'end', atau null.
String? messStayAction(Map<String, dynamic> stay, DateTime today) {
  final status = stay['status'] as String? ?? 'APPROVED';
  final day = DateTime(today.year, today.month, today.day);
  final start = DateTime.parse(stay['stay_start_date'] as String);
  final end = DateTime.parse(stay['stay_end_date'] as String);
  if (status == 'REQUESTED') return 'cancel';
  if (status != 'APPROVED') return null;
  if (start.isAfter(day)) return 'cancel';
  if (!end.isBefore(day)) return 'end';
  return null;
}

/// Hunian mess saya: riwayat + pengajuan, dengan pilihan mess berupa kartu (bukan ketik manual).
class MessScreen extends ConsumerStatefulWidget {
  const MessScreen({super.key});

  @override
  ConsumerState<MessScreen> createState() => _MessScreenState();
}

class _MessScreenState extends ConsumerState<MessScreen> {
  List<Map<String, dynamic>> _stays = [];
  bool _loading = true;
  String? _error;
  final _query = ListQuery();

  @override
  void dispose() {
    _query.dispose();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final items = await ref.read(syncEngineProvider).api.myMess();
      if (!mounted) return;
      setState(() {
        _stays = items;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = apiErrorMessage(e);
        _loading = false;
      });
    }
  }

  void _snack(String text) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }

  /// "Ajukan lagi": buka dialog tanggal untuk mess yang sama, catatan sebelumnya terisi (bisa diubah).
  Future<void> _repeat(Map<String, dynamic> stay) async {
    try {
      final places = await ref.read(syncEngineProvider).api.messPlaces();
      final place = findMessPlace(places, stay['mess_id'] as String?);
      if (place == null) return _snack('Mess ini sudah tidak tersedia. Pilih mess lain lewat "Ajukan mess".');
      if (!mounted) return;
      final sent = await showDialog<bool>(
        context: context,
        builder: (_) => _RequestDialog(place: place, initialNote: stay['request_note'] as String?),
      );
      if (sent == true) {
        _snack('Pengajuan terkirim. Menunggu persetujuan PM/OM.');
        await _reload();
      }
    } catch (e) {
      _snack(apiErrorMessage(e));
    }
  }

  Future<void> _newRequest() async {
    final sent = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (_) => const _PlacePickerSheet(),
    );
    if (sent == true) {
      _snack('Pengajuan terkirim. Menunggu persetujuan PM/OM.');
      await _reload();
    }
  }

  Future<void> _cancel(Map<String, dynamic> stay) async {
    final approved = stay['status'] == 'APPROVED';
    if (!await confirmAction(
      context,
      title: approved ? 'Batalkan hunian?' : 'Batalkan pengajuan?',
      message: approved
          ? 'Hunian Anda di ${stay['mess_name']} sudah disetujui. Jika dibatalkan, tempat Anda dilepas dan Anda perlu mengajukan lagi bila masih butuh.'
          : 'Pengajuan hunian di ${stay['mess_name']} akan dibatalkan.',
      confirmLabel: approved ? 'Ya, batalkan hunian' : 'Ya, batalkan pengajuan',
      cancelLabel: 'Tidak jadi',
    )) {
      return;
    }
    try {
      await ref.read(syncEngineProvider).api.cancelMess(stay['mess_stay_id'] as String);
      _snack(approved ? 'Hunian dibatalkan.' : 'Pengajuan dibatalkan.');
      await _reload();
    } catch (e) {
      _snack(apiErrorMessage(e));
    }
  }

  Future<void> _end(Map<String, dynamic> stay) async {
    if (!await confirmAction(
      context,
      title: 'Selesaikan inap?',
      message: 'Inap di ${stay['mess_name']} akan ditandai selesai hari ini.',
      confirmLabel: 'Selesai inap',
    )) {
      return;
    }
    try {
      await ref.read(syncEngineProvider).api.endMess(stay['mess_stay_id'] as String);
      _snack('Inap ditandai selesai.');
      await _reload();
    } catch (e) {
      _snack(apiErrorMessage(e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    return Scaffold(
      appBar: VmsTopBar(onBack: () => context.pop()),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: ListView(
          padding: safeListPadding(context).add(const EdgeInsets.symmetric(horizontal: kListGutter)),
          children: [
            const HeroHeader(eyebrow: 'Layanan', title: 'Mess', horizontal: 4),
            FilledButton.icon(
              onPressed: _newRequest,
              icon: const Icon(Icons.add_home_work_rounded),
              label: const Text('Ajukan hunian mess'),
            ),
            const SizedBox(height: 16),
            if (_loading)
              const Padding(
                padding: EdgeInsets.all(32),
                child: Center(child: CircularProgressIndicator()),
              ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.all(16),
                child: Text(_error!, style: const TextStyle(color: Colors.red)),
              ),
            if (!_loading && _error == null && _stays.isEmpty)
              const EmptyState(
                icon: Icons.bed_rounded,
                title: 'Belum ada hunian mess',
                message: 'Ketuk "Ajukan hunian mess" untuk memilih mess dan tanggal inap.',
              ),
            if (_stays.isNotEmpty) ...[
              VmsSearchBar(
                query: _query,
                hint: 'Cari nama mess, kota, atau status...',
                chips: const [
                  VmsFilterOption('', 'Semua'),
                  VmsFilterOption('REQUESTED', 'Diajukan'),
                  VmsFilterOption('APPROVED', 'Disetujui'),
                  VmsFilterOption('REJECTED', 'Ditolak'),
                  VmsFilterOption('CANCELLED', 'Dibatalkan'),
                ],
              ),
              ListenableBuilder(
                listenable: _query,
                builder: (context, _) {
                  final all = _query.filter<Map<String, dynamic>>(
                    _stays,
                    (s) => [s['mess_name'], s['city'], s['address'], s['status'], s['request_note']],
                    chipTest: (s, chip) => '${s['status']}' == chip,
                  );
                  return Column(
                    children: [
                      if (all.isEmpty) VmsNoMatch(query: _query),
                      for (final s in _query.visible(all))
                        Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: _StayCard(
                            stay: s,
                            action: messStayAction(s, now),
                            onCancel: () => _cancel(s),
                            onEnd: () => _end(s),
                            onRepeat: s['mess_id'] == null || s['status'] == 'REQUESTED' ? null : () => _repeat(s),
                          ),
                        ),
                      VmsLoadMore(query: _query, total: all.length, noun: 'hunian'),
                    ],
                  );
                },
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _StayCard extends StatelessWidget {
  const _StayCard({
    required this.stay,
    required this.action,
    required this.onCancel,
    required this.onEnd,
    this.onRepeat,
  });
  final Map<String, dynamic> stay;
  final String? action;
  final VoidCallback onCancel;
  final VoidCallback onEnd;
  final VoidCallback? onRepeat;

  @override
  Widget build(BuildContext context) {
    final status = stay['status'] as String? ?? 'APPROVED';
    final note = stay['decision_note'] as String?;
    final color = switch (status) {
      'APPROVED' => Colors.green.shade700,
      'REQUESTED' => Colors.orange.shade800,
      _ => Colors.red.shade700,
    };
    return SurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  '${stay['mess_name']} · ${stay['city']}',
                  style: VmsTextStyles.bodySm.copyWith(fontWeight: FontWeight.w700),
                ),
              ),
              Chip(
                label: Text(messStatusLabel(status), style: TextStyle(color: color, fontSize: 12)),
                visualDensity: VisualDensity.compact,
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(stay['address'] as String? ?? '', style: VmsTextStyles.bodySm),
          const SizedBox(height: 4),
          Text('${_fmt(stay['stay_start_date'])} - ${_fmt(stay['stay_end_date'])}', style: VmsTextStyles.bodySm),
          if (note != null && note.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text('Catatan: $note', style: VmsTextStyles.bodySm),
          ],
          const SizedBox(height: 8),
          SizedBox(
            height: 48,
            child: TextButton.icon(
              key: Key('lampiran-mess-${stay['mess_stay_id']}'),
              onPressed: () => bukaLampiran(
                context,
                jenis: LampiranJenis.mess,
                id: stay['mess_stay_id'] as String,
                status: status,
              ),
              icon: const Icon(Icons.attach_file_rounded),
              label: const Text('Lampiran'),
            ),
          ),
          if (action != null) ...[
            const SizedBox(height: 8),
            OutlinedButton(
              onPressed: action == 'end' ? onEnd : onCancel,
              child: Text(
                action == 'end'
                    ? 'Selesai inap'
                    : status == 'REQUESTED'
                    ? 'Batalkan pengajuan'
                    : 'Batalkan hunian',
              ),
            ),
          ],
          if (onRepeat != null)
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: onRepeat,
                icon: const Icon(Icons.replay_rounded, size: 18),
                label: const Text('Ajukan lagi'),
              ),
            ),
        ],
      ),
    );
  }
}

/// Pilih mess dari daftar kartu; ketuk kartu membuka dialog tanggal + catatan.
class _PlacePickerSheet extends ConsumerStatefulWidget {
  const _PlacePickerSheet();

  @override
  ConsumerState<_PlacePickerSheet> createState() => _PlacePickerSheetState();
}

class _PlacePickerSheetState extends ConsumerState<_PlacePickerSheet> {
  List<Map<String, dynamic>> _places = [];
  bool _loading = true;
  String? _error;
  final _query = ListQuery();

  List<Map<String, dynamic>> get _filtered =>
      _query.filter<Map<String, dynamic>>(_places, (p) => [p['name'], p['city'], p['address']]);

  @override
  void dispose() {
    _query.dispose();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    _query.addListener(() {
      if (mounted) setState(() {});
    });
    _load();
  }

  Future<void> _load() async {
    try {
      final items = await ref.read(syncEngineProvider).api.messPlaces();
      if (mounted) {
        setState(() {
          _places = items;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = apiErrorMessage(e);
          _loading = false;
        });
      }
    }
  }

  Future<void> _open(Map<String, dynamic> place) async {
    final sent = await showDialog<bool>(
      context: context,
      builder: (_) => _RequestDialog(place: place),
    );
    if (sent == true && mounted) Navigator.of(context).pop(true);
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: MediaQuery.of(context).size.height * 0.88,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Pilih mess', style: VmsTextStyles.heading),
            const SizedBox(height: 4),
            Text('Ketuk mess untuk memilih tanggal inap.', style: VmsTextStyles.bodySm),
            const SizedBox(height: 12),
            VmsSearchBar(query: _query, hint: 'Cari nama mess atau kota...'),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _error != null
                  ? Center(
                      child: Text(_error!, style: const TextStyle(color: Colors.red)),
                    )
                  : _places.isEmpty
                  ? const Center(child: Text('Belum ada mess terdaftar. Hubungi HR/GA.'))
                  : ListView.separated(
                      padding: const EdgeInsets.only(bottom: 16),
                      itemCount: _query.visible(_filtered).length,
                      separatorBuilder: (_, _) => const SizedBox(height: 12),
                      itemBuilder: (_, i) {
                        final p = _query.visible(_filtered)[i];
                        return _PlaceCard(place: p, onTap: () => _open(p));
                      },
                    ),
            ),
            if (!_loading && _places.isNotEmpty)
              _filtered.isEmpty
                  ? VmsNoMatch(query: _query)
                  : VmsLoadMore(query: _query, total: _filtered.length, noun: 'mess'),
          ],
        ),
      ),
    );
  }
}

class _PlaceCard extends StatelessWidget {
  const _PlaceCard({required this.place, required this.onTap});
  final Map<String, dynamic> place;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final capacity = place['capacity'] as int?;
    final occupied = (place['occupied'] as num?)?.toInt() ?? 0;
    final full = capacity != null && occupied >= capacity;
    return Material(
      color: Theme.of(context).colorScheme.surface,
      borderRadius: BorderRadius.circular(16),
      elevation: 1,
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              const CircleAvatar(child: Icon(Icons.bed_rounded)),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('${place['mess_name']}', style: VmsTextStyles.bodySm.copyWith(fontWeight: FontWeight.w700)),
                    Text('${place['city']} · ${place['address']}', style: VmsTextStyles.bodySm),
                    const SizedBox(height: 2),
                    Text(
                      capacity == null
                          ? 'Kapasitas tidak dibatasi'
                          : full
                          ? 'Penuh hari ini ($occupied/$capacity)'
                          : 'Terisi $occupied dari $capacity',
                      style: TextStyle(fontSize: 12, color: full ? Colors.red.shade700 : Colors.black54),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right_rounded),
            ],
          ),
        ),
      ),
    );
  }
}

class _RequestDialog extends ConsumerStatefulWidget {
  const _RequestDialog({required this.place, this.initialNote});
  final Map<String, dynamic> place;
  final String? initialNote;

  @override
  ConsumerState<_RequestDialog> createState() => _RequestDialogState();
}

class _RequestDialogState extends ConsumerState<_RequestDialog> {
  late final _note = TextEditingController(text: widget.initialNote);
  // Satu niat pengajuan: percobaan ulang memakai kunci yang sama (lihat PengajuanIdempotency).
  final _idem = PengajuanIdempotency();
  DateTimeRange? _range;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  Future<void> _pickRange() async {
    final today = DateTime.now();
    final first = DateTime(today.year, today.month, today.day);
    final picked = await showDateRangePicker(
      context: context,
      firstDate: first,
      lastDate: first.add(const Duration(days: 365)),
      initialDateRange: _range,
      helpText: 'Pilih tanggal inap',
      saveText: 'Pilih',
    );
    if (picked != null) {
      setState(() {
        _range = picked;
        _error = null;
      });
    }
  }

  Future<void> _submit() async {
    if (_busy) return;
    if (_range == null) {
      setState(() => _error = 'Pilih tanggal mulai dan selesai inap.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref
          .read(syncEngineProvider)
          .api
          .requestMess(
            messId: widget.place['mess_id'] as String,
            start: _iso(_range!.start),
            end: _iso(_range!.end),
            note: _note.text.trim(),
            idem: _idem,
          );
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted) {
        setState(() {
          _busy = false;
          _error = apiErrorMessage(e);
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final range = _range;
    return AlertDialog(
      title: Text('${widget.place['mess_name']}'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('${widget.place['city']} · ${widget.place['address']}', style: VmsTextStyles.bodySm),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: _busy ? null : _pickRange,
              icon: const Icon(Icons.date_range_rounded),
              label: Text(
                range == null ? 'Pilih tanggal inap' : '${_date.format(range.start)} - ${_date.format(range.end)}',
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _note,
              maxLength: 500,
              maxLines: 2,
              decoration: const InputDecoration(labelText: 'Catatan (opsional)', hintText: 'Mis. penugasan proyek'),
            ),
            if (_error != null) Text(_error!, style: const TextStyle(color: Colors.red)),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: _busy ? null : () => Navigator.of(context).pop(false), child: const Text('Batal')),
        FilledButton(onPressed: _busy ? null : _submit, child: Text(_busy ? 'Mengirim...' : 'Ajukan')),
      ],
    );
  }
}
