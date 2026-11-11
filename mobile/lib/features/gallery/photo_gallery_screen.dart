import 'dart:io';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/gallery_save.dart';
import '../../core/local_storage.dart';
import '../../core/photo_capture.dart';
import '../../shared/ui/vms_list_filter.dart';
import '../../shared/ui/vms_ui.dart';
import '../notifications/notifications_screen.dart' show NotificationBell;
import 'team_logo_screen.dart';

final _stamp = DateFormat('d MMM yyyy, HH.mm', 'id_ID');

/// Galeri foto laporan di dalam aplikasi (T10): grid foto lokal `LocalFileKind.dailyReport`, terbaru dulu.
/// Ketuk = pratinjau. Dalam mode pilih ([selectMode]) ketukan mengembalikan jalur berkas untuk dilampirkan.
/// Swafoto absen tidak pernah tampil di sini (folder terpisah dan privat).
class PhotoGalleryScreen extends StatefulWidget {
  const PhotoGalleryScreen({super.key, this.selectMode = false, this.asTab = false});
  final bool selectMode;

  /// Tab di navbar: tanpa tombol kembali.
  final bool asTab;

  @override
  State<PhotoGalleryScreen> createState() => _PhotoGalleryScreenState();
}

class _PhotoGalleryScreenState extends State<PhotoGalleryScreen> {
  List<File> _files = [];
  bool _loading = true;
  String? _error;
  final _query = ListQuery(pageSize: 60);

  List<File> get _filtered => _query.filter<File>(
    _files,
    (f) => [f.uri.pathSegments.last],
    chipTest: (f, chip) {
      final days = chip == 'today' ? 1 : 7;
      return DateTime.now().difference(f.lastModifiedSync()).inDays < days;
    },
  );

  @override
  void dispose() {
    _query.dispose();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    _query.addListener(() {
      if (mounted) setState(() {});
    });
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final dir = await visiontechFolder(LocalFileKind.dailyReport);
      final files =
          dir
              .listSync()
              .whereType<File>()
              .where((f) => RegExp(r'\.(jpe?g|png)$', caseSensitive: false).hasMatch(f.path))
              .toList()
            ..sort((a, b) => b.lastModifiedSync().compareTo(a.lastModifiedSync()));
      if (mounted) setState(() => _files = files);
    } catch (e) {
      if (mounted) setState(() => _error = 'Galeri tidak dapat dibuka: $e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  /// Ambil foto baru lewat kamera aplikasi (bertanda air); tersimpan di galeri ini dan album "Visiontech".
  Future<void> _capture() async {
    final (file, err) = await captureWatermarkedPhoto(
      context: context,
      label: 'Foto baru',
      kind: LocalFileKind.dailyReport,
      hint: 'Foto hasil pekerjaan',
    );
    if (file == null) {
      if (err != null && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(err)));
      }
      return;
    }
    try {
      await saveToPhoneGallery(file.path);
    } catch (e) {
      if (mounted) {
        final msg = e is GallerySaveException ? e.message : 'Foto gagal disimpan ke galeri HP.';
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
      }
    }
    await _load();
  }

  Future<void> _delete(File file) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Hapus foto ini?'),
        content: const Text(
          'Foto dihapus dari galeri aplikasi dan album Visiontech di HP. Foto yang sudah diunggah ke laporan tidak terpengaruh.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Batal')),
          TextButton(
            key: const Key('gallery-delete-confirm'),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Hapus'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await deleteFromPhoneGallery(file.path);
      await file.delete();
    } catch (e) {
      if (mounted) {
        final msg = e is GallerySaveException ? e.message : 'Foto tidak dapat dihapus.';
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
      }
    }
    await _load();
  }

  Future<void> _open(File file) async {
    if (widget.selectMode) {
      Navigator.of(context).pop(file.path);
      return;
    }
    await showDialog<void>(
      context: context,
      builder: (ctx) => Dialog(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            InteractiveViewer(child: Image.file(file)),
            Padding(padding: const EdgeInsets.all(8), child: Text(_stamp.format(file.lastModifiedSync()))),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Tutup')),
                TextButton.icon(
                  key: const Key('gallery-delete'),
                  onPressed: () {
                    Navigator.pop(ctx);
                    _delete(file);
                  },
                  icon: const Icon(Icons.delete_outline_rounded),
                  label: const Text('Hapus'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    floatingActionButton: widget.selectMode
        ? null
        : FloatingActionButton.extended(
            key: const Key('gallery-capture'),
            onPressed: _capture,
            icon: const Icon(Icons.add_a_photo_rounded),
            label: const Text('Ambil foto'),
          ),
    appBar: VmsTopBar(
      onBack: widget.asTab ? null : () => Navigator.of(context).maybePop(),
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (!widget.selectMode)
            Semantics(
              label: 'Logo tim',
              button: true,
              child: TextButton.icon(
                key: const Key('gallery-team-logo'),
                style: TextButton.styleFrom(minimumSize: const Size(48, 48)),
                icon: const Icon(Icons.groups_2_outlined),
                label: const Text('Logo tim'),
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const TeamLogoScreen()),
                ),
              ),
            ),
          if (widget.asTab) const NotificationBell(),
        ],
      ),
    ),
    body: _loading
        ? const Center(child: CircularProgressIndicator())
        : _error != null
        ? Center(
            child: Padding(padding: const EdgeInsets.all(24), child: Text(_error!)),
          )
        : _files.isEmpty
        ? const EmptyState(
            icon: Icons.photo_library_outlined,
            title: 'Belum ada foto laporan',
            message: 'Ketuk "Ambil foto" atau foto lewat kamera aplikasi; hasilnya tersimpan di sini.',
          )
        : Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
                child: VmsSearchBar(
                  query: _query,
                  hint: 'Cari nama berkas foto...',
                  chips: const [
                    VmsFilterOption('', 'Semua'),
                    VmsFilterOption('today', 'Hari ini'),
                    VmsFilterOption('week', '7 hari'),
                  ],
                ),
              ),
              Expanded(
                child: _filtered.isEmpty
                    ? VmsNoMatch(query: _query)
                    : RefreshIndicator(
            onRefresh: _load,
            child: GridView.builder(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(12, 12, 12, 88),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 3,
                mainAxisSpacing: 8,
                crossAxisSpacing: 8,
              ),
              itemCount: _query.visible(_filtered).length,
              itemBuilder: (_, i) {
                final f = _query.visible(_filtered)[i];
                return InkWell(
                  key: Key('gallery-photo-$i'),
                  onTap: () => _open(f),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: Image.file(f, fit: BoxFit.cover, cacheWidth: 300),
                  ),
                );
              },
            ),
          ),
              ),
              if (_filtered.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(bottom: 72),
                  child: VmsLoadMore(query: _query, total: _filtered.length, noun: 'foto'),
                ),
            ],
          ),
  );
}
