import 'dart:io';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/gallery_save.dart';
import '../../core/local_storage.dart';
import '../../core/photo_capture.dart';
import '../../shared/ui/vms_ui.dart';

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
      final dir = await visiontechFolder(LocalFileKind.dailyReport);
      final files = dir
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
    await saveToPhoneGallery(file.path);
    await _load();
  }

  Future<void> _delete(File file) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Hapus foto ini?'),
        content: const Text('Foto dihapus dari galeri aplikasi dan album Visiontech di HP. Foto yang sudah diunggah ke laporan tidak terpengaruh.'),
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
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Foto tidak dapat dihapus: $e')));
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
            Padding(
              padding: const EdgeInsets.all(8),
              child: Text(_stamp.format(file.lastModifiedSync())),
            ),
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
      trailing: HeaderAction(icon: Icons.refresh_rounded, tooltip: 'Muat ulang', onTap: _load),
    ),
    body: _loading
        ? const Center(child: CircularProgressIndicator())
        : _error != null
        ? Center(child: Padding(padding: const EdgeInsets.all(24), child: Text(_error!)))
        : _files.isEmpty
        ? const EmptyState(
            icon: Icons.photo_library_outlined,
            title: 'Belum ada foto laporan',
            message: 'Ketuk "Ambil foto" atau foto lewat kamera aplikasi; hasilnya tersimpan di sini.',
          )
        : GridView.builder(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 88),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 3,
              mainAxisSpacing: 8,
              crossAxisSpacing: 8,
            ),
            itemCount: _files.length,
            itemBuilder: (_, i) => InkWell(
              key: Key('gallery-photo-$i'),
              onTap: () => _open(_files[i]),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: Image.file(_files[i], fit: BoxFit.cover, cacheWidth: 300),
              ),
            ),
          ),
  );
}
