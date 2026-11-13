import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/error_message.dart';
import '../../core/location_helper.dart';
import '../../core/providers.dart';
import '../../data/sync_engine.dart';
import '../../shared/ui/vms_select_field.dart';
import '../../shared/ui/vms_ui.dart';
import 'photo_slots.dart' show PhotoOrigin, pickReportPhoto;
import 'wo_survey_draft.dart';

/// Layar isi survei work order: titik, jenis pekerjaan, lokasi, foto, kebutuhan barang.
/// Dikirim lewat antrean (`WO_SURVEY_SUBMIT`) sehingga tetap jalan tanpa sinyal.
/// Menutup dengan `true` bila survei sudah dicatat (terkirim atau menunggu sinyal).
class WoSurveyFormScreen extends ConsumerStatefulWidget {
  const WoSurveyFormScreen({super.key, required this.survey});

  final Map<String, dynamic> survey;

  @override
  ConsumerState<WoSurveyFormScreen> createState() => _WoSurveyFormScreenState();
}

class _WoSurveyFormScreenState extends ConsumerState<WoSurveyFormScreen> {
  final _draft = WoSurveyDraft();
  List<Map<String, dynamic>> _types = const [];
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _loadTypes();
  }

  Future<void> _loadTypes() async {
    try {
      final engine = ref.read(syncEngineProvider);
      final items = (await engine.fetchList('work_types', () => engine.api.workTypes())).items;
      if (mounted) setState(() => _types = items);
    } catch (_) {
      // Tanpa daftar jenis pekerjaan, kirim tidak mungkin; pesannya muncul saat memilih.
    }
  }

  void _snack(String text) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));

  Future<void> _addPhoto(WoSurveyPoint p, PhotoOrigin origin) async {
    final picked = await pickReportPhoto(
      context: context,
      slot: 'Foto titik',
      origin: origin,
      onError: _snack,
    );
    if (picked == null || !mounted) return;
    setState(() => p.photoPaths.add(picked.path));
  }

  Future<void> _useLocation(WoSurveyPoint p) async {
    final r = await getCurrentPositionSafely();
    if (!mounted) return;
    if (r.position == null) {
      _snack('Lokasi belum didapat. Pastikan GPS menyala lalu coba lagi.');
      return;
    }
    if (r.isMocked) {
      _snack(mockLocationMessage);
      return;
    }
    setState(() {
      p.lat = r.position!.latitude;
      p.lng = r.position!.longitude;
    });
  }

  Future<void> _addBom(WoSurveyPoint p) async {
    final name = TextEditingController();
    final qty = TextEditingController(text: '1');
    final unit = TextEditingController(text: 'unit');
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Tambah barang kebutuhan'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: name,
              decoration: const InputDecoration(labelText: 'Nama barang'),
              inputFormatters: [LengthLimitingTextInputFormatter(woSurveyBomNameMax)],
            ),
            TextField(
              controller: qty,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(labelText: 'Jumlah'),
            ),
            TextField(
              controller: unit,
              decoration: const InputDecoration(labelText: 'Satuan'),
              inputFormatters: [LengthLimitingTextInputFormatter(20)],
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Batal')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Tambah')),
        ],
      ),
    );
    if (ok == true && name.text.trim().isNotEmpty) {
      setState(() => p.bom.add(WoBomLine(
            name: name.text,
            qty: num.tryParse(qty.text.replaceAll(',', '.')) ?? 0,
            unit: unit.text.trim().isEmpty ? 'unit' : unit.text,
          )));
    }
  }

  Future<void> _send() async {
    if (_busy) return;
    final err = _draft.validate();
    if (err != null) return _snack(err);
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Kirim survei?'),
        content: Text(
          'Survei berisi ${_draft.points.length} titik akan dikirim ke PM. '
          'Setelah dikirim, isinya tidak bisa diubah dari HP. '
          'Bila tidak ada sinyal, survei dikirim otomatis nanti.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Belum')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Kirim')),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    setState(() => _busy = true);
    try {
      final sent = await ref
          .read(syncEngineProvider)
          .submit(OfflineOp.woSurveySubmit, _draft.toPayload('${widget.survey['work_order_id']}'));
      if (!mounted) return;
      _snack(sent ? 'Survei terkirim.' : 'Survei tersimpan. Akan dikirim saat ada sinyal.');
      Navigator.of(context).pop(true);
    } on SyncRejectedException catch (e) {
      if (mounted) _snack(e.message);
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      _snack(apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.survey;
    return Scaffold(
      appBar: AppBar(title: const Text('Isi survei')),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 10),
          child: PrimaryAction(label: 'Kirim survei', icon: Icons.send_rounded, busy: _busy, onTap: _send),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
        children: [
          Text('${s['wo_number']} · ${s['title']}', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 12),
          VmsSelectField<String>(
            label: 'Jenis survei',
            icon: Icons.fact_check_outlined,
            options: [for (final f in woSurveyFormats) VmsOption(f, f)],
            value: _draft.format,
            onChanged: (v) => setState(() => _draft.format = v),
          ),
          const SizedBox(height: 12),
          TextField(
            decoration: const InputDecoration(labelText: 'Ringkasan hasil survei (boleh kosong)'),
            maxLines: 3,
            inputFormatters: [LengthLimitingTextInputFormatter(woSurveyNarrativeMax)],
            onChanged: (v) => _draft.narrative = v,
          ),
          const SectionTitle('Titik survei'),
          for (var i = 0; i < _draft.points.length; i++) _pointCard(i, _draft.points[i]),
          SizedBox(
            height: 48,
            child: OutlinedButton.icon(
              onPressed: () => setState(() => _draft.points.add(WoSurveyPoint())),
              icon: const Icon(Icons.add_location_alt_outlined),
              label: const Text('Tambah titik'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _pointCard(int i, WoSurveyPoint p) {
    return Padding(
      key: ObjectKey(p),
      padding: const EdgeInsets.only(bottom: 12),
      child: SurfaceCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(child: Text('Titik ${i + 1}', style: Theme.of(context).textTheme.titleSmall)),
                IconButton(
                  tooltip: 'Hapus titik',
                  constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
                  onPressed: () => setState(() => _draft.points.remove(p)),
                  icon: const Icon(Icons.delete_outline),
                ),
              ],
            ),
            TextFormField(
              initialValue: p.name,
              decoration: const InputDecoration(labelText: 'Nama titik'),
              inputFormatters: [LengthLimitingTextInputFormatter(woSurveyPointNameMax)],
              onChanged: (v) => p.name = v,
            ),
            const SizedBox(height: 8),
            VmsSelectField<String>(
              label: 'Jenis pekerjaan yang disarankan',
              icon: Icons.build_outlined,
              options: [for (final t in _types) VmsOption('${t['id']}', '${t['name']}')],
              value: p.workTypeId,
              onChanged: (v) => setState(() => p.workTypeId = v),
            ),
            const SizedBox(height: 8),
            TextFormField(
              initialValue: p.remarks,
              decoration: const InputDecoration(labelText: 'Catatan (boleh kosong)'),
              maxLines: 2,
              inputFormatters: [LengthLimitingTextInputFormatter(woSurveyRemarksMax)],
              onChanged: (v) => p.remarks = v,
            ),
            const SizedBox(height: 8),
            SizedBox(
              height: 48,
              child: OutlinedButton.icon(
                onPressed: () => _useLocation(p),
                icon: Icon(p.lat == null ? Icons.my_location : Icons.check_circle_outline),
                label: Text(p.lat == null ? 'Pakai lokasi saya sekarang' : 'Lokasi terisi (ketuk untuk perbarui)'),
              ),
            ),
            const SizedBox(height: 8),
            Text('Foto titik: ${p.photoPaths.length}'),
            Row(
              children: [
                Expanded(
                  child: SizedBox(
                    height: 48,
                    child: OutlinedButton.icon(
                      onPressed: () => _addPhoto(p, PhotoOrigin.camera),
                      icon: const Icon(Icons.photo_camera_rounded),
                      label: const Text('Foto'),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: SizedBox(
                    height: 48,
                    child: OutlinedButton.icon(
                      onPressed: () => _addPhoto(p, PhotoOrigin.phoneGallery),
                      icon: const Icon(Icons.photo_library_rounded),
                      label: const Text('Galeri'),
                    ),
                  ),
                ),
              ],
            ),
            if (p.photoPaths.isNotEmpty)
              TextButton(
                onPressed: () => setState(p.photoPaths.removeLast),
                child: const Text('Hapus foto terakhir'),
              ),
            const SizedBox(height: 8),
            for (final b in p.bom)
              ListTile(
                contentPadding: EdgeInsets.zero,
                minTileHeight: 48,
                title: Text('${b.name} · ${b.qty} ${b.unit}'),
                trailing: IconButton(
                  tooltip: 'Hapus barang',
                  onPressed: () => setState(() => p.bom.remove(b)),
                  icon: const Icon(Icons.close),
                ),
              ),
            SizedBox(
              height: 48,
              child: TextButton.icon(
                onPressed: () => _addBom(p),
                icon: const Icon(Icons.add),
                label: const Text('Tambah barang kebutuhan'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
