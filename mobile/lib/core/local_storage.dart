import 'dart:io';

import 'package:intl/intl.dart';
import 'package:path_provider/path_provider.dart';

/// Jenis berkas lokal → subfolder di dalam folder `Visiontech` (R-16).
enum LocalFileKind {
  selfie('Swafoto Absensi', 'swafoto'),
  dailyReport('Foto Laporan Harian', 'laporan'),
  incident('Foto Insiden', 'insiden'),
  other('Lainnya', 'berkas');

  const LocalFileKind(this.folder, this.prefix);

  /// Nama subfolder yang terlihat di pengelola berkas.
  final String folder;

  /// Awalan nama berkas.
  final String prefix;
}

/// Folder penyimpanan lokal aplikasi saat offline/antrean sinkron (R-16):
/// `…/Android/data/<paket>/files/Visiontech/<Jenis>/`.
///
/// Sengaja memakai penyimpanan KHUSUS APLIKASI (bukan galeri publik): swafoto & foto berkoordinat
/// adalah data pribadi karyawan, tidak boleh terbaca aplikasi lain; tidak perlu izin penyimpanan,
/// dan terhapus bersama aplikasi. Bila penyimpanan eksternal tidak tersedia → folder dokumen aplikasi.
Future<Directory> visiontechFolder(LocalFileKind kind) async {
  final base =
      (Platform.isAndroid ? await getExternalStorageDirectory() : null) ??
      await getApplicationDocumentsDirectory();
  final dir = Directory(
    '${base.path}${Platform.pathSeparator}Visiontech${Platform.pathSeparator}${kind.folder}',
  );
  await dir.create(recursive: true);
  return dir;
}

/// Berkas baru bernama rapi: `laporan_20260926_184512_123.jpg`.
Future<File> newLocalFile(
  LocalFileKind kind, {
  String extension = 'jpg',
}) async {
  final dir = await visiontechFolder(kind);
  final now = DateTime.now();
  final stamp =
      '${DateFormat('yyyyMMdd_HHmmss').format(now)}_${now.millisecond.toString().padLeft(3, '0')}';
  return File(
    '${dir.path}${Platform.pathSeparator}${kind.prefix}_$stamp.$extension',
  );
}
