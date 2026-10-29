import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/error_message.dart';
import '../../core/location_helper.dart';
import '../../core/providers.dart';
import '../../shared/ui/vms_network_image.dart';
import '../../shared/ui/vms_text_field.dart';
import '../../shared/ui/vms_ui.dart';
import 'photo_slots.dart' show ExampleThumb, PhotoOrigin, pickReportPhoto;

/// Kolom tabel "Hitungan installasi Fiber Optic (FO) CCTV" (sama dengan laporan baku, docs/37).
const foNumericColumns = [
  'Galian/Tarikan',
  'Indoor Cable',
  'Spare cable',
  'Kabel FO',
  'Kabel Power',
  'Cable Subduct',
  'Pipe 2"',
  'Patch Cord SC-SC',
  'Pigtail SC',
  'FDU',
  'Concrete Cable Cover',
  'Concrete Marker Block (Straight)',
  'Concrete Marker Block (Bend)',
  'Plastic Marker Tape',
];

/// Kebutuhan pemasangan yang sering muncul (pilih cepat; bisa ditambah sendiri).
const quickNeeds = [
  'Tangga panjang',
  'Scaffolding / Bucket Truck',
  'Grounding',
  'Galian',
  'Box Panel',
  'Izin kerja / Facility Owner',
];

class _Photo {
  _Photo({this.fileId, this.path, required this.requirementId});
  String? fileId;
  final String? path;
  final String requirementId;
}

class _Material {
  _Material(this.name, this.qty, this.unit);
  final String name;
  num qty;
  final String unit;
}

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
            title: 'Jenis & nama titik',
            subtitle: 'Jenis titik menentukan foto dan katalog material yang diminta.',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 8,
                  runSpacing: 4,
                  children: [
                    for (final t in _types)
                      ChoiceChip(
                        label: Text('${t['name']}'),
                        selected: _typeId == '${t['work_type_id']}',
                        onSelected: _edit ? (_) => _setType('${t['work_type_id']}') : null,
                      ),
                  ],
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
            child: Column(children: [for (final slot in _slots) _slotRow(slot)]),
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

  Widget _slotRow(Map<String, dynamic> slot) {
    final reqId = '${slot['requirement_id']}';
    final mine = _photos.where((p) => p.requirementId == reqId).toList();
    final mandatory = slot['mandatory'] == true;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text('${slot['name']}', style: Theme.of(context).textTheme.titleSmall)),
              if (mandatory)
                Text(
                  mine.isEmpty ? 'Wajib' : '✓',
                  style: TextStyle(color: mine.isEmpty ? Accent.rose.strong : Colors.green),
                ),
            ],
          ),
          if (slot['hint'] != null) Text('${slot['hint']}', style: Theme.of(context).textTheme.bodySmall),
          if (slot['example_file_id'] != null) ...[
            const SizedBox(height: 6),
            ExampleThumb(fileId: '${slot['example_file_id']}', label: '${slot['name']}'),
          ],
          const SizedBox(height: 6),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final p in mine) _photoTile(p),
              if (_edit) ...[
                _AddTile(
                  icon: Icons.photo_camera_rounded,
                  label: 'Kamera',
                  onTap: () => _addPhoto(slot, PhotoOrigin.camera),
                ),
                _AddTile(
                  icon: Icons.photo_library_rounded,
                  label: 'Galeri',
                  onTap: () => _addPhoto(slot, PhotoOrigin.phoneGallery),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }

  Widget _photoTile(_Photo p) {
    final Widget image = p.path != null
        ? Image.file(File(p.path!), fit: BoxFit.cover)
        : VmsNetworkImage(fileId: p.fileId!);
    return Stack(
      children: [
        Container(
          width: 96,
          height: 96,
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(10), color: Colors.black12),
          clipBehavior: Clip.antiAlias,
          child: image,
        ),
        if (_edit)
          Positioned(
            right: 2,
            top: 2,
            child: InkWell(
              onTap: () => setState(() => _photos.remove(p)),
              child: const CircleAvatar(
                radius: 11,
                backgroundColor: Colors.black54,
                child: Icon(Icons.close, size: 14, color: Colors.white),
              ),
            ),
          ),
      ],
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.number, required this.title, required this.child, this.subtitle});
  final int number;
  final String title;
  final String? subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: SurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              CircleAvatar(radius: 12, child: Text('$number', style: const TextStyle(fontSize: 12))),
              const SizedBox(width: 8),
              Expanded(child: Text(title, style: Theme.of(context).textTheme.titleMedium)),
            ],
          ),
          if (subtitle != null) ...[
            const SizedBox(height: 4),
            Text(subtitle!, style: Theme.of(context).textTheme.bodySmall),
          ],
          const SizedBox(height: 10),
          child,
        ],
      ),
    ),
  );
}

class _AddTile extends StatelessWidget {
  const _AddTile({required this.icon, required this.label, required this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
    onTap: onTap,
    borderRadius: BorderRadius.circular(10),
    child: Container(
      width: 96,
      height: 96,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(fontSize: 12)),
        ],
      ),
    ),
  );
}

/// Lembar pemilih material: cari di katalog work type, atau pakai teks yang diketik sebagai material baru.
/// Material terpilih: dari katalog (satuan baku) atau di luar katalog (satuan dari daftar).
class SurveyMaterialPick {
  const SurveyMaterialPick(this.name, this.qty, this.unit);
  final String name;
  final num qty;
  final String unit;
}

/// Satuan baku untuk material di luar katalog — tidak diketik bebas agar BoM tidak salah satuan.
const surveyUnits = ['Unit', 'Meter', 'Pasang', 'Batang', 'Roll', 'Set', 'Buah', 'Lot'];

/// Cari material di katalog atau tambah di luar katalog, lalu isi jumlah. Dipakai titik & material umum lokasi.
Future<SurveyMaterialPick?> pickSurveyMaterial(BuildContext context, List<Map> catalog) async {
  final picked = await showModalBottomSheet<Map<String, String>>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (ctx) => _MaterialPicker(catalog: catalog),
  );
  if (picked == null || !context.mounted) return null;
  final fromCatalog = picked['custom'] != '1';
  final qty = TextEditingController(text: picked['qty'] ?? '1');
  var unit = picked['unit'] ?? 'Unit';
  final ok = await showDialog<bool>(
    context: context,
    builder: (ctx) => StatefulBuilder(
      builder: (ctx, setLocal) => AlertDialog(
        title: Text(picked['name']!),
        content: Row(
          children: [
            Expanded(
              child: TextField(
                controller: qty,
                autofocus: true,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(labelText: 'Jumlah'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: fromCatalog
                  ? InputDecorator(
                      decoration: const InputDecoration(labelText: 'Satuan'),
                      child: Text(unit),
                    )
                  : DropdownButtonFormField<String>(
                      initialValue: unit,
                      decoration: const InputDecoration(labelText: 'Satuan'),
                      items: [for (final u in surveyUnits) DropdownMenuItem(value: u, child: Text(u))],
                      onChanged: (v) => setLocal(() => unit = v ?? unit),
                    ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Batal')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Tambah')),
        ],
      ),
    ),
  );
  final q = num.tryParse(qty.text.replaceAll(',', '.'));
  if (ok != true || q == null || q <= 0) return null;
  return SurveyMaterialPick(picked['name']!, q, unit);
}

class _MaterialPicker extends StatefulWidget {
  const _MaterialPicker({required this.catalog});
  final List<Map> catalog;

  @override
  State<_MaterialPicker> createState() => _MaterialPickerState();
}

class _MaterialPickerState extends State<_MaterialPicker> {
  final _q = TextEditingController();

  static String _qtyText(Object? v) {
    final n = num.tryParse('${v ?? 1}') ?? 1;
    return n == n.roundToDouble() ? n.toInt().toString() : n.toString();
  }

  @override
  void dispose() {
    _q.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final q = _q.text.trim().toLowerCase();
    final items = widget.catalog.where((m) => '${m['name']}'.toLowerCase().contains(q)).toList();
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: SizedBox(
        height: MediaQuery.of(context).size.height * 0.7,
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: TextField(
                controller: _q,
                autofocus: true,
                onChanged: (_) => setState(() {}),
                decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Cari material…'),
              ),
            ),
            if (q.isNotEmpty && !items.any((m) => '${m['name']}'.toLowerCase() == q))
              ListTile(
                leading: const Icon(Icons.add_circle_outline),
                title: Text('Tambah "${_q.text.trim()}"'),
                subtitle: const Text('Material di luar katalog'),
                onTap: () => Navigator.pop(context, {'name': _q.text.trim(), 'unit': 'Unit', 'custom': '1'}),
              ),
            Expanded(
              child: ListView(
                children: [
                  for (final m in items)
                    ListTile(
                      leading: const Icon(Icons.inventory_2_outlined),
                      title: Text('${m['name']}'),
                      subtitle: Text('${m['unit']}'),
                      onTap: () => Navigator.pop(context, {
                        'name': '${m['name']}',
                        'unit': '${m['unit']}',
                        'qty': _qtyText(m['default_qty']),
                      }),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
