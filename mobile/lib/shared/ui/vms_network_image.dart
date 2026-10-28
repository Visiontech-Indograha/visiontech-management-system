import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/providers.dart';

/// Berkas gambar yang sudah dimuat, dipakai ulang di memori dan disimpan di cache disk aplikasi
/// (kunci = id berkas + varian; isi berkas tidak berubah per id), sehingga gambar yang sama tidak diunduh lagi.
final Map<String, Future<File>> _files = {};

Future<File> _cachedFile(WidgetRef ref, String fileId, String variant) {
  final key = '${fileId}_$variant';
  return _files.putIfAbsent(key, () async {
    final dir = Directory('${(await getTemporaryDirectory()).path}/vms_img');
    final file = File('${dir.path}/$key');
    if (await file.exists() && await file.length() > 0) return file;
    final bytes = await ref.read(syncEngineProvider).api.fileBytes(fileId, variant: variant);
    await dir.create(recursive: true);
    await file.writeAsBytes(bytes, flush: true);
    return file;
  })
    // Permintaan gagal tidak disimpan agar bisa dicoba lagi.
    ..catchError((Object _) {
      _files.remove(key);
      return File('');
    });
}

/// Gambar dari berkas server (id berkas + varian) dengan penampung, ikon galat, dan cache URL.
class VmsNetworkImage extends ConsumerWidget {
  const VmsNetworkImage({
    super.key,
    required this.fileId,
    this.variant = 'thumb',
    this.fit = BoxFit.cover,
    this.fallback,
  });

  final String fileId;
  final String variant;
  final BoxFit fit;
  final Widget? fallback;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final broken = fallback ?? const Center(child: Icon(Icons.broken_image_outlined, color: Colors.black38));
    return FutureBuilder<File>(
      future: _cachedFile(ref, fileId, variant),
      builder: (_, s) => s.hasData
          ? Image.file(s.data!, fit: fit, gaplessPlayback: true, errorBuilder: (_, _, _) => broken)
          : s.hasError
          ? broken
          : const Center(child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))),
    );
  }
}

/// Avatar bulat: foto profil bila ada, selain itu inisial nama.
class VmsAvatar extends StatelessWidget {
  const VmsAvatar({super.key, required this.name, this.fileId, this.radius = 20});

  final String? name;
  final String? fileId;
  final double radius;

  static String initials(String? name) {
    final parts = (name ?? '').trim().split(RegExp(r'\s+')).where((p) => p.isNotEmpty).toList();
    if (parts.isEmpty) return '?';
    final first = parts.first.characters.first;
    final last = parts.length > 1 ? parts.last.characters.first : '';
    return '$first$last'.toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final text = Center(
      child: Text(
        initials(name),
        style: TextStyle(color: scheme.onPrimaryContainer, fontWeight: FontWeight.w600, fontSize: radius * 0.7),
      ),
    );
    return Container(
      width: radius * 2,
      height: radius * 2,
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(shape: BoxShape.circle, color: scheme.primaryContainer),
      child: fileId == null || fileId!.isEmpty
          ? text
          : VmsNetworkImage(fileId: fileId!, variant: radius > 28 ? 'view' : 'thumb', fallback: text),
    );
  }
}

/// Membuka gambar layar penuh yang bisa dicubit untuk memperbesar.
Future<void> showVmsImageViewer(BuildContext context, String fileId) => showDialog<void>(
  context: context,
  builder: (_) => Dialog(
    clipBehavior: Clip.antiAlias,
    child: InteractiveViewer(
      child: SizedBox(height: 420, child: VmsNetworkImage(fileId: fileId, variant: 'view', fit: BoxFit.contain)),
    ),
  ),
);
