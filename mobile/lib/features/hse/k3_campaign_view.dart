import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../shared/ui/vms_network_image.dart';
import 'k3_campaign.dart';

const _tick = Duration(milliseconds: 200);

/// Auto-geser menunggu selama ini sejak interaksi terakhir (zoom/geser) pada foto itu.
const _quietWaitMs = 5000;
const _maxZoom = 4.0;

/// Tampilan wajib baca K3: foto (PageView + zoom), keterangan per foto, bilah waktu, dan tombol konfirmasi.
///
/// Waktu baca hanya berjalan saat aplikasi di depan: saat ke latar belakang, timer dan pergantian foto berhenti.
/// Geser, zoom, dan tombol foto tidak mempercepat waktu baca. Tombol konfirmasi terkunci sampai waktu habis.
class K3CampaignView extends StatefulWidget {
  const K3CampaignView({
    super.key,
    required this.campaign,
    required this.onConfirm,
    this.sending = false,
    this.error,
    this.photoBuilder,
  });

  final K3Campaign campaign;

  /// Dipanggil saat tombol konfirmasi ditekan; argumen = detik waktu baca sebenarnya.
  final void Function(int readSeconds) onConfirm;
  final bool sending;
  final String? error;

  /// Bagaimana satu foto (id berkas) digambar. Bawaan: unduh resolusi penuh lewat API dan cache di perangkat.
  final Widget Function(BuildContext context, String fileId)? photoBuilder;

  @override
  State<K3CampaignView> createState() => _K3CampaignViewState();
}

class _K3CampaignViewState extends State<K3CampaignView> with WidgetsBindingObserver {
  final PageController _page = PageController();
  final TransformationController _zoom = TransformationController();
  Timer? _timer;
  bool _foreground = true;
  bool _landscapeLocked = false;
  bool _photoLandscape = false;
  int _elapsedMs = 0;
  int _slideMs = 0;
  int _quietMs = 0;
  int _index = 0;
  Size _viewport = Size.zero;
  Offset _tapAt = Offset.zero;

  int get _total => widget.campaign.cooldownSeconds;
  int get _count => widget.campaign.mediaIds.length;
  int get _remaining => k3RemainingSeconds(_total, _elapsedMs);
  bool get _done => _remaining == 0;
  double get _scale => _zoom.value.getMaxScaleOnAxis();
  bool get _zoomed => _scale > 1.01;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _zoom.addListener(_onZoomChanged);
    _timer = Timer.periodic(_tick, (_) => _onTick());
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // Hanya saat benar-benar di depan yang dihitung; latar belakang / tarik notifikasi menghentikan waktu.
    _foreground = state == AppLifecycleState.resumed;
  }

  void _onZoomChanged() {
    if (mounted) setState(() {});
  }

  void _onTick() {
    if (!_foreground || !mounted) return;
    const tickMs = 200;
    final totalMs = _total * 1000;
    var advance = false;
    setState(() {
      if (_elapsedMs < totalMs) {
        _elapsedMs = (_elapsedMs + tickMs).clamp(0, totalMs);
      }
      if (_count > 1) {
        _slideMs += tickMs;
        _quietMs += tickMs;
        // Dekat akhir waktu baca, auto-geser tidak menunggu lagi.
        final nearEnd = totalMs - _elapsedMs <= _quietWaitMs;
        final quietOk = _quietMs >= _quietWaitMs || nearEnd;
        if (_slideMs >= k3SlideIntervalMs(_total, _count) && quietOk) {
          _slideMs = 0;
          advance = true;
        }
      }
    });
    if (advance) _goRelative(1);
  }

  void _onPageChanged(int i) {
    // Setiap perpindahan foto (manual atau otomatis) memulai ulang interval, dan zoom kembali ke 1x.
    setState(() {
      _index = i;
      _slideMs = 0;
      _quietMs = 0;
    });
    _zoom.value = Matrix4.identity();
  }

  void _goRelative(int delta) {
    if (_count <= 1) return;
    final target = (_index + delta + _count) % _count;
    _quietMs = 0;
    _page.animateToPage(target, duration: const Duration(milliseconds: 300), curve: Curves.easeInOut);
  }

  /// Ubah skala ke [target] dengan titik tetap [focal] (koordinat layar foto).
  void _setScale(double target, Offset focal) {
    final clamped = target.clamp(1.0, _maxZoom);
    if (clamped <= 1.01) {
      _zoom.value = Matrix4.identity();
    } else {
      final f = clamped / _scale;
      final m = Matrix4.identity()
        ..translateByDouble(focal.dx, focal.dy, 0, 1)
        ..scaleByDouble(f, f, f, 1)
        ..translateByDouble(-focal.dx, -focal.dy, 0, 1);
      _zoom.value = m * _zoom.value;
    }
    _quietMs = 0;
  }

  Offset get _center => Offset(_viewport.width / 2, _viewport.height / 2);

  void _onDoubleTap() => _setScale(_zoomed ? 1 : 2, _tapAt);

  void _onPhotoSize(int i, Size s) {
    final landscape = s.width > s.height;
    if (i == _index && landscape != _photoLandscape && mounted) {
      setState(() => _photoLandscape = landscape);
    }
  }

  void _toggleLandscape() {
    setState(() => _landscapeLocked = !_landscapeLocked);
    SystemChrome.setPreferredOrientations(
      _landscapeLocked ? const [DeviceOrientation.landscapeLeft, DeviceOrientation.landscapeRight] : const [],
    );
  }

  void _openText() {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (ctx) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.55,
        minChildSize: 0.3,
        maxChildSize: 0.9,
        builder: (ctx, controller) => ListView(
          controller: controller,
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
          children: [
            Text(widget.campaign.title, style: Theme.of(ctx).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700)),
            const SizedBox(height: 12),
            Text(
              widget.campaign.contentText.isEmpty ? '-' : widget.campaign.contentText,
              style: Theme.of(ctx).textTheme.bodyLarge?.copyWith(height: 1.5, fontSize: 17),
            ),
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _timer?.cancel();
    _zoom.removeListener(_onZoomChanged);
    _zoom.dispose();
    _page.dispose();
    if (_landscapeLocked) SystemChrome.setPreferredOrientations(const []);
    super.dispose();
  }

  int get _readSeconds => (_elapsedMs / 1000).round().clamp(1, 1 << 30);

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Material(
      color: scheme.surface,
      child: SafeArea(
        child: LayoutBuilder(
          builder: (context, c) {
            final landscape = c.maxWidth > c.maxHeight;
            final header = _header(context);
            final footer = _footer(context);
            if (landscape) {
              return Padding(
                padding: const EdgeInsets.all(8),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    header,
                    Expanded(
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Expanded(flex: 3, child: _photos(context)),
                          const SizedBox(width: 12),
                          Expanded(
                            flex: 2,
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.end,
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [footer],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              );
            }
            return Padding(
              padding: const EdgeInsets.fromLTRB(8, 4, 8, 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  header,
                  if (_photoLandscape) _rotateBanner(context),
                  Expanded(child: _photos(context)),
                  footer,
                ],
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _header(BuildContext context) {
    final theme = Theme.of(context).textTheme;
    return Row(
      children: [
        Expanded(
          child: Semantics(
            header: true,
            child: Text(
              'PANDUAN K3: ${widget.campaign.title}',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: theme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
            ),
          ),
        ),
        TextButton(onPressed: _openText, child: const Text('Baca keterangan')),
        IconButton(
          tooltip: _landscapeLocked ? 'Lepas kunci layar' : 'Putar layar',
          icon: const Icon(Icons.screen_rotation),
          onPressed: _toggleLandscape,
        ),
      ],
    );
  }

  Widget _rotateBanner(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 4),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(color: const Color(0xFFFFF3CD), borderRadius: BorderRadius.circular(8)),
      child: const Text(
        'Putar HP agar foto lebih besar',
        style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Colors.black87),
        textAlign: TextAlign.center,
      ),
    );
  }

  Widget _photos(BuildContext context) {
    final ids = widget.campaign.mediaIds;
    final legacy = widget.campaign.mediaUrl;
    final neutral = Theme.of(context).colorScheme.surfaceContainerHighest;
    final caption = ids.isEmpty ? '' : widget.campaign.captionAt(_index);

    Widget area;
    if (ids.isNotEmpty) {
      area = LayoutBuilder(
        builder: (context, c) {
          _viewport = c.biggest;
          return Stack(
            children: [
              Positioned.fill(
                child: ColoredBox(
                  color: neutral,
                  child: PageView.builder(
                    controller: _page,
                    itemCount: ids.length,
                    physics: _zoomed ? const NeverScrollableScrollPhysics() : const PageScrollPhysics(),
                    onPageChanged: _onPageChanged,
                    itemBuilder: (context, i) => _photoPage(context, ids[i], i),
                  ),
                ),
              ),
              Positioned(top: 4, right: 4, child: _zoomButtons()),
              if (ids.length > 1) Positioned(left: 0, right: 0, bottom: 0, child: _pageControls(ids.length)),
            ],
          );
        },
      );
    } else if (legacy != null) {
      area = ColoredBox(
        color: neutral,
        child: Image.network(legacy, fit: BoxFit.contain, errorBuilder: (_, _, _) => const _NoPhoto()),
      );
    } else {
      area = ColoredBox(color: neutral, child: const _NoPhoto());
    }

    return Column(
      children: [
        Expanded(child: ClipRRect(borderRadius: BorderRadius.circular(8), child: area)),
        if (caption.isNotEmpty)
          ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 120),
            child: SingleChildScrollView(
              padding: const EdgeInsets.only(top: 8),
              child: Semantics(
                label: 'Keterangan foto: $caption',
                child: Text(
                  caption,
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600, height: 1.35, color: Colors.black87),
                ),
              ),
            ),
          ),
      ],
    );
  }

  Widget _photoPage(BuildContext context, String fileId, int i) {
    final photo = widget.photoBuilder?.call(context, fileId) ??
        VmsNetworkImage(fileId: fileId, variant: 'full', fit: BoxFit.contain, onSize: (s) => _onPhotoSize(i, s));
    return Semantics(
      label: 'Foto ${i + 1} dari ${widget.campaign.mediaIds.length}',
      image: true,
      child: GestureDetector(
        onDoubleTapDown: (d) => _tapAt = d.localPosition,
        onDoubleTap: _onDoubleTap,
        child: InteractiveViewer(
          transformationController: _zoom,
          minScale: 1,
          maxScale: _maxZoom,
          // Geser satu jari dibiarkan ke PageView saat belum di-zoom; pan hanya saat zoom.
          panEnabled: _zoomed,
          onInteractionStart: (_) => _quietMs = 0,
          onInteractionEnd: (_) => _quietMs = 0,
          child: SizedBox.expand(child: photo),
        ),
      ),
    );
  }

  Widget _zoomButtons() {
    return Material(
      color: Colors.black54,
      borderRadius: BorderRadius.circular(8),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(
            tooltip: 'Perbesar',
            color: Colors.white,
            icon: const Icon(Icons.zoom_in),
            onPressed: () => _setScale(_scale * 1.5, _center),
          ),
          IconButton(
            tooltip: 'Perkecil',
            color: Colors.white,
            icon: const Icon(Icons.zoom_out),
            onPressed: () => _setScale(_scale / 1.5, _center),
          ),
          IconButton(
            tooltip: 'Pas layar',
            color: Colors.white,
            icon: const Icon(Icons.fit_screen),
            onPressed: () => _setScale(1, _center),
          ),
        ],
      ),
    );
  }

  Widget _pageControls(int count) {
    return Material(
      color: Colors.black54,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Semantics(
              label: 'Foto ${_index + 1} dari $count',
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    '${_index + 1} dari $count',
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 16),
                  ),
                  const SizedBox(width: 10),
                  for (var i = 0; i < count; i++)
                    Container(
                      width: 8,
                      height: 8,
                      margin: const EdgeInsets.symmetric(horizontal: 3),
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: i == _index ? Colors.white : Colors.white38,
                      ),
                    ),
                ],
              ),
            ),
            Row(
              children: [
                Expanded(
                  child: TextButton.icon(
                    style: TextButton.styleFrom(foregroundColor: Colors.white, padding: const EdgeInsets.symmetric(horizontal: 4)),
                    onPressed: () => _goRelative(-1),
                    icon: const Icon(Icons.chevron_left),
                    label: const Text('Sebelumnya'),
                  ),
                ),
                Expanded(
                  child: TextButton.icon(
                    style: TextButton.styleFrom(foregroundColor: Colors.white, padding: const EdgeInsets.symmetric(horizontal: 4)),
                    onPressed: () => _goRelative(1),
                    icon: const Icon(Icons.chevron_right),
                    label: const Text('Selanjutnya'),
                    iconAlignment: IconAlignment.end,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _footer(BuildContext context) {
    final total = _total <= 0 ? 1 : _total * 1000;
    final fraction = (_elapsedMs / total).clamp(0.0, 1.0);
    final canConfirm = _done && !widget.sending;
    final label = widget.sending
        ? 'Mengirim...'
        : widget.error != null
        ? 'Coba lagi'
        : 'Saya telah membaca dan memahami';
    final scheme = Theme.of(context).colorScheme;
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Semantics(
          liveRegion: true,
          child: Text(
            _done ? 'Waktu baca sudah habis. Silakan konfirmasi.' : 'Mohon baca sampai waktu habis. Sisa $_remaining detik.',
            style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15),
          ),
        ),
        const SizedBox(height: 4),
        ExcludeSemantics(child: LinearProgressIndicator(value: fraction, minHeight: 6)),
        if (widget.error != null) ...[
          const SizedBox(height: 6),
          Semantics(
            liveRegion: true,
            child: Text(widget.error!, style: TextStyle(color: scheme.error, fontWeight: FontWeight.w600)),
          ),
        ],
        const SizedBox(height: 6),
        // Terkunci (tipis) sampai waktu habis; setelah itu jadi tombol besar.
        if (_done)
          SizedBox(
            height: 56,
            child: FilledButton(
              onPressed: canConfirm ? () => widget.onConfirm(_readSeconds) : null,
              child: Text(label, textAlign: TextAlign.center),
            ),
          )
        else
          const SizedBox(
            height: 36,
            child: FilledButton(
              onPressed: null,
              child: Text('Baca sampai waktu habis', textAlign: TextAlign.center),
            ),
          ),
      ],
    );
  }
}

class _NoPhoto extends StatelessWidget {
  const _NoPhoto();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.image_not_supported_outlined, size: 40, color: Colors.black45),
          SizedBox(height: 4),
          Text('Tidak ada foto', style: TextStyle(color: Colors.black54)),
        ],
      ),
    );
  }
}
