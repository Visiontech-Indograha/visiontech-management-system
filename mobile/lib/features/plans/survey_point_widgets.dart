part of 'survey_point_screen.dart';

/// Satu baris slot foto (nama, petunjuk, contoh, foto yang sudah ada, tombol tambah).
class _SlotRow extends StatelessWidget {
  const _SlotRow({
    required this.slot,
    required this.photos,
    required this.edit,
    required this.onAdd,
    required this.onRemove,
  });
  final Map<String, dynamic> slot;
  final List<_Photo> photos;
  final bool edit;
  final void Function(PhotoOrigin origin) onAdd;
  final void Function(_Photo photo) onRemove;

  @override
  Widget build(BuildContext context) {
    final reqId = '${slot['requirement_id']}';
    final mine = photos.where((p) => p.requirementId == reqId).toList();
    final mandatory = slot['mandatory'] == true;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text('${slot['name']}', style: Theme.of(context).textTheme.titleSmall)),
              if (mandatory)
                Text(
                  mine.isEmpty ? 'Wajib' : '✓',
                  style: TextStyle(color: mine.isEmpty ? Accent.rose.strong : Colors.green),
                ),
            ],
          ),
          if (slot['hint'] != null) Text('${slot['hint']}', style: Theme.of(context).textTheme.bodySmall),
          if (slot['example_file_id'] != null) ...[
            const SizedBox(height: 6),
            ExampleThumb(fileId: '${slot['example_file_id']}', label: '${slot['name']}'),
          ],
          const SizedBox(height: 6),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final p in mine) _photoTile(p),
              if (mine.isEmpty && !edit)
                Container(
                  height: 56,
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  decoration: BoxDecoration(
                    color: Colors.black12.withValues(alpha: 0.05),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.black26),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.image_not_supported_outlined, size: 20, color: Colors.black45),
                      const SizedBox(width: 8),
                      Text('Tidak ada foto', style: Theme.of(context).textTheme.bodySmall),
                    ],
                  ),
                ),
              if (edit) ...[
                _AddTile(
                  icon: Icons.photo_camera_rounded,
                  label: 'Kamera',
                  onTap: () => onAdd(PhotoOrigin.camera),
                ),
                _AddTile(
                  icon: Icons.photo_library_rounded,
                  label: 'Galeri',
                  onTap: () => onAdd(PhotoOrigin.phoneGallery),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }

  Widget _photoTile(_Photo p) {
    final Widget image = p.path != null
        ? Image.file(File(p.path!), fit: BoxFit.cover)
        : VmsNetworkImage(fileId: p.fileId!);
    return Stack(
      children: [
        Container(
          width: 96,
          height: 96,
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(10), color: Colors.black12),
          clipBehavior: Clip.antiAlias,
          child: image,
        ),
        if (edit)
          Positioned(
            right: 2,
            top: 2,
            child: InkWell(
              onTap: () => onRemove(p),
              child: const CircleAvatar(
                radius: 11,
                backgroundColor: Colors.black54,
                child: Icon(Icons.close, size: 14, color: Colors.white),
              ),
            ),
          ),
      ],
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.number, required this.title, required this.child, this.subtitle});
  final int number;
  final String title;
  final String? subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: SurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              CircleAvatar(radius: 12, child: Text('$number', style: const TextStyle(fontSize: 12))),
              const SizedBox(width: 8),
              Expanded(child: Text(title, style: Theme.of(context).textTheme.titleMedium)),
            ],
          ),
          if (subtitle != null) ...[
            const SizedBox(height: 4),
            Text(subtitle!, style: Theme.of(context).textTheme.bodySmall),
          ],
          const SizedBox(height: 10),
          child,
        ],
      ),
    ),
  );
}

class _AddTile extends StatelessWidget {
  const _AddTile({required this.icon, required this.label, required this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
    onTap: onTap,
    borderRadius: BorderRadius.circular(10),
    child: Container(
      width: 96,
      height: 96,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(fontSize: 12)),
        ],
      ),
    ),
  );
}

/// Lembar pemilih material: cari di katalog work type, atau pakai teks yang diketik sebagai material baru.
