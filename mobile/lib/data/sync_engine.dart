import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:drift/drift.dart';
import 'package:uuid/uuid.dart';

import '../core/api_client.dart';
import '../core/device_id.dart';
import 'app_database.dart';
import 'offline_attendance.dart';
import 'vms_api.dart';

class SyncSummary {
  const SyncSummary({required this.pushErrors, required this.pullErrors});
  final List<String> pushErrors;
  final List<String> pullErrors;
  bool get hasErrors => pushErrors.isNotEmpty || pullErrors.isNotEmpty;
}

/// Jenis operasi yang boleh dikirim luring (dok 02 A-08; backend `OFFLINE_ALLOWED`).
/// Absensi, penerbitan & persetujuan wajib daring.
class OfflineOp {
  static const dailyReportSave = 'DAILY_REPORT_SAVE';
  static const dailyReportSubmit = 'DAILY_REPORT_SUBMIT';
  static const taskToggle = 'TASK_TOGGLE';
  static const incidentReport = 'INCIDENT_REPORT';
  static const overtimeReport = 'OVERTIME_REPORT';

  static const labels = {
    dailyReportSave: 'Simpan laporan harian',
    dailyReportSubmit: 'Kirim laporan harian',
    taskToggle: 'Centang tugas',
    incidentReport: 'Laporan insiden',
    overtimeReport: 'Laporan lembur',
    OfflineAttendance.entityType: 'Absensi luring',
  };
}

/// Mesin sinkronisasi luring (M12). Setiap aksi lapangan dicatat dulu di antrean
/// lokal (`PendingSyncOperations`) dengan `client_op_id` unik, lalu dikirim lewat
/// `POST /sync/operations` — server idempoten per `client_op_id`, jadi kirim ulang
/// setelah sinyal putus tidak menggandakan data. Foto bukti disimpan sebagai path
/// lokal (`_local_files`) dan diunggah tepat sebelum operasinya dikirim.
class SyncEngine {
  SyncEngine({
    required ApiClient apiClient,
    required AppDatabase db,
    required DeviceIdProvider deviceId,
  }) : _api = VmsApi(apiClient),
       _db = db, // ignore: prefer_initializing_formals
       _deviceId = deviceId {
    // ignore: prefer_initializing_formals
    offlineAttendance = OfflineAttendance(
      db: db,
      api: _api,
      deviceId: deviceId,
    );
  }

  /// R-34: absen lapangan luring — disimpan bertanda tangan, dikirim otomatis saat online.
  late final OfflineAttendance offlineAttendance;

  final VmsApi _api;
  final AppDatabase _db;
  final DeviceIdProvider _deviceId;

  static const _uuid = Uuid();
  static const _localFiles = '_local_files';

  VmsApi get api => _api;

  // --- Antrean -------------------------------------------------------------

  Future<int> _enqueue(
    String opType,
    Map<String, dynamic> payload,
    List<String> localFiles,
  ) {
    final record = {
      'client_op_id': _uuid.v4(),
      'op_type': opType,
      'payload': {
        ...payload,
        if (localFiles.isNotEmpty) _localFiles: localFiles,
      },
      'client_created_at': DateTime.now().toUtc().toIso8601String(),
    };
    return _db
        .into(_db.pendingSyncOperations)
        .insert(
          PendingSyncOperationsCompanion.insert(
            entityType: opType,
            payloadJson: jsonEncode(record),
          ),
        );
  }

  /// Catat operasi lalu langsung coba kirim. Mengembalikan `true` bila sudah
  /// diterapkan server, `false` bila masih menunggu sinyal. Penolakan server
  /// dilempar sebagai [SyncRejectedException] (operasinya tetap tersimpan di
  /// "Perlu perhatian").
  Future<bool> submit(
    String opType,
    Map<String, dynamic> payload, {
    List<String> localFiles = const [],
  }) async {
    final id = await _enqueue(opType, payload, localFiles);
    try {
      await _push();
    } on DioException catch (e) {
      if (!isNetworkFailure(e)) rethrow;
    }
    final row = await (_db.select(
      _db.pendingSyncOperations,
    )..where((t) => t.id.equals(id))).getSingleOrNull();
    if (row == null) return true;
    if (row.deadLetter) {
      throw SyncRejectedException(row.lastError ?? 'Ditolak server.');
    }
    return false;
  }

  Future<void> _push() async {
    // Absen luring dikirim lebih dulu lewat endpoint-nya sendiri (bertanda tangan).
    await offlineAttendance.push();
    final rows =
        await (_db.select(_db.pendingSyncOperations)
              ..where(
                (t) =>
                    t.deadLetter.equals(false) &
                    t.entityType.equals(OfflineAttendance.entityType).not(),
              )
              ..orderBy([(t) => OrderingTerm.asc(t.id)]))
            .get();
    if (rows.isEmpty) return;

    final ready = <int, Map<String, dynamic>>{};
    for (final row in rows) {
      final record = Map<String, dynamic>.from(
        jsonDecode(row.payloadJson) as Map,
      );
      final payload = Map<String, dynamic>.from(record['payload'] as Map);
      final files = List<String>.from(
        (payload[_localFiles] as List?) ?? const [],
      );
      if (files.isNotEmpty) {
        try {
          final ids = List<String>.from(
            (payload['evidence_file_ids'] as List?) ?? const [],
          );
          for (final path in files) {
            ids.add(await _api.uploadFile(File(path)));
          }
          payload
            ..remove(_localFiles)
            ..['evidence_file_ids'] = ids;
          record['payload'] = payload;
          await (_db.update(
            _db.pendingSyncOperations,
          )..where((t) => t.id.equals(row.id))).write(
            PendingSyncOperationsCompanion(
              payloadJson: Value(jsonEncode(record)),
            ),
          );
        } on DioException catch (e) {
          if (isNetworkFailure(e)) {
            break; // urutan dijaga: berhenti di sini, coba lagi nanti
          }
          await _markDead(row.id, 'Foto gagal diunggah: ${_describe(e)}');
          continue;
        } on FileSystemException {
          await _markDead(row.id, 'Foto bukti tidak ditemukan di HP.');
          continue;
        }
      }
      ready[row.id] = record;
    }
    if (ready.isEmpty) return;

    final byClientId = {
      for (final e in ready.entries) e.value['client_op_id'] as String: e.key,
    };
    final results = await _api.syncOperations(
      await _deviceId.getClientId(),
      ready.values.toList(),
    );
    for (final r in results) {
      final rowId = byClientId[r['client_op_id']];
      if (rowId == null) continue;
      switch (r['status']) {
        case 'APPLIED':
          await (_db.delete(
            _db.pendingSyncOperations,
          )..where((t) => t.id.equals(rowId))).go();
        case 'REJECTED' || 'CONFLICT':
          await _markDead(
            rowId,
            (r['error_message'] as String?) ?? 'Ditolak server.',
          );
        default:
          await (_db.update(
            _db.pendingSyncOperations,
          )..where((t) => t.id.equals(rowId))).write(
            PendingSyncOperationsCompanion(
              attemptCount: Value(
                rows.firstWhere((x) => x.id == rowId).attemptCount + 1,
              ),
            ),
          );
      }
    }
  }

  Future<void> _markDead(int id, String error) =>
      (_db.update(
        _db.pendingSyncOperations,
      )..where((t) => t.id.equals(id))).write(
        PendingSyncOperationsCompanion(
          deadLetter: const Value(true),
          lastError: Value(error),
        ),
      );

  static String _describe(DioException e) {
    final data = e.response?.data;
    if (data is Map) {
      final detail = data['detail'] ?? data['message'];
      if (detail is Map && detail['message'] != null) {
        return detail['message'].toString();
      }
      if (detail != null) return detail.toString();
    }
    return 'HTTP ${e.response?.statusCode ?? '-'}';
  }

  // --- Cache baca-luring ---------------------------------------------------

  Future<void> cachePut(String key, Object data) => _db
      .into(_db.cachedSyncGroups)
      .insertOnConflictUpdate(
        CachedSyncGroupsCompanion.insert(
          syncGroup: key,
          dataJson: jsonEncode(data),
          lastSyncedAt: DateTime.now(),
        ),
      );

  Future<({dynamic data, DateTime? at})> cacheGet(String key) async {
    final row = await (_db.select(
      _db.cachedSyncGroups,
    )..where((t) => t.syncGroup.equals(key))).getSingleOrNull();
    return (
      data: row == null ? null : jsonDecode(row.dataJson),
      at: row?.lastSyncedAt,
    );
  }

  /// `fetchList` luring tanpa cache memberi `cachedAt` = epoch 0: itu BUKAN data tersimpan.
  static bool neverCached(DateTime? cachedAt) =>
      cachedAt != null && cachedAt.millisecondsSinceEpoch == 0;

  static const offlineNoDataMessage =
      'Tidak ada koneksi dan belum ada data tersimpan di HP ini. '
      'Sambungkan internet untuk memuat pertama kali.';

  /// Ambil dari server lalu simpan ke cache; bila luring kembalikan isi cache.
  Future<({List<Map<String, dynamic>> items, DateTime? cachedAt})> fetchList(
    String key,
    Future<List<Map<String, dynamic>>> Function() fetch,
  ) async {
    try {
      final items = await fetch();
      await cachePut(key, items);
      return (items: items, cachedAt: null);
    } on DioException catch (e) {
      if (!isNetworkFailure(e)) rethrow;
      final cached = await cacheGet(key);
      final items = ((cached.data as List?) ?? const [])
          .map((x) => Map<String, dynamic>.from(x as Map))
          .toList();
      return (
        items: items,
        cachedAt: cached.at ?? DateTime.fromMillisecondsSinceEpoch(0),
      );
    }
  }

  // --- Dipakai banner, profil & layar antrean -----------------------------

  Future<SyncSummary> syncAll() async {
    final push = <String>[];
    final pull = <String>[];
    try {
      await _push();
    } on DioException catch (e) {
      push.add(isNetworkFailure(e) ? 'Tidak ada koneksi.' : _describe(e));
    }
    try {
      await cachePut('daily_today', await _api.dailyPlans(start: _today(), end: _today()));
    } on DioException catch (e) {
      pull.add(
        isNetworkFailure(e) ? 'Tidak ada koneksi.' : 'Jadwal harian: ${_describe(e)}',
      );
    }
    return SyncSummary(pushErrors: push, pullErrors: pull);
  }

  Future<List<PendingSyncRow>> allPendingOperations() => (_db.select(
    _db.pendingSyncOperations,
  )..orderBy([(t) => OrderingTerm.asc(t.id)])).get();

  Future<List<PendingAttachmentRow>> allPendingAttachments() =>
      _db.select(_db.pendingAttachments).get();

  Future<void> retryOperation(int id) async {
    await (_db.update(
      _db.pendingSyncOperations,
    )..where((t) => t.id.equals(id))).write(
      const PendingSyncOperationsCompanion(
        deadLetter: Value(false),
        lastError: Value(null),
      ),
    );
    await syncAll();
  }

  Future<void> deleteOperation(int id) async {
    final row = await (_db.select(
      _db.pendingSyncOperations,
    )..where((t) => t.id.equals(id))).getSingleOrNull();
    await (_db.delete(
      _db.pendingSyncOperations,
    )..where((t) => t.id.equals(id))).go();
    // Absen luring: swafotonya di folder internal ikut dibuang.
    if (row?.entityType == OfflineAttendance.entityType) {
      final path = (jsonDecode(row!.payloadJson) as Map)['selfie_path'];
      if (path is String) {
        await File(path).delete().catchError((_) => File(path));
      }
    }
  }

  Future<void> retryAttachment(int id) async {}

  Future<void> deleteAttachment(int id) =>
      (_db.delete(_db.pendingAttachments)..where((t) => t.id.equals(id))).go();

  Future<int> pendingOperationCount() async => (await (_db.select(
    _db.pendingSyncOperations,
  )..where((t) => t.deadLetter.equals(false))).get()).length;

  Future<int> deadLetterCount() async => (await (_db.select(
    _db.pendingSyncOperations,
  )..where((t) => t.deadLetter.equals(true))).get()).length;

  Future<int> pendingPhotoCount() async {
    var n = 0;
    for (final row in await (_db.select(
      _db.pendingSyncOperations,
    )..where((t) => t.deadLetter.equals(false))).get()) {
      final record = jsonDecode(row.payloadJson) as Map;
      if (row.entityType == OfflineAttendance.entityType) {
        // Absen luring: payload-nya string bertanda tangan; swafotonya di selfie_path.
        if (record['selfie_path'] != null && record['selfie_file_id'] == null) {
          n++;
        }
        continue;
      }
      final payload = record['payload'] as Map;
      n += ((payload[_localFiles] as List?) ?? const []).length;
    }
    return n;
  }
  static String _today() => DateTime.now().toIso8601String().substring(0, 10);
}

class SyncRejectedException implements Exception {
  SyncRejectedException(this.message);
  final String message;

  @override
  String toString() => message;

}
