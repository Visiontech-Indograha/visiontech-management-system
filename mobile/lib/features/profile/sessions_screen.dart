import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../core/theme/theme.dart';
import '../../shared/ui/vms_ui.dart';

/// Daftar perangkat yang sedang masuk ke akun ini. Perlu internet.
class SessionsScreen extends ConsumerStatefulWidget {
  const SessionsScreen({super.key});

  @override
  ConsumerState<SessionsScreen> createState() => _SessionsScreenState();
}

class _SessionsScreenState extends ConsumerState<SessionsScreen> {
  List<Map<String, dynamic>> _items = const [];
  bool _loading = true;
  bool _busy = false;
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
      final items = await ref.read(syncEngineProvider).api.authSessions();
      if (mounted) setState(() => _items = items);
    } catch (e) {
      if (mounted) {
        setState(() => _error = 'Tidak bisa memuat daftar perangkat. Pastikan HP tersambung internet, lalu coba lagi.\n(${apiErrorMessage(e)})');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String _fmt(dynamic iso) {
    final d = DateTime.tryParse('${iso ?? ''}')?.toLocal();
    return d == null ? '-' : DateFormat('d MMM yyyy, HH:mm').format(d);
  }

  Future<bool> _confirm(String title, String message, String action) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Batal')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: Text(action)),
        ],
      ),
    );
    return ok == true;
  }

  Future<void> _run(Future<void> Function() job, String okMsg) async {
    setState(() => _busy = true);
    try {
      await job();
      if (mounted) showVmsToast(context, okMsg);
      await _load();
    } catch (e) {
      if (mounted) showVmsToast(context, apiErrorMessage(e), error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _revoke(Map<String, dynamic> s) async {
    final label = (s['device_label'] ?? 'perangkat ini') as String;
    if (!await _confirm('Keluarkan perangkat?', '"$label" akan keluar dari akun Anda dan harus masuk lagi.', 'Keluarkan')) return;
    await _run(() => ref.read(syncEngineProvider).api.revokeAuthSession('${s['id']}'), 'Perangkat dikeluarkan.');
  }

  Future<void> _revokeOthers() async {
    if (!await _confirm('Keluarkan semua perangkat lain?', 'Semua perangkat selain HP ini akan keluar dari akun Anda.', 'Keluarkan semua')) return;
    await _run(() => ref.read(syncEngineProvider).api.revokeOtherAuthSessions(), 'Semua perangkat lain dikeluarkan.');
  }

  @override
  Widget build(BuildContext context) {
    final others = _items.where((s) => s['current'] != true).length;
    return Scaffold(
      appBar: AppBar(title: const Text('Perangkat yang masuk')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: _loading
            ? ListView(children: const [SizedBox(height: 200), Center(child: CircularProgressIndicator())])
            : _error != null
            ? ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  EmptyState(icon: Icons.wifi_off_rounded, title: 'Perlu internet', message: _error, accent: Accent.amber),
                  OutlinedButton.icon(onPressed: _load, icon: const Icon(Icons.refresh_rounded), label: const Text('Coba lagi')),
                ],
              )
            : ListView(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
                children: [
                  if (_items.isEmpty)
                    const EmptyState(icon: Icons.devices_rounded, title: 'Belum ada perangkat'),
                  for (final s in _items) ...[
                    SurfaceCard(
                      padding: const EdgeInsets.all(14),
                      child: Row(
                        children: [
                          IconTile(
                            icon: Icons.smartphone_rounded,
                            accent: s['current'] == true ? Accent.emerald : Accent.blue,
                            size: 40,
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('${s['device_label'] ?? s['user_agent'] ?? 'Perangkat tidak dikenal'}', style: VmsTextStyles.subheading),
                                if (s['current'] == true)
                                  Text('Perangkat ini', style: VmsTextStyles.caption.copyWith(color: VmsColors.brand700, fontWeight: FontWeight.w700)),
                                Text('Terakhir dipakai: ${_fmt(s['last_used_at'])}', style: VmsTextStyles.caption),
                                if (s['ip_address'] != null) Text('Alamat: ${s['ip_address']}', style: VmsTextStyles.caption),
                              ],
                            ),
                          ),
                          if (s['current'] != true)
                            TextButton(onPressed: _busy ? null : () => _revoke(s), child: const Text('Cabut')),
                        ],
                      ),
                    ),
                    const SizedBox(height: 8),
                  ],
                  if (others > 0) ...[
                    const SizedBox(height: 8),
                    OutlinedButton.icon(
                      onPressed: _busy ? null : _revokeOthers,
                      icon: const Icon(Icons.logout_rounded),
                      label: const Text('Keluarkan semua perangkat lain'),
                    ),
                  ],
                ],
              ),
      ),
    );
  }
}
