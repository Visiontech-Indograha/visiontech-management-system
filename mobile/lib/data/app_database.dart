import 'dart:io';

import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

part 'app_database.g.dart';

/// Antrian tulis offline: tiap baris adalah satu operasi (create/update) yang
/// menunggu dikirim ke `POST .../sync` begitu online. [payloadJson] berisi
/// JSON persis sesuai skema per-entitas di
/// docs/requirements/MOBILE_SYNC_CONTRACT.md backend.
@DataClassName('PendingSyncRow')
class PendingSyncOperations extends Table {
  IntColumn get id => integer().autoIncrement()();

  /// 'absence' | 'leave' | 'progress_report' | 'vehicle_booking' | 'tool_borrow'
  TextColumn get entityType => text()();
  TextColumn get payloadJson => text()();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();

  /// Berapa kali pengiriman baris ini sudah dicoba, dan pesan gagal terakhir.
  /// Kedua kolom ini sudah ada di skema sejak awal tapi TIDAK PERNAH ditulis --
  /// akibatnya tidak ada cara membedakan "baru gagal sekali karena sinyal" dari
  /// "gagal terus karena datanya memang ditolak".
  IntColumn get attemptCount => integer().withDefault(const Constant(0))();
  TextColumn get lastError => text().nullable()();

  /// Berhenti dicoba otomatis: entah ditolak server secara permanen (4xx) atau
  /// sudah melewati batas percobaan. Barisnya SENGAJA tidak dihapus supaya
  /// datanya tidak hilang & user bisa melihat alasannya lalu memutuskan sendiri
  /// (coba lagi / hapus) di layar Antrian Sinkronisasi.
  BoolColumn get deadLetter => boolean().withDefault(const Constant(false))();
}

/// Cache hasil delta-pull terakhir per grup sinkronisasi (attendance/
/// fieldwork/logbook), supaya riwayat tetap bisa dilihat saat offline.
/// [dataJson] menyimpan array JSON mentah dari respons pull.
@DataClassName('CachedSyncGroupRow')
class CachedSyncGroups extends Table {
  TextColumn get syncGroup => text()();
  TextColumn get dataJson => text()();
  DateTimeColumn get lastSyncedAt => dateTime()();

  @override
  Set<Column> get primaryKey => {syncGroup};
}

/// Foto (sudah di-watermark) yang gagal diupload saat entitas induknya
/// dibuat -- entity id SUDAH diketahui client-side (UUID dibuat sebelum
/// submit, lihat pola `const Uuid().v4()` di tiap form), jadi [endpoint]
/// sudah lengkap berisi id tsb dan tidak perlu kolom entityId terpisah.
/// Di-retry lewat SyncEngine.uploadPendingPhotos() tiap kali syncAll() jalan.
@DataClassName('PendingAttachmentRow')
class PendingAttachments extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get endpoint => text()();
  TextColumn get localFilePath => text()();
  TextColumn get label => text()();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();
  IntColumn get attemptCount => integer().withDefault(const Constant(0))();
  TextColumn get lastError => text().nullable()();
  BoolColumn get deadLetter => boolean().withDefault(const Constant(false))();
}

@DriftDatabase(
  tables: [PendingSyncOperations, CachedSyncGroups, PendingAttachments],
)
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(_openConnection());

  AppDatabase.forTesting(super.executor);

  @override
  int get schemaVersion => 3;

  /// Tidak memakai destructiveFallback: antrian offline yang belum terkirim
  /// TIDAK BOLEH hilang hanya karena aplikasi diperbarui. Setiap kenaikan
  /// versi wajib punya cabangnya sendiri di sini.
  @override
  MigrationStrategy get migration => MigrationStrategy(
    onCreate: (m) => m.createAll(),
    onUpgrade: (m, from, to) async {
      if (from < 2) {
        await m.createTable(pendingAttachments);
      }
      if (from < 3) {
        await m.addColumn(
          pendingSyncOperations,
          pendingSyncOperations.deadLetter,
        );
        await m.addColumn(pendingAttachments, pendingAttachments.lastError);
        await m.addColumn(pendingAttachments, pendingAttachments.deadLetter);
      }
    },
  );

  /// Dipanggil saat user logout MANUAL. Tanpa ini, antrian milik user
  /// sebelumnya akan tersinkron atas nama user berikutnya yang login di HP yang
  /// sama -- server selalu menimpa employee_id dari token pengirim.
  Future<void> wipeAllLocalData() async {
    await delete(pendingSyncOperations).go();
    await delete(pendingAttachments).go();
    await delete(cachedSyncGroups).go();
  }
}

LazyDatabase _openConnection() {
  return LazyDatabase(() async {
    final dbFolder = await getApplicationDocumentsDirectory();
    final file = File(p.join(dbFolder.path, 'vms_mobile.sqlite'));
    return NativeDatabase.createInBackground(file);
  });
}
