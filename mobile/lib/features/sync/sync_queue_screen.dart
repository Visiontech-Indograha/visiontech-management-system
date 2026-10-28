import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../data/app_database.dart';
import '../../data/sync_engine.dart';

/// Daftar isi antrian sinkronisasi, beserta jalan keluarnya.
///
/// Sebelum layar ini ada, satu item yang gagal permanen tidak punya penyelesaian
/// sama sekali: user hanya melihat angka "N foto menunggu upload" yang tidak
/// pernah hilang, dan satu-satunya cara membersihkannya adalah menghapus data
/// aplikasi -- yang ikut membuang SELURUH antrian lain yang masih sah.
class SyncQueueScreen extends ConsumerStatefulWidget {
  const SyncQueueScreen({super.key});

  @override
  ConsumerState<SyncQueueScreen> createState() => _SyncQueueScreenState();
}

class _SyncQueueScreenState extends ConsumerState<SyncQueueScreen> {
  List<PendingSyncRow> _operations = const [];
  List<PendingAttachmentRow> _photos = const [];
  bool _loading = true;

  static const _entityLabels = OfflineOp.labels;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final engine = ref.read(syncEngineProvider);
    final operations = await engine.allPendingOperations();
    final photos = await engine.allPendingAttachments();
    if (!mounted) return;
    setState(() {
      _operations = operations;
      _photos = photos;
      _loading = false;
    });
  }

  Future<void> _syncNow() async {
    setState(() => _loading = true);
    await ref.read(syncEngineProvider).syncAll(manual: true);
    await _load();
  }

  Future<bool> _confirmDelete(String what) async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Hapus dari antrian?'),
        content: Text(
          '$what akan dibuang permanen dari HP dan TIDAK akan pernah terkirim ke server. '
          'Lakukan ini hanya kalau Anda memang tidak butuh data tersebut.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Batal'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Hapus'),
          ),
        ],
      ),
    );
    return yes ?? false;
  }

  String _describeOperation(PendingSyncRow row) {
    final label = _entityLabels[row.entityType] ?? row.entityType;
    try {
      final payload = jsonDecode(row.payloadJson) as Map<String, dynamic>;
      final waktu = payload['client_created_at'];
      final parsed = waktu is String
          ? DateTime.tryParse(waktu)?.toLocal()
          : null;
      if (parsed != null) {
        final tanggal =
            '${parsed.day.toString().padLeft(2, '0')}/'
            '${parsed.month.toString().padLeft(2, '0')}/${parsed.year}';
        return '$label — $tanggal';
      }
    } catch (_) {
      // Payload tidak terbaca: label saja sudah cukup informatif.
    }
    return label;
  }

  @override
  Widget build(BuildContext context) {
    final total = _operations.length + _photos.length;
    return Scaffold(
      appBar: AppBar(title: const Text('Antrian Sinkronisasi')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  if (total == 0)
                    const Card(
                      child: ListTile(
                        leading: Icon(Icons.check_circle_outline),
                        title: Text('Semua data sudah terkirim'),
                        subtitle: Text('Tidak ada yang menunggu di antrian.'),
                      ),
                    )
                  else
                    Text(
                      'Data di bawah ini dibuat di HP dan belum sampai ke server. '
                      'Yang bertanda "berhenti dicoba" butuh keputusan Anda.',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  const SizedBox(height: 12),
                  for (final row in _operations)
                    _QueueTile(
                      icon: Icons.description_outlined,
                      title: _describeOperation(row),
                      attemptCount: row.attemptCount,
                      lastError: row.lastError,
                      deadLetter: row.deadLetter,
                      onRetry: () async {
                        await ref
                            .read(syncEngineProvider)
                            .retryOperation(row.id);
                        await _load();
                      },
                      onDelete: () async {
                        if (!await _confirmDelete(_describeOperation(row))) {
                          return;
                        }
                        await ref
                            .read(syncEngineProvider)
                            .deleteOperation(row.id);
                        await _load();
                      },
                    ),
                  for (final row in _photos)
                    _QueueTile(
                      icon: Icons.photo_camera_outlined,
                      title: 'Foto: ${row.label}',
                      attemptCount: row.attemptCount,
                      lastError: row.lastError,
                      deadLetter: row.deadLetter,
                      onRetry: () async {
                        await ref
                            .read(syncEngineProvider)
                            .retryAttachment(row.id);
                        await _load();
                      },
                      onDelete: () async {
                        if (!await _confirmDelete('Foto ${row.label}')) return;
                        await ref
                            .read(syncEngineProvider)
                            .deleteAttachment(row.id);
                        await _load();
                      },
                    ),
                  const SizedBox(height: 16),
                  FilledButton.icon(
                    onPressed: _syncNow,
                    icon: const Icon(Icons.sync),
                    label: const Text('Coba Kirim Semua Sekarang'),
                  ),
                ],
              ),
            ),
    );
  }
}

class _QueueTile extends StatelessWidget {
  const _QueueTile({
    required this.icon,
    required this.title,
    required this.attemptCount,
    required this.lastError,
    required this.deadLetter,
    required this.onRetry,
    required this.onDelete,
  });

  final IconData icon;
  final String title;
  final int attemptCount;
  final String? lastError;
  final bool deadLetter;
  final Future<void> Function() onRetry;
  final Future<void> Function() onDelete;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  icon,
                  size: 20,
                  color: deadLetter ? scheme.error : scheme.primary,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    title,
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              deadLetter
                  ? 'Berhenti dicoba otomatis setelah $attemptCount percobaan.'
                  : attemptCount == 0
                  ? 'Menunggu dikirim otomatis saat ada sinyal.'
                  : 'Sudah dicoba $attemptCount kali, akan dicoba lagi otomatis.',
              style: Theme.of(context).textTheme.bodySmall
                  ?.copyWith(color: deadLetter ? scheme.error : null),
            ),
            if (lastError != null) ...[
              const SizedBox(height: 4),
              Text(
                'Alasan: $lastError',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                if (deadLetter)
                  TextButton.icon(
                    onPressed: onRetry,
                    icon: const Icon(Icons.refresh, size: 18),
                    label: const Text('Coba Lagi'),
                  ),
                TextButton.icon(
                  onPressed: onDelete,
                  icon: Icon(
                    Icons.delete_outline,
                    size: 18,
                    color: scheme.error,
                  ),
                  label: Text('Hapus', style: TextStyle(color: scheme.error)),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
