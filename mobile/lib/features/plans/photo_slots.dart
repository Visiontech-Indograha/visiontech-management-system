import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/gallery_save.dart';
import '../../core/local_storage.dart';
import '../../core/photo_capture.dart';
import '../../core/providers.dart';
import '../../core/theme/theme.dart';
import '../../shared/ui/vms_ui.dart';
import '../gallery/photo_gallery_screen.dart';

/// Asal foto laporan: kamera aplikasi (bertanda air), galeri HP, atau galeri foto di dalam aplikasi.
enum PhotoOrigin { camera, phoneGallery, appGallery }

/// Foto yang baru diambil/dipilih dan belum diunggah: jalur berkas, slot template (null = "Foto lain"), sumber.
class PendingPhoto {
  const PendingPhoto({required this.path, this.slot, required this.source});
  final String path;
  final String? slot;
  final String source; // CAMERA | GALLERY
}

/// Ambil foto laporan: kamera aplikasi (bertanda air) atau galeri HP (diunggah apa adanya; server yang mengompresi).
/// Mengembalikan null bila dibatalkan; pesan galat lewat [onError].
Future<PendingPhoto?> pickReportPhoto({
  required BuildContext context,
  required String? slot,
  required PhotoOrigin origin,
  String? hint,
  required void Function(String message) onError,
}) async {
  if (origin == PhotoOrigin.phoneGallery) {
    final picked = await ImagePicker().pickImage(source: ImageSource.gallery);
    return picked == null ? null : PendingPhoto(path: picked.path, slot: slot, source: 'GALLERY');
  }
  if (origin == PhotoOrigin.appGallery) {
    // Foto lama dari kamera aplikasi: sumbernya tetap CAMERA (bertanda air).
    final path = await Navigator.of(context).push<String>(
      MaterialPageRoute(builder: (_) => const PhotoGalleryScreen(selectMode: true)),
    );
    return path == null ? null : PendingPhoto(path: path, slot: slot, source: 'CAMERA');
  }
  final (file, err) = await captureWatermarkedPhoto(
    context: context,
    label: slot ?? 'Foto bukti',
    kind: LocalFileKind.dailyReport,
    hint: hint ?? 'Foto hasil pekerjaan hari ini',
  );
  if (file == null) {
    if (err != null) onError(err);
    return null;
  }
  // T10: foto laporan dari kamera ikut tampil di album "Visiontech" galeri HP (galat tidak menggagalkan apa pun).
  unawaited(saveToPhoneGallery(file.path));
  return PendingPhoto(path: file.path, slot: slot, source: 'CAMERA');
}

/// Kartu foto per slot template (label, petunjuk, tanda wajib) + bagian "Foto lain". Tiap kartu: Kamera dan Galeri.
class PhotoSlots extends StatelessWidget {
  const PhotoSlots({
    super.key,
    required this.template,
    required this.saved,
    required this.pending,
    required this.enabled,
    required this.onAdd,
    required this.onRemove,
  });

  /// Slot template rencana kerja: `{label, hint, required}`; kosong → hanya "Foto lain".
  final List<Map<String, dynamic>> template;

  /// Bukti yang sudah tersimpan di server: `{file_id, slot_label, source}`.
  final List<Map<String, dynamic>> saved;
  final List<PendingPhoto> pending;
  final bool enabled;
  final void Function(String? slot, PhotoOrigin origin) onAdd;
  final void Function(PendingPhoto photo) onRemove;

  /// Label slot wajib yang belum punya foto (tersimpan maupun baru).
  static List<String> missingRequired(
    List<Map<String, dynamic>> template,
    List<Map<String, dynamic>> saved,
    List<PendingPhoto> pending,
  ) => [
    for (final s in template)
      if (s['required'] == true &&
          !saved.any((e) => e['slot_label'] == s['label']) &&
          !pending.any((p) => p.slot == s['label']))
        '${s['label']}',
  ];

  int _count(String? slot) =>
      saved.where((e) => (e['slot_label'] as String?) == slot).length +
      pending.where((p) => p.slot == slot).length;

  @override
  Widget build(BuildContext context) {
    final slots = <String?>[for (final s in template) s['label'] as String, null];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final slot in slots)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: SurfaceCard(
              key: Key('photo-slot-${slot ?? 'other'}'),
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          slot ?? 'Foto lain',
                          style: VmsTextStyles.bodySm.copyWith(fontWeight: FontWeight.w700),
                        ),
                      ),
                      if (slot != null && _isRequired(slot))
                        Text(
                          'Wajib',
                          style: VmsTextStyles.caption.copyWith(color: Accent.rose.strong),
                        ),
                    ],
                  ),
                  if (slot != null && _hint(slot) != null)
                    Text(_hint(slot)!, style: VmsTextStyles.caption),
                  if (slot != null && _example(slot) != null) ExampleThumb(fileId: _example(slot)!, label: slot),
                  const SizedBox(height: 6),
                  Text('${_count(slot)} foto', style: VmsTextStyles.caption),
                  for (final p in pending.where((p) => p.slot == slot))
                    ListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      leading: ClipRRect(
                        borderRadius: BorderRadius.circular(6),
                        child: Image.file(File(p.path), width: 40, height: 40, fit: BoxFit.cover),
                      ),
                      title: Text(p.source == 'GALLERY' ? 'Dari galeri (belum diunggah)' : 'Kamera (belum diunggah)'),
                      trailing: enabled
                          ? IconButton(
                              tooltip: 'Buang foto',
                              icon: const Icon(Icons.close_rounded),
                              onPressed: () => onRemove(p),
                            )
                          : null,
                    ),
                  if (enabled)
                    Row(
                      children: [
                        TextButton.icon(
                          key: Key('photo-camera-${slot ?? 'other'}'),
                          onPressed: () => onAdd(slot, PhotoOrigin.camera),
                          icon: const Icon(Icons.add_a_photo_rounded),
                          label: const Text('Kamera'),
                        ),
                        TextButton.icon(
                          key: Key('photo-gallery-${slot ?? 'other'}'),
                          onPressed: () => onAdd(slot, PhotoOrigin.phoneGallery),
                          icon: const Icon(Icons.photo_library_rounded),
                          label: const Text('Galeri'),
                        ),
                        TextButton.icon(
                          key: Key('photo-app-${slot ?? 'other'}'),
                          onPressed: () => onAdd(slot, PhotoOrigin.appGallery),
                          icon: const Icon(Icons.collections_rounded),
                          label: const Text('Foto saya'),
                        ),
                      ],
                    ),
                ],
              ),
            ),
          ),
      ],
    );
  }

  String? _example(String slot) {
    final id = template.where((s) => s['label'] == slot).firstOrNull?['example_file_id'];
    return id == null || '$id'.isEmpty ? null : '$id';
  }

  bool _isRequired(String slot) => template.any((s) => s['label'] == slot && s['required'] == true);

  String? _hint(String slot) {
    final h = template.where((s) => s['label'] == slot).firstOrNull?['hint'];
    return h == null || '$h'.isEmpty ? null : '$h';
  }
}

/// Foto contoh dari PM untuk satu slot: thumbnail kecil; ketuk = pratinjau besar yang bisa di-zoom.
class ExampleThumb extends ConsumerStatefulWidget {
  const ExampleThumb({super.key, required this.fileId, required this.label});
  final String fileId;
  final String label;

  @override
  ConsumerState<ExampleThumb> createState() => _ExampleThumbState();
}

class _ExampleThumbState extends ConsumerState<ExampleThumb> {
  late final Future<String> _url = ref.read(syncEngineProvider).api.fileUrl(widget.fileId);

  void _preview(String url) => showDialog<void>(
    context: context,
    builder: (ctx) => Dialog(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: Text('Contoh: ${widget.label}', style: VmsTextStyles.bodySm.copyWith(fontWeight: FontWeight.w700)),
          ),
          Flexible(child: InteractiveViewer(child: Image.network(url, fit: BoxFit.contain))),
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Tutup')),
        ],
      ),
    ),
  );

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 6),
    child: FutureBuilder<String>(
      future: _url,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const SizedBox(height: 72, child: Center(child: CircularProgressIndicator(strokeWidth: 2)));
        }
        if (snap.hasError || snap.data == null) {
          return Text('Foto contoh tidak dapat dimuat.', style: VmsTextStyles.caption);
        }
        final url = snap.data!;
        return Row(
          children: [
            InkWell(
              key: Key('example-${widget.fileId}'),
              onTap: () => _preview(url),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: Image.network(url, width: 72, height: 72, fit: BoxFit.cover,
                    errorBuilder: (_, _, _) => const SizedBox(width: 72, height: 72, child: Icon(Icons.broken_image_outlined))),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(child: Text('Contoh foto dari PM. Ketuk untuk memperbesar.', style: VmsTextStyles.caption)),
          ],
        );
      },
    ),
  );
}
