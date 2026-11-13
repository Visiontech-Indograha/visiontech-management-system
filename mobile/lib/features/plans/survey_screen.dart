import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../shared/ui/vms_text_field.dart';
import '../../shared/ui/vms_ui.dart';
import 'survey_map_screen.dart';
import 'survey_point_screen.dart' show SurveyPointScreen, pickSurveyMaterial;
import 'survey_widgets.dart';

const surveyStateLabel = {'DRAFT': 'Sedang diisi', 'SUBMITTED': 'Menunggu PM', 'APPROVED': 'Disetujui PM'};

/// Buka berkas laporan (PDF / .docx) dengan aplikasi penampil di HP.
Future<String?> openReportFile(List<int> bytes, String name) async {
  final dir = await getTemporaryDirectory();
  final file = File('${dir.path}/$name');
  await file.writeAsBytes(bytes, flush: true);
  final opened = await OpenFilex.open(file.path);
  if (opened.type == ResultType.done) return null;
  if (name.endsWith('.pdf')) return 'Tidak ada aplikasi PDF untuk membuka laporan.';
  if (name.endsWith('.pptx')) return 'Slide berupa .pptx — pasang PowerPoint/WPS untuk membukanya.';
  return 'Laporan berupa .docx — pasang Word/WPS untuk membukanya.';
}

/// Survei berformat baku (docs/37). Urutan kerja ketua tim jelas di layar: (1) tambah titik sebanyak yang ditemui
/// di lapangan, (2) isi informasi laporan, (3) pratinjau, (4) kirim ke PM. Setelah dikirim/disetujui survei tetap
/// bisa dibuka di sini (atau lewat "Survei saya") untuk melihat laporan dan mengunduh dokumen resminya.
class SurveyScreen extends ConsumerStatefulWidget {
  const SurveyScreen({super.key, required this.taskId});

  final String taskId;

  @override
  ConsumerState<SurveyScreen> createState() => _SurveyScreenState();
}

class _SurveyScreenState extends ConsumerState<SurveyScreen> {
  Map<String, dynamic>? _s;
  String? _error;
  bool _busy = false;
  final _narrative = TextEditingController();
  final _location = TextEditingController();
  final _purpose = TextEditingController();
  bool _infoDirty = false;

  bool get _editable => _s?['can_edit'] == true;
  List<Map<String, dynamic>> get _points =>
      (_s?['points'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();

  @override
  void initState() {
    super.initState();
    _load();
    for (final c in [_narrative, _location, _purpose]) {
      c.addListener(() => _infoDirty = true);
    }
  }

  @override
  void dispose() {
    _narrative.dispose();
    _location.dispose();
    _purpose.dispose();
    super.dispose();
  }

  void _apply(Map<String, dynamic> s) {
    _s = s;
    _narrative.text = '${s['narrative'] ?? ''}';
    _location.text = '${s['location'] ?? ''}';
    _purpose.text = '${s['purpose'] ?? ''}';
    _infoDirty = false;
  }

  Future<void> _load() async {
    try {
      final engine = ref.read(syncEngineProvider);
      final s = await engine.fetchMap('survey_${widget.taskId}', () => engine.api.survey(widget.taskId));
      if (!mounted) return;
      setState(() {
        _apply(s);
        _error = null;
      });
    } catch (e) {
      if (mounted) setState(() => _error = apiErrorMessage(e));
    }
  }

  void _snack(String text) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));

  Future<bool> _run(Future<Map<String, dynamic>> Function() action, String done) async {
    setState(() => _busy = true);
    try {
      final s = await action();
      if (!mounted) return false;
      setState(() => _apply(s));
      _snack(done);
      return true;
    } catch (e) {
      _snack(apiErrorMessage(e));
      return false;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _openPoint([Map<String, dynamic>? point]) async {
    if (_infoDirty) await _saveInfo(quiet: true);
    if (!mounted) return;
    final result = await Navigator.of(context).push<Map<String, dynamic>>(
      MaterialPageRoute(
        builder: (_) => SurveyPointScreen(survey: _s!, point: point, readOnly: !_editable),
      ),
    );
    if (result != null && mounted) setState(() => _apply(result));
  }

  Future<void> _deletePoint(Map<String, dynamic> point) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Hapus titik "${point['name']}"?'),
        content: const Text('Foto, remark, dan material titik ini ikut terhapus.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Batal')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Hapus')),
        ],
      ),
    );
    if (ok != true) return;
    await _run(() => ref.read(syncEngineProvider).api.deleteSurveyPoint('${point['point_id']}'), 'Titik dihapus.');
  }

  Future<bool> _saveInfo({bool quiet = false}) async {
    if (!_editable) return true;
    return _run(() async {
      return ref.read(syncEngineProvider).api.saveSurveyReport(widget.taskId, {
        'narrative': _narrative.text.trim(),
        'location': _location.text.trim(),
        'purpose': _purpose.text.trim(),
      });
    }, quiet ? 'Informasi laporan tersimpan otomatis.' : 'Informasi laporan tersimpan.');
  }

  Future<void> _preview() async {
    if (_infoDirty) {
      if (!await _saveInfo(quiet: true)) return;
    }
    setState(() => _busy = true);
    try {
      _snack('Menyiapkan pratinjau laporan…');
      final res = await ref.read(syncEngineProvider).api.surveyPreview(widget.taskId);
      final err = await openReportFile(res.bytes, 'pratinjau-survei.${res.isPdf ? 'pdf' : 'docx'}');
      if (err != null) _snack(err);
    } catch (e) {
      _snack(apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _official() async {
    setState(() => _busy = true);
    try {
      _snack('Mengunduh laporan resmi…');
      final bytes = await ref.read(syncEngineProvider).api.surveyOfficialReport(widget.taskId);
      final err = await openReportFile(bytes, 'laporan-survei-${_s!['format']}.docx');
      if (err != null) _snack(err);
    } catch (e) {
      _snack(apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _submit() async {
    if (_busy) return;
    if (_infoDirty) {
      if (!await _saveInfo(quiet: true)) return;
    }
    if (!mounted) return;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Kirim survei ke PM?'),
        content: Text(
          '${_points.length} titik akan dikirim. Sesudah dikirim survei terkunci, kecuali PM '
          'mengembalikannya untuk diperbaiki. Laporan tetap bisa dilihat di sini.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Periksa lagi')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Kirim')),
        ],
      ),
    );
    if (ok != true) return;
    await _run(() => ref.read(syncEngineProvider).api.submitSurvey(widget.taskId), 'Survei terkirim ke PM.');
  }

  @override
  Widget build(BuildContext context) {
    final s = _s;
    return Scaffold(
      appBar: AppBar(title: Text(s == null ? 'Survei' : 'Survei ${s['format']}')),
      bottomNavigationBar: s == null ? null : _actionBar(s),
      body: s == null
          ? Center(
              child: _error == null
                  ? const CircularProgressIndicator()
                  : Padding(
                      padding: const EdgeInsets.all(16),
                      child: NoticeBanner(icon: Icons.error_outline, text: _error!),
                    ),
            )
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                children: [
                  _header(s),
                  const SizedBox(height: 12),
                  _statusCard(s),
                  SectionTitle(
                    '1. Titik survei (${_points.length})',
                    trailing: _editable
                        ? TextButton.icon(
                            key: const Key('survey-add-point'),
                            onPressed: _busy ? null : _openPoint,
                            icon: const Icon(Icons.add_location_alt_rounded),
                            label: const Text('Tambah titik'),
                          )
                        : null,
                  ),
                  if (_points.isEmpty)
                    EmptyState(
                      icon: Icons.add_location_alt_outlined,
                      title: 'Belum ada titik',
                      message: _editable
                          ? 'Tambahkan setiap ${s['format'] == 'ACS' ? 'pintu' : 'posisi kamera'} yang disurvei — '
                                'jumlahnya bebas sesuai kondisi lapangan.'
                          : null,
                    ),
                  if (_points.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: OutlinedButton.icon(
                        onPressed: () async {
                          await Navigator.of(context)
                              .push(MaterialPageRoute<void>(builder: (_) => SurveyMapScreen(survey: s)));
                          if (mounted) await _load();
                        },
                        icon: const Icon(Icons.map_rounded),
                        label: Text(s['can_move'] == true ? 'Peta layout · atur posisi titik' : 'Lihat peta titik'),
                      ),
                    ),
                  for (final p in _points)
                    SurveyPointCard(
                      point: p,
                      editable: _editable,
                      busy: _busy,
                      onOpen: () => _openPoint(p),
                      onDelete: () => _deletePoint(p),
                    ),
                  _generalLines(s),
                  const SectionTitle('3. Informasi laporan'),
                  _infoCard(s),
                  if ((s['bom'] as List).isNotEmpty) ...[
                    const SectionTitle('Daftar material (otomatis dari semua titik)'),
                    SurfaceCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          for (final (i, b) in (s['bom'] as List).cast<Map>().indexed) ...[
                            if (i == 0 || (s['bom'] as List).cast<Map>()[i - 1]['group'] != b['group'])
                              Padding(
                                padding: EdgeInsets.only(top: i == 0 ? 0 : 10, bottom: 2),
                                child: Text('${b['group']}', style: Theme.of(context).textTheme.labelLarge),
                              ),
                            Padding(
                              padding: const EdgeInsets.symmetric(vertical: 3),
                              child: Row(
                                children: [
                                  Expanded(
                                    child: Text('${b['name']}${b['custom'] == true ? ' · di luar katalog' : ''}'),
                                  ),
                                  Text(
                                    '${_num(b['qty'])} ${b['unit']}',
                                    style: const TextStyle(fontWeight: FontWeight.w600),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
    );
  }

  /// Material umum lokasi: tidak menempel ke satu titik (rack, panel ACS, switch, kabel tray utama).
  Widget _generalLines(Map<String, dynamic> s) {
    final lines = (s['general_lines'] as List? ?? const []).cast<Map>();
    final canEdit = s['can_edit_bom'] == true;
    if (lines.isEmpty && !canEdit) return const SizedBox.shrink();
    final catalog = [
      for (final t in (s['point_types'] as List? ?? const []).cast<Map>())
        ...(t['catalog'] as List? ?? const []).cast<Map>(),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SectionTitle('2. Material umum lokasi'),
        SurfaceCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Material yang dipakai bersama, bukan milik satu titik.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              for (final l in lines)
                ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.inventory_2_outlined),
                  title: Text('${l['name']}'),
                  subtitle: Text('${_num(l['qty'])} ${l['unit']}${l['custom'] == true ? ' · di luar katalog' : ''}'),
                  trailing: canEdit
                      ? IconButton(
                          icon: const Icon(Icons.delete_outline),
                          onPressed: _busy
                              ? null
                              : () => _run(
                                  () => ref.read(syncEngineProvider).api.deleteSurveyLine('${l['bom_id']}'),
                                  'Material dihapus.',
                                ),
                        )
                      : null,
                ),
              if (canEdit)
                OutlinedButton.icon(
                  onPressed: _busy
                      ? null
                      : () async {
                          final m = await pickSurveyMaterial(context, catalog);
                          if (m == null) return;
                          await _run(
                            () => ref.read(syncEngineProvider).api.addSurveyLine(widget.taskId, {
                              'name': m.name,
                              'qty': m.qty,
                              'unit': m.unit,
                            }),
                            'Material umum ditambahkan.',
                          );
                        },
                  icon: const Icon(Icons.add),
                  label: const Text('Tambah material umum'),
                ),
            ],
          ),
        ),
      ],
    );
  }

  static String _num(dynamic v) {
    final n = num.tryParse('$v') ?? 0;
    return n == n.roundToDouble() ? n.toInt().toString() : n.toString();
  }

  Widget _header(Map<String, dynamic> s) => SurfaceCard(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(child: Text('${s['client_name']}', style: Theme.of(context).textTheme.titleMedium)),
            StatusPill('${s['state']}', label: surveyStateLabel[s['state']]),
          ],
        ),
        const SizedBox(height: 6),
        InfoRow(icon: Icons.assignment_outlined, text: '${s['project_title']}'),
        const SizedBox(height: 4),
        InfoRow(icon: Icons.category_outlined, text: '${s['work_type_name']} · ${s['division_name']}'),
        const SizedBox(height: 4),
        InfoRow(icon: Icons.groups_2_outlined, text: '${s['team_name'] ?? '-'} · ${surveyTgl(s['work_date'])}'),
      ],
    ),
  );

  Widget _statusCard(Map<String, dynamic> s) {
    final state = s['state'];
    final note = '${s['review_note'] ?? ''}'.trim();
    if (state == 'APPROVED') {
      return const NoticeBanner(
        icon: Icons.verified_rounded,
        accent: Accent.emerald,
        text: 'Survei disetujui PM. Laporan resmi bisa diunduh lewat tombol di bawah.',
      );
    }
    if (state == 'SUBMITTED') {
      return const NoticeBanner(
        icon: Icons.hourglass_top_rounded,
        text: 'Survei sudah dikirim dan menunggu tinjauan PM. Anda tetap bisa melihat pratinjau laporannya.',
      );
    }
    if (!_editable) {
      return const NoticeBanner(
        icon: Icons.lock_clock_rounded,
        text: 'Survei diisi oleh ketua tim setelah jadwal terbit.',
      );
    }
    final points = _points;
    final slots = (s['slots'] as List? ?? const []).cast<Map>();
    final mandatory = slots.where((x) => x['mandatory'] == true).map((x) => '${x['requirement_id']}').toSet();
    final photosOk =
        points.isNotEmpty &&
        points.every((p) {
          final given = (p['photos'] as List? ?? const []).cast<Map>().map((x) => '${x['requirement_id']}').toSet();
          return given.isNotEmpty && mandatory.every(given.contains);
        });
    final infoOk = _location.text.trim().isNotEmpty;
    return SurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (note.isNotEmpty) ...[
            NoticeBanner(icon: Icons.feedback_outlined, text: 'Dikembalikan PM: $note'),
            const SizedBox(height: 8),
          ],
          Text('Langkah mengisi survei', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 6),
          SurveyStep(done: points.isNotEmpty, text: 'Tambah titik (${points.length} titik)'),
          SurveyStep(done: photosOk, text: 'Setiap titik berfoto sesuai format'),
          SurveyStep(done: infoOk, text: 'Isi lokasi dan uraian (layout dibuat otomatis)'),
          const SurveyStep(done: false, text: 'Pratinjau laporan, lalu kirim ke PM'),
        ],
      ),
    );
  }

  Widget _infoCard(Map<String, dynamic> s) {
    return SurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          VmsTextField(
            controller: _location,
            maxLength: 500,
            enabled: _editable,
            decoration: const InputDecoration(labelText: 'Lokasi', hintText: 'mis. Lab Office Duri'),
          ),
          const SizedBox(height: 8),
          VmsTextField(
            controller: _purpose,
            maxLength: 255,
            enabled: _editable,
            decoration: const InputDecoration(labelText: 'Tujuan', hintText: 'mis. Assesment pemasangan ACS'),
          ),
          const SizedBox(height: 8),
          VmsTextField(
            controller: _narrative,
            maxLength: 4000,
            enabled: _editable,
            maxLines: 4,
            decoration: const InputDecoration(
              labelText: 'Uraian survei (opsional)',
              hintText: 'Kosongkan bila ingin dibuat otomatis dari tanggal dan nama tim.',
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              const Icon(Icons.map_outlined, size: 18),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  'Layout dibuat otomatis dari koordinat titik (peta satelit + penanda). '
                  'PM bisa menggeser posisi titik di web.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (_editable) ...[
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerRight,
              child: FilledButton.tonalIcon(
                onPressed: _busy ? null : _saveInfo,
                icon: const Icon(Icons.save_outlined),
                label: const Text('Simpan informasi'),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _actionBar(Map<String, dynamic> s) {
    final hasPoints = _points.isNotEmpty;
    final secondary = OutlinedButton.icon(
      key: const Key('survey-preview'),
      onPressed: _busy || !hasPoints ? null : _preview,
      icon: const Icon(Icons.visibility_outlined),
      label: const Text('Pratinjau'),
    );
    Widget primary;
    if (_editable) {
      primary = FilledButton.icon(
        key: const Key('survey-submit'),
        onPressed: _busy || !hasPoints ? null : _submit,
        icon: const Icon(Icons.send_rounded),
        label: const Text('Kirim ke PM'),
      );
    } else if (s['state'] != 'DRAFT') {
      primary = FilledButton.icon(
        key: const Key('survey-official'),
        onPressed: _busy ? null : _official,
        icon: const Icon(Icons.download_rounded),
        label: const Text('Laporan resmi'),
      );
    } else {
      primary = const SizedBox.shrink();
    }
    return SafeArea(
      child: Container(
        padding: const EdgeInsets.fromLTRB(16, 10, 16, 10),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          boxShadow: const [BoxShadow(color: Color(0x14000000), blurRadius: 8, offset: Offset(0, -2))],
        ),
        child: Row(
          children: [
            Expanded(child: secondary),
            const SizedBox(width: 10),
            Expanded(child: _busy ? const Center(child: CircularProgressIndicator()) : primary),
          ],
        ),
      ),
    );
  }
}

