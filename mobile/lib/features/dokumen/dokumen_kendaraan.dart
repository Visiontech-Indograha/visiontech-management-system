import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/error_message.dart';
import '../../core/providers.dart';
import '../../core/theme/theme.dart';
import '../../data/sync_engine.dart';
import '../../shared/ui/vms_ui.dart';

/// Batas "segera habis" (hari). Sama dengan ambang pengingat di server.
const int kDokumenSegeraHari = 30;

enum DokumenStatus { aman, segera, lewat }

/// Sisa hari dihitung dari tanggal berlaku (bukan `days_left` cache yang bisa basi).
int dokumenSisaHari(String expiredOn, DateTime hariIni) {
  final d = DateTime.tryParse(expiredOn);
  if (d == null) return 99999;
  final a = DateTime(d.year, d.month, d.day);
  final b = DateTime(hariIni.year, hariIni.month, hariIni.day);
  return a.difference(b).inDays;
}

DokumenStatus dokumenStatus(int sisaHari) => sisaHari < 0
    ? DokumenStatus.lewat
    : sisaHari <= kDokumenSegeraHari
    ? DokumenStatus.segera
    : DokumenStatus.aman;

/// Contoh: "Berlaku sampai 12 Des 2026 (30 hari lagi)".
String dokumenLabelBerlaku(String expiredOn, int sisaHari) {
  final d = DateTime.tryParse(expiredOn);
  final tgl = d == null ? expiredOn : DateFormat('d MMM yyyy', 'id_ID').format(d);
  if (sisaHari < 0) return 'Sudah lewat ${-sisaHari} hari (berlaku sampai $tgl)';
  if (sisaHari == 0) return 'Berlaku sampai $tgl (habis hari ini)';
  return 'Berlaku sampai $tgl ($sisaHari hari lagi)';
}

/// Dokumen yang perlu perhatian (<= 30 hari atau sudah lewat), paling mendesak dulu.
List<Map<String, dynamic>> dokumenPerluPerhatian(
  List<Map<String, dynamic>> items,
  DateTime hariIni,
) {
  final r = [
    for (final x in items)
      if (dokumenSisaHari('${x['expired_on']}', hariIni) <= kDokumenSegeraHari) x,
  ];
  r.sort((a, b) => '${a['expired_on']}'.compareTo('${b['expired_on']}'));
  return r;
}

typedef DokumenData = ({List<Map<String, dynamic>> items, DateTime? cachedAt});

/// Dokumen milik pengemudi ini. Lewat cache: tetap terbaca tanpa sinyal.
final dokumenSayaProvider = FutureProvider.autoDispose<DokumenData>((ref) async {
  final engine = ref.watch(syncEngineProvider);
  return engine.fetchList('vehicle_docs_mine', engine.api.vehicleDocumentsMine);
});

/// Daftar kantor (HSE/OM): yang akan atau sudah jatuh tempo.
final dokumenKantorProvider = FutureProvider.autoDispose<DokumenData>((ref) async {
  final engine = ref.watch(syncEngineProvider);
  return engine.fetchList(
    'vehicle_docs_expiring',
    () => engine.api.vehicleDocumentsExpiring(),
  );
});

(Accent, IconData, String) _tampilan(DokumenStatus s) => switch (s) {
  DokumenStatus.aman => (Accent.emerald, Icons.check_circle_rounded, 'Aman'),
  DokumenStatus.segera => (Accent.amber, Icons.schedule_rounded, 'Segera habis'),
  DokumenStatus.lewat => (Accent.rose, Icons.error_rounded, 'Sudah lewat'),
};

/// Kartu pengingat di Beranda. Diam (tidak tampil) bila tidak ada yang perlu perhatian,
/// masih memuat, atau gagal: Beranda tidak boleh terganggu.
class DokumenPengingatBanner extends ConsumerWidget {
  const DokumenPengingatBanner({super.key, this.hariIni});
  final DateTime? hariIni;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final data = ref.watch(dokumenSayaProvider).value;
    if (data == null) return const SizedBox.shrink();
    final hari = hariIni ?? DateTime.now();
    final perlu = dokumenPerluPerhatian(data.items, hari);
    if (perlu.isEmpty) return const SizedBox.shrink();
    final d = perlu.first;
    final sisa = dokumenSisaHari('${d['expired_on']}', hari);
    final lewat = sisa < 0;
    final nama = '${d['doc_type_name']} ${d['number_plate'] ?? ''}'.trim();
    final teks = lewat
        ? '$nama sudah lewat ${-sisa} hari. Segera perpanjang.'
        : '$nama habis ${sisa == 0 ? 'hari ini' : 'dalam $sisa hari'}.';
    return Semantics(
      button: true,
      label: 'Pengingat dokumen. $teks Ketuk untuk melihat.',
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => context.push('/dokumen-kendaraan'),
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 48),
          child: NoticeBanner(
            icon: lewat ? Icons.error_rounded : Icons.schedule_rounded,
            text: perlu.length > 1 ? '$teks (+${perlu.length - 1} lainnya)' : teks,
            accent: lewat ? Accent.rose : Accent.amber,
          ),
        ),
      ),
    );
  }
}

class _DokumenKartu extends StatelessWidget {
  const _DokumenKartu({required this.item, required this.hariIni});
  final Map<String, dynamic> item;
  final DateTime hariIni;

  @override
  Widget build(BuildContext context) {
    final sisa = dokumenSisaHari('${item['expired_on']}', hariIni);
    final (accent, ikon, status) = _tampilan(dokumenStatus(sisa));
    final kendaraan = '${item['vehicle_name'] ?? ''} ${item['number_plate'] ?? ''}'.trim();
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: SurfaceCard(
        padding: const EdgeInsets.all(14),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            IconTile(icon: ikon, accent: accent, size: 40),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${item['doc_type_name']}', style: VmsTextStyles.subheading),
                  if (kendaraan.isNotEmpty) Text(kendaraan, style: VmsTextStyles.caption),
                  const SizedBox(height: 4),
                  Text(
                    dokumenLabelBerlaku('${item['expired_on']}', sisa),
                    style: VmsTextStyles.bodySm.copyWith(color: accent.strong, fontWeight: FontWeight.w600),
                  ),
                  Text(status, style: VmsTextStyles.caption.copyWith(color: accent.strong)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _DokumenListScreen extends ConsumerWidget {
  const _DokumenListScreen({
    required this.judul,
    required this.provider,
    required this.kosongJudul,
    required this.kosongPesan,
    this.hariIni,
  });
  final String judul;
  final FutureProvider<DokumenData> provider;
  final String kosongJudul;
  final String kosongPesan;
  final DateTime? hariIni;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(provider);
    final hari = hariIni ?? DateTime.now();
    return Scaffold(
      appBar: VmsTopBar(onBack: () => context.pop()),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(provider);
          await ref.read(provider.future).catchError((_) => (items: <Map<String, dynamic>>[], cachedAt: null));
        },
        child: ListView(
          padding: safeListPadding(context).add(const EdgeInsets.symmetric(horizontal: kListGutter)),
          children: [
            HeroHeader(eyebrow: 'Kendaraan', title: judul, horizontal: 4),
            ...async.when(
              loading: () => [const SkeletonCards(height: 96)],
              error: (e, _) => [
                NoticeBanner(
                  icon: Icons.error_outline_rounded,
                  text: apiErrorMessage(e, fallback: 'Dokumen belum bisa dimuat.'),
                  accent: Accent.rose,
                ),
                SizedBox(
                  height: 48,
                  child: OutlinedButton(
                    onPressed: () => ref.invalidate(provider),
                    child: const Text('Coba lagi'),
                  ),
                ),
              ],
              data: (d) {
                if (SyncEngine.neverCached(d.cachedAt) && d.items.isEmpty) {
                  return [
                    const NoticeBanner(
                      icon: Icons.cloud_off_rounded,
                      text: SyncEngine.offlineNoDataMessage,
                    ),
                  ];
                }
                return [
                  if (d.cachedAt != null && !SyncEngine.neverCached(d.cachedAt))
                    NoticeBanner(
                      icon: Icons.cloud_off_rounded,
                      text: 'Tanpa sinyal. Data terakhir ${DateFormat('d MMM HH:mm', 'id_ID').format(d.cachedAt!)}',
                    ),
                  if (d.items.isEmpty)
                    EmptyState(icon: Icons.verified_rounded, title: kosongJudul, message: kosongPesan, accent: Accent.emerald)
                  else
                    for (final x in d.items) _DokumenKartu(item: x, hariIni: hari),
                ];
              },
            ),
          ],
        ),
      ),
    );
  }
}

/// Dokumen kendaraan yang dikemudikan karyawan (STNK, SIM, dan lain-lain).
class DokumenSayaScreen extends StatelessWidget {
  const DokumenSayaScreen({super.key, this.hariIni});
  final DateTime? hariIni;
  @override
  Widget build(BuildContext context) => _DokumenListScreen(
    judul: 'Dokumen kendaraan saya',
    provider: dokumenSayaProvider,
    kosongJudul: 'Belum ada dokumen',
    kosongPesan: 'Dokumen kendaraan yang Anda kemudikan akan tampil di sini.',
    hariIni: hariIni,
  );
}

/// Untuk HSE dan Operational Manager: dokumen kantor yang akan habis. Hanya baca.
class DokumenKantorScreen extends StatelessWidget {
  const DokumenKantorScreen({super.key, this.hariIni});
  final DateTime? hariIni;
  @override
  Widget build(BuildContext context) => _DokumenListScreen(
    judul: 'Dokumen akan habis',
    provider: dokumenKantorProvider,
    kosongJudul: 'Tidak ada yang akan habis',
    kosongPesan: 'Semua dokumen kendaraan masih berlaku lebih dari 30 hari.',
    hariIni: hariIni,
  );
}
