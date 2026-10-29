import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image/image.dart' as img;

import 'geofence_confirm.dart';
import 'local_storage.dart';
import 'team_logo.dart';
import 'watermark_camera_screen.dart';

/// Satu slot foto wajib dalam form -- label + panduan singkat apa yang harus
/// difoto (lihat tabel Keputusan 3 di plan "Verifikasi Kehadiran Lapangan").
class PhotoSlotConfig {
  const PhotoSlotConfig({
    required this.label,
    required this.hint,
    this.preferFrontCamera = false,
  });

  final String label;
  final String hint;

  /// Slot foto ORANG (mis. selfie "Foto diri di lokasi") dibuka dengan
  /// kamera DEPAN secara default -- tombol putar kamera tetap tersedia
  /// untuk berpindah manual. Ditambahkan setelah user melapor kamera depan
  /// "hilang" dibanding alur kamera bawaan HP sebelumnya.
  final bool preferFrontCamera;
}

/// Buka layar kamera watermark kustom ([WatermarkCameraScreen] -- overlay
/// lat/long/jam/keterangan sudah kelihatan LANGSUNG di layar bidik, lihat
/// plan M7 Keputusan 14), lalu gambar ulang watermark yang sama persis di
/// atas file JPEG final SEBELUM disimpan (EXIF GPS bawaan kamera HP tidak
/// bisa diandalkan). Proses gambar ulang dilakukan di isolate terpisah
/// (compute) supaya tidak macetkan UI.
///
/// [locationCaption] adalah baris keterangan konteks (mis. "Kantor Utama" /
/// "Lokasi Penugasan: Pemasangan CCTV 1") -- null berarti tidak ada baris
/// keterangan tambahan. [geofenceCheck], bila diisi, menampilkan status
/// "dalam/luar radius" LANGSUNG di layar kamera.
///
/// Dibuka lewat root navigator (bukan navigator cabang shell route) supaya
/// benar-benar menutupi SELURUH layar termasuk bottom nav bar aplikasi --
/// sebelumnya bottom nav tetap kelihatan/mengganggu di belakang kamera.
///
/// Return `(file, null)` bila sukses, `(null, pesanError)` bila gagal/dibatalkan
/// (pesan null berarti user membatalkan kamera, bukan error).
/// Celah uji: bila diisi, kamera tidak dibuka dan hasil ini yang dipakai (uji widget tanpa plugin kamera).
@visibleForTesting
Future<(File?, String?)> Function(String label)? photoCaptureOverride;

Future<(File?, String?)> captureWatermarkedPhoto({
  required BuildContext context,
  required String label,
  required String hint,
  String? locationCaption,
  bool preferFrontCamera = false,
  Future<GeofenceProximity?> Function(double latitude, double longitude)?
  geofenceCheck,
  LocalFileKind kind = LocalFileKind.other,
}) async {
  final override = photoCaptureOverride;
  if (override != null) return override(label);

  // Logo tim (bila ada & tersedia cepat) menggantikan logo default di kamera DAN di foto.
  final navigator = Navigator.of(context, rootNavigator: true);
  final logo = await _watermarkLogo(context);
  final result = await navigator.push<WatermarkCaptureResult>(
        MaterialPageRoute(
          fullscreenDialog: true,
          builder: (_) => WatermarkCameraScreen(
            title: label,
            hint: hint,
            locationCaption: locationCaption,
            preferFrontCamera: preferFrontCamera,
            geofenceCheck: geofenceCheck,
            logo: logo,
          ),
        ),
      );
  if (result == null) return (null, null); // dibatalkan user

  final bytes = await File(result.imagePath).readAsBytes();
  final watermarked = await compute(
    _drawWatermark,
    _WatermarkArgs(
      bytes: bytes,
      latitude: result.position.latitude,
      longitude: result.position.longitude,
      timestamp: result.capturedAt,
      isMocked: result.position.isMocked,
      locationCaption: locationCaption,
      address: result.address,
      logo: logo,
      overlay: result.overlayPng,
      overlayWidthFraction: result.overlayWidthFraction,
    ),
  );

  // Folder rapi per jenis: Visiontech/<Jenis>/ (R-16).
  final file = await newLocalFile(kind);
  await file.writeAsBytes(watermarked);
  return (file, null);
}

/// Logo watermark: logo tim bila tersedia (cache/server dengan batas waktu singkat), selain itu logo default.
Future<Uint8List> _watermarkLogo(BuildContext context) async {
  Uint8List? teamLogo;
  try {
    teamLogo = await teamLogoForWatermark(
      ProviderScope.containerOf(context, listen: false),
    );
  } catch (_) {
    teamLogo = null; // tanpa ProviderScope (mis. uji) → logo default
  }
  return teamLogo ??
      (await rootBundle.load(watermarkLogoAsset)).buffer.asUint8List();
}

class _WatermarkArgs {
  const _WatermarkArgs({
    required this.bytes,
    required this.latitude,
    required this.longitude,
    required this.timestamp,
    required this.isMocked,
    required this.locationCaption,
    required this.logo,
    this.address,
    this.overlay,
    this.overlayWidthFraction = 1,
  });

  final Uint8List bytes;
  final double latitude;
  final double longitude;
  final DateTime timestamp;
  final bool isMocked;
  final String? locationCaption;
  final Uint8List logo;

  /// Alamat dari GPS (null bila tidak tersedia) -- hanya dipakai pada jalur cadangan.
  final String? address;

  /// Panel watermark hasil tangkapan layar kamera (PNG) — bila ada, dibakar apa adanya (R-14).
  final Uint8List? overlay;
  final double overlayWidthFraction;
}

String _twoDigits(int n) => n.toString().padLeft(2, '0');

/// Format manual (bukan intl DateFormat) -- sengaja hindari locale data
/// ('id_ID') di dalam fungsi ini, karena dijalankan lewat compute() di
/// isolate TERPISAH yang tidak otomatis mewarisi inisialisasi locale dari
/// isolate utama (lihat initializeDateFormatting di main.dart). Panggilan
/// DateFormat ber-locale di sini pernah membuat seluruh proses macet tanpa
/// pernah selesai/melempar error yang tertangkap.
String _formatTimestamp(DateTime dt) =>
    '${_twoDigits(dt.day)}/${_twoDigits(dt.month)}/${dt.year} ${_twoDigits(dt.hour)}:${_twoDigits(dt.minute)}';

/// Baris teks watermark pada jalur cadangan: koordinat, alamat (bila ada), waktu, keterangan, peringatan GPS palsu.
@visibleForTesting
List<String> watermarkTextLines({
  required double latitude,
  required double longitude,
  required DateTime timestamp,
  required bool isMocked,
  String? locationCaption,
  String? address,
}) => [
  '${latitude.toStringAsFixed(6)}, ${longitude.toStringAsFixed(6)}',
  if (address != null && address.isNotEmpty) address,
  _formatTimestamp(timestamp),
  ?locationCaption,
  if (isMocked) 'PERINGATAN: lokasi mock/fake GPS',
];

Uint8List _drawWatermark(_WatermarkArgs args) {
  var image = img.decodeImage(args.bytes);
  if (image == null) return args.bytes;

  image = img.bakeOrientation(image);

  // Foto kamera asli bisa 12MP+ -- proses gambar murni-Dart (tanpa akselerasi
  // native) pada resolusi sebesar itu bisa sangat lambat, terutama di build
  // debug. Resize eksplisit di sini supaya waktu proses selalu terkendali.
  if (image.width > 1280) {
    image = img.copyResize(image, width: 1280);
  }

  // Utama: bakar panel yang PERSIS terlihat di layar kamera (teks, huruf, warna, logo) dengan
  // proporsi lebar yang sama, di tengah bawah — hasil = tampilan (R-14).
  final overlay = args.overlay == null ? null : img.decodePng(args.overlay!);
  if (overlay != null) {
    final width = (image.width * args.overlayWidthFraction.clamp(0.5, 1.0))
        .round();
    final panel = img.copyResize(
      overlay,
      width: width,
      interpolation: img.Interpolation.average,
    );
    final margin = ((image.width - width) / 2).round();
    img.compositeImage(
      image,
      panel,
      dstX: margin,
      dstY: image.height - panel.height - (margin > 0 ? margin : 16),
    );
    return Uint8List.fromList(img.encodeJpg(image, quality: 88));
  }

  // Cadangan (tangkapan panel gagal): gambar ulang ringkas.
  final lines = watermarkTextLines(
    latitude: args.latitude,
    longitude: args.longitude,
    timestamp: args.timestamp,
    isMocked: args.isMocked,
    locationCaption: args.locationCaption,
    address: args.address,
  );

  const padding = 14;
  const lineHeight = 20;
  final boxHeight = padding * 2 + lines.length * lineHeight;

  img.fillRect(
    image,
    x1: 0,
    y1: image.height - boxHeight,
    x2: image.width,
    y2: image.height,
    color: img.ColorRgba8(0, 0, 0, 170),
  );

  for (var i = 0; i < lines.length; i++) {
    img.drawString(
      image,
      lines[i],
      font: img.arial14,
      x: padding,
      y: image.height - boxHeight + padding + i * lineHeight,
      color: img.ColorRgb8(255, 255, 255),
    );
  }

  // Logo di sisi kanan kotak watermark, 'contain' di dalam kotak standar (logo persegi tampil lebih kecil).
  final logo = img.decodeImage(args.logo);
  if (logo != null) {
    final maxH = boxHeight - 20;
    const maxW = watermarkLogoBoxWidth;
    final scale = [
      1.0,
      maxW / logo.width,
      maxH / logo.height,
    ].reduce((a, b) => a < b ? a : b);
    final badge = img.copyResize(
      logo,
      width: (logo.width * scale).round().clamp(1, maxW.toInt()),
      height: (logo.height * scale).round().clamp(1, maxH.toInt()),
      interpolation: img.Interpolation.average,
    );
    img.compositeImage(
      image,
      badge,
      dstX: image.width - badge.width - padding,
      dstY: image.height - boxHeight + 10,
    );
  }

  return Uint8List.fromList(img.encodeJpg(image, quality: 85));
}

/// Widget form: daftar slot foto wajib, tiap slot ditampilkan sebagai kartu
/// tap-untuk-foto dengan label & panduan. Melaporkan daftar file (null untuk
/// slot yang belum diisi) lewat [onChanged] setiap kali berubah.
class GuidedPhotoCapture extends StatefulWidget {
  const GuidedPhotoCapture({
    required this.slots,
    required this.onChanged,
    this.locationCaption,
    this.geofenceCheck,
    super.key,
  });

  final List<PhotoSlotConfig> slots;
  final ValueChanged<List<File?>> onChanged;

  /// Baris keterangan konteks yang ikut ditulis di watermark tiap foto dari
  /// widget ini (mis. "Kantor Utama"). Lihat plan M7 Keputusan 15.
  final String? locationCaption;

  /// Bila diisi, tiap slot menampilkan status "dalam/luar radius" LANGSUNG
  /// di layar kamera -- dipakai konteks yang punya target geofence (absensi,
  /// tiba di lokasi). Null berarti tidak ditampilkan (mis. logbook, yang
  /// tidak divalidasi geofence).
  final Future<GeofenceProximity?> Function(double latitude, double longitude)?
  geofenceCheck;

  @override
  State<GuidedPhotoCapture> createState() => _GuidedPhotoCaptureState();
}

class _GuidedPhotoCaptureState extends State<GuidedPhotoCapture> {
  // Sengaja list yang bisa berubah panjang (bukan List.filled yang panjangnya
  // TETAP): jumlah slot bisa bertambah/berkurang saat form berjalan, mis. slot
  // "foto nota" baru muncul begitu ada material dicatat di Bill of Material.
  // Sebelumnya daftar ini dibuat sekali dengan panjang awal dan tidak pernah
  // menyesuaikan, sehingga slot yang baru muncul langsung melempar RangeError.
  late List<File?> _files = List<File?>.generate(
    widget.slots.length,
    (_) => null,
  );
  int? _capturingIndex;
  String? _error;

  @override
  void didUpdateWidget(covariant GuidedPhotoCapture oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.slots.length == _files.length) return;
    // Pertahankan foto yang sudah terlanjur diambil untuk slot yang masih ada.
    final resized = List<File?>.generate(
      widget.slots.length,
      (i) => i < _files.length ? _files[i] : null,
    );
    _files = resized;
    // Beri tahu pemanggil bentuk barunya, supaya validasi "foto lengkap" di
    // sana tidak menilai berdasarkan jumlah slot yang sudah usang.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) widget.onChanged(List<File?>.of(_files));
    });
  }

  Future<void> _capture(int index) async {
    setState(() {
      _capturingIndex = index;
      _error = null;
    });
    try {
      final (file, error) = await captureWatermarkedPhoto(
        context: context,
        label: widget.slots[index].label,
        hint: widget.slots[index].hint,
        locationCaption: widget.locationCaption,
        preferFrontCamera: widget.slots[index].preferFrontCamera,
        geofenceCheck: widget.geofenceCheck,
      );
      if (!mounted) return;
      if (file != null) {
        setState(() => _files[index] = file);
        widget.onChanged(List<File?>.of(_files));
      } else if (error != null) {
        setState(() => _error = error);
      }
    } catch (e) {
      // Pertahanan terakhir -- APAPUN yang gagal di sini (mis. proses gambar
      // di isolate terpisah error), jangan sampai spinner macet selamanya
      // tanpa penjelasan.
      if (mounted) setState(() => _error = 'Gagal memproses foto: $e');
    } finally {
      if (mounted) setState(() => _capturingIndex = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (_error != null)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: Text(
              _error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ),
        for (var i = 0; i < widget.slots.length; i++)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: InkWell(
              onTap: _capturingIndex != null ? null : () => _capture(i),
              borderRadius: BorderRadius.circular(10),
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  border: Border.all(
                    color: _files[i] != null
                        ? Theme.of(context).colorScheme.primary
                        : Colors.grey.shade400,
                  ),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Row(
                  children: [
                    if (_capturingIndex == i)
                      const SizedBox(
                        width: 48,
                        height: 48,
                        child: Center(
                          child: CircularProgressIndicator(strokeWidth: 2),
                        ),
                      )
                    else if (_files[i] != null)
                      ClipRRect(
                        borderRadius: BorderRadius.circular(6),
                        child: Image.file(
                          _files[i]!,
                          width: 48,
                          height: 48,
                          fit: BoxFit.cover,
                        ),
                      )
                    else
                      Icon(
                        Icons.camera_alt_outlined,
                        size: 32,
                        color: Colors.grey.shade600,
                      ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            widget.slots[i].label,
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                          Text(
                            _files[i] != null
                                ? 'Terambil -- tap untuk ambil ulang'
                                : widget.slots[i].hint,
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    ),
                    if (_files[i] != null)
                      Icon(
                        Icons.check_circle,
                        color: Theme.of(context).colorScheme.primary,
                      ),
                  ],
                ),
              ),
            ),
          ),
      ],
    );
  }
}
