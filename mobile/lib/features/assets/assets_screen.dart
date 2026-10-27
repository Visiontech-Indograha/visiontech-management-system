import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/error_message.dart';
import '../../core/photo_capture.dart';
import '../../core/providers.dart';
import '../../core/theme/theme.dart';
import '../../shared/ui/vms_ui.dart';

/// Label status pengajuan pinjam aset (alur: karyawan mengajukan, HR/GA memutuskan).
String loanRequestStatusLabel(String status) => switch (status) {
  'PENDING' => 'Menunggu HR/GA',
  'APPROVED' => 'Disetujui',
  'REJECTED' => 'Ditolak',
  'CANCELLED' => 'Dibatalkan',
  _ => status,
};

/// Status pinjaman berjalan: pengembalian sudah diajukan atau belum.
String loanStateLabel(Map<String, dynamic> loan) =>
    loan['return_requested_at'] != null
    ? 'Menunggu konfirmasi pengembalian'
    : 'Sedang dipinjam';

const _conditions = {'ready': 'Baik', 'damaged': 'Rusak', 'lost': 'Hilang'};

class AssetsScreen extends ConsumerStatefulWidget {
  const AssetsScreen({super.key});

  @override
  ConsumerState<AssetsScreen> createState() => _AssetsScreenState();
}

class _AssetsScreenState extends ConsumerState<AssetsScreen> {
  List<Map<String, dynamic>> _loans = [];
  List<Map<String, dynamic>> _requests = [];
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
      final api = ref.read(syncEngineProvider).api;
      final loans = await api.myLoans();
      final requests = await api.myLoanRequests();
      if (!mounted) return;
      setState(() {
        _loans = loans;
        _requests = requests;
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

  void _toast(String message) {
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
    }
  }

  Future<void> _newRequest() async {
    final done = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (_) => const _RequestSheet(),
    );
    if (done == true) await _load();
  }

  Future<void> _returnLoan(Map<String, dynamic> loan) async {
    final done = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _ReturnSheet(loan: loan),
    );
    if (done == true) await _load();
  }

  Future<void> _cancel(Map<String, dynamic> request) async {
    if (!await confirmAction(
      context,
      title: 'Batalkan pengajuan?',
      message: 'Pengajuan pinjam ini akan dibatalkan dan tidak diproses HR/GA.',
      confirmLabel: 'Batalkan pengajuan',
    )) {
      return;
    }
    try {
      await ref
          .read(syncEngineProvider)
          .api
          .cancelLoanRequest(request['request_id'] as String);
      await _load();
    } catch (e) {
      _toast(apiErrorMessage(e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final openRequests = _requests
        .where((r) => r['status'] == 'PENDING')
        .toList();
    final history = _requests.where((r) => r['status'] != 'PENDING').toList();
    return Scaffold(
      appBar: VmsTopBar(onBack: () => context.pop()),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _newRequest,
        icon: const Icon(Icons.add_rounded),
        label: const Text('Ajukan pinjam'),
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: safeListPadding(context),
          children: [
            const HeroHeader(eyebrow: 'Layanan', title: 'Kendaraan & Alat'),
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
            if (!_loading && _error == null) ...[
              const SectionTitle('Pinjaman saya'),
              if (_loans.isEmpty)
                const _Empty('Tidak ada aset yang sedang dipinjam.'),
              for (final l in _loans) _loanCard(l),
              const SectionTitle('Pengajuan menunggu'),
              if (openRequests.isEmpty)
                const _Empty('Tidak ada pengajuan yang menunggu.'),
              for (final r in openRequests) _requestCard(r),
              if (history.isNotEmpty) const SectionTitle('Riwayat pengajuan'),
              for (final r in history) _requestCard(r),
            ],
          ],
        ),
      ),
    );
  }

  Widget _loanCard(Map<String, dynamic> l) {
    final waiting = l['return_requested_at'] != null;
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: SurfaceCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${l['asset_name']} (${l['asset_code']})',
              style: VmsTextStyles.bodySm.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 4),
            Text(
              l['asset_type'] == 'VEHICLE' ? 'Kendaraan' : 'Alat',
              style: VmsTextStyles.bodySm,
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Chip(label: Text(loanStateLabel(l))),
                const Spacer(),
                if (!waiting)
                  FilledButton(
                    onPressed: () => _returnLoan(l),
                    child: const Text('Kembalikan'),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _requestCard(Map<String, dynamic> r) {
    final status = r['status'] as String;
    final note = r['review_note'] as String?;
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: SurfaceCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${r['asset_name']} (${r['asset_code']})',
              style: VmsTextStyles.bodySm.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 4),
            Text(r['purpose'] as String? ?? '', style: VmsTextStyles.bodySm),
            const SizedBox(height: 8),
            Row(
              children: [
                Chip(label: Text(loanRequestStatusLabel(status))),
                const Spacer(),
                if (status == 'PENDING')
                  TextButton(
                    onPressed: () => _cancel(r),
                    child: const Text('Batalkan'),
                  ),
              ],
            ),
            if (status == 'REJECTED' && note != null && note.isNotEmpty)
              Text('Alasan: $note', style: VmsTextStyles.bodySm),
          ],
        ),
      ),
    );
  }
}

class _Empty extends StatelessWidget {
  const _Empty(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 12),
    child: Text(text, style: VmsTextStyles.bodySm),
  );
}

class _RequestSheet extends ConsumerStatefulWidget {
  const _RequestSheet();

  @override
  ConsumerState<_RequestSheet> createState() => _RequestSheetState();
}

class _RequestSheetState extends ConsumerState<_RequestSheet> {
  String _kind = 'tools';
  List<Map<String, dynamic>> _assets = [];
  String? _assetId;
  final _purpose = TextEditingController();
  bool _busy = false;
  bool _loadingAssets = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadAssets();
  }

  @override
  void dispose() {
    _purpose.dispose();
    super.dispose();
  }

  Future<void> _loadAssets() async {
    setState(() {
      _loadingAssets = true;
      _assetId = null;
    });
    try {
      final list = await ref
          .read(syncEngineProvider)
          .api
          .assetsAvailable(_kind);
      if (mounted) {
        setState(() {
          _assets = list;
          _loadingAssets = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = apiErrorMessage(e);
          _loadingAssets = false;
        });
      }
    }
  }

  String _label(Map<String, dynamic> a) => _kind == 'tools'
      ? '${a['name']} (${a['tool_code']})'
      : '${a['name']} (${a['number_plate']})';

  String _id(Map<String, dynamic> a) =>
      (_kind == 'tools' ? a['tool_id'] : a['vehicle_id']) as String;

  Future<void> _submit() async {
    if (_assetId == null || _purpose.text.trim().length < 3) {
      setState(
        () => _error = 'Pilih aset dan isi tujuan (minimal 3 karakter).',
      );
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
          .requestLoan(
            assetType: _kind == 'tools' ? 'TOOL' : 'VEHICLE',
            assetId: _assetId!,
            purpose: _purpose.text.trim(),
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
    return Padding(
      padding: EdgeInsets.fromLTRB(
        16,
        16,
        16,
        MediaQuery.of(context).viewInsets.bottom + 16,
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'tools', label: Text('Alat')),
                ButtonSegment(value: 'vehicles', label: Text('Kendaraan')),
              ],
              selected: {_kind},
              onSelectionChanged: (s) {
                setState(() => _kind = s.first);
                _loadAssets();
              },
            ),
            const SizedBox(height: 8),
            if (_loadingAssets)
              const Padding(
                padding: EdgeInsets.all(16),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_assets.isEmpty)
              const Padding(
                padding: EdgeInsets.all(8),
                child: Text('Tidak ada aset yang tersedia.'),
              )
            else
              DropdownButtonFormField<String>(
                initialValue: _assetId,
                isExpanded: true,
                decoration: const InputDecoration(labelText: 'Aset'),
                items: [
                  for (final a in _assets)
                    DropdownMenuItem(value: _id(a), child: Text(_label(a))),
                ],
                onChanged: (v) => setState(() => _assetId = v),
              ),
            const SizedBox(height: 8),
            TextField(
            maxLength: 500,
              controller: _purpose,
              maxLines: 2,
              decoration: const InputDecoration(labelText: 'Tujuan penggunaan'),
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(_error!, style: const TextStyle(color: Colors.red)),
              ),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: _busy ? null : _submit,
              child: Text(_busy ? 'Mengirim...' : 'Kirim pengajuan'),
            ),
          ],
        ),
      ),
    );
  }
}

class _ReturnSheet extends ConsumerStatefulWidget {
  const _ReturnSheet({required this.loan});
  final Map<String, dynamic> loan;

  @override
  ConsumerState<_ReturnSheet> createState() => _ReturnSheetState();
}

class _ReturnSheetState extends ConsumerState<_ReturnSheet> {
  String _condition = 'ready';
  final _note = TextEditingController();
  String? _photoPath;
  bool _busy = false;
  String? _error;
  dynamic _photo;

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  Future<void> _takePhoto() async {
    final (file, err) = await captureWatermarkedPhoto(
      context: context,
      label: 'Foto kondisi aset',
      hint: 'Foto aset yang dikembalikan agar kondisinya terlihat jelas.',
    );
    if (!mounted) return;
    if (file != null) {
      setState(() {
        _photo = file;
        _photoPath = file.path;
        _error = null;
      });
    } else if (err != null) {
      setState(() => _error = err);
    }
  }

  Future<void> _submit() async {
    if (_photo == null) {
      setState(() => _error = 'Foto kondisi wajib diambil dengan kamera.');
      return;
    }
    if (!await confirmAction(
      context,
      title: 'Ajukan pengembalian?',
      message: 'HR/GA akan memeriksa foto dan kondisi aset sebelum pengembalian diterima.',
      confirmLabel: 'Ajukan pengembalian',
    )) {
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final api = ref.read(syncEngineProvider).api;
      final fileId = await api.uploadFile(_photo);
      await api.requestReturn(
        assignmentId: widget.loan['assignment_id'] as String,
        condition: _condition,
        photoFileId: fileId,
        note: _note.text.trim(),
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
    return Padding(
      padding: EdgeInsets.fromLTRB(
        16,
        16,
        16,
        MediaQuery.of(context).viewInsets.bottom + 16,
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Kembalikan ${widget.loan['asset_name']}',
              style: VmsTextStyles.bodySm.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              initialValue: _condition,
              decoration: const InputDecoration(labelText: 'Kondisi'),
              items: [
                for (final e in _conditions.entries)
                  DropdownMenuItem(value: e.key, child: Text(e.value)),
              ],
              onChanged: (v) => setState(() => _condition = v ?? _condition),
            ),
            const SizedBox(height: 8),
            TextField(
            maxLength: 500,
              controller: _note,
              maxLines: 2,
              decoration: const InputDecoration(
                labelText: 'Catatan (opsional)',
              ),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: _busy ? null : _takePhoto,
              icon: const Icon(Icons.photo_camera_rounded),
              label: Text(
                _photoPath == null ? 'Ambil foto kondisi' : 'Ambil ulang foto',
              ),
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(_error!, style: const TextStyle(color: Colors.red)),
              ),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: _busy ? null : _submit,
              child: Text(_busy ? 'Mengirim...' : 'Ajukan pengembalian'),
            ),
          ],
        ),
      ),
    );
  }
}
