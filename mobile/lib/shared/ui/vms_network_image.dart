import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';

/// URL berkas yang sudah diminta, dipakai ulang selama tiketnya masih berlaku. Server menerbitkan URL yang sama
/// dalam satu jendela waktu, sehingga cache gambar Flutter (memori) memakai ulang gambar yang sudah diunduh.
final Map<String, ({DateTime at, Future<String> url})> _urlCache = {};
const Duration _urlTtl = Duration(minutes: 20);

Future<String> _cachedUrl(WidgetRef ref, String fileId, String variant) {
  final key = '$fileId|$variant';
  final hit = _urlCache[key];
  if (hit != null && DateTime.now().difference(hit.at) < _urlTtl) return hit.url;
  final url = ref.read(syncEngineProvider).api.fileUrl(fileId, variant: variant);
  _urlCache[key] = (at: DateTime.now(), url: url);
  // Permintaan gagal tidak disimpan agar bisa dicoba lagi.
  url.catchError((Object _) {
    _urlCache.remove(key);
    return '';
  });
  return url;
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
    return FutureBuilder<String>(
      future: _cachedUrl(ref, fileId, variant),
      builder: (_, s) => s.hasData && s.data!.isNotEmpty
          ? Image.network(s.data!, fit: fit, gaplessPlayback: true, errorBuilder: (_, _, _) => broken)
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
