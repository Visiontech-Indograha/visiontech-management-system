import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/error_message.dart';
import '../../core/location_helper.dart';
import '../../core/providers.dart';
import '../../shared/ui/vms_network_image.dart';
import '../../shared/ui/vms_select_field.dart';
import '../../shared/ui/vms_text_field.dart';
import '../../shared/ui/vms_ui.dart';
import 'photo_slots.dart' show ExampleThumb, PhotoOrigin, pickReportPhoto;

part 'survey_point_data.dart';
part 'survey_point_widgets.dart';
part 'survey_point_material.dart';


/// Isi satu titik survei, dalam urutan yang sama dengan laporan:
/// 1 Nama titik · 2 Foto sesuai format · 3 Remark · 4 Kebutuhan pemasangan · 5 Material · 6 (CCTV) Kabel FO.
/// Jumlah titik bebas — ketua tim menambah sesuai kondisi lapangan.
class SurveyPointScreen extends ConsumerStatefulWidget {
  const SurveyPointScreen({super.key, required this.survey, this.point, this.readOnly = false});

  final Map<String, dynamic> survey;
  final Map<String, dynamic>? point; // null = titik baru
  final bool readOnly;

  @override
  ConsumerState<SurveyPointScreen> createState() => _SurveyPointScreenState();
}

class _SurveyPointScreenState extends ConsumerState<SurveyPointScreen> {
  final _name = TextEditingController();
  final _newRemark = TextEditingController();
  final _uplink = TextEditingController();
  final _foRemark = TextEditingController();
  final Map<String, TextEditingController> _fo = {for (final c in foNumericColumns) c: TextEditingController()};
  final List<_Photo> _photos = [];
  final List<String> _remarks = [];
  final List<_Material> _materials = [];
  final Set<String> _needs = {};
  bool _busy = false;
  num? _lat;
  num? _lng;
  String? _typeId; // jenis titik (work type SURVEY_POINT)
  String _status = 'PROPOSED'; // EXISTING = sudah terpasang, PROPOSED = usulan baru

  bool get _cctv => widget.survey['format'] == 'CCTV';
  bool get _edit => !widget.readOnly;
  List<Map<String, dynamic>> get _types =>
      (widget.survey['point_types'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();
  Map<String, dynamic>? get _type => _types.where((t) => '${t['work_type_id']}' == _typeId).firstOrNull;
  List<Map<String, dynamic>> get _slots =>
      (_type?['slots'] as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();
  List<Map> get _catalog => (_type?['catalog'] as List? ?? const []).cast<Map>();
  bool _inCatalog(String name) => _catalog.any((m) => '${m['name']}'.toLowerCase() == name.toLowerCase());

  /// Ganti jenis titik: foto dipindah ke slot bernama sama di jenis baru, sisanya dilepas.
  void _setType(String id) {
    if (id == _typeId) return;
    setState(() {
      _typeId = id;
      final byName = {for (final sl in _slots) '${sl['name']}'.toLowerCase(): '${sl['requirement_id']}'};
      final oldNames = {for (final ph in _photos) ph.requirementId: _slotNameOf(ph.requirementId)};
      final kept = <_Photo>[];
      for (final ph in _photos) {
        final target = byName[(oldNames[ph.requirementId] ?? '').toLowerCase()];
        if (target != null) kept.add(_Photo(fileId: ph.fileId, path: ph.path, requirementId: target));
      }
      if (kept.length < _photos.length) _snack('Foto yang slotnya tidak ada di jenis ini dilepas.');
      _photos
        ..clear()
        ..addAll(kept);
    });
  }

  final Map<String, String> _slotNames = {};
  String? _slotNameOf(String requirementId) => _slotNames[requirementId];

  @override
  void initState() {
    super.initState();
    for (final t in _types) {
      for (final sl in (t['slots'] as List? ?? const []).cast<Map>()) {
        _slotNames['${sl['requirement_id']}'] = '${sl['name']}';
      }
    }
    if (_types.length == 1) _typeId = '${_types.first['work_type_id']}';
    final p = widget.point;
    if (p != null) {
      _name.text = '${p['name']}';
      _typeId = '${p['point_type_id'] ?? _typeId}';
      _status = '${p['point_status'] ?? 'PROPOSED'}';
      _remarks.addAll((p['remarks'] as List? ?? const []).map((e) => '$e'));
      _lat = num.tryParse('${p['site_lat'] ?? ''}');
      _lng = num.tryParse('${p['site_lng'] ?? ''}');
      // Foto dari slot lama (work type pernah diubah) dipetakan ke slot sekarang lewat nama.
      final byName = {for (final s in _slots) '${s['name']}'.toLowerCase(): '${s['requirement_id']}'};
      for (final ph in (p['photos'] as List? ?? const []).cast<Map>()) {
        final slot = '${ph['slot'] ?? ''}'.toLowerCase();
        final rid = byName[slot] ?? '${ph['requirement_id']}';
        _slotNames.putIfAbsent(rid, () => '${ph['slot'] ?? ''}');
        _photos.add(_Photo(fileId: '${ph['file_id']}', requirementId: rid));
      }
      for (final l in (p['lines'] as List? ?? const []).cast<Map>()) {
        final name = '${l['name']}';
        final qty = num.tryParse('${l['qty']}') ?? 0;
        switch (l['category']) {
          case 'KEBUTUHAN':
            _needs.add(name);
          case 'KABEL':
            if (name == 'Uplink Switch') {
              _uplink.text = '${l['notes'] ?? ''}';
            } else if (name == 'Remark') {
              _foRemark.text = '${l['notes'] ?? ''}';
            } else if (_fo.containsKey(name)) {
              _fo[name]!.text = _fmt(qty);
            }
          default:
            _materials.add(_Material(name, qty, '${l['unit']}'));
        }
      }
    } else {
      // Koordinat titik dari GPS yang sudah hangat sejak aplikasi dibuka — tidak menunggu.
      getCurrentPositionSafely().then((r) {
        if (!mounted || r.position == null) return;
        setState(() {
          _lat = r.position!.latitude;
          _lng = r.position!.longitude;
        });
      });
    }
  }

  @override
  void dispose() {
    for (final c in [_name, _newRemark, _uplink, _foRemark, ..._fo.values]) {
      c.dispose();
    }
    super.dispose();
  }

  String _fmt(num n) => n == n.roundToDouble() ? n.toInt().toString() : n.toString();

  void _snack(String text) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));

  Future<void> _addPhoto(Map<String, dynamic> slot, PhotoOrigin origin) async {
    final picked = await pickReportPhoto(
      context: context,
      slot: '${slot['name']}',
      origin: origin,
      hint: slot['hint'] as String?,
      onError: _snack,
    );
    if (picked == null || !mounted) return;
    setState(() => _photos.add(_Photo(path: picked.path, requirementId: '${slot['requirement_id']}')));
  }

  void _addRemark() {
    final text = _newRemark.text.trim();
    if (text.isEmpty) return;
    setState(() {
      _remarks.add(text);
      _newRemark.clear();
    });
  }

  /// Pilih material dari katalog jenis titik (cari) atau ketik sendiri, lalu isi jumlah.
  Future<void> _pickMaterial() async {
    final m = await pickSurveyMaterial(context, _catalog);
    if (m != null && mounted) setState(() => _materials.add(_Material(m.name, m.qty, m.unit)));
  }

  Future<void> _addNeed() async {
    final ctrl = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Kebutuhan lain'),
        content: VmsTextField(
          controller: ctrl,
          autofocus: true,
          maxLength: 255,
          decoration: const InputDecoration(labelText: 'mis. Crane, izin kerja panas'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Batal')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Tambah')),
        ],
      ),
    );
    if (ok == true && ctrl.text.trim().isNotEmpty) setState(() => _needs.add(ctrl.text.trim()));
  }

  Future<void> _save() async {
    if (_busy) return;
    if (_name.text.trim().length < 2) return _snack('Isi nama titik dulu (langkah 1).');
    if (_typeId == null) return _snack('Pilih jenis titik dulu (langkah 1).');
    if (_photos.isEmpty) return _snack('Ambil minimal satu foto (langkah 2).');
    if (_newRemark.text.trim().isNotEmpty) _addRemark();
    setState(() => _busy = true);
    try {
      final api = ref.read(syncEngineProvider).api;
      for (final p in _photos.where((p) => p.fileId == null)) {
        p.fileId = await api.uploadFile(File(p.path!));
      }
      final lines = <Map<String, dynamic>>[
        for (final m in _materials) {'category': 'MATERIAL', 'name': m.name, 'qty': m.qty, 'unit': m.unit},
        for (final n in _needs) {'category': 'KEBUTUHAN', 'name': n, 'qty': 1, 'unit': 'unit'},
        if (_cctv) ...[
          for (final e in _fo.entries)
            if ((num.tryParse(e.value.text.replaceAll(',', '.')) ?? 0) > 0)
              {'category': 'KABEL', 'name': e.key, 'qty': num.parse(e.value.text.replaceAll(',', '.')), 'unit': 'm'},
          if (_uplink.text.trim().isNotEmpty)
            {'category': 'KABEL', 'name': 'Uplink Switch', 'qty': 0, 'unit': '-', 'notes': _uplink.text.trim()},
          if (_foRemark.text.trim().isNotEmpty)
            {'category': 'KABEL', 'name': 'Remark', 'qty': 0, 'unit': '-', 'notes': _foRemark.text.trim()},
        ],
      ];
      final body = {
        'name': _name.text.trim(),
        'point_type_id': _typeId,
        'point_status': _status,
        'remarks': _remarks,
        'photos': [
          for (final p in _photos) {'file_id': p.fileId, 'requirement_id': p.requirementId},
        ],
        'lines': lines,
        'site_lat': ?_lat,
        'site_lng': ?_lng,
      };
      final result = widget.point == null
          ? await api.addSurveyPoint('${widget.survey['task_id']}', body)
          : await api.updateSurveyPoint('${widget.point!['point_id']}', body);
      if (mounted) Navigator.of(context).pop(result);
    } catch (e) {
      _snack(apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final title = widget.readOnly ? 'Detail titik' : (widget.point == null ? 'Titik baru' : 'Ubah titik');
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      bottomNavigationBar: _edit
          ? SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 10),
                child: PrimaryAction(label: 'Simpan titik', icon: Icons.save_rounded, busy: _busy, onTap: _save),
              ),
            )
          : null,
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
        children: [
          _Section(
            number: 1,
            title: 'Jenis dan nama titik',
            subtitle: 'Jenis titik menentukan foto dan katalog material yang diminta.',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (_types.isNotEmpty)
                  VmsSelectField<String>(
                    label: 'Jenis Pekerjaan Titik',
                    icon: Icons.work_outline,
                    value: _typeId,
                    options: [
                      for (final t in _types)
                        VmsOption('${t['work_type_id']}', '${t['name']}'),
                    ],
                    onChanged: _setType,
                  ),
                const SizedBox(height: 8),
                SegmentedButton<String>(
                  segments: const [
                    ButtonSegment(value: 'PROPOSED', label: Text('Usulan baru'), icon: Icon(Icons.add_location_alt)),
                    ButtonSegment(value: 'EXISTING', label: Text('Sudah terpasang'), icon: Icon(Icons.check_circle)),
                  ],
                  selected: {_status},
                  onSelectionChanged: _edit ? (v) => setState(() => _status = v.first) : null,
                ),
                const SizedBox(height: 12),
                VmsTextField(
                  key: const Key('survey-point-name'),
                  controller: _name,
                  maxLength: 150,
                  enabled: _edit,
                  decoration: InputDecoration(
                    hintText: _cctv ? 'mis. Titik Pemasangan CCTV 03' : 'mis. Pintu akses Samping (perlu dipasang ACS)',
                  ),
                ),
                if (_lat != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: InfoRow(
                      icon: Icons.my_location_rounded,
                      text: 'Koordinat ${_lat!.toStringAsFixed(6)}, ${_lng!.toStringAsFixed(6)}',
                    ),
                  ),
              ],
            ),
          ),
          _Section(
            number: 2,
            title: 'Foto ${_type?['name'] ?? 'titik'}',
            subtitle: _typeId == null ? 'Pilih jenis titik dulu di langkah 1.' : 'Ikuti foto panduan di setiap slot.',
            child: Column(children: [for (final slot in _slots) _SlotRow(slot: slot, photos: _photos, edit: _edit, onAdd: (o) => _addPhoto(slot, o), onRemove: (p) => setState(() => _photos.remove(p)))]),
          ),
          _Section(
            number: 3,
            title: 'Keterangan',
            subtitle: 'Catatan kondisi titik, satu poin per baris (tampil sebagai daftar di laporan).',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (var i = 0; i < _remarks.length; i++)
                  ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.remove, size: 16),
                    title: Text(_remarks[i]),
                    trailing: _edit
                        ? IconButton(
                            icon: const Icon(Icons.close_rounded),
                            onPressed: () => setState(() => _remarks.removeAt(i)),
                          )
                        : null,
                  ),
                if (_edit)
                  VmsTextField(
                    controller: _newRemark,
                    maxLength: 255,
                    textInputAction: TextInputAction.done,
                    onSubmitted: (_) => _addRemark(),
                    decoration: InputDecoration(
                      hintText: 'Tulis remark lalu tekan +',
                      suffixIcon: IconButton(icon: const Icon(Icons.add_circle_rounded), onPressed: _addRemark),
                    ),
                  ),
                if (!_edit && _remarks.isEmpty) const Text('-'),
              ],
            ),
          ),
          _Section(
            number: 4,
            title: 'Kebutuhan pemasangan',
            subtitle: 'Alat/izin yang harus disiapkan sebelum pemasangan (dipakai PM menyusun rencana).',
            child: Wrap(
              spacing: 8,
              runSpacing: 4,
              children: [
                for (final n in {...quickNeeds, ..._needs})
                  if (_edit || _needs.contains(n))
                    FilterChip(
                      label: Text(n),
                      selected: _needs.contains(n),
                      onSelected: _edit ? (on) => setState(() => on ? _needs.add(n) : _needs.remove(n)) : null,
                    ),
                if (_edit)
                  ActionChip(
                    avatar: const Icon(Icons.add, size: 18),
                    label: const Text('Lainnya'),
                    onPressed: _addNeed,
                  ),
              ],
            ),
          ),
          _Section(
            number: 5,
            title: 'Material ${_type?['name'] ?? ''}'.trim(),
            subtitle:
                'Dijumlahkan otomatis ke daftar material di laporan. '
                'Material di luar katalog ditandai dan diperiksa PM.',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (final m in _materials)
                  ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.inventory_2_outlined),
                    title: Text(m.name),
                    subtitle: Text('${_fmt(m.qty)} ${m.unit}${_inCatalog(m.name) ? '' : ' · di luar katalog'}'),
                    trailing: _edit
                        ? IconButton(
                            icon: const Icon(Icons.delete_outline),
                            onPressed: () => setState(() => _materials.remove(m)),
                          )
                        : null,
                  ),
                if (_edit)
                  OutlinedButton.icon(
                    onPressed: _typeId == null ? null : _pickMaterial,
                    icon: const Icon(Icons.add),
                    label: const Text('Tambah material'),
                  ),
                if (!_edit && _materials.isEmpty) const Text('-'),
              ],
            ),
          ),
          if (_cctv)
            _Section(
              number: 6,
              title: 'Hitungan kabel (FO)',
              subtitle: 'Masuk tabel "Hitungan installasi Fiber Optic". Kosongkan yang tidak dipakai.',
              child: Column(
                children: [
                  GridView.count(
                    crossAxisCount: 2,
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    childAspectRatio: 3.2,
                    crossAxisSpacing: 8,
                    children: [
                      for (final e in _fo.entries)
                        TextField(
                          controller: e.value,
                          enabled: _edit,
                          keyboardType: const TextInputType.numberWithOptions(decimal: true),
                          decoration: InputDecoration(labelText: e.key, isDense: true),
                        ),
                    ],
                  ),
                  VmsTextField(
                    controller: _uplink,
                    maxLength: 150,
                    enabled: _edit,
                    decoration: const InputDecoration(labelText: 'Uplink switch', hintText: 'mis. Control Room'),
                  ),
                  VmsTextField(
                    controller: _foRemark,
                    maxLength: 255,
                    enabled: _edit,
                    decoration: const InputDecoration(
                      labelText: 'Keterangan kabel',
                      hintText: 'mis. Penarikan Kabel STP',
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

}
