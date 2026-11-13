import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/error_message.dart';
import '../../core/photo_capture.dart';
import '../../core/providers.dart';
import '../../core/theme/theme.dart';
import '../../shared/ui/vms_ui.dart';
import 'inspeksi_kendaraan.dart';

Widget _galat(String pesan, VoidCallback ulang) => Column(
  children: [
    NoticeBanner(icon: Icons.error_outline_rounded, text: pesan, accent: Accent.rose),
    SizedBox(height: 48, child: OutlinedButton(onPressed: ulang, child: const Text('Coba lagi'))),
  ],
);

/// Daftar "Inspeksi saya" (baca lewat cache) dan tombol periksa kendaraan.
class InspeksiKendaraanScreen extends ConsumerStatefulWidget {
  const InspeksiKendaraanScreen({super.key});

  @override
  ConsumerState<InspeksiKendaraanScreen> createState() => _InspeksiState();
}

class _InspeksiState extends ConsumerState<InspeksiKendaraanScreen> {
  List<Map<String, dynamic>> _items = [];
  DateTime? _cachedAt;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final engine = ref.read(syncEngineProvider);
      final r = await engine.fetchList('inspeksi_saya', engine.api.myInspections);
      if (!mounted) return;
      setState(() {
        _items = r.items;
        _cachedAt = r.cachedAt;
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

  Future<void> _periksa() async {
    final ok = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => const FormInspeksiScreen()),
    );
    if (ok == true) await _load();
  }

  Widget _isi() {
    if (_loading) return const SkeletonCards();
    if (_error != null) return _galat(_error!, _load);
    if (_items.isEmpty) {
      return const EmptyState(
        icon: Icons.fact_check_outlined,
        title: 'Belum ada inspeksi',
        message: 'Tekan "Periksa kendaraan" untuk membuat pemeriksaan pertama.',
      );
    }
    return Column(
      children: [
        if (_cachedAt != null)
          const NoticeBanner(
            icon: Icons.cloud_off_rounded,
            text: 'Tidak ada sinyal. Ini data terakhir yang tersimpan di HP.',
          ),
        for (final it in _items)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: SurfaceCard(
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => DetailInspeksiScreen(id: '${it['inspection_id']}')),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${it['vehicle_name'] ?? 'Kendaraan'} ${it['number_plate'] ?? ''}'.trim(),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: VmsTextStyles.subheading.copyWith(fontWeight: FontWeight.w700),
                  ),
                  Text(
                    '${inspeksiPeriodeLabel('${it['period_type']}')} - ${it['inspection_date']}',
                    style: VmsTextStyles.bodySm,
                  ),
                  Text(inspeksiStatusLabel('${it['status']}'), style: VmsTextStyles.bodySm),
                ],
              ),
            ),
          ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Inspeksi kendaraan')),
    body: RefreshIndicator(
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.all(16), children: [_isi()]),
    ),
    bottomNavigationBar: SafeArea(
      minimum: const EdgeInsets.all(16),
      child: PrimaryAction(label: 'Periksa kendaraan', icon: Icons.add_task_rounded, onTap: _periksa),
    ),
  );
}

/// Formulir periksa kendaraan. Mengirim butuh sinyal; isian tetap di layar bila gagal.
class FormInspeksiScreen extends ConsumerStatefulWidget {
  const FormInspeksiScreen({super.key});

  @override
  ConsumerState<FormInspeksiScreen> createState() => _FormState();
}

class _FormState extends ConsumerState<FormInspeksiScreen> {
  List<Map<String, dynamic>> _vehicles = [];
  List<Map<String, dynamic>> _butir = [];
  bool _loading = true;
  String? _error;
  String? _vehicleId;
  String _periode = 'DAILY';
  final Map<String, String> _jawab = {};
  final List<File> _foto = [];
  final _catatan = TextEditingController();
  final _odo = TextEditingController();
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _catatan.dispose();
    _odo.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final engine = ref.read(syncEngineProvider);
      final v = await engine.fetchList('inspeksi_kendaraan', engine.api.vehiclesForInspection);
      final t = await engine.fetchMap('inspeksi_templat', engine.api.inspectionChecklistTemplate);
      if (!mounted) return;
      setState(() {
        _vehicles = v.items;
        _butir = ((t['items'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();
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

  Future<void> _ambilFoto() async {
    if (_foto.length >= inspeksiMaxFoto) return;
    final (file, _) = await captureWatermarkedPhoto(
      context: context,
      label: 'Foto bukti',
      hint: 'Foto bagian kendaraan yang diperiksa',
    );
    if (file != null && mounted) setState(() => _foto.add(file));
  }

  void _pesan(String m) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
  }

  Future<void> _kirim() async {
    final salah = inspeksiBelumSiap(vehicleId: _vehicleId, jumlahButir: _butir.length, terjawab: _jawab.length);
    if (salah != null) return _pesan(salah);
    setState(() => _sending = true);
    try {
      final api = ref.read(syncEngineProvider).api;
      final ids = <String>[];
      for (final f in _foto) {
        ids.add(await api.uploadFile(f));
      }
      await api.createInspection(
        buildInspeksiBody(
          vehicleId: _vehicleId!,
          periodType: _periode,
          checklist: _jawab,
          photoIds: ids,
          notes: _catatan.text,
          odometerKm: int.tryParse(_odo.text.trim()),
        ),
      );
      if (!mounted) return;
      _pesan('Inspeksi terkirim.');
      Navigator.of(context).pop(true);
    } catch (e) {
      final offline = e is DioException && isNetworkFailure(e);
      _pesan(offline ? 'Tidak ada sinyal. Isian Anda masih di layar. Coba kirim lagi saat sinyal ada.' : apiErrorMessage(e));
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  Widget _form() {
    if (_vehicles.isEmpty) {
      return const EmptyState(
        icon: Icons.directions_car_outlined,
        title: 'Tidak ada kendaraan',
        message: 'Anda belum punya kendaraan yang boleh diperiksa.',
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        DropdownButtonFormField<String>(
          initialValue: _vehicleId,
          isExpanded: true,
          decoration: const InputDecoration(labelText: 'Kendaraan'),
          items: [
            for (final v in _vehicles)
              DropdownMenuItem(
                value: '${v['vehicle_id']}',
                child: Text('${v['name'] ?? ''} ${v['number_plate'] ?? ''}'.trim(), overflow: TextOverflow.ellipsis),
              ),
          ],
          onChanged: (x) => setState(() => _vehicleId = x),
        ),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          initialValue: _periode,
          decoration: const InputDecoration(labelText: 'Jenis pemeriksaan'),
          items: [
            for (final p in const ['DAILY', 'WEEKLY', 'MONTHLY'])
              DropdownMenuItem(value: p, child: Text(inspeksiPeriodeLabel(p))),
          ],
          onChanged: (x) => setState(() => _periode = x ?? 'DAILY'),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _odo,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Angka kilometer (boleh kosong)'),
        ),
        const SectionTitle('Daftar periksa'),
        for (final b in _butir)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: SurfaceCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${b['label']}', style: VmsTextStyles.body),
                  Wrap(
                    spacing: 8,
                    children: [
                      for (final o in List<String>.from(b['options'] as List))
                        ConstrainedBox(
                          constraints: const BoxConstraints(minHeight: 48),
                          child: ChoiceChip(
                            label: Text(inspeksiHasilLabel(o)),
                            selected: _jawab['${b['key']}'] == o,
                            onSelected: (_) => setState(() => _jawab['${b['key']}'] = o),
                          ),
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        TextField(
          controller: _catatan,
          maxLength: inspeksiMaxCatatan,
          maxLines: 3,
          decoration: const InputDecoration(labelText: 'Catatan (boleh kosong)'),
        ),
        SectionTitle('Foto bukti (${_foto.length} dari $inspeksiMaxFoto)'),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (var i = 0; i < _foto.length; i++)
              Stack(
                children: [
                  Image.file(_foto[i], width: 88, height: 88, fit: BoxFit.cover),
                  Positioned(
                    right: 0,
                    top: 0,
                    child: IconButton(
                      tooltip: 'Hapus foto',
                      constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
                      icon: const Icon(Icons.cancel_rounded),
                      onPressed: () => setState(() => _foto.removeAt(i)),
                    ),
                  ),
                ],
              ),
          ],
        ),
        const SizedBox(height: 8),
        SizedBox(
          height: 48,
          child: OutlinedButton.icon(
            onPressed: _foto.length >= inspeksiMaxFoto ? null : _ambilFoto,
            icon: const Icon(Icons.photo_camera_rounded),
            label: const Text('Ambil foto'),
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Periksa kendaraan')),
    body: _loading
        ? const Padding(padding: EdgeInsets.all(16), child: SkeletonCards())
        : _error != null
        ? Padding(padding: const EdgeInsets.all(16), child: _galat(_error!, _load))
        : ListView(padding: const EdgeInsets.all(16), children: [_form()]),
    bottomNavigationBar: _loading || _error != null || _vehicles.isEmpty
        ? null
        : SafeArea(
            minimum: const EdgeInsets.all(16),
            child: PrimaryAction(label: 'Kirim inspeksi', icon: Icons.send_rounded, busy: _sending, onTap: _kirim),
          ),
  );
}

class DetailInspeksiScreen extends ConsumerStatefulWidget {
  const DetailInspeksiScreen({super.key, required this.id});
  final String id;

  @override
  ConsumerState<DetailInspeksiScreen> createState() => _DetailState();
}

class _DetailState extends ConsumerState<DetailInspeksiScreen> {
  Map<String, dynamic>? _d;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _error = null);
    try {
      final engine = ref.read(syncEngineProvider);
      final d = await engine.fetchMap('inspeksi_${widget.id}', () => engine.api.inspectionDetail(widget.id));
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) setState(() => _error = apiErrorMessage(e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    return Scaffold(
      appBar: AppBar(title: const Text('Detail inspeksi')),
      body: _error != null
          ? Padding(padding: const EdgeInsets.all(16), child: _galat(_error!, _load))
          : d == null
          ? const Padding(padding: EdgeInsets.all(16), child: SkeletonCards())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Text(
                  '${d['vehicle_name'] ?? ''} ${d['number_plate'] ?? ''}'.trim(),
                  style: VmsTextStyles.subheading.copyWith(fontWeight: FontWeight.w700),
                ),
                Text('${inspeksiPeriodeLabel('${d['period_type']}')} - ${d['inspection_date']}'),
                Text(inspeksiStatusLabel('${d['status']}')),
                if (d['odometer_km'] != null) Text('Kilometer: ${d['odometer_km']}'),
                const SectionTitle('Daftar periksa'),
                for (final e in ((d['checklist_json'] as Map?) ?? const {}).entries)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Text('${e.key}: ${inspeksiHasilLabel('${e.value}')}'),
                  ),
                if ('${d['notes'] ?? ''}'.isNotEmpty) ...[const SectionTitle('Catatan'), Text('${d['notes']}')],
                Text('Foto bukti: ${((d['photos_json'] as List?) ?? const []).length}'),
              ],
            ),
    );
  }
}
