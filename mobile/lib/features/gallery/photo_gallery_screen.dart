import 'dart:io';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/local_storage.dart';
import '../../shared/ui/vms_ui.dart';

final _stamp = DateFormat('d MMM yyyy, HH.mm', 'id_ID');

/// Galeri foto laporan di dalam aplikasi (T10): grid foto lokal `LocalFileKind.dailyReport`, terbaru dulu.
/// Ketuk = pratinjau. Dalam mode pilih ([selectMode]) ketukan mengembalikan jalur berkas untuk dilampirkan.
/// Swafoto absen tidak pernah tampil di sini (folder terpisah dan privat).
class PhotoGalleryScreen extends StatefulWidget {
  const PhotoGalleryScreen({super.key, this.selectMode = false});
  final bool selectMode;

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
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Tutup')),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: VmsTopBar(
      onBack: () => Navigator.of(context).maybePop(),
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
            message: 'Foto laporan yang diambil lewat kamera aplikasi tersimpan di sini.',
          )
        : GridView.builder(
            padding: const EdgeInsets.all(12),
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
