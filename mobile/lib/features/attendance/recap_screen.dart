import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../core/theme/theme.dart';
import '../../shared/ui/vms_network_image.dart';
import '../../shared/ui/vms_ui.dart';

final _rupiah = NumberFormat.currency(
  locale: 'id_ID',
  symbol: 'Rp ',
  decimalDigits: 0,
);
final _day = DateFormat('EEE, d MMM', 'id_ID');
final _hour = DateFormat('HH.mm');

/// Bulan sebelumnya/berikutnya dalam format YYYY-MM (aritmatika kalender, bukan tanggal HP).
String shiftMonth(String month, int delta) {
  final year = int.parse(month.substring(0, 4));
  final mon = int.parse(month.substring(5, 7));
  final index = year * 12 + (mon - 1) + delta;
  final y = index ~/ 12;
  final m = index % 12 + 1;
  return '${y.toString().padLeft(4, '0')}-${m.toString().padLeft(2, '0')}';
}

class RecapScreen extends ConsumerStatefulWidget {
  const RecapScreen({super.key, this.initialMonth});

  /// Bulan awal (YYYY-MM); kosong = bulan berjalan menurut server.
  final String? initialMonth;

  @override
  ConsumerState<RecapScreen> createState() => _RecapScreenState();
}

class _RecapScreenState extends ConsumerState<RecapScreen> {
  String? _month;
  Map<String, dynamic>? _data;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _month = widget.initialMonth;
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = ref.read(syncEngineProvider).api;
      final data = await api.myRecap(
        _month ?? DateFormat('yyyy-MM').format(DateTime.now()),
      );
      if (!mounted) return;
      setState(() {
        _data = data;
        _month = data['month'] as String;
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

  void _go(int delta) {
    if (_month == null) return;
    _month = shiftMonth(_month!, delta);
    _load();
  }

  @override
  Widget build(BuildContext context) {
    final data = _data;
    final items =
        (data?['items'] as List?)?.cast<Map<String, dynamic>>() ?? const [];
    return Scaffold(
      appBar: VmsTopBar(onBack: () => context.pop()),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: safeListPadding(context).add(const EdgeInsets.symmetric(horizontal: kListGutter)),
          children: [
            const HeroHeader(eyebrow: 'Absensi', title: 'Rekap Bulanan', horizontal: 4),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                IconButton(
                  tooltip: 'Bulan sebelumnya',
                  onPressed: _loading ? null : () => _go(-1),
                  icon: const Icon(Icons.chevron_left_rounded),
                ),
                Text(
                  _month == null
                      ? '-'
                      : DateFormat(
                          'MMMM yyyy',
                          'id_ID',
                        ).format(DateTime.parse('$_month-01')),
                  style: VmsTextStyles.bodySm.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                IconButton(
                  tooltip: 'Bulan berikutnya',
                  onPressed: _loading ? null : () => _go(1),
                  icon: const Icon(Icons.chevron_right_rounded),
                ),
              ],
            ),
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
            if (data != null && !_loading) ...[
              SurfaceCard(
                child: Wrap(
                  alignment: WrapAlignment.spaceAround,
                  runSpacing: 12,
                  spacing: 24,
                  children: [
                    _stat('Hadir', '${data['days_present']}'),
                    _stat('Terlambat', '${data['late_days']}'),
                    _stat('Pulang awal', '${data['early_leave_days']}'),
                    _stat('Menunggu', '${data['pending_days']}'),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              SurfaceCard(
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Uang makan (absensi sah)',
                      style: VmsTextStyles.bodySm,
                    ),
                    Text(
                      _rupiah.format(
                        (data['meal_allowance_total'] as num).toDouble(),
                      ),
                      style: VmsTextStyles.bodySm.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ],
                ),
              ),
              if (items.isEmpty)
                const Padding(
                  padding: EdgeInsets.all(32),
                  child: Center(child: Text('Belum ada absensi bulan ini.')),
                ),
              for (final i in items) _row(i),
            ],
          ],
        ),
      ),
    );
  }

  Widget _stat(String label, String value) => Column(
    children: [
      Text(
        value,
        style: VmsTextStyles.bodySm.copyWith(
          fontSize: 22,
          fontWeight: FontWeight.w800,
        ),
      ),
      Text(label, style: VmsTextStyles.bodySm),
    ],
  );

  Widget _row(Map<String, dynamic> i) {
    final inAt = DateTime.parse(i['check_in_at'] as String).toLocal();
    final outRaw = i['check_out_at'] as String?;
    final outAt = outRaw == null ? null : DateTime.parse(outRaw).toLocal();
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: SurfaceCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                if (i['selfie_file_id'] != null) ...[
                  InkWell(
                    onTap: () => showVmsImageViewer(context, '${i['selfie_file_id']}'),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: SizedBox(
                        width: 48,
                        height: 48,
                        child: VmsNetworkImage(fileId: '${i['selfie_file_id']}'),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                ],
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _day.format(DateTime.parse(i['work_date'] as String)),
                        style: VmsTextStyles.bodySm.copyWith(fontWeight: FontWeight.w700),
                      ),
                      Text(
                        '${_hour.format(inAt)} - ${outAt == null ? '--.--' : _hour.format(outAt)}',
                        style: VmsTextStyles.bodySm,
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 8,
              children: [
                if (i['is_late'] == true) const Chip(label: Text('Terlambat')),
                if (i['is_early_leave'] == true)
                  const Chip(label: Text('Pulang awal')),
                if (i['is_pending'] == true)
                  const Chip(label: Text('Menunggu OM')),
                if (i['is_valid'] == true) const Chip(label: Text('Sah')),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
