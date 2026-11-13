part of 'vms_ui.dart';

/// Keadaan kosong/galat yang ramah.
class EmptyState extends StatelessWidget {
  const EmptyState({super.key, required this.icon, required this.title, this.message, this.accent = Accent.indigo});
  final IconData icon;
  final String title;
  final String? message;
  final Accent accent;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 32, horizontal: 16),
    child: Column(
      children: [
        IconTile(icon: icon, accent: accent, size: 64),
        const SizedBox(height: 14),
        Text(
          title,
          textAlign: TextAlign.center,
          style: VmsTextStyles.subheading.copyWith(fontWeight: FontWeight.w700),
        ),
        if (message != null) ...[
          const SizedBox(height: 4),
          Text(
            message!,
            textAlign: TextAlign.center,
            style: VmsTextStyles.bodySm.copyWith(color: VmsColors.neutral500),
          ),
        ],
      ],
    ),
  );
}

/// Pita pemberitahuan (offline/galat).
class NoticeBanner extends StatelessWidget {
  const NoticeBanner({super.key, required this.icon, required this.text, this.accent = Accent.amber});
  final IconData icon;
  final String text;
  final Accent accent;
  @override
  Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.only(bottom: 12),
    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
    decoration: BoxDecoration(color: accent.soft, borderRadius: BorderRadius.circular(14)),
    child: Row(
      children: [
        Icon(icon, size: 18, color: accent.strong),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            text,
            style: VmsTextStyles.bodySm.copyWith(color: accent.strong, fontWeight: FontWeight.w600),
          ),
        ),
      ],
    ),
  );
}

/// Tombol utama besar bergradasi (aksi terpenting di layar), dengan efek tekan.
class PrimaryAction extends StatelessWidget {
  const PrimaryAction({
    super.key,
    required this.label,
    required this.icon,
    this.onTap,
    this.busy = false,
    this.accent,
    this.gold = false,
  });
  final String label;
  final IconData icon;
  final VoidCallback? onTap;
  final bool busy;
  final Accent? accent;

  /// Tombol emas bertulisan navy — untuk aksi utama di atas kartu sorotan navy.
  final bool gold;
  @override
  Widget build(BuildContext context) {
    final enabled = onTap != null && !busy;
    final color = gold ? VmsColors.gold : accent?.strong ?? VmsColors.brand700;
    final fg = gold ? VmsColors.brand900 : Colors.white;
    return Opacity(
      opacity: enabled ? 1 : 0.55,
      child: Pressable(
        onTap: enabled ? onTap : null,
        child: Container(
          height: 56,
          decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(18)),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (busy)
                SizedBox.square(dimension: 20, child: CircularProgressIndicator(strokeWidth: 2.4, color: fg))
              else
                Icon(icon, color: fg),
              const SizedBox(width: 10),
              Text(
                label,
                style: VmsTextStyles.subheading.copyWith(color: fg, fontWeight: FontWeight.w700),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Nama + tombol Telepon & WhatsApp (kontak PM ↔ ketua/anggota tim). Tanpa nomor → keterangan netral "nomor HP belum tercatat".
class ContactRow extends StatelessWidget {
  const ContactRow({super.key, required this.label, required this.name, this.phone});
  final String label;
  final String name;
  final String? phone;

  static String _wa(String phone) {
    final d = phone.replaceAll(RegExp(r'\D'), '');
    return d.startsWith('0') ? '62${d.substring(1)}' : d;
  }

  @override
  Widget build(BuildContext context) {
    final p = phone;
    return Row(
      children: [
        const Icon(Icons.contact_phone_outlined, size: 18),
        const SizedBox(width: 8),
        Expanded(
          child: Text.rich(
            TextSpan(
              children: [
                TextSpan(text: '$label: $name'),
                // Keterangan netral (bukan galat): nomor memang belum dicatat di data karyawan.
                if (p == null)
                  TextSpan(
                    text: ' · nomor HP belum tercatat',
                    style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant),
                  ),
              ],
            ),
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ),
        if (p != null) ...[
          IconButton(
            tooltip: 'Telepon $name',
            icon: const Icon(Icons.call_rounded),
            onPressed: () => launchUrl(Uri(scheme: 'tel', path: p.replaceAll(RegExp(r'[^\d+]'), ''))),
          ),
          IconButton(
            tooltip: 'WhatsApp $name',
            icon: const Icon(Icons.chat_rounded),
            onPressed: () => launchUrl(Uri.parse('https://wa.me/${_wa(p)}'), mode: LaunchMode.externalApplication),
          ),
        ],
      ],
    );
  }
}

/// Warna per jenis pekerjaan (sama dengan web).
const phaseAccent = <String, Accent>{
  'SURVEY': Accent.sky,
  'PREPARATION': Accent.slate,
  'INSTALLATION': Accent.emerald,
  'REPLACEMENT': Accent.amber,
  'MAINTENANCE': Accent.indigo,
};

/// Notifikasi singkat berwarna: hijau ✓ berhasil, merah ! gagal (muncul melayang dari bawah).
void showVmsToast(BuildContext context, String text, {bool error = false}) {
  final a = error ? Accent.rose : Accent.emerald;
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(
      SnackBar(
        backgroundColor: a.strong,
        duration: Duration(seconds: error ? 4 : 2),
        content: Row(
          children: [
            Icon(error ? Icons.error_outline_rounded : Icons.check_circle_rounded, color: Colors.white),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                text,
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
              ),
            ),
          ],
        ),
      ),
    );
}

/// Kerangka kartu berdenyut selama data dimuat (pengganti lingkaran putar).
class SkeletonCards extends StatefulWidget {
  const SkeletonCards({super.key, this.count = 3, this.height = 120});
  final int count;
  final double height;

  @override
  State<SkeletonCards> createState() => _SkeletonCardsState();
}

class _SkeletonCardsState extends State<SkeletonCards> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 900))
    ..repeat(reverse: true);

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => FadeTransition(
    opacity: Tween<double>(begin: 0.45, end: 1).animate(_c),
    child: Column(
      children: [
        for (var i = 0; i < widget.count; i++)
          Container(
            height: widget.height,
            margin: const EdgeInsets.only(bottom: 12),
            decoration: BoxDecoration(color: const Color(0xFFE6E9F0), borderRadius: BorderRadius.circular(18)),
          ),
      ],
    ),
  );
}
