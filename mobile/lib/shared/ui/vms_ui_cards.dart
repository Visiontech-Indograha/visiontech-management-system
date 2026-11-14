part of 'vms_ui.dart';

/// True bila widget berada di dalam kartu sorotan navy — komponen kit menyesuaikan warnanya.
bool onHighlight(BuildContext context) => context.dependOnInheritedWidgetOfExactType<_HighlightScope>() != null;

class _HighlightScope extends InheritedWidget {
  const _HighlightScope({required super.child});
  @override
  bool updateShouldNotify(_HighlightScope oldWidget) => false;
}

/// Lengkung emas dekoratif meniru "swirl" pada logo Visiontech.
class _SwirlPainter extends CustomPainter {
  const _SwirlPainter();
  @override
  void paint(Canvas canvas, Size size) {
    final c = Offset(size.width + 10, -20);
    final p = Paint()
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawArc(
      Rect.fromCircle(center: c, radius: 96),
      math.pi * 0.52,
      math.pi * 0.62,
      false,
      p
        ..color = VmsColors.gold
        ..strokeWidth = 5,
    );
    canvas.drawArc(
      Rect.fromCircle(center: c, radius: 124),
      math.pi * 0.56,
      math.pi * 0.5,
      false,
      p
        ..color = VmsColors.gold.withValues(alpha: 0.35)
        ..strokeWidth = 3,
    );
  }

  @override
  bool shouldRepaint(_SwirlPainter oldDelegate) => false;
}

/// Kartu permukaan: putih, sudut 22, garis tipis, tanpa bayangan berat. `highlight` = kartu sorotan
/// navy (warna utama logo) dengan lengkung emas seperti swirl logo — satu per layar.
/// `accent` = garis tipis berwarna di kiri.
class SurfaceCard extends StatelessWidget {
  const SurfaceCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.onTap,
    this.accent,
    this.highlight = false,
  });
  final Widget child;
  final EdgeInsetsGeometry padding;
  final VoidCallback? onTap;
  final Color? accent;
  final bool highlight;
  @override
  Widget build(BuildContext context) {
    final card = Container(
      decoration: BoxDecoration(
        color: highlight ? VmsColors.brand800 : VmsColors.neutral0,
        borderRadius: BorderRadius.circular(highlight ? 26 : 22),
        border: highlight ? null : Border.all(color: VmsColors.neutral200),
      ),
      clipBehavior: Clip.antiAlias,
      child: highlight
          ? CustomPaint(
              painter: const _SwirlPainter(),
              child: _HighlightScope(
                child: Padding(padding: padding, child: child),
              ),
            )
          : accent == null
          ? Padding(padding: padding, child: child)
          : IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Container(width: 4, color: accent),
                  Expanded(
                    child: Padding(padding: padding, child: child),
                  ),
                ],
              ),
            ),
    );
    return onTap == null ? card : Pressable(onTap: onTap, child: card);
  }
}

/// Lingkaran ikon berwarna (latar lembut + ikon warna kuat).
class IconTile extends StatelessWidget {
  const IconTile({super.key, required this.icon, required this.accent, this.size = 44});
  final IconData icon;
  final Accent accent;
  final double size;
  @override
  Widget build(BuildContext context) {
    final hl = onHighlight(context);
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(color: hl ? Colors.white.withValues(alpha: 0.12) : accent.soft, shape: BoxShape.circle),
      child: Icon(icon, color: hl ? VmsColors.gold : accent.strong, size: size * 0.48),
    );
  }
}

/// Judul bagian dengan aksi opsional di kanan.
class SectionTitle extends StatelessWidget {
  const SectionTitle(this.text, {super.key, this.trailing});
  final String text;
  final Widget? trailing;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(4, 20, 4, 10),
    child: Row(
      children: [
        Expanded(
          child: Text(
            text,
            style: VmsTextStyles.heading.copyWith(fontWeight: FontWeight.w700, color: VmsColors.neutral900),
          ),
        ),
        ?trailing,
      ],
    ),
  );
}

/// Label & warna status domain (SK, laporan, absensi) — satu sumber untuk seluruh aplikasi.
({String label, Accent accent}) statusStyle(String? status) => switch (status) {
  'DRAFT' => (label: 'Draf', accent: Accent.slate),
  'PUBLISHED' => (label: 'Terbit', accent: Accent.blue),
  'ACCEPTED' => (label: 'Diterima', accent: Accent.indigo),
  'APPEALED' => (label: 'Revisi diminta', accent: Accent.amber),
  'IN_PROGRESS' => (label: 'Berjalan', accent: Accent.blue),
  'ITEM_IN_PROGRESS' => (label: 'Sedang dikerjakan', accent: Accent.blue),
  'ITEM_PARTIAL' => (label: 'Belum selesai', accent: Accent.amber),
  'COMPLETION_REVIEW' || 'COMPLETION_REQUESTED' => (label: 'Pengajuan penutupan', accent: Accent.violet),
  'COMPLETED' => (label: 'Selesai', accent: Accent.emerald),
  'CANCELLED' => (label: 'Dibatalkan', accent: Accent.rose),
  'SUBMITTED' => (label: 'Dikirim', accent: Accent.amber),
  'RESUBMITTED' => (label: 'Dikirim ulang', accent: Accent.amber),
  'SENT' => (label: 'Terkirim ke ketua', accent: Accent.emerald),
  // Dokumen SK (alur SK v2).
  'AWAITING_ACCEPTANCE' => (label: 'Menunggu tanda tangan', accent: Accent.amber),
  'EFFECTIVE' => (label: 'Berlaku', accent: Accent.emerald),
  'SUPERSEDED' => (label: 'Tidak berlaku', accent: Accent.slate),
  'APPROVED' => (label: 'Disetujui', accent: Accent.emerald),
  'CHANGES_REQUESTED' => (label: 'Perlu perbaikan', accent: Accent.rose),
  'AUTO_VALID' => (label: 'Valid', accent: Accent.emerald),
  'NEEDS_REVIEW' => (label: 'Perlu ditinjau', accent: Accent.amber),
  'REJECTED' => (label: 'Ditolak', accent: Accent.rose),
  // Jadwal harian & item per titik (V2, daily-first).
  'ONGOING' => (label: 'Berjalan', accent: Accent.blue),
  'TODO' => (label: 'Belum mulai', accent: Accent.slate),
  'DONE' => (label: 'Selesai', accent: Accent.emerald),
  'LATE' => (label: 'Terlambat', accent: Accent.rose),
  'PARTIAL' => (label: 'Selesai sebagian', accent: Accent.yellow),
  'PENDING_ROLLOVER' => (label: 'Minta pindah hari', accent: Accent.amber),
  'SHIFTED_DAY' => (label: 'Pindah hari', accent: Accent.violet),
  // R-34: absen offline yang belum terkirim ke server.
  'OFFLINE' => (label: 'Tersimpan offline', accent: Accent.indigo),
  null => (label: 'Belum ada', accent: Accent.slate),
  _ => (label: status, accent: Accent.slate),
};

/// Chip status berbentuk pil terisi.
class StatusPill extends StatelessWidget {
  const StatusPill(this.status, {super.key, this.label});
  final String? status;

  /// Label pengganti (mis. "Disetujui PM"); warna tetap dari kode [status].
  final String? label;
  @override
  Widget build(BuildContext context) {
    final s = statusStyle(status);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(color: s.accent.soft, borderRadius: BorderRadius.circular(99)),
      child: Text(
        label ?? s.label,
        style: VmsTextStyles.caption.copyWith(color: s.accent.strong, fontWeight: FontWeight.w700),
      ),
    );
  }
}

/// Baris info: ikon kecil + teks redup.
class InfoRow extends StatelessWidget {
  const InfoRow({super.key, required this.icon, required this.text});
  final IconData icon;
  final String text;
  @override
  Widget build(BuildContext context) {
    final color = onHighlight(context) ? Colors.white.withValues(alpha: 0.78) : VmsColors.neutral600;
    return Row(
      children: [
        Icon(icon, size: 16, color: color),
        const SizedBox(width: 6),
        Expanded(
          child: Text(
            text,
            style: VmsTextStyles.bodySm.copyWith(color: color),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
}

/// Ubin aksi cepat bergaris: ikon di atas, label di bawah.
class ActionTile extends StatelessWidget {
  const ActionTile({super.key, required this.icon, required this.label, required this.accent, required this.onTap});
  final IconData icon;
  final String label;
  final Accent accent;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) => Pressable(
    onTap: onTap,
    child: Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
      decoration: BoxDecoration(
        color: VmsColors.neutral0,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: VmsColors.neutral200),
      ),
      child: Column(
        children: [
          IconTile(icon: icon, accent: accent, size: 40),
          const SizedBox(height: 8),
          Text(
            label,
            textAlign: TextAlign.center,
            style: VmsTextStyles.bodySm.copyWith(fontWeight: FontWeight.w700, color: VmsColors.neutral900),
          ),
        ],
      ),
    ),
  );
}
