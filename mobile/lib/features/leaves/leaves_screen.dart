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

final _tgl = DateFormat('d MMM yyyy', 'id_ID');
final _iso = DateFormat('yyyy-MM-dd');

/// Label status cuti untuk karyawan (alur: PM lalu HR).
String leaveStatusLabel(String status) => switch (status) {
  'PENDING' => 'Menunggu PM',
  'APPROVED_BY_PM' => 'Disetujui PM, menunggu HR',
  'APPROVED_BY_HR' || 'APPROVED_BY_FINANCE' => 'Disetujui',
  'REJECTED' => 'Ditolak',
  'CANCELLED' => 'Dibatalkan',
  _ => status,
};

/// Cuti masih bisa dibatalkan pemohon selama belum final.
bool leaveCancellable(String status) =>
    status == 'PENDING' || status == 'APPROVED_BY_PM';

class LeavesScreen extends ConsumerStatefulWidget {
  const LeavesScreen({super.key});

  @override
  ConsumerState<LeavesScreen> createState() => _LeavesScreenState();
}

class _LeavesScreenState extends ConsumerState<LeavesScreen> {
  List<Map<String, dynamic>> _items = [];
  Map<String, dynamic>? _balance;
  bool _loading = true;
  String? _error;

  String get _employeeId {
    final s = ref.read(authControllerProvider);
    return s is AuthAuthenticated ? s.user.employeeId : '';
  }

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
      final items = await api.myLeaves(_employeeId);
      final balance = await api.leaveBalance(_employeeId);
      if (!mounted) return;
      setState(() {
        _items = items;
        _balance = balance;
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

  Future<void> _cancel(Map<String, dynamic> leave) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Batalkan pengajuan?'),
        content: const Text('Pengajuan cuti ini akan dibatalkan.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Tidak'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Batalkan'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await ref
          .read(syncEngineProvider)
          .api
          .cancelLeave(leave['leave_id'] as String);
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(apiErrorMessage(e))));
      }
    }
  }

  Future<void> _apply() async {
    final done = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (_) => const _ApplyLeaveSheet(),
    );
    if (done == true) await _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: VmsTopBar(onBack: () => context.pop()),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _apply,
        icon: const Icon(Icons.add_rounded),
        label: const Text('Ajukan cuti'),
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: safeListPadding(context).add(const EdgeInsets.symmetric(horizontal: kListGutter)),
          children: [
            const HeroHeader(eyebrow: 'Layanan', title: 'Cuti & Izin', horizontal: 4),
            if (_balance != null) _balanceCard(_balance!),
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
            if (!_loading && _error == null && _items.isEmpty)
              const Padding(
                padding: EdgeInsets.all(32),
                child: Center(child: Text('Belum ada pengajuan cuti.')),
              ),
            for (final l in _items) _leaveCard(l),
          ],
        ),
      ),
    );
  }

  Widget _balanceCard(Map<String, dynamic> b) => SurfaceCard(
    child: Row(
      mainAxisAlignment: MainAxisAlignment.spaceAround,
      children: [
        _stat('Kuota', '${b['total_quota']}'),
        _stat('Terpakai', '${b['used_quota']}'),
        _stat('Sisa', '${b['remaining_quota']}'),
      ],
    ),
  );

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

  Widget _leaveCard(Map<String, dynamic> l) {
    final status = l['status'] as String;
    final start = DateTime.parse(l['start_date'] as String);
    final end = DateTime.parse(l['end_date'] as String);
    final note = l['rejection_note'] as String?;
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: SurfaceCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${_tgl.format(start)} - ${_tgl.format(end)} (${l['total_days']} hari)',
              style: VmsTextStyles.bodySm.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 4),
            Text(l['reason'] as String? ?? '', style: VmsTextStyles.bodySm),
            const SizedBox(height: 8),
            Row(
              children: [
                Chip(label: Text(leaveStatusLabel(status))),
                const Spacer(),
                if (leaveCancellable(status))
                  TextButton(
                    onPressed: () => _cancel(l),
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

class _ApplyLeaveSheet extends ConsumerStatefulWidget {
  const _ApplyLeaveSheet();

  @override
  ConsumerState<_ApplyLeaveSheet> createState() => _ApplyLeaveSheetState();
}

class _ApplyLeaveSheetState extends ConsumerState<_ApplyLeaveSheet> {
  List<Map<String, dynamic>> _types = [];
  String _type = 'ANNUAL';
  DateTime? _start;
  DateTime? _end;
  final _reason = TextEditingController();
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    ref
        .read(syncEngineProvider)
        .api
        .leaveTypes()
        .then((t) {
          if (mounted) setState(() => _types = t);
        })
        .catchError((_) {});
  }

  @override
  void dispose() {
    _reason.dispose();
    super.dispose();
  }

  Future<void> _pick(bool start) async {
    final now = DateTime.now();
    final d = await showDatePicker(
      context: context,
      initialDate: (start ? _start : _end) ?? _start ?? now,
      firstDate: now.subtract(const Duration(days: 30)),
      lastDate: now.add(const Duration(days: 365)),
    );
    if (d == null) return;
    setState(() {
      if (start) {
        _error = null;
        _start = d;
        if (_end != null && _end!.isBefore(d)) _end = d;
      } else {
        _error = null;
        _end = d;
      }
    });
  }

  Future<void> _submit() async {
    if (_start == null || _end == null || _reason.text.trim().length < 3) {
      setState(
        () => _error = 'Lengkapi tanggal dan alasan (minimal 3 karakter).',
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
          .applyLeave(
            leaveType: _type,
            startDate: _iso.format(_start!),
            endDate: _iso.format(_end!),
            reason: _reason.text.trim(),
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
    final types = _types.isEmpty
        ? [
            {'code': 'ANNUAL', 'label': 'Cuti tahunan'},
            {'code': 'SICK', 'label': 'Sakit'},
          ]
        : _types;
    return Padding(
      padding: EdgeInsets.fromLTRB(
        16,
        16,
        16,
        MediaQuery.of(context).viewInsets.bottom + 16,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          DropdownButtonFormField<String>(
            initialValue: _type,
            decoration: const InputDecoration(labelText: 'Jenis'),
            items: [
              for (final t in types)
                DropdownMenuItem(
                  value: t['code'] as String,
                  child: Text(t['label'] as String),
                ),
            ],
            onChanged: (v) => setState(() => _type = v ?? _type),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () => _pick(true),
                  child: Text(_start == null ? 'Mulai' : _tgl.format(_start!)),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: OutlinedButton(
                  onPressed: () => _pick(false),
                  child: Text(_end == null ? 'Selesai' : _tgl.format(_end!)),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          TextField(
            maxLength: 1000,
            controller: _reason,
            onChanged: (_) {
              if (_error != null) setState(() => _error = null);
            },
            maxLines: 3,
            decoration: const InputDecoration(labelText: 'Alasan'),
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
    );
  }
}
