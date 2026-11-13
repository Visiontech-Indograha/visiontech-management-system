part of 'vms_ui.dart';

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
    this.horizontal = 20,
  });

  /// Jarak kiri/kanan header; 4 bila daftar induk sudah memberi gutter 16 (lihat [kListGutter]).
  final double horizontal;
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
        padding: EdgeInsets.fromLTRB(horizontal, top + 10, horizontal, 8),
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
