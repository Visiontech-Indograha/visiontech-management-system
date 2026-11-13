import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/theme/theme.dart';

part 'vms_ui_header.dart';
part 'vms_ui_cards.dart';
part 'vms_ui_feedback.dart';

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

/// Gutter kiri/kanan isi daftar agar kartu/teks tidak menempel ke tepi layar.
const double kListGutter = 16;

/// Safe zone (R-14): padding daftar yang menjauhkan konten dari area sistem — tepi bawah (bilah
/// gestur/navigasi yang disembunyikan), lekuk layar & notch di kiri/kanan. Atas diurus header/appBar.
EdgeInsets safeListPadding(BuildContext context, {double bottomGap = 24}) {
  final mq = MediaQuery.of(context);
  final bottom = math.max(mq.padding.bottom, mq.systemGestureInsets.bottom);
  return EdgeInsets.only(left: mq.padding.left, right: mq.padding.right, bottom: bottom + bottomGap);
}

bool _reduceMotion(BuildContext context) => MediaQuery.maybeDisableAnimationsOf(context) ?? false;


/// Teks untuk field yang boleh kosong dari API: null/kosong → [fallback], bukan kata 'null' di layar.
String textOr(Object? value, String fallback) {
  final s = value?.toString().trim() ?? '';
  return s.isEmpty ? fallback : s;
}

const _bulanSingkat = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];

/// Judul kartu jadwal: lokasi, lalu nama proyek. Bila keduanya kosong: nama tim dan tanggal kerja (mis. "Tim A · 30 Okt").
String jadwalTitle(Map<String, dynamic> p) {
  final judul = textOr(p['site_name'], textOr(p['project_title'], ''));
  if (judul.isNotEmpty) return judul;
  final tim = textOr(p['team_name'], '');
  final hari = DateTime.tryParse(textOr(p['work_date'], ''));
  final tanggal = hari == null ? '' : '${hari.day} ${_bulanSingkat[hari.month - 1]}';
  final bagian = [if (tim.isNotEmpty) 'Tim $tim', if (tanggal.isNotEmpty) tanggal];
  return bagian.isEmpty ? 'Jadwal tanpa lokasi' : bagian.join(' · ');
}

/// Keadaan kerja satu jadwal (sama dengan web): biru berjalan, merah terlambat, hijau selesai,
/// kuning selesai sebagian, abu belum mulai. Hasilnya kode status untuk [StatusPill]/[statusStyle].
String workState(Map<String, dynamic> p, String today) {
  final done = (p['done_count'] as num?)?.toInt() ?? 0;
  final total = (p['item_count'] as num?)?.toInt() ?? 0;
  final pct = workPercent(p);
  final date = '${p['work_date']}';
  // Selesai hanya bila semua item (termasuk yang dipindah/menunggu pindah) DONE — sama dengan web workState.
  if (total > 0 && done >= total) return 'DONE';
  if (p['status'] == 'COMPLETED') return pct > 0 ? 'PARTIAL' : 'LATE';
  if (date.compareTo(today) < 0) return 'LATE';
  if (p['status'] == 'ONGOING' || pct > 0) return 'ONGOING';
  return 'TODO';
}

/// Persen progres nyata jadwal (rata-rata jumlah dikerjakan/target) dari API, 0–100.
int workPercent(Map<String, dynamic> p) {
  final done = (p['done_count'] as num?)?.toInt() ?? 0;
  final total = (p['item_count'] as num?)?.toInt() ?? 0;
  final v = p['progress_pct'];
  final raw = v is num ? v.toInt() : (total == 0 ? 0 : (done * 100 / total).round());
  // Sama dengan web displayPct: 100 hanya bila semua item DONE; selainnya maksimal 99.
  final allDone = total > 0 && done >= total;
  return allDone ? raw.clamp(0, 100).toInt() : raw.clamp(0, 99).toInt();
}


/// Membuang controller milik dialog setelah animasi tutup dialog selesai. Membuangnya langsung setelah `showDialog`
/// kembali membuat TextField yang masih tampil saat animasi memicu error "_dependents.isEmpty" (layar merah).
void disposeAfterDialog(List<TextEditingController> controllers) {
  Future<void>.delayed(const Duration(milliseconds: 500), () {
    for (final c in controllers) {
      c.dispose();
    }
  });
}

/// Konfirmasi sebelum aksi penting; true bila pengguna menekan tombol konfirmasi.
Future<bool> confirmAction(
  BuildContext context, {
  required String title,
  required String message,
  String confirmLabel = 'Ya, lanjutkan',
  String cancelLabel = 'Batal',
}) async {
  final ok = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: Text(title),
      content: Text(message),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(cancelLabel)),
        FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text(confirmLabel)),
      ],
    ),
  );
  return ok == true;
}

/// Tombol Back saat form berisi isian belum dikirim: true bila pengguna memilih "Ya, buang".
Future<bool> confirmBuangIsian(BuildContext context) async {
  final ok = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: const Text('Buang isian?'),
      content: const Text('Isian yang belum dikirim akan hilang.'),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Lanjut mengisi')),
        FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Ya, buang')),
      ],
    ),
  );
  return ok == true;
}


/// Deteksi layar ponsel sempit (< 360 dp) agar tata letak kartu otomatis menyederhanakan jarak.
bool isCompactPhone(BuildContext context) => MediaQuery.sizeOf(context).width < 360;

/// Deteksi layar tablet / ponsel lipat terbuka (≥ 600 dp) untuk tata letak 2 kolom.
bool isTablet(BuildContext context) => MediaQuery.sizeOf(context).width >= 600;

/// Membuka modal bottom sheet dengan ruang lega, adaptif terhadap keyboard,
/// dan mendukung pengguliran konten panjang hingga 90% tinggi layar.
Future<T?> showVmsModalBottomSheet<T>({
  required BuildContext context,
  required WidgetBuilder builder,
  bool isDismissible = true,
  bool enableDrag = true,
}) {
  return showModalBottomSheet<T>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    isDismissible: isDismissible,
    enableDrag: enableDrag,
    builder: (ctx) {
      final mq = MediaQuery.of(ctx);
      final maxHeight = mq.size.height * 0.90;
      return ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: maxHeight,
          maxWidth: (mq.size.width * 0.96).clamp(0.0, 960.0),
        ),
        child: Padding(
          padding: EdgeInsets.only(bottom: mq.viewInsets.bottom),
          child: builder(ctx),
        ),
      );
    },
  );
}

