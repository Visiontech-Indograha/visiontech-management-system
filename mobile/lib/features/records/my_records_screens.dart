import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../core/theme/theme.dart';
import '../../shared/ui/vms_ui.dart';
import '../auth/auth_controller.dart';
import '../auth/auth_state.dart';

final _date = DateFormat('d MMM yyyy', 'id_ID');

String _fmt(dynamic iso) => iso == null ? '-' : _date.format(DateTime.parse(iso as String));

/// Label status lembur untuk karyawan.
String overtimeStatusLabel(String status) => switch (status) {
  'PENDING' => 'Menunggu persetujuan',
  'APPROVED' => 'Disetujui',
  'REJECTED' => 'Ditolak',
  _ => status,
};

/// Label status dokumen pribadi menurut masa berlakunya.
/// Nama jenis dokumen yang ramah dibaca (sama dengan web); jenis lain ditampilkan apa adanya.
String documentTypeLabel(String type) => switch (type) {
  'KTP' => 'KTP',
  'SIM_A' => 'SIM A',
  'SIM_B1' => 'SIM B I',
  'SIM_B2' => 'SIM B II',
  'SIM_C' => 'SIM C',
  'MCU' => 'Medical check-up',
  'SERTIFIKAT_K3' => 'Sertifikat K3',
  'SERTIFIKAT_TEKNIS' => 'Sertifikat teknis',
  'KONTRAK_PKWT' => 'Kontrak PKWT',
  _ => type.replaceAll('_', ' '),
};

String documentStatusLabel(String status) => switch (status) {
  'active' => 'Berlaku',
  'extended' => 'Diperpanjang',
  'expired' => 'Kedaluwarsa',
  _ => status,
};

/// Dokumen yang akan habis dalam [days] hari (atau sudah lewat) perlu diperingatkan.
bool documentExpiresSoon(Map<String, dynamic> doc, DateTime today, {int days = 30}) {
  final raw = doc['expired_at'] as String?;
  if (raw == null || doc['status'] != 'active') return false;
  final left = DateTime.parse(raw).difference(DateTime(today.year, today.month, today.day)).inDays;
  return left <= days;
}

/// Kerangka layar daftar sederhana: judul, muat ulang, kosong/galat, lalu isi.
class _ListScreen extends ConsumerStatefulWidget {
  const _ListScreen({
    required this.title,
    required this.empty,
    required this.load,
    required this.builder,
  });

  final String title;
  final String empty;
  final Future<List<Map<String, dynamic>>> Function(WidgetRef ref) load;
  final Widget Function(Map<String, dynamic> item) builder;

  @override
  ConsumerState<_ListScreen> createState() => _ListScreenState();
}

class _ListScreenState extends ConsumerState<_ListScreen> {
  List<Map<String, dynamic>> _items = [];
  bool _loading = true;
  String? _error;

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
      final items = await widget.load(ref);
      if (!mounted) return;
      setState(() {
        _items = items;
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: VmsTopBar(onBack: () => context.pop()),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: ListView(
          padding: safeListPadding(context).add(const EdgeInsets.symmetric(horizontal: kListGutter)),
          children: [
            HeroHeader(eyebrow: 'Layanan', title: widget.title, horizontal: 4),
            if (_loading)
              const Padding(padding: EdgeInsets.all(32), child: Center(child: CircularProgressIndicator())),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.all(16),
                child: Text(_error!, style: const TextStyle(color: Colors.red)),
              ),
            if (!_loading && _error == null && _items.isEmpty)
              Padding(padding: const EdgeInsets.all(32), child: Center(child: Text(widget.empty))),
            for (final item in _items)
              Padding(padding: const EdgeInsets.only(top: 12), child: widget.builder(item)),
          ],
        ),
      ),
    );
  }
}

String _employeeId(WidgetRef ref) {
  final s = ref.read(authControllerProvider);
  return s is AuthAuthenticated ? s.user.employeeId : '';
}

/// Riwayat dan status pengajuan lembur milik sendiri.
class OvertimeHistoryScreen extends StatelessWidget {
  const OvertimeHistoryScreen({super.key});

  @override
  Widget build(BuildContext context) => _ListScreen(
    title: 'Riwayat Lembur',
    empty: 'Belum ada pengajuan lembur.',
    load: (ref) => ref.read(syncEngineProvider).api.myOvertime(),
    builder: (o) => SurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '${_fmt(o['work_date'])} · ${o['hours']} jam',
            style: VmsTextStyles.bodySm.copyWith(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 4),
          Text(o['reason'] as String? ?? '', style: VmsTextStyles.bodySm),
          const SizedBox(height: 8),
          Chip(label: Text(overtimeStatusLabel(o['status'] as String))),
          if ((o['review_note'] as String?)?.isNotEmpty == true)
            Text('Catatan: ${o['review_note']}', style: VmsTextStyles.bodySm),
        ],
      ),
    ),
  );
}

/// Dokumen pribadi (SIM, sertifikat, dll.) beserta masa berlakunya.
class DocumentsScreen extends StatelessWidget {
  const DocumentsScreen({super.key});

  @override
  Widget build(BuildContext context) => _ListScreen(
    title: 'Dokumen Saya',
    empty: 'Belum ada dokumen yang tercatat.',
    load: (ref) => ref.read(syncEngineProvider).api.myDocuments(_employeeId(ref)),
    builder: (d) {
      final soon = documentExpiresSoon(d, DateTime.now());
      return SurfaceCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              documentTypeLabel(d['doc_type'] as String),
              style: VmsTextStyles.bodySm.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 4),
            Text(
              d['expired_at'] == null
                  ? 'Berlaku sejak ${_fmt(d['active_at'])}'
                  : 'Berlaku ${_fmt(d['active_at'])} s.d. ${_fmt(d['expired_at'])}',
              style: VmsTextStyles.bodySm,
            ),
            if (d['file_id'] != null) ...[const SizedBox(height: 8), _DocumentFile(fileId: d['file_id'] as String)],
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                Chip(label: Text(documentStatusLabel(d['status'] as String))),
                if (soon) const Chip(label: Text('Segera habis')),
              ],
            ),
          ],
        ),
      );
    },
  );
}

/// Pratinjau berkas dokumen (foto) dari server; ketuk untuk memperbesar. Berkas non-gambar (PDF) tampil sebagai ikon.
class _DocumentFile extends ConsumerWidget {
  const _DocumentFile({required this.fileId});
  final String fileId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    const fallback = Center(child: Icon(Icons.description_rounded, size: 36, color: Colors.black38));
    Widget image(String variant, BoxFit fit) => FutureBuilder<String>(
      future: ref.read(syncEngineProvider).api.fileUrl(fileId, variant: variant),
      builder: (_, s) => s.hasData
          ? Image.network(s.data!, fit: fit, errorBuilder: (_, _, _) => fallback)
          : s.hasError
          ? fallback
          : const Center(child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))),
    );
    return InkWell(
      onTap: () => showDialog<void>(
        context: context,
        builder: (_) => Dialog(
          clipBehavior: Clip.antiAlias,
          child: InteractiveViewer(child: SizedBox(height: 420, child: image('view', BoxFit.contain))),
        ),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: Container(
          height: 120,
          width: double.infinity,
          color: Colors.black.withValues(alpha: 0.05),
          child: image('thumb', BoxFit.cover),
        ),
      ),
    );
  }
}
