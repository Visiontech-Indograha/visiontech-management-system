import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/theme/theme.dart';

/// Logo Visiontech transparan (latar terang) & versi putih (header gelap).
const logoAsset = 'assets/branding/logo_visiontech.png';
const logoWhiteAsset = 'assets/branding/logo_visiontech_white.png';

/// Tanda "V + swirl emas" di kanvas 288 dp — sama dengan ikon layar pembuka native.
const splashMarkAsset = 'assets/branding/splash_mark.png';

/// Kit UI mobile Visiontech (R-14). Gaya mengikuti rujukan Dribbble "Delivery Mobile App" (Ronas IT):
/// header terang dengan judul besar tebal, tombol bulat bergaris, kartu bergaris tipis tanpa bayangan
/// berat, satu kartu sorotan emas per layar, ubin aksi bergaris. Palet warna tetap milik Visiontech.
/// Efek tekan memantul & animasi masuk bertahap. Hanya transform/opacity (ringan),
/// dan patuh "kurangi gerakan" sistem (MediaQuery.disableAnimations).

/// Warna aksen per fitur — supaya layar tidak monoton. Teks di atas `soft` memakai `strong`.
class Accent {
  const Accent(this.strong, this.soft);
  final Color strong;
  final Color soft;

  static const blue = Accent(Color(0xFF2563EB), Color(0xFFE8F0FE));
  static const indigo = Accent(Color(0xFF4338CA), Color(0xFFEEF0FF));
  static const emerald = Accent(Color(0xFF047857), Color(0xFFE6F6EF));
  static const amber = Accent(Color(0xFFB45309), Color(0xFFFFF4E0));
  static const rose = Accent(Color(0xFFBE123C), Color(0xFFFFEBEF));
  static const violet = Accent(Color(0xFF6D28D9), Color(0xFFF3ECFF));
  static const teal = Accent(Color(0xFF0F766E), Color(0xFFE3F6F4));
  static const slate = Accent(Color(0xFF475467), Color(0xFFEEF0F4));
  static const sky = Accent(Color(0xFF0369A1), Color(0xFFE0F2FE));
  static const yellow = Accent(Color(0xFFA16207), Color(0xFFFEF9C3));
}

/// Safe zone (R-14): padding daftar yang menjauhkan konten dari area sistem — tepi bawah (bilah
/// gestur/navigasi yang disembunyikan), lekuk layar & notch di kiri/kanan. Atas diurus header/appBar.
EdgeInsets safeListPadding(BuildContext context, {double bottomGap = 24}) {
  final mq = MediaQuery.of(context);
  final bottom = math.max(mq.padding.bottom, mq.systemGestureInsets.bottom);
  return EdgeInsets.only(left: mq.padding.left, right: mq.padding.right, bottom: bottom + bottomGap);
}

bool _reduceMotion(BuildContext context) => MediaQuery.maybeDisableAnimationsOf(context) ?? false;

/// Header terang: baris atas (kembali/logo + aksi bulat bergaris), label kecil, lalu judul besar tebal.
/// Menyatu dengan latar halaman — tanpa gradasi.
class HeroHeader extends StatelessWidget {
  const HeroHeader({
    super.key,
    required this.title,
    this.eyebrow,
    this.subtitle,
    this.trailing,
    this.bottom,
    this.onBack,
  });

  final String title;
  final String? eyebrow;
  final String? subtitle;
  final Widget? trailing;
  final Widget? bottom;
  final VoidCallback? onBack;

  @override
  Widget build(BuildContext context) {
    // Bila layar memakai VmsTopBar (appBar, tetap saat digulir), baris logo tidak digambar lagi.
    final pinned = Scaffold.maybeOf(context)?.hasAppBar ?? false;
    final top = pinned ? 0.0 : MediaQuery.paddingOf(context).top;
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.dark.copyWith(statusBarColor: Colors.transparent),
      child: Padding(
        padding: EdgeInsets.fromLTRB(20, top + 10, 20, 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (!pinned) ...[
              _TopRow(onBack: onBack, trailing: trailing),
              const SizedBox(height: 22),
            ] else
              const SizedBox(height: 6),
            if (eyebrow != null) ...[
              Text(
                eyebrow!,
                style: VmsTextStyles.bodySm.copyWith(color: VmsColors.brand500, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 4),
            ],
            Text(
              title,
              style: VmsTextStyles.titleLg.copyWith(
                color: VmsColors.brand900,
                fontWeight: FontWeight.w800,
                fontSize: 28,
                height: 1.15,
                letterSpacing: -0.6,
              ),
            ),
            if (subtitle != null) ...[
              const SizedBox(height: 6),
              Text(subtitle!, style: VmsTextStyles.bodySm.copyWith(color: VmsColors.neutral500)),
            ],
            if (bottom != null) ...[const SizedBox(height: 12), bottom!],
          ],
        ),
      ),
    );
  }
}

class _TopRow extends StatelessWidget {
  const _TopRow({this.onBack, this.trailing});
  final VoidCallback? onBack;
  final Widget? trailing;
  @override
  Widget build(BuildContext context) => Row(
    children: [
      if (onBack != null)
        HeaderAction(icon: Icons.arrow_back_rounded, onTap: onBack!, tooltip: 'Kembali')
      else
        Image.asset(logoAsset, height: 28, semanticLabel: 'Visiontech Indograha'),
      const Spacer(),
      ?trailing,
    ],
  );
}

/// Bar atas tetap (pinned) untuk setiap tab/halaman: logo (atau tombol kembali) + aksi bulat.
/// Judul besar tetap di HeroHeader dan ikut bergulir; bar ini tidak.
class VmsTopBar extends StatelessWidget implements PreferredSizeWidget {
  const VmsTopBar({super.key, this.onBack, this.trailing});
  final VoidCallback? onBack;
  final Widget? trailing;

  @override
  Size get preferredSize => const Size.fromHeight(64);

  @override
  Widget build(BuildContext context) => AppBar(
    automaticallyImplyLeading: false,
    toolbarHeight: 64,
    titleSpacing: 20,
    backgroundColor: Theme.of(context).scaffoldBackgroundColor,
    surfaceTintColor: Colors.transparent,
    elevation: 0,
    scrolledUnderElevation: 0,
    shape: const Border(bottom: BorderSide(color: Colors.transparent)),
    systemOverlayStyle: SystemUiOverlayStyle.dark.copyWith(statusBarColor: Colors.transparent),
    title: Padding(
      padding: const EdgeInsets.only(right: 20),
      child: _TopRow(onBack: onBack, trailing: trailing),
    ),
  );
}

/// Tombol ikon bulat bergaris tipis (header, aksi kartu).
class HeaderAction extends StatelessWidget {
  const HeaderAction({super.key, required this.icon, required this.onTap, required this.tooltip});
  final IconData icon;
  final VoidCallback onTap;
  final String tooltip;
  @override
  Widget build(BuildContext context) => Pressable(
    onTap: onTap,
    child: Tooltip(
      message: tooltip,
      child: Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          border: Border.all(color: VmsColors.neutral300),
        ),
        child: Icon(icon, color: VmsColors.brand800, size: 21),
      ),
    ),
  );
}

/// Efek tekan: mengecil sedikit lalu memantul kembali (pegas ringan).
class Pressable extends StatefulWidget {
  const Pressable({super.key, required this.child, this.onTap});
  final Widget child;
  final VoidCallback? onTap;
  @override
  State<Pressable> createState() => _PressableState();
}

class _PressableState extends State<Pressable> {
  bool _down = false;
  void _set(bool v) {
    if (widget.onTap != null && _down != v) setState(() => _down = v);
  }

  @override
  Widget build(BuildContext context) {
    final reduce = _reduceMotion(context);
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTapDown: (_) => _set(true),
      onTapUp: (_) => _set(false),
      onTapCancel: () => _set(false),
      onTap: widget.onTap,
      child: AnimatedScale(
        scale: _down && !reduce ? 0.965 : 1,
        duration: Duration(milliseconds: _down ? 90 : 380),
        curve: _down ? Curves.easeOut : Curves.elasticOut,
        child: widget.child,
      ),
    );
  }
}

/// Masuk bertahap: memudar + naik sedikit, jeda per urutan (maks. ~360 ms).
class FadeSlideIn extends StatelessWidget {
  const FadeSlideIn({super.key, required this.child, this.index = 0});
  final Widget child;
  final int index;
  @override
  Widget build(BuildContext context) {
    if (_reduceMotion(context)) return child;
    final delay = math.min(index, 6) * 0.08;
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: Duration(milliseconds: 420 + (delay * 1000).round()),
      curve: Interval(delay / (0.42 + delay), 1, curve: Curves.easeOutCubic),
      builder: (_, t, c) => Opacity(
        opacity: t,
        child: Transform.translate(offset: Offset(0, 14 * (1 - t)), child: c),
      ),
      child: child,
    );
  }
}

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
  'NEEDS_REVIEW' => (label: 'Perlu review', accent: Accent.amber),
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

/// Nama + tombol Telepon & WhatsApp (kontak PM ↔ ketua/anggota tim). Tanpa nomor → keterangan "belum ada nomor HP".
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
          child: Text(
            '$label: $name${p == null ? ' · belum ada nomor HP' : ''}',
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

/// Keadaan kerja satu jadwal (sama dengan web): biru berjalan, merah terlambat, hijau selesai,
/// kuning selesai sebagian, abu belum mulai. Hasilnya kode status untuk [StatusPill]/[statusStyle].
String workState(Map<String, dynamic> p, String today) {
  final done = (p['done_count'] as num?)?.toInt() ?? 0;
  final total = (p['item_count'] as num?)?.toInt() ?? 0;
  final pct = workPercent(p);
  final date = '${p['work_date']}';
  if (total > 0 && (done >= total || pct >= 100)) return 'DONE';
  if (p['status'] == 'COMPLETED') return pct > 0 ? 'PARTIAL' : 'LATE';
  if (date.compareTo(today) < 0) return 'LATE';
  if (p['status'] == 'ONGOING' || pct > 0) return 'ONGOING';
  return 'TODO';
}

/// Persen progres nyata jadwal (rata-rata jumlah dikerjakan/target) dari API, 0–100.
int workPercent(Map<String, dynamic> p) {
  final v = p['progress_pct'];
  if (v is num) return v.toInt();
  final done = (p['done_count'] as num?)?.toInt() ?? 0;
  final total = (p['item_count'] as num?)?.toInt() ?? 0;
  return total == 0 ? 0 : (done * 100 / total).round();
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
