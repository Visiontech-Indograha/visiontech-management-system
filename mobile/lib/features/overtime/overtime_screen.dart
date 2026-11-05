import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/api_client.dart';
import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../core/theme/theme.dart';
import '../../shared/ui/vms_ui.dart';

final _tanggal = DateFormat('d MMM yyyy', 'id_ID');

/// Label status lembur untuk layar. API memakai `PENDING_PM` untuk menunggu persetujuan.
String overtimeStatusLabel(String status) => switch (status) {
  'PENDING_PM' || 'PENDING' => 'Menunggu persetujuan',
  'APPROVED' => 'Disetujui',
  'REJECTED' => 'Ditolak',
  _ => 'Status belum diketahui',
};

String _jam(num h) => h % 1 == 0 ? h.toInt().toString() : h.toString();

String _tanggalLembur(dynamic iso) =>
    iso is String ? _tanggal.format(DateTime.parse(iso)) : '-';

/// Pesan galat untuk keputusan lembur. Persetujuan tidak diantrikan offline,
/// jadi saat tidak ada koneksi pengguna diberi tahu dengan jelas.
String _pesanKeputusan(Object e) {
  if (e is DioException && isNetworkFailure(e)) {
    return 'Persetujuan lembur hanya bisa dikirim saat HP terhubung ke internet. Coba lagi saat ada sinyal.';
  }
  return apiErrorMessage(e, fallback: 'Keputusan lembur gagal dikirim. Coba lagi.');
}

/// Riwayat lembur. Karyawan melihat pengajuannya sendiri; atasan yang berwenang
/// (`can_review` dari API) juga bisa menyetujui atau menolak pengajuan tim.
/// Pengajuan baru dibuat dari jadwal kerja harian (offline-first lewat antrean sinkron).
class OvertimeScreen extends ConsumerStatefulWidget {
  const OvertimeScreen({super.key});

  @override
  ConsumerState<OvertimeScreen> createState() => _OvertimeScreenState();
}

class _OvertimeScreenState extends ConsumerState<OvertimeScreen> {
  List<Map<String, dynamic>> _items = [];
  bool _memuat = true;
  String? _galatMuat;
  String? _galatKeputusan;
  final Set<String> _sedang = {};

  @override
  void initState() {
    super.initState();
    _muat();
  }

  Future<void> _muat() async {
    setState(() {
      _memuat = true;
      _galatMuat = null;
    });
    try {
      final items = await ref.read(syncEngineProvider).api.myOvertime();
      if (!mounted) return;
      setState(() {
        _items = items;
        _memuat = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _galatMuat = apiErrorMessage(e, fallback: 'Riwayat lembur belum bisa dimuat.');
        _memuat = false;
      });
    }
  }

  Future<void> _putuskan(Map<String, dynamic> o, {required bool setujui}) async {
    final id = o['id'] as String;
    final ringkas = '${o['employee_name'] ?? ''} · ${_tanggalLembur(o['work_date'])} · ${_jam(o['hours'] as num)} jam';
    final catatan = await showDialog<String>(
      context: context,
      builder: (_) => _DialogKeputusan(setujui: setujui, ringkas: ringkas),
    );
    if (catatan == null || !mounted) return; // dibatalkan

    setState(() {
      _sedang.add(id);
      _galatKeputusan = null;
    });
    try {
      final hasil = await ref
          .read(syncEngineProvider)
          .api
          .reviewOvertime(
            id: id,
            decision: setujui ? 'APPROVED' : 'REJECTED',
            note: catatan.isEmpty ? null : catatan,
          );
      if (!mounted) return;
      setState(() {
        _items = [
          for (final it in _items)
            if (it['id'] == id) {...it, ...hasil, 'can_review': false} else it,
        ];
        _sedang.remove(id);
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(setujui ? 'Lembur disetujui.' : 'Lembur ditolak.')),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _sedang.remove(id);
        _galatKeputusan = _pesanKeputusan(e);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: VmsTopBar(onBack: () => context.pop()),
      body: RefreshIndicator(
        onRefresh: _muat,
        child: ListView(
          padding: safeListPadding(context).add(const EdgeInsets.symmetric(horizontal: kListGutter)),
          children: [
            const HeroHeader(eyebrow: 'Layanan', title: 'Riwayat Lembur', horizontal: 4),
            ..._isi(),
          ],
        ),
      ),
    );
  }

  List<Widget> _isi() {
    // Memuat (belum ada data).
    if (_memuat && _items.isEmpty) {
      return const [
        Padding(
          padding: EdgeInsets.all(32),
          child: Center(child: CircularProgressIndicator()),
        ),
      ];
    }
    // Galat tanpa data.
    if (_galatMuat != null && _items.isEmpty) {
      return [
        EmptyState(icon: Icons.cloud_off_rounded, title: _galatMuat!, message: 'Tarik layar ke bawah untuk mencoba lagi.'),
        const SizedBox(height: 12),
        _tombolCobaLagi(),
      ];
    }
    // Kosong.
    if (_items.isEmpty) {
      return const [
        EmptyState(
          icon: Icons.more_time_rounded,
          title: 'Belum ada lembur',
          message: 'Ajukan lembur dari tab Jadwal kerja: buka jadwal hari ini, lalu tekan Ajukan lembur.',
        ),
      ];
    }
    // Berhasil, atau sebagian (data lama tampil bersama peringatan galat).
    return [
      if (_galatMuat != null)
        Padding(
          padding: const EdgeInsets.only(top: 12),
          child: NoticeBanner(icon: Icons.wifi_off_rounded, text: '$_galatMuat Menampilkan data terakhir.'),
        ),
      if (_galatKeputusan != null)
        Padding(
          padding: const EdgeInsets.only(top: 12),
          child: NoticeBanner(icon: Icons.error_outline_rounded, text: _galatKeputusan!),
        ),
      for (final o in _items)
        Padding(padding: const EdgeInsets.only(top: 12), child: _kartu(o)),
    ];
  }

  Widget _tombolCobaLagi() => SizedBox(
    height: 48,
    child: FilledButton(
      onPressed: _memuat ? null : _muat,
      child: const Text('Coba lagi'),
    ),
  );

  Widget _kartu(Map<String, dynamic> o) {
    final id = o['id'] as String;
    final sedang = _sedang.contains(id);
    final bisaPutus = o['can_review'] == true;
    final nama = o['employee_name'] as String?;
    final status = o['status'] as String? ?? '';
    final catatanTinjau = o['review_note'] as String?;

    return SurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (nama != null && nama.isNotEmpty)
            Text(nama, style: VmsTextStyles.bodySm.copyWith(fontWeight: FontWeight.w700)),
          Text(
            '${_tanggalLembur(o['work_date'])} · ${_jam(o['hours'] as num)} jam',
            style: VmsTextStyles.bodySm.copyWith(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 4),
          Text(o['reason'] as String? ?? '', style: VmsTextStyles.bodySm),
          const SizedBox(height: 8),
          StatusPill(status, label: overtimeStatusLabel(status)),
          if (catatanTinjau != null && catatanTinjau.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text('Catatan: $catatanTinjau', style: VmsTextStyles.bodySm),
            ),
          if (bisaPutus) ...[
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: SizedBox(
                    height: 48,
                    child: OutlinedButton(
                      onPressed: sedang ? null : () => _putuskan(o, setujui: false),
                      child: const Text('Tolak'),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: SizedBox(
                    height: 48,
                    child: FilledButton(
                      onPressed: sedang ? null : () => _putuskan(o, setujui: true),
                      child: const Text('Setujui'),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

/// Konfirmasi keputusan lembur. Mengembalikan catatan (boleh kosong), atau null bila dibatalkan.
class _DialogKeputusan extends StatefulWidget {
  const _DialogKeputusan({required this.setujui, required this.ringkas});

  final bool setujui;
  final String ringkas;

  @override
  State<_DialogKeputusan> createState() => _DialogKeputusanState();
}

class _DialogKeputusanState extends State<_DialogKeputusan> {
  final _catatan = TextEditingController();

  @override
  void dispose() {
    _catatan.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(widget.setujui ? 'Setujui lembur ini?' : 'Tolak lembur ini?'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(widget.ringkas),
          const SizedBox(height: 12),
          TextField(
            controller: _catatan,
            maxLength: 1000,
            minLines: 1,
            maxLines: 3,
            decoration: const InputDecoration(labelText: 'Catatan (boleh dikosongkan)'),
          ),
        ],
      ),
      actions: [
        SizedBox(
          height: 48,
          child: TextButton(onPressed: () => Navigator.pop(context), child: const Text('Batal')),
        ),
        SizedBox(
          height: 48,
          child: FilledButton(
            onPressed: () => Navigator.pop(context, _catatan.text.trim()),
            child: Text(widget.setujui ? 'Setujui' : 'Tolak'),
          ),
        ),
      ],
    );
  }
}
