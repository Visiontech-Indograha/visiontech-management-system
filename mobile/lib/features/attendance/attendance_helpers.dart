part of 'attendance_screen.dart';

/// Jam sekarang di WIB (UTC+7, aturan jam absen server), bukan zona waktu perangkat.
int _wibHour(DateTime now) => now.toUtc().add(const Duration(hours: 7)).hour;

int _wibMinutes(DateTime now) {
  final w = now.toUtc().add(const Duration(hours: 7));
  return w.hour * 60 + w.minute;
}

/// Build development (`VMS_DEVELOPMENT`, juga `--dart-define=VMS_DEVELOPMENT=true`) boleh melewati gerbang jam
/// absen masuk 06:45 di aplikasi bila `VMS_SKIP_ATTENDANCE_HOURS=true`. Build lain selalu dibatasi, flag diabaikan.
const _devBuildFlag = bool.fromEnvironment('VMS_DEVELOPMENT');
const _skipHoursFlag = bool.fromEnvironment('VMS_SKIP_ATTENDANCE_HOURS');

bool attendanceHoursSkipped({bool devBuild = _devBuildFlag, bool skipFlag = _skipHoursFlag}) => devBuild && skipFlag;

/// Pesan jam buka absen sebagai dialog (bukan snackbar yang cepat hilang); tombol OK menutupnya.
Future<void> tampilkanJamBukaAbsen(BuildContext context) {
  return showDialog<void>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: const Text('Absensi belum dibuka'),
      content: const Text('Absensi masuk baru dibuka mulai pukul 06:45 WIB.'),
      actions: [
        TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('OK')),
      ],
    ),
  );
}

/// Layar singkat sebelum kamera swafoto absen. true bila pengguna menekan Lanjut.
Future<bool> konfirmasiSwafoto(BuildContext context) async {
  final ok = await showDialog<bool>(
    context: context,
    barrierDismissible: false,
    builder: (ctx) => AlertDialog(
      title: const Text('Swafoto'),
      content: const Text('Swafoto wajib. Pastikan hanya wajah Anda di depan kamera.'),
      actions: [
        OutlinedButton(
          style: OutlinedButton.styleFrom(minimumSize: const Size(110, 48)),
          onPressed: () => Navigator.pop(ctx, false),
          child: const Text('Batal'),
        ),
        FilledButton(
          style: FilledButton.styleFrom(minimumSize: const Size(110, 48)),
          onPressed: () => Navigator.pop(ctx, true),
          child: const Text('Lanjut'),
        ),
      ],
    ),
  );
  return ok == true;
}

/// Jam untuk aturan jam absen (07.00 masuk, 19.00 batas pulang). Uji membekukannya agar tidak bergantung jam CI.
DateTime Function() attendanceClock = DateTime.now;


/// Kartu "Menunggu tindakan Anda": hanya baris berisi (>0); yang punya layar di HP bisa diketuk.
class _QueueSummaryCard extends StatelessWidget {
  const _QueueSummaryCard({required this.summary, required this.onReturn});

  final Map<String, int> summary;

  /// Dipanggil setelah kembali dari layar tujuan, agar angka tidak basi.
  final Future<void> Function() onReturn;

  static const _rows = <(String, String, String?)>[
    ('leaves_to_review', 'Cuti menunggu keputusan', '/leaves'),
    ('mess_to_review', 'Pengajuan mess menunggu', '/mess'),
    ('loan_requests_to_review', 'Pengajuan pinjam aset menunggu', '/assets'),
    ('attendance_to_review', 'Absensi perlu diperiksa', null),
    ('overtime_to_review', 'Lembur menunggu persetujuan', '/overtime'),
    ('corrections_to_review', 'Koreksi laporan harian menunggu', null),
    ('my_leaves_pending', 'Cuti saya belum diputuskan', '/leaves'),
  ];

  @override
  Widget build(BuildContext context) {
    final rows = [for (final r in _rows) if ((summary[r.$1] ?? 0) > 0) r];
    if (rows.isEmpty) return const SizedBox.shrink();
    return Card(
      margin: const EdgeInsets.only(top: 16),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Menunggu tindakan Anda', style: Theme.of(context).textTheme.titleSmall),
            for (final r in rows)
              ListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                title: Text(r.$2),
                trailing: Badge(label: Text('${summary[r.$1]}')),
                onTap: r.$3 == null
                    ? null
                    : () async {
                        await context.push(r.$3!);
                        await onReturn();
                      },
              ),
          ],
        ),
      ),
    );
  }
}
